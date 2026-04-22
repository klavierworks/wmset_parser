import io
import os
import struct
from typing import Dict, List, Optional, Tuple

from PIL import Image
from pygltflib import (
    GLTF2,
    Accessor,
    Asset,
    Buffer,
    BufferView,
    Image as GLTFImage,
    Material,
    Mesh,
    Node,
    PbrMetallicRoughness,
    Primitive as GLTFPrimitive,
    Sampler,
    Scene,
    Texture,
    TextureInfo,
)

from file_header import FileHeader
from sections.section_37 import Section37
from sections.section_38 import Section38
from wmx.atlas import (
    build_land_atlas,
    build_road_composite,
    build_sea_composite,
)
from wmx.parser import SEGMENT_GRID_COLS, WORLD_SEGMENT_COUNT, WmxFile, WmxSegment
from wmx.segment_mesh import (
    MaterialKey,
    Primitive,
    PrimitiveKey,
    build_segment_primitives,
)
from wmx.texl import parse_texl

# glTF enum shorthands
COMP_U8 = 5121
COMP_U16 = 5123
COMP_U32 = 5125
COMP_F32 = 5126
TYPE_SCALAR = "SCALAR"
TYPE_VEC2 = "VEC2"
TYPE_VEC3 = "VEC3"
TYPE_VEC4 = "VEC4"
ARR_BUFFER = 34962
ELE_BUFFER = 34963

FILTER_NEAREST = 9728
WRAP_REPEAT = 10497
WRAP_CLAMP = 33071

LAND_CLUT_COUNT = 16


class _BufferBuilder:
    def __init__(self, gltf: GLTF2) -> None:
        self.gltf = gltf
        self.blob = bytearray()

    def align(self) -> None:
        while len(self.blob) % 4 != 0:
            self.blob.append(0)

    def add_accessor(
        self,
        data: bytes,
        component_type: int,
        type_: str,
        count: int,
        *,
        min_: Optional[List[float]] = None,
        max_: Optional[List[float]] = None,
        target: Optional[int] = None,
    ) -> int:
        self.align()
        byte_offset = len(self.blob)
        self.blob.extend(data)
        bv = BufferView(buffer=0, byteOffset=byte_offset, byteLength=len(data))
        if target is not None:
            bv.target = target
        bv_idx = len(self.gltf.bufferViews)
        self.gltf.bufferViews.append(bv)
        acc = Accessor(bufferView=bv_idx, componentType=component_type, count=count, type=type_)
        if min_ is not None:
            acc.min = min_
        if max_ is not None:
            acc.max = max_
        acc_idx = len(self.gltf.accessors)
        self.gltf.accessors.append(acc)
        return acc_idx

    def add_image(self, png_bytes: bytes, name: str) -> int:
        self.align()
        byte_offset = len(self.blob)
        self.blob.extend(png_bytes)
        bv = BufferView(buffer=0, byteOffset=byte_offset, byteLength=len(png_bytes))
        bv_idx = len(self.gltf.bufferViews)
        self.gltf.bufferViews.append(bv)
        img_idx = len(self.gltf.images)
        self.gltf.images.append(GLTFImage(bufferView=bv_idx, mimeType="image/png", name=name))
        return img_idx


def _pack_floats(values: List[Tuple[float, ...]], dim: int) -> bytes:
    out = bytearray(len(values) * dim * 4)
    fmt = f"<{dim}f"
    offset = 0
    for row in values:
        struct.pack_into(fmt, out, offset, *row)
        offset += dim * 4
    return bytes(out)


def _pack_indices(values: List[int]) -> Tuple[bytes, int]:
    if len(values) == 0 or max(values) < 0x10000:
        return struct.pack(f"<{len(values)}H", *values), COMP_U16
    return struct.pack(f"<{len(values)}I", *values), COMP_U32


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _new_material(
    gltf: GLTF2,
    name: str,
    texture_idx: int,
    alpha_mode: str,
) -> int:
    mat = Material(
        name=name,
        pbrMetallicRoughness=PbrMetallicRoughness(
            baseColorTexture=TextureInfo(index=texture_idx, texCoord=0),
            baseColorFactor=[1.0, 1.0, 1.0, 1.0],
            metallicFactor=0.0,
            roughnessFactor=1.0,
        ),
        alphaMode=alpha_mode,
        doubleSided=True,
    )
    if alpha_mode == "MASK":
        mat.alphaCutoff = 0.5
    idx = len(gltf.materials)
    gltf.materials.append(mat)
    return idx


def _primitive_to_gltf(
    prim: Primitive,
    builder: _BufferBuilder,
    material_idx: int,
) -> GLTFPrimitive:
    pos_min = [min(v[i] for v in prim.positions) for i in range(3)]
    pos_max = [max(v[i] for v in prim.positions) for i in range(3)]
    pos_acc = builder.add_accessor(
        _pack_floats(prim.positions, 3), COMP_F32, TYPE_VEC3, len(prim.positions),
        min_=pos_min, max_=pos_max, target=ARR_BUFFER,
    )
    nrm_acc = builder.add_accessor(
        _pack_floats(prim.normals, 3), COMP_F32, TYPE_VEC3, len(prim.normals), target=ARR_BUFFER,
    )
    uv_acc = builder.add_accessor(
        _pack_floats(prim.uvs, 2), COMP_F32, TYPE_VEC2, len(prim.uvs), target=ARR_BUFFER,
    )
    flag_bytes = bytearray(len(prim.flags) * 4)
    offset = 0
    for a, b, c, d in prim.flags:
        flag_bytes[offset] = a
        flag_bytes[offset + 1] = b
        flag_bytes[offset + 2] = c
        flag_bytes[offset + 3] = d
        offset += 4
    flag_acc = builder.add_accessor(
        bytes(flag_bytes), COMP_U8, TYPE_VEC4, len(prim.flags), target=ARR_BUFFER,
    )
    idx_bytes, idx_comp = _pack_indices(prim.indices)
    idx_acc = builder.add_accessor(idx_bytes, idx_comp, TYPE_SCALAR, len(prim.indices), target=ELE_BUFFER)
    return GLTFPrimitive(
        attributes={
            "POSITION": pos_acc,
            "NORMAL": nrm_acc,
            "TEXCOORD_0": uv_acc,
            "_FLAGS": flag_acc,
        },
        indices=idx_acc,
        material=material_idx,
        mode=4,
    )


def _segment_node_name(seg_idx: int, is_variant: bool) -> str:
    return f"variant_{seg_idx - WORLD_SEGMENT_COUNT:03d}" if is_variant else f"segment_{seg_idx:03d}"


def _segment_extras(seg_idx: int, segment: WmxSegment, is_variant: bool) -> dict:
    extras = {
        "segment_index": seg_idx,
        "group_id": segment.group_id,
        "is_story_variant": is_variant,
    }
    if not is_variant:
        extras["segment_col"] = seg_idx % SEGMENT_GRID_COLS
        extras["segment_row"] = seg_idx // SEGMENT_GRID_COLS
    return extras


def _collect_alpha_usage(wmx: WmxFile) -> Tuple[bool, bool, bool]:
    """Return (land_alpha_used, water_alpha_used, road_alpha_used). With sea/road
    collapsed to one material each, we only need to know whether any transparent
    poly of that kind exists to decide whether to emit the MASK variant."""
    land_alpha = water_alpha = road_alpha = False
    for segment in wmx.segments:
        for block in segment.blocks:
            if block is None:
                continue
            for poly in block.polygons:
                transparent = bool(poly.flags1 & 0x14)
                if not transparent:
                    continue
                if poly.is_water:
                    water_alpha = True
                elif poly.is_road:
                    road_alpha = True
                else:
                    land_alpha = True
    return land_alpha, water_alpha, road_alpha


def _load_wmset_tims(wmset_path: str) -> Tuple[List, List]:
    """Return (world_textures, road_textures) TIM lists from wmsetus.obj. We
    need the TIM objects directly because the sea/road composites depend on
    each TIM's imgPos() — information that's lost if you go via extracted PNGs."""
    with open(wmset_path, "rb") as f:
        data = f.read()
    fh = FileHeader(data)
    world_tex = Section37(fh.sections[37]).textures
    road_tex = Section38(fh.sections[38]).textures
    return world_tex, road_tex


def export_wmx_to_gltf(
    wmx: WmxFile,
    texl_path: str,
    output_glb_path: str,
    wmset_path: Optional[str] = None,
) -> None:
    output_dir = os.path.dirname(output_glb_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    print(f"Parsing texl.obj from {texl_path}...")
    tims = parse_texl(texl_path)

    if wmset_path is None:
        raise ValueError("wmset_path is required to build sea/road composites")
    print(f"Parsing wmsetus.obj from {wmset_path}...")
    world_tex, road_tex = _load_wmset_tims(wmset_path)

    land_alpha_used, water_alpha_used, road_alpha_used = _collect_alpha_usage(wmx)
    print("Materials: 1 land (gridImage atlas) + 1 water (sea composite) + 1 road (road composite)")

    gltf = GLTF2()
    gltf.asset = Asset(generator="worldmap_models wmx exporter", version="2.0")
    gltf.scenes = [Scene(nodes=[])]
    gltf.scene = 0
    gltf.nodes = []
    gltf.meshes = []
    gltf.materials = []
    gltf.textures = []
    gltf.images = []
    gltf.samplers = []
    gltf.bufferViews = []
    gltf.accessors = []

    # CLAMP everywhere: UVs stay inside their texture's native footprint
    # (1024×1280 land, 256×128 sea, 192×64 road) so there's nothing to wrap.
    sampler_clamp = len(gltf.samplers)
    gltf.samplers.append(Sampler(
        magFilter=FILTER_NEAREST, minFilter=FILTER_NEAREST,
        wrapS=WRAP_CLAMP, wrapT=WRAP_CLAMP,
    ))

    builder = _BufferBuilder(gltf)

    material_indices: Dict[Tuple[MaterialKey, bool], int] = {}

    def add_texture(name: str, img) -> int:
        img.save(os.path.join(output_dir, f"wmx_{name}.png"))
        image_idx = builder.add_image(_png_bytes(img), name)
        tex_idx = len(gltf.textures)
        gltf.textures.append(Texture(sampler=sampler_clamp, source=image_idx))
        return tex_idx

    def register_material(kind: str, opaque_name: str, tex_idx: int, alpha_used: bool) -> None:
        material_indices[((kind, 0), False)] = _new_material(gltf, opaque_name, tex_idx, "OPAQUE")
        if alpha_used:
            material_indices[((kind, 0), True)] = _new_material(gltf, f"{opaque_name}_alpha", tex_idx, "MASK")

    print("Building land gridImage atlas...")
    register_material("land", "land", add_texture("atlas_land", build_land_atlas(tims)), land_alpha_used)

    print("Building sea composite (Sea1..Sea5 + Cascade + Beach1/Beach2)...")
    register_material("water", "water", add_texture("atlas_sea", build_sea_composite(world_tex)), water_alpha_used)

    print("Building road composite...")
    register_material("road", "road", add_texture("atlas_road", build_road_composite(road_tex)), road_alpha_used)

    world_root = Node(name="WorldMap", children=[])
    world_root_idx = len(gltf.nodes)
    gltf.nodes.append(world_root)
    gltf.scenes[0].nodes.append(world_root_idx)

    variants_root = Node(name="StoryVariants", children=[])
    variants_root_idx = len(gltf.nodes)
    gltf.nodes.append(variants_root)
    world_root.children.append(variants_root_idx)

    total_verts = 0
    total_tris = 0

    print(f"Building {len(wmx.segments)} segments...")
    for seg_idx in range(len(wmx.segments)):
        segment = wmx.segments[seg_idx]
        is_variant = seg_idx >= WORLD_SEGMENT_COUNT
        primitives = build_segment_primitives(segment, seg_idx)

        node_name = _segment_node_name(seg_idx, is_variant)
        node = Node(name=node_name, extras=_segment_extras(seg_idx, segment, is_variant))

        if primitives:
            gltf_primitives: List[GLTFPrimitive] = []
            for pkey, prim in primitives.items():
                if not prim.indices:
                    continue
                mat_idx = material_indices.get(pkey)
                if mat_idx is None:
                    # Fall back to the opaque variant of the same kind when a
                    # MASK variant wasn't created (no transparent polys of that
                    # kind exist, so the alpha material was skipped).
                    mat_idx = material_indices.get((pkey[0], False))
                    if mat_idx is None:
                        continue
                gltf_primitives.append(_primitive_to_gltf(prim, builder, mat_idx))
                total_verts += len(prim.positions)
                total_tris += len(prim.indices) // 3
            if gltf_primitives:
                mesh_idx = len(gltf.meshes)
                gltf.meshes.append(Mesh(name=f"{node_name}_mesh", primitives=gltf_primitives))
                node.mesh = mesh_idx

        node_idx = len(gltf.nodes)
        gltf.nodes.append(node)
        if is_variant:
            variants_root.children.append(node_idx)
        else:
            world_root.children.append(node_idx)

    builder.align()
    gltf.buffers = [Buffer(byteLength=len(builder.blob))]
    gltf.set_binary_blob(bytes(builder.blob))

    print(f"Writing {output_glb_path} ({total_verts} vertices, {total_tris} triangles)...")
    gltf.save_binary(output_glb_path)
