import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wmx.gltf_exporter import export_wmx_to_gltf
from wmx.parser import parse_wmx


def process_wmx(wmx_path: str, texl_path: str, wmset_path: str, output_glb_path: str) -> None:
    for p, label in ((wmx_path, "wmx"), (texl_path, "texl"), (wmset_path, "wmset")):
        if not os.path.exists(p):
            raise FileNotFoundError(f"{label} file {p} does not exist")

    print(f"Parsing {wmx_path}...")
    wmx = parse_wmx(wmx_path)
    print(f"Parsed {len(wmx.segments)} segments")

    print(f"Exporting to {output_glb_path}...")
    export_wmx_to_gltf(wmx, texl_path, output_glb_path, wmset_path=wmset_path)
    print("Done")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    wmx_path = os.path.join(base_dir, "wmx.obj")
    texl_path = os.path.join(base_dir, "texl.obj")
    wmset_path = os.path.join(base_dir, "wmsetus.obj")
    output_path = os.path.join(base_dir, "output", "wmx.glb")
    process_wmx(wmx_path, texl_path, wmset_path, output_path)
