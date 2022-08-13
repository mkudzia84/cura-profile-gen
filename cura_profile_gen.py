from ensurepip import version
import os, sys, argparse
import logging
import json
import copy

from typing import Any, List, Dict, NewType, TypeVar, Optional
from unicodedata import name

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('cura-profile-gen')

# File definition
T = TypeVar('T')

#----------------------------------------------------------------------------------------

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

#----------------------------------------------------------------------------------------

@singleton
class CuraSettingsDef:
    """
    Cura settings validator
    """

    def __init__(self):
        self.fdm_printer_def = None
        self.fdm_extruder_def = None

    def load_settings_def(self, cura_path : str):
        def_path = os.path.join(cura_path, 'resources', 'definitions')
        with open(os.path.join(def_path, 'fdmprinter.def.json')) as fdm_printer_def_file:
            self.fdm_printer_def = json.load(fdm_printer_def_file)
        with open(os.path.join(def_path, 'fdmextruder.def.json')) as fdm_extruder_def_file:
            self.fdm_extruder_def = json.load(fdm_extruder_def_file)

    @property
    def version(self) -> int:
        return int(self.fdm_printer_def['metadata']['setting_version'])


    def _validate_def_node(self, setting_def_node : dict, setting_name : str) -> bool:
        if setting_name in setting_def_node:
            return True
        if (children := setting_def_node.get('children')) != None:
            if setting_name in children:
                return True
            for child_def in children.values():
                if self._validate_def_node(child_def, setting_name) == True:
                    return True
        return False

    def validate_printer_setting(self, setting_name : str) -> bool:
        """Validates the setting against the schema in definition"""
        for setting_category in self.fdm_printer_def['settings'].values():
            if self._validate_def_node(setting_category, setting_name) == True:
                return True
        return False
    
    def validate_extruder_setting(self, setting_name : str) -> bool:
        """Validate the setting against the schema in definition"""
        for setting_category in self.fdm_extruder_def["settings"].values():
            if self._validate_def_node(setting_category, setting_name) == True:
                return True
        return False

#----------------------------------------------------------------------------------------
# Errors
class BadRefIdError(Exception):
    """Bad reference in JSON"""
    pass

class InvalidFieldError(Exception):
    """Invalid field in JSON"""
    pass

#----------------------------------------------------------------------------------------

def save_def(file_path, data: Dict[str, str]):
    """ Write the .def.json file"""
    dir_path = os.path.split(file_path)[0]

    if not os.path.exists(dir_path):
        log.warning(f"Creating directory {dir_path}")
        os.makedirs(dir_path)

    with open(file_path, mode='w') as fh:
        json.dump(data, fh, indent=4)

def save_cfg(file_path: str, **kwargs):
    """ Save the CFG file """
    dir_path = os.path.split(file_path)[0]

    if not os.path.exists(dir_path):
        logging.warning(f"Creating directory {dir_path}")
        os.makedirs(dir_path)

    with open(file_path, mode='w') as fh:
        for header, settings in kwargs.items():
            fh.write(f"[{header}]\n")
            for k, v in settings.items():
                fh.write(f"{k} = {v}\n")

#----------------------------------------------------------------------------------------
# Dataclasses corresponding to data in json config file
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase

Settings = NewType('Settings', Dict[str, Any])
Identifiers = NewType('Identifiers', List[str])

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PrinterVariant:
    id : str
    name : str
    inherits : str
    metadata : Settings

    overrides : Settings
    
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Extruder:
    name : str
    overrides : Settings

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass 
class Variant:
    id : str
    toolhead_variant_settings : Settings
    toolhead_variant_limits : Optional[Settings] = None

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Profile:
    id : str
    name : str
    profile_settings : Settings
    compatible_variants : Identifiers
    
    def is_variant_compatible(self, variant_id : str) -> bool:
        """Check if variant is compatible with profile"""
        return variant_id in self.compatible_variants
    
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass 
class Material:
    id : str
    name : str 

    compatible_variants : Optional[Identifiers] = None
    compatible_profiles : Optional[Identifiers] = None

    material_settings : Optional[Settings] = None
    
    def is_profile_compatible(self, profile_id : str) -> bool:
        """Check if profile is compatible with this material"""
        if self.compatible_profiles == None:
            return True
        else:
            return profile_id in self.compatible_profiles
        
    def is_variant_compatible(self, variant_id : str) -> bool:
        """Check if variant is compatible with this material"""
        if self.compatible_variants == None:
            return True
        else:
            return variant_id in self.compatible_variants

@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Configuration:
    printers : List[PrinterVariant]
    extruders : List[Extruder]
    variants : List[Variant]
    profiles : List[Profile]
    materials : List[Material]

    base_quality_definition : str

    def load(path : str):
        with open(path, mode='r') as fd:
            try:
                return Configuration.from_dict(json.load(fd))
            except KeyError as exc:
                raise KeyError(f"JSON document missing the {exc}")
            
    def __post_init__(self):
        # Initialize the lookup tables
        self._printer_variant_lookup = {variant.id : indx for indx, variant in enumerate(self.printers)}
        self._variant_lookup = {variant.id : indx for indx, variant in enumerate(self.variants)}
        self._profile_lookup = {profile.id : indx for indx, profile in enumerate(self.profiles)}
        self._material_lookup = {material.id : indx for indx, material in enumerate(self.materials)}
        
        # Perform validation
        if self.verify_references() == False:
            raise BadRefIdError
        
        if self.verify_fields() == False:
            raise InvalidFieldError
        
    def verify_references(self) -> bool:
        """Perform verification of references"""
        # Valid
        valid = True
                    
        # Verify references in the profiles towards variants
        for profile in self.profiles:
            for variant_ref_id in profile.compatible_variants:
                if variant_ref_id not in self._variant_lookup.keys():
                    log.error(f"Variant '{variant_ref_id}' referenced in profile '{profile.id}' not defined in variants section, configured variants are [{','.join(self._variant_lookup.keys())}]")
                    valid = False
                    
        # Verify references in the materials towards profiles and variants
        for material in self.materials:
            if material.compatible_profiles != None:
                for profile_ref_id in material.compatible_profiles:
                    if profile_ref_id not in self._profile_lookup.keys():
                        log.error(f"Profile '{profile_ref_id}' referenced in material '{material.id}' not defined in profiles section, configured profiles are [{','.join(self._profile_lookup.keys())}]")
                        valid = False
            if material.compatible_variants != None:
                for variant_ref_id in material.compatible_variants:
                    if variant_ref_id not in self._variant_lookup.keys():
                        log.error(f"Variant {variant_ref_id} referenced in material {material.id} not defined in variants section, configured variants are [{','.join(self._variant_lookup.keys())}]")
                        valid = False
        
        return valid
        
    def verify_fields(self) -> bool:
        """Perform verification of the fields against the schema"""
        valid = True
        
        # Validator
        cura_settings_def = CuraSettingsDef()
        
        # First check the Printer section
        for printer_variant in self.printers:
            for setting in printer_variant.overrides.keys():
                if cura_settings_def.validate_printer_setting(setting) == False:
                    log.error(f"Setting '{setting}' in printer {printer_variant.id}/machineVariantSettings section is invalid, compare against the fdmprinter.def.json")
                    valid = False
        
        # Verify the extuder settings
        for extruder in self.extruders:
            for setting in extruder.overrides.keys():
                if cura_settings_def.validate_extruder_setting(setting) == False:
                    log.error(f"Setting '{setting}' in extruder {extruder.id}/overrides section is invalid, compare against the fdmextruder.def.json")
                    valid = False
                    
        # Verify the variants
        for variant in self.variants:
            for setting in variant.toolhead_variant_settings.keys():
                if cura_settings_def.validate_printer_setting(setting) == False:
                    log.error(f"Setting '{setting}' in variant {variant.id}/toolheadVariantSetting section is invalid, compare against the fdmprinter.def.json")
                    valid = False
        
            if variant.toolhead_variant_limits != None:
                for setting in variant.toolhead_variant_limits.keys():
                    if cura_settings_def.validate_printer_setting(setting) == False:
                        log.error(f"Setting '{setting}' in variant {variant.id}/toolheadVariantLimits section is invalid, compare against the fdmprinter.def.json")
                        valid = False
        
        # Verify the profiles
        for profile in self.profiles:
            for setting in profile.profile_settings.keys():
                if cura_settings_def.validate_printer_setting(setting) == False:
                    log.error(f"Setting '{setting}' in profile {profile.id}/profileSettings section is invalid, compare against the fdmprinter.def.json")
                    valid = False
        
        # Verify the materials
        for material in self.materials:
            if material.material_settings != None:
                for setting in material.material_settings.keys():
                    if cura_settings_def.validate_printer_setting(setting) == False:
                        log.error(f"Setting '{setting}' in material {material.id}/materialSetting section is invalid, compare against the fdmprinter.def.json")
                        valid = False
        
        return valid

    #------------------------------------------------------------------------------------

    def save_printer_defs(self, path: str):
        """ Save the printer definition file """
        log.info("Writing printer definition files")
        
        for printer_variant in self.printers:
            extruder_ids = []
            
            # Write printer extruder definition files
            for indx, extruder in enumerate(self.extruders):
                extruder_id = f"{printer_variant.id}_extruder_{indx}"
                def_file_path = os.path.join(path, "extruders", f"{extruder_id}.def.json")
                
                log.info(f"Writing extruder definition for '{extruder_id}' under {def_file_path}")
                         
                save_def(
                    file_path = def_file_path,
                    data = {
                        'version' : 2,
                        'id' : extruder_id,
                        'name' : extruder.name,
                        'inherits' : 'fdmextruder',
                        'metadata' : {
                            'machine' : printer_variant.id,
                            'position' : indx
                        },
                        'overrides' : extruder.overrides
                    }
                )
                
                extruder_ids.append(extruder_id)
            
            # Write printer definition files
            def_file_path = os.path.join(path, "definitions", f"{printer_variant.id}.def.json")
            log.info(f"Writing printer definition for '{printer_variant.id}' under {def_file_path}")
            
            metadata : Dict[str, Any] = copy.copy(printer_variant.metadata)
            metadata.update({
                'machine_extruder_trains' : {indx : extruder_id for indx, extruder_id in enumerate(extruder_ids)},
                'quality_definition' : self.base_quality_definition,
                'has_machine_quality' : True,
                'has_materials' : True,
                'has_variants' : True
            })
            
            save_def(
                file_path = def_file_path,
                data = {
                    'version' : 2,
                    'name' : printer_variant.name,
                    'inherits' : printer_variant.inherits,
                    'metadata' : metadata,
                    'overrides' : printer_variant.overrides
                }
            )
    
    def save_printer_cfgs(self, path: str):
        """ Save the variants/profiles/materials configs"""
    
        cura_config = CuraSettingsDef()
    

        # Variants
        for variant in self.variants:
            variant_path_segment = variant.id.replace(' ', '').replace('-', '_')
            cfg_file_path = os.path.join(path, 'variants', f"{self.base_quality_definition}_{variant_path_segment}.inst.cfg")
            log.info(f"Writing variant config for '{self.base_quality_definition}/{variant.id}' under {cfg_file_path}")
            
            save_cfg(
                file_path = cfg_file_path,
                general = {
                    'version' : 4,
                    'name' : variant.id,
                    'definition' : self.base_quality_definition
                },
                metadata = {
                    'setting_version' : cura_config.version,
                    'type' : 'variant',
                    'hardware_type' : 'nozzle'
                },
                values = variant.toolhead_variant_settings
            )
            
        # Profiles
        log.info(f"Writing global quality profiles for printer '{self.base_quality_definition}'")
        for profile in self.profiles:
            cfg_file_path = os.path.join(path, 'quality', self.base_quality_definition, f"{self.base_quality_definition}_global_{profile.id}.inst.cfg")
            log.info(f"Writing global quality profile config for '{self.base_quality_definition}/{profile.id}' under {cfg_file_path}")
            
            save_cfg(
                file_path = cfg_file_path,
                general = {
                    'version' : 4,
                    'name' : profile.name,
                    'definition' : self.base_quality_definition
                },
                metadata = {
                    'setting_version' : cura_config.version,
                    'type' : 'quality',
                    'quality_type' : profile.id,
                    'global_quality' : True
                },
                values = profile.profile_settings
            )
            
        # Material specific profiles
        log.info(f"Writing material specific quality profiles for printer '{self.base_quality_definition}'")
        for material in self.materials:
            log.info(f"Writing material specific quality profiles for material '{material.name}'")
            
            # Go over each profile
            for profile in self.profiles:
                # Check compatibility
                if material.is_profile_compatible(profile.id) == False:
                    log.info(f"Profile '{profile.id} is not compatible with Material '{material.name}', skipping...")
                    continue
                
                # Go over each variant
                for variant in self.variants:
                    # Check compatibility
                    if profile.is_variant_compatible(variant.id) == False or material.is_variant_compatible(variant.id) == False:
                        log.info(f"Variant '{variant.id}' is not compatible with '{material.name}/{profile.id}' material/profile combo, skipping...")
                        continue
                    
                    overrides = {}
                    if material.material_settings != None:
                        overrides = material.material_settings
                    
                    variant_path_segment = variant.id.replace(' ','').replace('-', '_')
                    cfg_file_path = os.path.join(path, 'quality', self.base_quality_definition, f"{self.base_quality_definition}_{variant_path_segment}_{material.name}_{profile.id}.inst.cfg")
                    
                    save_cfg(
                        file_path = cfg_file_path,
                        general = {
                            'version' : 4,
                            'name' : profile.name,
                            'definition' : self.base_quality_definition
                        },
                        metadata = {
                            'setting_version' : cura_config.version,
                            'type' : 'quality',
                            'quality_type' : profile.id,
                            'material' : material.id,
                            'variant' : variant.id
                        },
                        values = overrides
                    )
                        

def main():
    """ Setup the parser"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--cura-dir", help="Path to Cura installation", required = True)
    parser.add_argument("--output-dir", help="Output directory override")
    parser.add_argument("profile_gen_path", type=str, help="Path to the profile-gen.json file")
    
    settings_ver = None
    deployment_dir = None

    args = parser.parse_args()
    
    if (args.output_dir != None):
        deployment_dir = args.output_dir
    else:
        deployment_dir = os.path.join(args.cura_dir, 'resources')
    
    cura_settings_def = CuraSettingsDef()
    cura_settings_def.load_settings_def(args.cura_dir)
    
    log.info(f"Generating profiles under {deployment_dir}, Cura settings Ver = {cura_settings_def.version}")
    log.info(f"Loading profile settings from {args.profile_gen_path}...")

    try:
        config = Configuration.load(args.profile_gen_path)
        config.save_printer_defs(path = deployment_dir)
        config.save_printer_cfgs(path = deployment_dir)
    except Exception as exc:
        log.error(f"Error loading the profile-gen file...")
        log.exception(exc, exc_info=1, stack_info=False)
        exit(1)


if __name__ == '__main__':
    main()