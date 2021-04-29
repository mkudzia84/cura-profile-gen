# cura-profile-gen
Python script used to generate robust Cura profiles for Custom printers.

The Cura GUI printer and profile editor is very limited and confusing and hides a lot of functions - like customizable variants.
In order to unlock those features, custom profile config files need to be handcrafted and populated into *the cura/resource* installation folder.
The CURA printer and quality profiles are split into *printer.def.json* file, *extruder(s).def.json* file, multiple *tool/nozzle variant.inst.cfg* files and most importantly the *quality.inst.cfg* files.
CURA requires a seperate *quality.inst.cfg* file for every allowed *quality-profile/variant/material* type.
As a result, even adding one new variant or allowed material type (even if no new setting overrides are needed) - raises the number of files exponentially.
In example with 4 variants (0.20, 0.25, 0.40 and 0.60mm nozzle), and supported 6 material types (PLA, PET, NYLON, TPU, ABS, ASA) adding one quality profile - requires creation of 24 new *quality.inst.cfg* files.
This workflow is error prone and hard to manage with file definitions having to be cross-referenced etc.

The script automates the CURA profile creation process by merging all settings into a single profile-gen.json file, which is validated, all of the cross refences are checked and/or generated - and from which all the def.json and inst.cfg files are being generated - and optionally populated into Cura installation directory.
The single file is easier to edit and version and provides a better overview of the settings

# Usage
Requirements: Python 3.8+

    python cura_profile_gen.py -d {deployment_directory} path-to.profile-gen.json
    
For deployment to CURA directory:

    python cura_profile_gen.py -d "D:\apps\3dprint\Ultimaker Cura 4.8.0\resources" profile-gen\prusa_mk3s.profile-gen.json

# Repository contents

 - cura_profile_gen.py script
 - profile-gen\prusa_mk3s.profile-gen.json - profile-gen template for Prusa MK3S (with 0.20, 0.25, 0.40, and 0.60 and Mosquito variant nozzles)
 - profile-gen\e3dtoolchanger.profile-gen.json - profile-gen template for E3D ToolChanging printer (with 0.20, 0.25, 0.40 and 0.60 nozzle variants)

# profile-gen.json format

The template format wrapps the standard cura def.json formats and extends it:
Following example (For E3D tool changer with descriptions)

    {
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
			
			"material_bed_temperature": 				{ "default_value": 60 },
			
			"retraction_enable":						{ "default_value": true },
			"retraction_amount": 						{ "default_value": 1.2 },
			"retraction_speed": 						{ "default_value": 35 },
			"retraction_retract_speed": 				{ "default_value": 35 },
			"retraction_prime_speed": 					{ "default_value": 35 },
			"retraction_hop_enabled": 					{ "default_value": true },
			"retraction_hop": 							{ "default_value" : 0.6 },
			"retraction_count_max": 					{ "default_value": 30 },
			"retraction_combing":                       { "default_value": false },

			"travel_avoid_other_parts" : 				{ "value": true },
			"travel_avoid_supports" : 					{ "value": true },
			"travel_retract_before_outer_wall" : 		{ "value": true },
			
			"adhesion_type": 							{ "default_value": "raft" },
			"raft_airgap" : 							{ "default_value": 0.10 },
			"raft_base_speed" : 						{ "default_value" : 20 },

			"speed_travel" :							{ "maximum_value": 500, "value": 400, "maximum_value_warning": 501 },
			"speed_travel_layer_0" :					{ "value": "math.ceil(speed_travel * 0.4)" },
			"speed_layer_0" :							{ "value": "math.ceil(speed_print * 0.25)" },
			"speed_wall" :								{ "value": "math.ceil(speed_print * 0.33)" },
			"speed_wall_0" :							{ "value": "math.ceil(speed_print * 0.50)" },
			"speed_wall_x" :							{ "value": "math.ceil(speed_print * 0.66)" },
			"speed_topbottom" :							{ "value": "math.ceil(speed_print * 0.66)" },
			"speed_roofing" :							{ "value": "math.ceil(speed_print * 0.33)" },
			"speed_infill" :                            { "value": "math.ceil(speed_print * 2.00)" },
			"speed_slowdown_layers" :					{ "default_value": 4 },
			
			"optimize_wall_printing_order" :      		{ "default_value": true },
			"infill_enable_travel_optimization":       	{ "default_value": true },
			
			"z_seam_type" : 							{ "default_value": "'back'" },
			"z_seam_corner" : 							{ "default_value": "'z_seam_corner_none'" },
			
			"support_interface_enable" : 				{ "value": true },
			"support_interface_height" : 				{ "value": "layer_height * 4" },
			"support_interface_density" : 				{ "value": 33.333 },
			"support_interface_pattern" : 				{ "value": "'grid'" },
			
			"wall_thickness" : 							{ "value": "line_width * 2" },
			
			"machine_head_with_fans_polygon" : 			{ "default_value": [[-31,31],[34,31],[34,-40],[-31,-40]] },
			"gantry_height" : 							{ "default_value": 28 },
	
			"jerk_enabled" :							{ "default_value": false },
			"jerk_wall_0" :								{ "value": 10 },
			"jerk_roofing" :							{ "value": 10 },
			
			"machine_gcode_flavor": 					{ "default_value": "RepRap (RepRap)" },
			"machine_start_gcode": {
				"default_value": "T-1\nG28 ; Home\nG29\nG29 S1 ; Enable bed compensation\n\n\nM140 S{material_bed_temperature}\nG10 P{initial_extruder_nr} S{material_print_temperature} R{material_print_temperature}\nM116\n;Set tool active temperature\nT{initial_extruder_nr} ; Tool\nG92 E0\nG1 F200 E3\nG92 E0"
			},
			"machine_end_gcode": {
				"default_value": "M140 S0 ; Bed temperature\nM144 ; Bed off\n\n; Retract the filament\nG92 E1\nG1 E-1 F300\n\nG10 P0 S0 R0\nG10 P1 S0 R0\nG10 P2 S0 R0\nG10 P3 S0 R0; Tool heater off\nM106 S0 ; Fan off\n\nT-1\n\nG29 S2 ; Disable bed compensation\nG1 X0 Y-149 F15000 ; Park\nM84 ; Motors off"
			}
		}
	},

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
		{
			"id": "e3d_tc_extruder_1",
			"name": "Tool 2",
			"inherits": "fdmextruder",
			"metadata": {
				"machine": "e3d_tc",
				"position": "1"
			},
		
			"overrides": {
				"extruder_nr" : 		{ "default_value": 1 },
				"material_diameter" : 	{ "default_value": 1.75 },
				"machine_extruder_end_code" : { "default_value" : "T-1" },
				"machine_extruder_start_code" : { "default_value" : "G10 P1 S{material_print_temperature} ; Set tool 1 active temperature\nM116 ; Wait for temperatures\nT0" }
			}
		},
		{
			"id": "e3d_tc_extruder_2",
			"name": "Tool 3",
			"inherits": "fdmextruder",
			"metadata": {
				"machine": "e3d_tc",
				"position": "2"
			},
		
			"overrides": {
				"extruder_nr" : 		{ "default_value": 2 },
				"material_diameter" : 	{ "default_value": 1.75 },
				"machine_extruder_end_code" : { "default_value" : "T-1" },
				"machine_extruder_start_code" : { "default_value" : "G10 P2 S{material_print_temperature} ; Set tool 1 active temperature\nM116 ; Wait for temperatures\nT0" }
			}
		},
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
		{
			"id" : "normal",
			"name" : "Normal",
			"overrides" : { 
				"layer_height" : 0.15,
				"layer_height_0" : 0.20
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
					"overrides" : {}
				},
				{
					"variant" : "0.60mm",
					"overrides" : {}
				}
			]
		},
		{
			"id" : "fine",
			"name" : "Fine",
			"overrides" : {
				"layer_height" : 0.10,
				"layer_height_0" : 0.15
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
					"overrides" : {}
				}
			]
		},
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
			"profileFilter" : [],
			"variantFilter" : [],
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

