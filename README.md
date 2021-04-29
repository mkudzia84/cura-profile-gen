
# cura-profile-gen
Python script used to generate robust Cura profiles for Custom printers.

![enter image description here](https://github.com/mkudzia84/cura-profile-gen/blob/master/docs/variant.png?raw=true)

The Cura GUI printer and profile editor is very limited and confusing and hides a lot of functions - like customizable variants.
In order to unlock those features, custom profile config files need to be handcrafted and populated into *the cura/resource* installation folder.
The CURA printer and quality profiles are split into *printer.def.json* file, *extruder(s).def.json* file, multiple *tool/nozzle variant.inst.cfg* files and most importantly the *quality.inst.cfg* files.
CURA requires a seperate *quality.inst.cfg* file for every allowed *quality-profile/variant/material* type.
As a result, even adding one new variant or allowed material type (even if no new setting overrides are needed) - raises the number of files exponentially.
In example with 4 variants (0.20, 0.25, 0.40 and 0.60mm nozzle), and supported 6 material types (PLA, PET, NYLON, TPU, ABS, ASA) adding one quality profile - requires creation of 24 new *quality.inst.cfg* files.
This workflow is error prone and hard to manage with file definitions having to be cross-referenced etc.

The script automates the CURA profile creation process by merging all settings into a single profile-gen.json file, which is validated, all of the cross refences are checked and/or generated - and from which all the def.json and inst.cfg files are being generated - and optionally populated into Cura installation directory.
The single file is easier to edit and version and provides a better overview of the settings

## Usage
Requirements: Python 3.8+

    python cura_profile_gen.py -d {deployment_directory} path-to.profile-gen.json
    
For deployment to CURA directory:

    python cura_profile_gen.py -d "D:\apps\3dprint\Ultimaker Cura 4.8.0\resources" profile-gen\prusa_mk3s.profile-gen.json

## Repository contents

 - cura_profile_gen.py script
 - profile-gen\prusa_mk3s.profile-gen.json - profile-gen template for Prusa MK3S (with 0.20, 0.25, 0.40, and 0.60 and Mosquito variant nozzles)
 - profile-gen\e3dtoolchanger.profile-gen.json - profile-gen template for E3D ToolChanging printer (with 0.20, 0.25, 0.40 and 0.60 nozzle variants)

## profile-gen.json format

The template format wrapps the standard cura def.json formats and extends it:
Please follow the [e3dtoolchanger.profile-gen.json](https://github.com/mkudzia84/cura-profile-gen/blob/master/profile-gen/e3dtoolchanger.profile-gen.json "e3dtoolchanger.profile-gen.json") as an example

### Printer section
Wraps the printed definition and follows the [fdmprinter.def.json](https://github.com/Ultimaker/Cura/blob/master/resources/definitions/fdmprinter.def.json "fdmprinter.def.json") CURA format.
The additional field is the *id* which defines the ID of the definition and is used as a base name of the printer def.json file.
The Id then is used as reference in all other files.
The file generated from this section is named *{printer.id}.def.json* and is stored under *{deploydir}/definitions* directory
	
		"printer" : {
			"id" : "e3d_tc",
			"name": "E3D ToolChanger",
			"inherits": "fdmprinter",
			"metadata": {
				"visible": true,
				"author": "Marcin Kudzia",
				"manufacturer": "E3D",
				"file_formats": "text/x-gcode",
				"preferred_quality_type": "fast",
				"icon": "icon_ultimaker2",
				
				"variants_name" : "Toolhead",
				"preferred_variant_name" : "0.40mm",
				"preferred_material" : "generic_pla",
				
				"quality_definition" : "e3d_tc",
				"machine_extruder_trains":
				{
					"0": "e3d_tc_extruder_0",
					"1": "e3d_tc_extruder_1",
					"2": "e3d_tc_extruder_2",
					"3": "e3d_tc_extruder_3"
				}
			},

			"overrides": {
				"machine_name": 							{ "default_value": "E3D Tool Changer" },
				"machine_heated_bed": 						{ "default_value": true },
				"machine_width": 							{ "default_value": 300 },
				"machine_height": 							{ "default_value": 285 },
				"machine_depth": 							{ "default_value": 200 },
				"machine_center_is_zero": 					{ "default_value": false },

				"machine_extruder_count": 					{ "default_value": 4 },
				"machine_nozzle_heat_up_speed":				{ "default_value": 1.4 },
				"machine_nozzle_cool_down_speed":			{ "default_value": 0.8 },

				"machine_max_feedrate_z": 					{ "default_value": 20 },
				"machine_max_acceleration_x": 				{ "default_value": 4000 },
				"machine_max_acceleration_y": 				{ "default_value": 4000 },
				"machine_max_acceleration_z": 				{ "default_value": 400 },
				"machine_max_jerk_xy": 						{ "default_value": 10 },
				"machine_max_jerk_z": 						{ "default_value": 0.4 },
				...
				"travel_avoid_other_parts" : 				{ "value": true },
				"travel_avoid_supports" : 					{ "value": true },
				"travel_retract_before_outer_wall" : 		{ "value": true },
				
				"adhesion_type": 							{ "default_value": "raft" },
				"raft_airgap" : 							{ "default_value": 0.10 },
				"raft_base_speed" : 						{ "default_value" : 20 }
			}
		},

### Extruders Section
Here all of the extruders can be defined, the *id* of the extruders must match the ids in *"machine_extruder_trains"* of printer definition.
The section follows the format of [fdmextruder.def.json](https://github.com/Ultimaker/Cura/blob/master/resources/definitions/fdmextruder.def.json "fdmextruder.def.json") file
The file generates from the section are named *{extruder.id}.def.json* and are placed under *{deploy_dir}/extruders* directory

		"extruders" : [
			{
				"id": "e3d_tc_extruder_0",
				"name": "Tool 1",
				"inherits": "fdmextruder",
				"metadata": {
					"machine": "e3d_tc",
					"position": "0"
				},
			
				"overrides": {
					"extruder_nr" : 		{ "default_value": 0 },
					"material_diameter" : 	{ "default_value": 1.75 },
					"machine_extruder_end_code" : { "default_value" : "T-1" },
					"machine_extruder_start_code" : { "default_value" : "G10 P0 S{material_print_temperature} ; Set tool 1 active temperature\nM116 ; Wait for temperatures\nT0" }
				}
			},
			...
			{
				"id": "e3d_tc_extruder_3",
				"name": "Tool 4",
				"inherits": "fdmextruder",
				"metadata": {
					"machine": "e3d_tc",
					"position": "3"
				},
			
				"overrides": {
					"extruder_nr" : 		{ "default_value": 3 },
					"material_diameter" : 	{ "default_value": 1.75 },
					"machine_extruder_end_code" : { "default_value" : "T-1" },
					"machine_extruder_start_code" : { "default_value" : "G10 P3 S{material_print_temperature} ; Set tool 1 active temperature\nM116 ; Wait for temperatures\nT0" }
				}
			}
		],

### Variants
The section defines available variants of tools / nozzles.
overrides field contains the names of CURA settings that will be overridden.
Additionally, to minimize the amount of repetition, inheritance between Variants is allowed via *inherits* field - multiple level inheritance is allowed (i.e. 0.20mm -> Mosquito 0.20mm -> Mosquito Sherpa 0.20mm)
When inheritance relation is present the child variant inherits all of the overrides of the parent, if one of the overrides of the child override same setting as of the parent, the childs setting is used.
This section generates the *{printer.id}_{variant.id}.inst.cfg* files under the *{deploy_dir}/variants* directory

		"variants" : [
			{
				"id" : "0.20mm",
				"overrides" : {
					"machine_nozzle_size" : 0.20,
					"speed_print" : 40
				}
			},
			{
				"id" : "0.25mm",
				"overrides" : {
					"machine_nozzle_size" : 0.25,
					"speed_print" : 40
				}
			},
			{
				"id" : "0.40mm",
				"overrides" : {
					"machine_nozzle_size" : 0.40,
					"speed_print" : 60
				}
			},
			{
				"id" : "0.60mm",
				"overrides" : { 
					"machine_nozzle_size" : 0.60,
					"speed_print" : 75
				}
			},
			{
				"id" : "Dragon - 0.20mm",
				"inherits" : "0.20mm",
				"overrides" : {
					"retraction_amount" : 2.0,
					"retraction_speed" : 35
				}
			},
			{
				"id" : "Dragon - 0.40mm",
				"inherits" : "0.40mm",
				"overrides" : {
					"retraction_amount" : 2.0,
					"retraction_speed" : 35
				}
			}
		],

## Profiles section
The section defines the quality profiles and the quality profile setting overrides.
The *compatibleVariants* list defines the compatible variants (i.e. Fine profile will only support 0.25 or 0.40 nozzle variants, but NOT the 0.60 or 0.80mm nozzle, where the Fast variant will support only 0.40 and 0.60mm nozzles)
Additional setting overrides can be defined on per variant level

		"profiles" : [
			{
				"id" : "fast",
				"name" : "Fast",
				"overrides" : {
					"layer_height" : 0.20,
					"layer_height_0" : 0.20
				},
				"compatibleVariants" : [
					{
						"variant" : "0.40mm",
						"overrides" : {}
					},
					{
						"variant" : "0.60mm", 
						"overrides" : {}
					}
				]
			},
			...
			{
				"id" : "extrafine",
				"name" : "Extra Fine",
				"overrides" : {
					"layer_height" : 0.07,
					"layer_height0" : 0.10,
					"raft_airgap" : 0.05
				},
				"compatibleVariants" : [
					{
						"variant" : "0.20mm",
						"overrides" : {}
					},
					{
						"variant" : "0.25mm",
						"overrides" : {}
					},
					{
						"variant" : "0.40mm",
						"overrides" : {
							"speed_print" : 30
						}
					}
				]
			}
		],

### Material section
The material section defines the list of materials compatible with the printer.
When no *profileFilter* and *variantFilter* are present the material quality profiles are generated for all possible Profile/Variant combinations (based on profile *compatibleVariants* section)
When profileFilter is present, material quality files will be only generated for the specified Profiles
When the *variantFilter* is present, material quality files will be only generated to the subset of variants specified in the filter, that are valid for specified (all or *profileFilter* filtered) profiles and their *compatibleVariants*
Additional override settings can be applied.

In example; here we can see that the PLA profiles will be generated for all of the profiles and variants
However for the TPU material, quality profiles will be only generated for nozzle variants of 0.40 and 0.60mm and for 'fine', 'normal' and 'fast' profiles. No quality profiles will be generated for 0.20 and 0.25 nozzle variants or extrafine profiles.
Additionally, an extra setting override will be added limiting the print speed to 20mm/s

This section generates *{printer.id}_{material.name}_{profile.id}.inst.cfg* files under the *quality/{printer.id}/{material.name}* directories

		"materials" : [
			{
				"id" : "generic_pla",
				"name" : "PLA",
				"overrides" : []
			},
			{
				"id" : "generic_petg",
				"name" : "PETG",
				"overrides" : []
			},
			{
				"id" : "generic_abs",
				"name" : "ABS",
				"overrides" : []
			},
			{
				"id" : "generic_asa",
				"name" : "ASA",
				"overrides" : []
			},
			{
				"id" : "generic_tpu",
				"name" : "TPU",
				"profileFilter" : ["fine", "normal", "fast"],
				"variantFilter" : ["0.40mm", "0.60mm"],
				"overrides" : [
					{
						"profiles" : ["fine", "normal", "fast"],
						"variants" : ["0.40mm", "0.60mm"],
						"settings" : {
							"speed_print" : 20
						}
					}
				]
			},
			{
				"id" : "generic_greentec",
				"name" : "GREENTEC"
			},
			{
				"id" : "generic_nylon",
				"name" : "NYLON",
				"profileFilter" : ["fine", "normal", "fast"],
				"variantFilter" : ["0.25mm", "0.40mm", "0.60mm"]
			}
		]
	}

