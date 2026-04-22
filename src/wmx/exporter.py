import math
import os
from dataclasses import dataclass
from typing import List, Tuple

from wmx.atlas import (
    ATLAS_H,
    ATLAS_W,
    build_mega_atlas,
    road_pixel_origin,
    tex_page_pixel_origin,
    water_pixel_origin,
)
from wmx.parser import (
    BLOCK_GRID_DIM,
    BLOCK_SIZE_UNITS,
    SEGMENT_GRID_COLS,
    WORLD_SEGMENT_COUNT,
    WmxFile,
    WmxPolygon,
)
from wmx.texl import parse_texl

SCALE = 1.0 / 100.0
MATERIAL_NAME = "wmx_atlas"


@dataclass
class _Face:
    v: Tuple[int, int, int]
    vt: Tuple[int, int, int]
    vn: Tuple[int, int, int]
    group_id: int


def _polygon_atlas_origin(poly: WmxPolygon) -> Tuple[int, int]:
    if poly.is_water:
        return water_pixel_origin()
    if poly.is_road:
        return road_pixel_origin()
    return tex_page_pixel_origin(poly.tex_page)


def _atlas_uv(u: int, v: int, origin: Tuple[int, int]) -> Tuple[float, float]:
    px = origin[0] + u
    py = origin[1] + v
    return px / ATLAS_W, 1.0 - py / ATLAS_H


def _normalize(x: float, y: float, z: float) -> Tuple[float, float, float]:
    length = math.sqrt(x * x + y * y + z * z)
    if length == 0.0:
        return 0.0, 1.0, 0.0
    return x / length, y / length, z / length


def export_wmx_to_obj(wmx: WmxFile, texl_path: str, obj_path: str) -> None:
    output_dir = os.path.dirname(obj_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    obj_basename = os.path.splitext(os.path.basename(obj_path))[0]
    mtl_basename = obj_basename + ".mtl"
    atlas_basename = obj_basename + "_atlas.png"

    print(f"Parsing texl.obj from {texl_path}...")
    tims = parse_texl(texl_path)

    print("Building mega atlas (5x5 tiles, gridImage(4,4) per TIM)...")
    atlas = build_mega_atlas(tims)
    atlas.save(os.path.join(output_dir, atlas_basename))

    with open(os.path.join(output_dir, mtl_basename), "w") as f:
        f.write(f"# Material for {obj_basename}.obj\n")
        f.write(f"newmtl {MATERIAL_NAME}\n")
        f.write("Ka 1.000 1.000 1.000\n")
        f.write("Kd 1.000 1.000 1.000\n")
        f.write("Ks 0.000 0.000 0.000\n")
        f.write("d 1.0\n")
        f.write("illum 2\n")
        f.write(f"map_Kd {atlas_basename}\n")

    vertices: List[Tuple[float, float, float]] = []
    normals: List[Tuple[float, float, float]] = []
    uvs: List[Tuple[float, float]] = []
    faces: List[_Face] = []

    for seg_idx in range(min(len(wmx.segments), WORLD_SEGMENT_COUNT)):
        segment = wmx.segments[seg_idx]
        seg_col = seg_idx % SEGMENT_GRID_COLS
        seg_row = seg_idx // SEGMENT_GRID_COLS
        seg_world_east = seg_col * BLOCK_GRID_DIM * BLOCK_SIZE_UNITS
        seg_world_north = seg_row * BLOCK_GRID_DIM * BLOCK_SIZE_UNITS

        for block_idx, block in enumerate(segment.blocks):
            if block is None or block.polygon_count == 0:
                continue
            block_col = block_idx % BLOCK_GRID_DIM
            block_row = block_idx // BLOCK_GRID_DIM
            block_world_east = seg_world_east + block_col * BLOCK_SIZE_UNITS
            block_world_north = seg_world_north + block_row * BLOCK_SIZE_UNITS

            vertex_base = len(vertices) + 1
            for v in block.vertices:
                obj_x = (block_world_east + v.x) * SCALE
                obj_y = -v.y * SCALE
                obj_z = (block_world_north + (-v.z)) * SCALE
                vertices.append((obj_x, obj_y, obj_z))

            normal_base = len(normals) + 1
            for n in block.normals:
                nx, ny, nz = float(n.x), -float(n.y), -float(n.z)
                normals.append(_normalize(nx, ny, nz))

            for poly in block.polygons:
                origin = _polygon_atlas_origin(poly)
                uv_base = len(uvs) + 1
                uvs.append(_atlas_uv(poly.u1, poly.t1, origin))
                uvs.append(_atlas_uv(poly.u2, poly.t2, origin))
                uvs.append(_atlas_uv(poly.u3, poly.t3, origin))
                faces.append(_Face(
                    v=(vertex_base + poly.v1, vertex_base + poly.v2, vertex_base + poly.v3),
                    vt=(uv_base, uv_base + 1, uv_base + 2),
                    vn=(normal_base + poly.n1, normal_base + poly.n2, normal_base + poly.n3),
                    group_id=segment.group_id,
                ))

    faces.sort(key=lambda f: f.group_id)

    with open(obj_path, "w") as f:
        f.write("# FF8 worldmap geometry exported from wmx.obj\n")
        f.write(f"# world segments: {min(len(wmx.segments), WORLD_SEGMENT_COUNT)} "
                f"(skipped {max(0, len(wmx.segments) - WORLD_SEGMENT_COUNT)} story variants)\n")
        f.write(f"# vertices={len(vertices)} normals={len(normals)} uvs={len(uvs)} faces={len(faces)}\n")
        f.write(f"mtllib {mtl_basename}\n")
        f.write(f"usemtl {MATERIAL_NAME}\n")
        f.write("o wmx_worldmap\n")

        for x, y, z in vertices:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        for u, v in uvs:
            f.write(f"vt {u:.6f} {v:.6f}\n")
        for nx, ny, nz in normals:
            f.write(f"vn {nx:.6f} {ny:.6f} {nz:.6f}\n")

        last_group: int | None = None
        for face in faces:
            if face.group_id != last_group:
                f.write(f"g group_{face.group_id}\n")
                last_group = face.group_id
            (v1, v2, v3) = face.v
            (t1, t2, t3) = face.vt
            (n1, n2, n3) = face.vn
            f.write(f"f {v1}/{t1}/{n1} {v2}/{t2}/{n2} {v3}/{t3}/{n3}\n")
