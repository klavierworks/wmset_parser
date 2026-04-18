from file_header import FileHeader
from sections.section_0 import Section0
from sections.section_1 import Section1
from sections.section_2 import Section2
from sections.section_3 import Section3
from sections.section_4 import Section4
from sections.section_5 import Section5
from sections.section_6 import Section6
from sections.section_10 import Section10
from sections.section_16 import Section16
from sections.section_7 import Section7
from sections.section_8 import Section8
from sections.section_9 import Section9
from sections.section_11 import Section11
from sections.section_12 import Section12
from sections.section_13 import Section13
from sections.section_15 import Section15
from sections.section_31 import Section31
from sections.section_34 import Section34
from sections.section_36 import Section36
from sections.section_41 import Section41
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

    print("Section 12: Warp Landing Positions")
    warp_landing_positions = Section12(file_header.sections[12])

    print("Section 13: Dialog Texts")
    dialog_text = Section13(file_header.sections[13])

    print(f"Section 15: Models")
    models = Section15(file_header.sections[15])
    print(f"Models: {len(models.models)} model(s)")

    print("Section 16: Unknown")
    unknown = Section16(file_header.sections[16])

    print("Section 31: Location Names")
    location_names = Section31(file_header.sections[31])

    print("Section 34: Draw Points")
    draw_points = Section34(file_header.sections[34])

    print("Section 41: Object Textures")
    object_textures = Section41(file_header.sections[41])
    
    print("Exporting models and textures...")
    for i, model in enumerate(models.models):
      texture = object_textures.textures[i]
      #Section15.export_model_to_obj(model, f"../output/models/model_{i}.obj", texture)
      #texture.save_png(f"../output/textures/texture_{i}.png")
      #print(f"Exported model_{i}.obj with texture_{i}.png")

    event_scripts = Section36(file_header.sections[36])

if __name__ == "__main__":
  test_file_path = "../wmsetus.obj"
  os.system('cls' if os.name == 'nt' else 'clear')
  process_file(test_file_path)