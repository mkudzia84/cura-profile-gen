import os, sys, argparse
import logging
import json
import copy

from typing import List, Dict, NewType, TypeVar

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('cura-profile-gen')

# File definition
T = TypeVar('T')

class CuraSettingsDef:
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

class Extruder:
    ExtruderId = NewType('ExtruderId', str)

    def __init__(self, id: ExtruderId, name: str, inherits: str, metadata: Dict[str,T], overrides: Dict[str, T]):
        self.id = id
        self.name = name
        self.inherits = inherits
        self.metadata = metadata
        self.overrides = overrides

class Variant:
    VariantId = NewType('VariantId', str)

    def __init__(self, id: VariantId, overrides: Dict[str, T], inherits = None):
        self.id = id
        self.inherits = inherits
        if inherits != None:
            self.overrides = inherits.overrides.copy()
            self.overrides.update(overrides)
        else:
            self.overrides = overrides

    def is_typeof(self, variant_id: VariantId):
        """ Check if the Variant is type of variant_id, uses inheritance """
        if self.inherits != None:
            return self.id == variant_id or self.inherits.is_typeof(variant_id)
        else:
            return self.id == variant_id

class Profile:
    ProfileId = NewType('ProfileId', str)

    class Variant:
        def __init__(self, variant_id: Variant.VariantId, overrides: Dict[str, T]):
            self.variant_id = variant_id
            self.overrides = overrides


    def __init__(self, id: ProfileId, name: str, overrides: Dict[str, T]):
        self.id = id
        self.name = name
        self.overrides = overrides
        self.compatible_variants: Dict[Variant.VariantId, Variant] = {}

    def is_variant_compatible(self, variant: Variant) -> bool:
        """ Check if the variant is compatible with the profile """
        for compatible_variant_id in self.compatible_variants.keys():
            if variant.is_typeof(compatible_variant_id):
                return True
        return False

class Material:
    MaterialId = NewType('MaterialId', str)

    class Overrides:
        def __init__(self, variant_ids: List[Variant.VariantId], profile_ids: List[Profile.ProfileId], settings: Dict[str, T]):
            self.variant_ids = variant_ids
            self.profile_ids = profile_ids
            self.settings = settings

        def is_match(self, profile: Profile, variant: Variant) -> bool:
            """ Does the override apply to Profile/Variant """
            if self.profile_ids != None and profile.id not in self.profile_ids:
                return False
            if self.variant_ids != None:
                is_found = False
                for variant_id in self.variant_ids:
                    if variant.is_typeof(variant_id) == True:
                        is_found = True
                        break
                return is_found
            return True

    def __init__(self, id: MaterialId, name: str):
        self.id = id
        self.name = name
        self.profile_filter: List[Profile.ProfileId] = None
        self.variant_filter: List[Variant.VariantId] = None
        self.overrides: List[Material.Overrides] = []

    def is_profile_compatible(self, profile: Profile) -> bool:
        """ Check if profile is compatible with the Material"""
        if self.profile_filter != None and len(self.profile_filter) > 0:
            return profile.id in self.profile_filter
        return True

    def is_variant_compatible(self, variant: Variant) -> bool:
        """ Check if the variant or variant derivatives are compatible with the Material """
        if self.variant_filter != None and len(self.variant_filter) > 0:
            for variant_id in self.variant_filter:
                if variant.is_typeof(variant_id) == True:
                    return True
            # It's not
            return False
        else:
            return True

class Printer:
    PrinterId = NewType('PrinterId', str)

    def __init__(self, printer_id: PrinterId, name: str, inherits: str, metadata: Dict[str, T], overrides: Dict[str, T]):
        self.id = printer_id
        self.name = name
        self.inherits = inherits
        self.metadata = metadata

        # Update the metadata
        self.metadata.update({
            'has_materials' : True,
			'has_variants' : True,
			'has_machine_quality' : True,
            'machine_extruder_trains' : {}
        })

        self.overrides = overrides

        self.extruders : List[Extruder] = []
        self.variants : Dict[str, Variant] = {}
        self.profiles : Dict[str, Profile] = {}
        self.materials : Dict[str, Material] = {}

    def add_extruder(self, extruder: Extruder):
        for loaded_extruder in self.extruders:
            if extruder.id == loaded_extruder.id:
                raise Exception(f"Extruder '{extruder.id} definition already loaded, aborting...")
        # Append metadata
        self.metadata['machine_extruder_trains'][str(len(self.extruders))] = extruder.id
        self.extruders.append(extruder)

    def add_variant(self, variant: Variant):
        if variant.id in self.variants:
            raise Exception(f"Attempting to add a duplicate Variant '{variant.id}', aborting...")
        self.variants[variant.id] = variant

    def add_profile(self, profile: Profile):
        if profile.id in self.profiles:
            raise Exception(f"Attempting to add duplicate Profile '{profile.id}', aborting...")
        for variant_id in profile.compatible_variants:
            if variant_id not in self.variants:
                raise Exception(f"Profile '{profile.id}' references an invalid '{variant_id}' Variant")

        self.profiles[profile.id] = profile

    def add_material(self, material: Material):
        if material.id in self.materials:
            raise Exception(f"Attempting to add duplicate Material '{material.id}', aborting...")
        # Verify the contents
        if material.profile_filter != None:
            for profile_id in material.profile_filter:
                if profile_id not in self.profiles:
                    raise Exception(f"Profile '{profile_id} reference in profile filter of Material '{material.id}' is invalid")
        if material.variant_filter != None:
            for variant_id in material.variant_filter:
                if variant_id not in self.variants:
                    raise Exception(f"Variant '{variant_id}'' reference in variant filter of Material '{material.id}' is invalid")

        # Verify the overrides
        if material.overrides != None:
            for override in material.overrides:
                if override.profile_ids != None:
                    for profile_id in override.profile_ids:
                        if profile_id not in self.profiles:
                            raise Exception(f"Profile '{profile_id}' reference in one of the overrides of Material '{material.id}' is invalid")
                if override.variant_ids != None:
                    for variant_id in override.variant_ids:
                        if variant_id not in self.variants:
                            raise Exception(f"Variant '{variant_id}' reference in one of the overrides of Material '{material.id}' is invalid")

        self.materials[material.id] = material

         
    def save_def(self, file_path, data: Dict[str,str]):
        log.info(f"Writing definition file to {file_path}")

        dir_path = os.path.split(file_path)[0]

        if not os.path.exists(dir_path):
            log.warning(f"Creating directory {dir_path}")
            os.makedirs(dir_path)

        with open(file_path, mode='w') as fh:
            json.dump(data, fh, indent=4)

    def save_printer_def(self, path: str):
        """ Save the printer definition file """
        log.info("Writing printer definition files")
        self.save_def(
            file_path = os.path.join(path, f"{self.id}.def.json"),
            data = {
                'version' : 2,
                'name' : self.name,
                'inherits' : self.inherits,
                'metadata' : self.metadata,
                'overrides' : self.overrides
            })

    def save_extruder_def(self, path: str):
        """ Save the extruder definition files """
        log.info("Writing Extruder definition files")
        for extruder in self.extruders:
            self.save_def(
                file_path = os.path.join(path, f"{extruder.id}.def.json"),
                data = {
                    'version' : 2,
                    'id' : extruder.id,
                    'name' : extruder.name,
                    'inherits' : extruder.inherits,
                    'metadata' : extruder.metadata,
                    'overrides' : extruder.overrides
                })

    def save_cfg(self, file_path: str, **kwargs):
        """ Save the CFG file """
        log.info(f"Writing CFG file to {file_path}")

        dir_path = os.path.split(file_path)[0]

        if not os.path.exists(dir_path):
            logging.warning(f"Creating directory {dir_path}")
            os.makedirs(dir_path)

        with open(file_path, mode='w') as fh:
            for header, settings in kwargs.items():
                fh.write(f"[{header}]\n")
                for k, v in settings.items():
                    fh.write(f"{k} = {v}\n")
            
    def save_variants_cfg(self, path : str, cura_settings_def : CuraSettingsDef):
        """ Saving variants config """
        log.info(f"Writing variants config files")

        for variant in self.variants.values():
            self.save_cfg(
                file_path = os.path.join(path, f"{self.id}_{variant.id}.inst.cfg"),
                general = {
                    'version' : 4,
                    'name' : variant.id,
                    'definition' : self.id
                },
                metadata = {
                    'setting_version' : cura_settings_def.version,
                    'type' : 'variant',
                    'hardware_type' : 'nozzle'
                },
                values = variant.overrides
            )

    def save_profiles_cfg(self, path : str, cura_settings_def : CuraSettingsDef):
        """ Saving profiles config """
        log.info(f"Writing profiles config files")

        for profile in self.profiles.values():
            log.info(f"Writing global quality config file for profile {profile.id}")
            self.save_cfg(
                file_path = os.path.join(path, self.id, f"{self.id}_global_{profile.id}.inst.cfg"),
                general = {
                    'version' : 4,
                    'name' : profile.name,
                    'definition' : self.id
                },
                metadata = {
                    'setting_version' : cura_settings_def.version,
                    'type' : 'quality',
                    'quality_type' : profile.id,
                    'global_quality' : True
                },
                values = profile.overrides
            )

    def save_material_cfg(self, path : str, cura_settings_def : CuraSettingsDef):
        """ Saving materials config """
        log.info(f"Writing material config files")

        for material in self.materials.values():
            log.info(f"Writing quality profiles for material {material.name}")

            # Go over each profile
            for profile in self.profiles.values():
                # Check if variant is supported
                if material.is_profile_compatible(profile) == False:
                    log.info(f"Profile '{profile.id}' is not supported by Material '{material.name}', skipping profile")
                    continue

                # Go over each variant for the profile
                for variant in self.variants.values():
                    # check if the variant is supported by profile
                    if profile.is_variant_compatible(variant) == False or material.is_variant_compatible(variant) == False:
                        log.info(f"Variant '{variant.id}' is not supported for Material/Profile '{material.name}/{profile.id}' combo, skipping")
                        continue

                    # Apply overrides from the profiles
                    overrides = {}
                    for compatible_variants in profile.compatible_variants.values():
                        if variant.is_typeof(compatible_variants.variant_id):
                            log.debug(f"Applying overrides from for Profile/Variant '{profile.id}/{compatible_variants.variant_id}'")
                            overrides.update(compatible_variants.overrides)

                    # Apply overrides from material overrides
                    for material_override in material.overrides:
                        if material_override.is_match(profile, variant):
                            overrides.update(material_override.settings)

                    log.debug(f"{material.name}/{profile.id}/{variant.id} setting overrides:")
                    for k, v in overrides.items():
                        log.debug(f"{k} = {v}")

                    self.save_cfg(
                        file_path = os.path.join(path, self.id, material.name, f"{self.id}_{variant.id}_{material.name}_{profile.id}.inst.cfg"),
                        general = {
                            'version' : 4,
                            'name' : profile.name,
                            'definition' : self.id
                        },
                        metadata = {
                            'setting_version' : cura_settings_def.version,
                            'type' : 'quality',
                            'quality_type' : profile.id,
                            'material' : material.id,
                            'variant' : variant.id
                        },
                        values = overrides
                    )

# Parse JSON
def load_printer_profile(path: str, settings_validator : CuraSettingsDef):
    """Load the json file"""

    def validate_printer_overrides(overrides : dict):
        for override in overrides.keys():
            if settings_validator.validate_printer_setting(setting_name=override) == False:
                raise Exception(f"Setting {override} is invalid, please check the fdmprinter.def.json for reference")

    def validate_extruder_overrides(overrides : dict):
        for override in overrides.keys():
            if settings_validator.validate_extruder_setting(setting_name=override) == False:
                raise Exception(f"Setting {override} is invalid, please check the fdmextruder.def.json for reference")

    with open(path) as fh:
        json_def = json.load(fh)

        # Load printer
        if (printer_json := json_def.get('printer')) == None:
            raise Exception(f"File {path} is missing the 'printer' section")
        if (printer_id := printer_json.get('id')) == None:
            raise Exception(f"File {path} is missing the 'printer/id' field")
        if (printer_name := printer_json.get('name')) == None:
            raise Exception(f"File {path} printer '{printer_id}' is missing the 'name' field")
        if (printer_inherits := printer_json.get('inherits')) == None:
            raise Exception(f"File {path} printer '{printer_id}' is missing the 'inherits' field")
        if (printer_metadata := printer_json.get('metadata')) == None:
            raise Exception(f"File {path} printer '{printer_id}' is missing the 'metadata' field")
        if (printer_overrides := printer_json.get('overrides')) == None:
            raise Exception(f"File {path} printer '{printer_id}' is missing the 'overrides' field")

        # Validate the overrides
        validate_printer_overrides(printer_overrides)

        printer = Printer(
            printer_id = printer_id, 
            name = printer_name,
            inherits = printer_inherits,
            metadata = printer_metadata,
            overrides = printer_overrides)

        # Load extruders
        if (extruders_json := json_def.get('extruders')) == None:
            raise Exception(f"File {path} is missing the 'extruders' section")
        if len(extruders_json) == 0:
            raise Exception(f"File {path} has no extruder definitions")

        for extruder_json in extruders_json:
            if (extruder_id := extruder_json.get('id')) == None:
                raise Exception(f"File {path} is missing 'extruders/id' field")
            if (extruder_name := extruder_json.get('name')) == None:
                raise Exception(f"File {path} extruder '{extruder_id}' is missing the 'name' field")
            if (extruder_inherits := extruder_json.get('inherits')) == None:
                raise Exception(f"File {path} extruder '{extruder_id}' is missing the 'inherits' field")
            if (extruder_metadata := extruder_json.get('metadata')) == None:
                raise Exception(f"File {path} extruder '{extruder_id}' is missing the 'metadata' section")
            if (extruder_overrides := extruder_json.get('overrides')) == None:
                raise Exception(f"File {path} extruder '{extruder_id}' is missing the 'overrides' section")
            
            # validate the overrides
            validate_extruder_overrides(extruder_overrides)

            printer.add_extruder(extruder = Extruder(
                id = extruder_id,
                name = extruder_name,
                inherits = extruder_inherits,
                metadata = extruder_metadata,
                overrides = extruder_overrides
            ))

        # Load variants
        if (variants_json := json_def.get('variants')) == None:
            raise Exception(f"File {path} is missing the 'variants' section")
        if len(variants_json) == 0:
            raise Exception(f"File {path} is missing the 'variants' definitions")

        for variant_json in variants_json:
            if (variant_id := variant_json.get('id')) == None:
                raise Exception(f"File {path} is missing the 'variants/id' field")
            variant_overrides = variant_json.get('overrides', {})
            parent_variant_id = variant_json.get('inherits')
            if parent_variant_id != None and parent_variant_id not in printer.variants:
                raise Exception(f"File {path} variant '{variant_id} references an undefined parent variant '{parent_variant_id}, parent variant definition must preceed the children")
            parent_variant = printer.variants[parent_variant_id] if parent_variant_id != None else None

            validate_printer_overrides(variant_overrides)

            printer.add_variant(variant = Variant(
                id = variant_id,
                overrides = variant_overrides,
                inherits = parent_variant
            ))

        # Load profiles
        if (profiles_json := json_def.get('profiles')) == None:
            raise Exception(f"File {path} is missing the 'profiles' section")
        if len(profiles_json) == 0:
            raise Exception(f"File {path} has no profile definitions")

        for profile_json in profiles_json:
            if (profile_id := profile_json.get('id')) == None:
                raise Exception(f"File {path} is missing the 'profiles/id' field")
            if (profile_name := profile_json.get('name')) == None:
                raise Exception(f"File {path} profile '{profile_id} is missing the 'name' field")
            profile_overrides = profile_json.get('overrides', {})

            validate_printer_overrides(profile_overrides)

            profile = Profile(
                id = profile_id, 
                name = profile_name, 
                overrides = profile_overrides
            )

            # Load the compatible variants
            if (compatible_variants_json := profile_json.get('compatibleVariants')) == None:
                raise Exception(f"File {path} profile '{profile_id}' is missing the 'compatibleVariants' section")
            if len(compatible_variants_json) == 0:
                raise Exception(f"File {path} profile '{profile_id}' is missing 'compatibleVarians'")

            for compatible_variant_json in compatible_variants_json:
                if (variant_id := compatible_variant_json.get('variant')) == None:
                    raise Exception(f"File {path} profile '{profile_id}' compatible variant is missing the 'variant' field")

                profile.compatible_variants[variant_id] = Profile.Variant(
                    variant_id = variant_id,
                    overrides = compatible_variant_json.get('overrides', {})
                )

            printer.add_profile(profile)
            
        # Load the materials
        if (materials_json := json_def.get('materials')) == None:
            raise Exception(f"File {path} is missing 'materials' section")
        if len(materials_json) == 0:
            raise Exception(f"File {path} has no material definitions")

        for material_json in materials_json:
            if (material_id := material_json.get('id')) == None:
                raise Exception(f"File {path} is missing the 'material/id' field")
            if (material_name := material_json.get('name')) == None:
                raise Exception(f"File {path} material '{material_id}' is missing the 'name' field")

            material = Material(id = material_id, name = material_name)
            material.profile_filter = material_json.get("profileFilter")
            material.variant_filter = material_json.get("variantFilter")

            # Load overrides
            if (overrides_json := material_json.get("overrides")) != None:
                for override in overrides_json:
                    profiles_ref_ids = override.get('profiles')
                    variants_ref_ids = override.get('variants')
                    settings = override.get('settings', {})

                    validate_printer_overrides(settings)

                    material.overrides.append(Material.Overrides(
                        variant_ids = variants_ref_ids, 
                        profile_ids = profiles_ref_ids, 
                    settings = settings))

            printer.add_material(material)

        # DONE
        return printer

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
        printer = load_printer_profile(args.profile_gen_path, settings_validator=cura_settings_def)
    except Exception as exc:
        log.error(f"Error loading the profile-gen file:")
        log.exception(exc, exc_info=1, stack_info=False)
        exit(1)

    logging.info(f"Saving generated profiles onto {deployment_dir}")
    try:
        printer.save_printer_def(path = os.path.join(deployment_dir, "definitions"))
        printer.save_extruder_def(path = os.path.join(deployment_dir, "extruders"))
        printer.save_variants_cfg(path = os.path.join(deployment_dir, "variants"), cura_settings_def=cura_settings_def)
        printer.save_profiles_cfg(path = os.path.join(deployment_dir, "quality"), cura_settings_def=cura_settings_def)
        printer.save_material_cfg(path = os.path.join(deployment_dir, "quality"), cura_settings_def=cura_settings_def)
    except Exception as exc:
        log.error(f"Error saving definition files:")
        log.exception(exc, exc_info=1, stack_info=False)
        exit(1)

if __name__ == '__main__':
    main()