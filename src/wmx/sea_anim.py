"""Sea (water) animation baker.

The wmset file encodes two independent systems that animate the sea composite:

1. Section 16 (image-frame animation): the TIM's indexed pixel data is swapped
   per frame. In wmsetus.obj this covers world TIM 21 (full 64×64) and world
   TIM 22 (two 64×32 halves — top & bottom independent descriptors). Each has
   4 frames that play ping-pong (0,1,2,3,2,1 → 6 display slots per cycle).

2. Section 40 (palette/CLUT animation): the TIM's 256-colour palette is
   rewritten per frame while the indexed pixel data stays put. In wmsetus.obj
   this covers world TIMs 16, 17, 18, 19 — 6 frames each, forward loop.

Section 16 ping-pong(4) and Section 40 forward(6) both run in 6-slot cycles,
so we bake a single 6-frame composite sheet and animate a shared UV offset.
"""

import io
import struct
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image

from sections.section_16 import AnimatedTextureDescriptor, Section16
from sections.section_40 import PaletteAnimation, Section40
from sections.textures.tim import TIM
from wmx.atlas import (
    SEA_COMPOSITE_H,
    SEA_COMPOSITE_W,
    _build_composite,
    _decode_indices,
    _palette_rgba,
    _tim_pixel_pos,
)

SEA_ANIM_FRAME_COUNT = 6
SEA_ANIM_PERIOD_SECONDS = 0.6  # 10 fps playback — matches FF8's perceived cadence

# The wmset sea composite is world TIMs 16..23.
_SEA_TIM_RANGE = range(16, 24)

# Ping-pong mapping: Section 16 stores 4 unique frames, plays forward then
# reverses for a 6-slot cycle (0→1→2→3→2→1). This aligns with Section 40's
# natural 6-frame forward cycle.
_PINGPONG_6_FROM_4 = (0, 1, 2, 3, 2, 1)


def _read_section16_frame_payloads(
    wmset_path: str, sec16: Section16
) -> List[List[bytes]]:
    """Re-read wmset raw bytes to extract each Section 16 frame's pixel payload.
    Section16 stores frame offsets only (pure metadata); the payload lives as a
    VRAM-transfer block: u32 marker(=18), u32 marker(=1), u32 size, u16 dest_x,
    u16 dest_y, u16 width_words, u16 height, then `size - 12` bytes of 8bpp
    indices. Returns payloads[descriptor_index][frame_index] → raw bytes."""
    from file_header import FileHeader  # local to avoid circular import concerns

    with open(wmset_path, "rb") as f:
        fh = FileHeader(f.read())
    sec_bytes = fh.sections[16].getvalue()

    out: List[List[bytes]] = []
    for desc_offset, descriptor in zip(sec16.offsets, sec16.descriptors):
        frame_table_start = desc_offset + 8  # skip 8-byte fixed descriptor header
        frame_payloads: List[bytes] = []
        for frame in descriptor.frames:
            base = frame_table_start + frame.offset
            size = struct.unpack_from("<I", sec_bytes, base + 8)[0]
            payload_len = size - 12  # size field includes dest_rect + w/h (12 bytes)
            frame_payloads.append(sec_bytes[base + 20 : base + 20 + payload_len])
        out.append(frame_payloads)
    return out


def _decode_palette_frame(raw: bytes) -> np.ndarray:
    """Decode 512 bytes of BGR555 (+ STP) into a 256×4 uint8 RGBA array.
    Same transparency rule as atlas._palette_rgba: only the all-zero word is
    transparent; the PSX STP bit is not alpha."""
    words = np.frombuffer(raw, dtype=np.uint16, count=256)
    r = ((words & 0x001F) * 255 // 31).astype(np.uint8)
    g = (((words >> 5) & 0x001F) * 255 // 31).astype(np.uint8)
    b = (((words >> 10) & 0x001F) * 255 // 31).astype(np.uint8)
    a = np.where(words == 0, 0, 255).astype(np.uint8)
    return np.stack([r, g, b, a], axis=-1)


def _tile_from_indices_and_palette(
    indices: np.ndarray, palette_rgba: np.ndarray
) -> Image.Image:
    return Image.fromarray(palette_rgba[indices], mode="RGBA")


def _tim_base_indices(tim: TIM) -> np.ndarray:
    return _decode_indices(tim)


def _tim_base_palette(tim: TIM) -> np.ndarray:
    return _palette_rgba(tim, 0)


def _composite_local_pos(tim: TIM, composite_min_x: int, composite_min_y: int) -> Tuple[int, int]:
    px, py = _tim_pixel_pos(tim)
    return px - composite_min_x, py - composite_min_y


def _match_section40_tim(anim: PaletteAnimation, tims: List[TIM]) -> Optional[int]:
    """Section 40's (value_a, value_b) is the destination palette VRAM position
    and uniquely identifies which TIM's palette is being overwritten each frame."""
    for idx, t in enumerate(tims):
        h = t.header
        if not h.has_palette:
            continue
        if (
            h.pal_x <= anim.value_a < h.pal_x + h.pal_w
            and h.pal_y <= anim.value_b < h.pal_y + h.pal_h
        ):
            return idx
    return None


def _match_section16_tim(
    descriptor: AnimatedTextureDescriptor, tims: List[TIM]
) -> Optional[int]:
    """Section 16's (tex_page, v_coord) is in the same unit as TIM.img_x/img_y
    (VRAM 16-bit-word columns), so we match against image region directly."""
    ax, ay = descriptor.tex_page, descriptor.v_coord
    for idx, t in enumerate(tims):
        h = t.header
        vram_cols = h.img_w // (4 if h.bpp == 0 else 2 if h.bpp == 1 else 1)
        if h.img_x <= ax < h.img_x + vram_cols and h.img_y <= ay < h.img_y + h.img_h:
            return idx
    return None


def _build_single_frame(
    world_tims: List[TIM],
    frame_idx: int,
    sec16_descriptors: List[AnimatedTextureDescriptor],
    sec16_payloads: List[List[bytes]],
    sec40_animations: List[PaletteAnimation],
) -> Image.Image:
    """Produce one 256×128 sea composite with the given frame of each
    animation baked in. Non-animated TIMs render at their default palette."""
    sea_tims = [world_tims[i] for i in _SEA_TIM_RANGE]
    base = _build_composite(sea_tims, SEA_COMPOSITE_W, SEA_COMPOSITE_H).copy()

    # Composite local-origin is the min (pixel_x, pixel_y) of the sea TIMs.
    positions = [_tim_pixel_pos(t) for t in sea_tims]
    min_x = min(px for px, _ in positions)
    min_y = min(py for _, py in positions)

    # Section 40: palette swap. Produces a full-TIM RGBA tile at the frame's palette.
    for anim in sec40_animations:
        tim_idx = _match_section40_tim(anim, world_tims)
        if tim_idx is None or tim_idx not in _SEA_TIM_RANGE:
            continue
        tim = world_tims[tim_idx]
        if not tim.header.has_palette or tim.header.bpp != 1:
            continue
        frame_n = frame_idx % anim.frame_count
        pal = _decode_palette_frame(anim.frames[frame_n].palette_data)
        tile = _tile_from_indices_and_palette(_tim_base_indices(tim), pal)
        lx, ly = _composite_local_pos(tim, min_x, min_y)
        base.paste(tile, (lx, ly))

    # Section 16: image-data swap. Payload is a rectangular 8bpp block pasted at
    # (tex_page, v_coord) in VRAM, and decoded with the target TIM's palette 0.
    for desc, payloads in zip(sec16_descriptors, sec16_payloads):
        tim_idx = _match_section16_tim(desc, world_tims)
        if tim_idx is None or tim_idx not in _SEA_TIM_RANGE:
            continue
        tim = world_tims[tim_idx]
        if not tim.header.has_palette or tim.header.bpp != 1:
            continue
        frame_n = _PINGPONG_6_FROM_4[frame_idx % SEA_ANIM_FRAME_COUNT] if len(payloads) == 4 else frame_idx % len(payloads)
        payload = payloads[frame_n]
        # Frame payload dims: block_width_words × 2 = pixel width; height matches rows.
        # Derive from payload length and descriptor v_coord offset within the TIM.
        tim_h = tim.header.img_h
        tim_w = tim.header.img_w
        # vertical extent of this payload inside the TIM
        tim_vram_y = tim.header.img_y
        v_top = desc.v_coord - tim_vram_y
        block_h = len(payload) // tim_w  # 8bpp: 1 byte per pixel; payload covers full TIM width
        block_w = tim_w
        if block_w * block_h != len(payload):
            # width-in-words wasn't full TIM width; fall back to square-ish shape.
            block_h = tim_h
            block_w = len(payload) // block_h
        indices = np.frombuffer(payload, dtype=np.uint8).reshape(block_h, block_w)
        pal = _tim_base_palette(tim)
        tile = _tile_from_indices_and_palette(indices, pal)
        lx, ly = _composite_local_pos(tim, min_x, min_y)
        base.paste(tile, (lx, ly + v_top))

    return base


def build_sea_animation_sheet(
    world_tims: List[TIM],
    sec16: Optional[Section16],
    sec40: Optional[Section40],
    wmset_path: Optional[str],
) -> Tuple[Image.Image, int]:
    """Bake N sea composites side-by-side into a horizontal sprite sheet. If
    either animation section is missing we still return a sheet (falling back
    to a single-frame repeat) so callers always have a consistent layout."""
    n = SEA_ANIM_FRAME_COUNT
    sheet = Image.new("RGBA", (SEA_COMPOSITE_W * n, SEA_COMPOSITE_H), (0, 0, 0, 0))

    sec16_descriptors = sec16.descriptors if sec16 is not None else []
    sec40_animations = sec40.animations if sec40 is not None else []
    sec16_payloads: List[List[bytes]] = []
    if sec16_descriptors and wmset_path is not None:
        sec16_payloads = _read_section16_frame_payloads(wmset_path, sec16)

    for frame_idx in range(n):
        frame = _build_single_frame(
            world_tims,
            frame_idx,
            sec16_descriptors,
            sec16_payloads,
            sec40_animations,
        )
        sheet.paste(frame, (frame_idx * SEA_COMPOSITE_W, 0))
    return sheet, n
