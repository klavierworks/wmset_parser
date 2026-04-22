import os
import sys

from sections.section_40 import Section40

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sections.section_16 import Section16
from wmx.gltf_exporter import export_wmx_to_gltf
from wmx.parser import parse_wmx


def process_wmx(wmx_path: str, texl_path: str, wmset_path: str, output_glb_path: str, animated_textures: Section16, palette_animations: Section40) -> None:
    for p, label in ((wmx_path, "wmx"), (texl_path, "texl"), (wmset_path, "wmset")):
        if not os.path.exists(p):
            raise FileNotFoundError(f"{label} file {p} does not exist")

    print(f"Parsing {wmx_path}...")
    wmx = parse_wmx(wmx_path)
    print(f"Parsed {len(wmx.segments)} segments")

    print(f"Exporting to {output_glb_path}...")
    export_wmx_to_gltf(wmx, texl_path, output_glb_path, wmset_path=wmset_path, animated_textures=animated_textures, palette_animations=palette_animations)
    print("Done")
