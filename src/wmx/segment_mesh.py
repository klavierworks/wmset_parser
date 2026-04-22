import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from wmx.atlas import (
    LAND_ATLAS_H,
    LAND_ATLAS_W,
    ROAD_COMPOSITE_H,
    ROAD_COMPOSITE_W,
    SEA_COMPOSITE_H,
    SEA_COMPOSITE_W,
    tex_page_pixel_origin,
)
from wmx.parser import (
    BLOCK_GRID_DIM,
    BLOCK_SIZE_UNITS,
    SEGMENT_GRID_COLS,
    WmxPolygon,
    WmxSegment,
)

# MaterialKey: land always ("land", 0) since clut is baked into the atlas's
# sub-tile layout. Water and road are ("water", 0) / ("road", 0) — all water
# polygons share one composite texture, same for road, because ground_type
# doesn't pick the texture in FF8 (the polygon's UV does). Splitting by
# ground_type is what produced the tiled-sea / sand-in-the-water artifacts.
MaterialKey = Tuple[str, int]


@dataclass
class Primitive:
    material_key: MaterialKey
    transparent: bool
    positions: List[Tuple[float, float, float]] = field(default_factory=list)
    normals: List[Tuple[float, float, float]] = field(default_factory=list)
    uvs: List[Tuple[float, float]] = field(default_factory=list)
    # Packed (flags1, flags2, ground_type, 0) as VEC4 of UNSIGNED_BYTE → 4-byte aligned.
    flags: List[Tuple[int, int, int, int]] = field(default_factory=list)
    indices: List[int] = field(default_factory=list)


def _material_key(poly: WmxPolygon) -> MaterialKey:
    if poly.is_water:
        return ("water", 0)
    if poly.is_road:
        return ("road", 0)
    return ("land", 0)


def _is_transparent(poly: WmxPolygon) -> bool:
    return bool(poly.flags1 & 0x14)


def _land_uv(u: int, v: int, tex_page: int) -> Tuple[float, float]:
    ox, oy = tex_page_pixel_origin(tex_page)
    return (ox + u) / LAND_ATLAS_W, (oy + v) / LAND_ATLAS_H


def _sea_uv(u: int, v: int) -> Tuple[float, float]:
    return u / SEA_COMPOSITE_W, v / SEA_COMPOSITE_H


def _road_uv(u: int, v: int) -> Tuple[float, float]:
    return u / ROAD_COMPOSITE_W, v / ROAD_COMPOSITE_H


def _polygon_uv(poly: WmxPolygon, u: int, v: int) -> Tuple[float, float]:
    if poly.is_water:
        return _sea_uv(u, v)
    if poly.is_road:
        return _road_uv(u, v)
    return _land_uv(u, v, poly.tex_page)


def _normalize(vec: Tuple[float, float, float]) -> Tuple[float, float, float]:
    x, y, z = vec
    length = math.sqrt(x * x + y * y + z * z)
    if length == 0.0:
        return 0.0, 1.0, 0.0
    return x / length, y / length, z / length


PrimitiveKey = Tuple[MaterialKey, bool]


def build_segment_primitives(segment: WmxSegment, seg_idx: int) -> Dict[PrimitiveKey, Primitive]:
    """Produce per-segment glTF primitives. One primitive per (material_key, transparent)
    combination. Vertex dedup within a primitive; normals averaged per world position
    across the entire segment so block seams are smoothed."""
    seg_col = seg_idx % SEGMENT_GRID_COLS
    seg_row = seg_idx // SEGMENT_GRID_COLS
    seg_world_east = seg_col * BLOCK_GRID_DIM * BLOCK_SIZE_UNITS
    seg_world_north = seg_row * BLOCK_GRID_DIM * BLOCK_SIZE_UNITS

    corners: List[Tuple[PrimitiveKey, List[Tuple[Tuple[float, float, float], Tuple[float, float], Tuple[int, int, int, int]]]]] = []
    pos_normals: Dict[Tuple[float, float, float], List[Tuple[float, float, float]]] = defaultdict(list)

    for block_idx, block in enumerate(segment.blocks):
        if block is None or block.polygon_count == 0:
            continue
        block_col = block_idx % BLOCK_GRID_DIM
        block_row = block_idx // BLOCK_GRID_DIM
        block_world_east = seg_world_east + block_col * BLOCK_SIZE_UNITS
        block_world_north = seg_world_north + block_row * BLOCK_SIZE_UNITS

        for poly in block.polygons:
            pkey = (_material_key(poly), _is_transparent(poly))
            packed_flags = (poly.flags1, poly.flags2, poly.ground_type, 0)
            tri: List[Tuple[Tuple[float, float, float], Tuple[float, float], Tuple[int, int, int, int]]] = []
            for i in range(3):
                v_idx = (poly.v1, poly.v2, poly.v3)[i]
                n_idx = (poly.n1, poly.n2, poly.n3)[i]
                u_raw = (poly.u1, poly.u2, poly.u3)[i]
                v_raw = (poly.t1, poly.t2, poly.t3)[i]
                v = block.vertices[v_idx]
                n = block.normals[n_idx]
                pos = (
                    float(block_world_east + v.x),
                    float(-v.y),
                    float(block_world_north + (-v.z)),
                )
                raw_nrm = (float(n.x), float(-n.y), float(-n.z))
                pos_normals[pos].append(raw_nrm)
                tri.append((pos, _polygon_uv(poly, u_raw, v_raw), packed_flags))
            corners.append((pkey, tri))

    averaged_normals: Dict[Tuple[float, float, float], Tuple[float, float, float]] = {}
    for pos, ns in pos_normals.items():
        sx = sum(n[0] for n in ns)
        sy = sum(n[1] for n in ns)
        sz = sum(n[2] for n in ns)
        averaged_normals[pos] = _normalize((sx, sy, sz))

    primitives: Dict[PrimitiveKey, Primitive] = {}
    caches: Dict[PrimitiveKey, Dict[Tuple, int]] = {}

    for pkey, tri in corners:
        if pkey not in primitives:
            primitives[pkey] = Primitive(material_key=pkey[0], transparent=pkey[1])
            caches[pkey] = {}
        prim = primitives[pkey]
        cache = caches[pkey]
        triangle: List[int] = []
        for (pos, uv, packed) in tri:
            key = (pos, uv, packed)
            idx = cache.get(key)
            if idx is None:
                idx = len(prim.positions)
                cache[key] = idx
                prim.positions.append(pos)
                prim.normals.append(averaged_normals[pos])
                prim.uvs.append(uv)
                prim.flags.append(packed)
            triangle.append(idx)
        prim.indices.extend(triangle)

    return primitives
