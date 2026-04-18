from file_header import FileHeader
from sections.section_0 import Section0
from sections.section_1 import Section1
from sections.section_2 import Section2
from sections.section_3 import Section3
from sections.section_4 import Section4
from sections.section_5 import Section5
from sections.section_6 import Section6
from sections.section_7 import Section7
from sections.section_8 import Section8
from sections.section_9 import Section9
from sections.section_10 import Section10
from sections.section_11 import Section11
from sections.section_12 import Section12
from sections.section_13 import Section13
from sections._unused_section_14 import UnusedSection14
from sections.section_15 import Section15
from sections.section_16 import Section16
from sections.section_17 import Section17
from sections.section_18 import Section18
from sections.section_19 import Section19
from sections.section_20 import Section20
from sections._unused_section_21 import UnusedSection21
from sections._unused_section_22 import UnusedSection22
from sections._unused_section_23 import UnusedSection23
from sections._unused_section_24 import UnusedSection24
from sections._unused_section_25 import UnusedSection25
from sections._unused_section_26 import UnusedSection26
from sections._unused_section_27 import UnusedSection27
from sections.section_28 import Section28
from sections.section_29 import Section29
from sections.section_30 import Section30
from sections.section_31 import Section31
from sections.section_32 import Section32
from sections.section_33 import Section33
from sections.section_34 import Section34
from sections.section_35 import Section35
from sections.section_36 import Section36
from sections.section_37 import Section37
from sections.section_38 import Section38
from sections.section_39 import Section39
from sections.section_40 import Section40
from sections.section_41 import Section41
from sections.section_42 import Section42
from sections.section_43 import Section43
from sections.section_44 import Section44
from sections.section_45 import Section45
from sections.section_46 import Section46
from sections.section_47 import Section47
import os

## IMPORTANT NOTE: in documentation sections are 1 indexed, in code they are 0 indexed. So section 1 in docs is section 0 in code.
def process_file(filepath: str) -> None:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File {filepath} does not exist")

    with open(filepath, "rb") as f:
        file_data = f.read()

    file_header = FileHeader(file_data)
    
    ## Print offsets with index as key
    for i, offset in enumerate(file_header.offsets):
        print(f"Offset {i}: {offset}")

    ## Remember, zero indexed! Section 13 in Wiki is section 12 here.
    print("Section 0: Encounter ID Supplier")
    encounter_id_supplier = Section0(file_header.sections[0])

    print("Section 1: World Map Regions")
    world_map_regions = Section1(file_header.sections[1])

    print("Section 2: Encounter Flags")
    encounter_flags = Section2(file_header.sections[2])

    print("Section 3: World Map Encounters")
    world_map_encounters = Section3(file_header.sections[3])

    print("Section 4: Lunar Cry Encounter Flags")
    lunar_cry_flags = Section4(file_header.sections[4])

    print("Section 5: Lunar Cry Encounters")
    lunar_cry_encounters = Section5(file_header.sections[5])

    print("Section 6: Polygon Texture Lookup")
    polygon_texture_lookup = Section6(file_header.sections[6])

    print("Section 7: Player Location Scripts")
    player_location_scripts = Section7(file_header.sections[7])

    print("Section 8: Field Landing Positions")
    field_landing_positions = Section8(file_header.sections[8])

    print("Section 9: Entity Spawn Scripts")
    entity_spawn_scripts = Section9(file_header.sections[9])

    print(f"Section 10: Entity Spawn Positions")
    entity_spawn_positions = Section10(file_header.sections[10])

    print("Section 11: Vehicle Warp Scripts")
    vehicle_warp_scripts = Section11(file_header.sections[11])

    print("Section 12: Train Exit Positions")
    train_exit_positions = Section12(file_header.sections[12])

    print("Section 13: Dialog Texts")
    dialog_text = Section13(file_header.sections[13])

    print("Section 14: Unused")
    UnusedSection14(file_header.sections[14])

    print(f"Section 15: Models")
    models = Section15(file_header.sections[15])
    print(f"Models: {len(models.models)} model(s)")

    print("Section 16: Animated Texture Descriptors")
    animated_textures = Section16(file_header.sections[16])

    print("Section 17: Encounter Formation Table")
    encounter_formations = Section17(file_header.sections[17])

    print("Section 18: Region Location IDs")
    region_location_ids = Section18(file_header.sections[18])

    print("Section 19: AKAO Frame Headers")
    akao_frame_headers = Section19(file_header.sections[19])

    print("Section 20: AKAO")
    akao = Section20(file_header.sections[20])

    print("Sections 21-27: Unused")
    UnusedSection21(file_header.sections[21])
    UnusedSection22(file_header.sections[22])
    UnusedSection23(file_header.sections[23])
    UnusedSection24(file_header.sections[24])
    UnusedSection25(file_header.sections[25])
    UnusedSection26(file_header.sections[26])
    UnusedSection27(file_header.sections[27])

    print("Section 28: Water Block")
    water_block = Section28(file_header.sections[28]) # likely PSX specific disk read workaround

    print("Section 29: Animation Frame Data")
    animation_frame_data = Section29(file_header.sections[29])
    
    print("Section 30: Animation Descriptors?")
    animation_descriptors = Section30(file_header.sections[30])

    print("Section 31: Location Names")
    location_names = Section31(file_header.sections[31])
    
    print("Section 32: Unknown light related")
    unknown_light_related = Section32(file_header.sections[32])
    
    print("Section 33: Unknown")
    section_33 = Section33(file_header.sections[33])

    print("Section 34: Draw Points")
    draw_points = Section34(file_header.sections[34])
    
    print("Section 35: Unknown")
    section_35 = Section35(file_header.sections[35])
    
    print("Section 36: Event Scripts")
    event_scripts = Section36(file_header.sections[36])
    
    print("Section 37: World Map textures")
    world_map_textures = Section37(file_header.sections[37])
    
    print("Section 38: Road/Tracks textures")
    road_tracks_textures = Section38(file_header.sections[38])

    print("Section 39: ONE World Map texture")
    one_world_map_texture = Section39(file_header.sections[39]) # likely PSX specific disk read workaround

    print("Section 40: Unknown")
    section_40 = Section40(file_header.sections[40])

    print("Section 41: Object Textures")
    object_textures = Section41(file_header.sections[41])

    print("Section 42: AKAO Sound/Music")
    section_42 = Section42(file_header.sections[42])

    print("Section 43: AKAO Music")
    section_43 = Section43(file_header.sections[43])

    print("Section 44: AKAO Sound/Music")
    section_44 = Section44(file_header.sections[44])

    print("Section 45: AKAO Sound/Music")
    section_45 = Section45(file_header.sections[45])

    print("Section 46: AKAO Sound/Music")
    section_46 = Section46(file_header.sections[46])

    print("Section 47: AKAO Sound/Music")
    section_47 = Section47(file_header.sections[47])

    print("Exporting models and textures...")
    for i, model in enumerate(models.models):
      texture = object_textures.textures[i]
      #Section15.export_model_to_obj(model, f"../output/models/model_{i}.obj", texture)
      #texture.save_png(f"../output/textures/texture_{i}.png")
      #print(f"Exported model_{i}.obj with texture_{i}.png")

if __name__ == "__main__":
  test_file_path = "../wmsetus.obj"
  os.system('cls' if os.name == 'nt' else 'clear')
  process_file(test_file_path)