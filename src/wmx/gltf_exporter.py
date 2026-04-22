import io
import os
import struct
from typing import Dict, List, Optional, Tuple

from PIL import Image
from pygltflib import (
    GLTF2,
    Accessor,
    Animation,
    AnimationChannel,
    AnimationChannelTarget,
    AnimationSampler,
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
from sections.section_16 import Section16
from sections.section_37 import Section37
from sections.section_38 import Section38
from sections.section_40 import Section40
from wmx.atlas import (
    build_land_atlas,
    build_road_composite,
)
from wmx.sea_anim import (
    SEA_ANIM_FRAME_COUNT,
    SEA_ANIM_PERIOD_SECONDS,
    build_sea_animation_sheet,
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
    *,
    uv_scale: Optional[Tuple[float, float]] = None,
) -> int:
    tex_info: TextureInfo = TextureInfo(index=texture_idx, texCoord=0)
    if uv_scale is not None:
        # KHR_texture_transform lets us sample only one frame of the sprite
        # sheet; the animation rewrites `offset.x` each tick to step frames.
        tex_info.extensions = {
            "KHR_texture_transform": {
                "offset": [0.0, 0.0],
                "scale": [uv_scale[0], uv_scale[1]],
            }
        }
    mat = Material(
        name=name,
        pbrMetallicRoughness=PbrMetallicRoughness(
            baseColorTexture=tex_info,
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
    wmset_path: str,
    animated_textures: Section16,
    palette_animations: Section40,
) -> None:
    output_dir = os.path.dirname(output_glb_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    print(f"Parsing texl.obj from {texl_path}...")
    tims = parse_texl(texl_path)

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

    def register_material(
        kind: str,
        opaque_name: str,
        tex_idx: int,
        alpha_used: bool,
        uv_scale: Optional[Tuple[float, float]] = None,
    ) -> None:
        material_indices[((kind, 0), False)] = _new_material(
            gltf, opaque_name, tex_idx, "OPAQUE", uv_scale=uv_scale
        )
        if alpha_used:
            material_indices[((kind, 0), True)] = _new_material(
                gltf, f"{opaque_name}_alpha", tex_idx, "MASK", uv_scale=uv_scale
            )

    print("Building land gridImage atlas...")
    register_material("land", "land", add_texture("atlas_land", build_land_atlas(tims)), land_alpha_used)

    print(f"Building animated sea sheet ({SEA_ANIM_FRAME_COUNT} frames)...")
    sea_sheet, sea_frame_count = build_sea_animation_sheet(
        world_tex, animated_textures, palette_animations, wmset_path
    )
    water_uv_scale = (1.0 / sea_frame_count, 1.0)
    register_material(
        "water", "water",
        add_texture("atlas_sea", sea_sheet),
        water_alpha_used,
        uv_scale=water_uv_scale,
    )

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

    _add_sea_uv_animation(
        gltf, builder, material_indices, sea_frame_count, SEA_ANIM_PERIOD_SECONDS
    )

    builder.align()
    gltf.buffers = [Buffer(byteLength=len(builder.blob))]
    gltf.set_binary_blob(bytes(builder.blob))

    print(f"Writing {output_glb_path} ({total_verts} vertices, {total_tris} triangles)...")
    gltf.save_binary(output_glb_path)


def _add_sea_uv_animation(
    gltf: GLTF2,
    builder: "_BufferBuilder",
    material_indices: Dict[Tuple[MaterialKey, bool], int],
    frame_count: int,
    period_seconds: float,
) -> None:
    """Attach a STEP animation that walks KHR_texture_transform.offset.x across
    the N sea-sheet frames. Targeted via KHR_animation_pointer, one channel
    per water material (opaque + optional MASK variant share the animation)."""
    water_materials = [
        material_indices[key]
        for key in (((("water", 0), False)), ((("water", 0), True)))
        if key in material_indices
    ]
    if not water_materials or frame_count < 2:
        return

    # N+1 keyframes with a final wrap back to offset 0 so every frame displays
    # for a full dt before the loop restarts. With only N keyframes the last
    # frame sits at t=duration (the loop point) and flashes for zero seconds.
    key_count = frame_count + 1
    dt = period_seconds / frame_count
    times = [i * dt for i in range(key_count)]
    offsets = [(i / frame_count, 0.0) for i in range(frame_count)] + [(0.0, 0.0)]

    time_bytes = struct.pack(f"<{key_count}f", *times)
    offset_bytes = _pack_floats(offsets, 2)
    input_acc = builder.add_accessor(
        time_bytes, COMP_F32, TYPE_SCALAR, key_count,
        min_=[0.0], max_=[times[-1]],
    )
    output_acc = builder.add_accessor(
        offset_bytes, COMP_F32, TYPE_VEC2, key_count,
    )

    # One shared sampler is enough — both channels read the same keyframes.
    shared_sampler_idx = 0
    samplers: List[AnimationSampler] = [AnimationSampler(
        input=input_acc, output=output_acc, interpolation="STEP",
    )]
    channels: List[AnimationChannel] = []
    for mat_idx in water_materials:
        pointer = (
            f"/materials/{mat_idx}/pbrMetallicRoughness/"
            f"baseColorTexture/extensions/KHR_texture_transform/offset"
        )
        target = AnimationChannelTarget(path="pointer")
        target.extensions = {"KHR_animation_pointer": {"pointer": pointer}}
        channels.append(AnimationChannel(sampler=shared_sampler_idx, target=target))

    if not gltf.animations:
        gltf.animations = []
    gltf.animations.append(Animation(
        name="sea_cycle", channels=channels, samplers=samplers,
    ))

    used = set(gltf.extensionsUsed or [])
    used.update(["KHR_texture_transform", "KHR_animation_pointer"])
    gltf.extensionsUsed = sorted(used)
