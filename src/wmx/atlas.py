import os
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from sections.textures.tim import TIM

TILE_SIZE = 256
LAND_COLS = 4   # 20 TIMs in a 4-wide x 5-tall grid (col-major: TIM i at col=i//5, row=i%5)
LAND_ROWS = 5
LAND_ATLAS_W = LAND_COLS * TILE_SIZE
LAND_ATLAS_H = LAND_ROWS * TILE_SIZE

# Sea + road are composed like Deling's composeTextureImage: each wmset TIM is
# placed at its VRAM pixel position relative to the composite's top-left, then
# water/road polygon UVs (8-bit) pick the right tile directly — NOT tiled.
# Dimensions here match the actual composite bounds in FF8's wmsetus.obj; both
# are deterministic because the game's TIM imgPos is fixed.
SEA_COMPOSITE_W = 256
SEA_COMPOSITE_H = 128
ROAD_COMPOSITE_W = 192
ROAD_COMPOSITE_H = 64

WATER_TILES: Dict[int, Tuple[str, str]] = {
    34: ("world", "world_17.png"),
    33: ("world", "world_18.png"),
    32: ("world", "world_22.png"),
    31: ("world", "world_19.png"),
    10: ("world", "world_21.png"),
}
WATER_FALLBACK: Tuple[str, str] = ("world", "world_17.png")
WATER_FALLBACK_RGBA: Tuple[int, int, int, int] = (38, 92, 148, 255)

ROAD_TILES: Dict[int, Tuple[str, str]] = {
    28: ("road", "road_2.png"),
    27: ("road", "road_11.png"),
    29: ("road", "road_1.png"),
}
ROAD_FALLBACK: Tuple[str, str] = ("road", "road_2.png")
ROAD_FALLBACK_RGBA: Tuple[int, int, int, int] = (118, 110, 96, 255)

# One wmset world texture per region (group_id 0..7). Experimental mapping.
LAND_GROUP_TILES: Dict[int, Tuple[str, str]] = {
    0: ("world", "world_0.png"),  # Trabia
    1: ("world", "world_1.png"),  # Balamb + FH
    2: ("world", "world_2.png"),  # Esthar West
    3: ("world", "world_3.png"),  # Esthar SE + Lab
    4: ("world", "world_4.png"),  # Esthar N + Mordor
    5: ("world", "world_5.png"),  # Centra
    6: ("world", "world_6.png"),  # Galbadia borders
    7: ("world", "world_7.png"),  # Galbadia middle
}
LAND_GROUP_FALLBACK_RGBA: Tuple[int, int, int, int] = (112, 112, 100, 255)


def tex_page_pixel_origin(tex_page: int) -> Tuple[int, int]:
    col = tex_page // LAND_ROWS
    row = tex_page % LAND_ROWS
    return col * TILE_SIZE, row * TILE_SIZE


def _decode_indices(tim: TIM) -> np.ndarray:
    w, h = tim.header.img_w, tim.header.img_h
    raw = np.frombuffer(tim.image_data, dtype=np.uint8)
    if tim.header.bpp == 1:
        return raw[:w * h].reshape(h, w)
    if tim.header.bpp == 0:
        low = raw & 0x0F
        high = (raw >> 4) & 0x0F
        interleaved = np.empty(raw.size * 2, dtype=np.uint8)
        interleaved[0::2] = low
        interleaved[1::2] = high
        return interleaved[:w * h].reshape(h, w)
    raise ValueError(f"Unsupported bpp {tim.header.bpp} for TIM {tim.name}")


def _palette_rgba(tim: TIM, palette_index: int) -> np.ndarray:
    # FF8 transparency rule (per deling FF8Color::fromPsColor): a texel is
    # transparent iff the whole 16-bit color word is 0x0000. The PSX STP bit
    # (bit 15) is NOT alpha — palettes like TIM 0 palette 5 have STP=1 on every
    # entry (stored as black in VRAM but drawn opaque in world render), and
    # treating STP as alpha blanks them out, producing the chunky dropout seen
    # in the mountain renders.
    colors_per_palette = 16 if tim.header.bpp == 0 else 256
    total = tim.header.nb_pal or 1
    idx = palette_index if palette_index < total else 0
    base_byte = idx * colors_per_palette * 2
    raw = np.frombuffer(
        tim.palette_data, dtype=np.uint16, count=colors_per_palette, offset=base_byte
    )
    r = ((raw & 0x001F) * 255 // 31).astype(np.uint8)
    g = (((raw >> 5) & 0x001F) * 255 // 31).astype(np.uint8)
    b = (((raw >> 10) & 0x001F) * 255 // 31).astype(np.uint8)
    a = np.where(raw == 0, 0, 255).astype(np.uint8)
    return np.stack([r, g, b, a], axis=-1)


def _render_tim_grid4x4(tim: TIM) -> Image.Image:
    """Mirror deling TextureFile::gridImage(4, 4): each 64x64 sub-tile (col, row) shows
    TIM pixels (col*64..+64, row*64..+64) recolored with palette `row*4 + col`."""
    if not tim.header.has_palette:
        w, h = tim.header.img_w, tim.header.img_h
        raw = np.frombuffer(tim.image_data, dtype=np.uint16)[:w * h].reshape(h, w)
        r = ((raw & 0x001F) * 255 // 31).astype(np.uint8)
        g = (((raw >> 5) & 0x001F) * 255 // 31).astype(np.uint8)
        b = (((raw >> 10) & 0x001F) * 255 // 31).astype(np.uint8)
        a = np.where(raw >> 15, 0, 255).astype(np.uint8)
        return Image.fromarray(np.stack([r, g, b, a], axis=-1), mode="RGBA")

    w, h = tim.header.img_w, tim.header.img_h
    if w % 4 != 0 or h % 4 != 0:
        raise ValueError(f"TIM {tim.name} size {w}x{h} not divisible by 4")
    col_factor = w // 4
    row_factor = h // 4
    indices = _decode_indices(tim)
    out = np.zeros((h, w, 4), dtype=np.uint8)
    total_palettes = tim.header.nb_pal or 0
    for row in range(4):
        for col in range(4):
            pal_idx = row * 4 + col
            if pal_idx >= total_palettes:
                continue
            pal = _palette_rgba(tim, pal_idx)
            x0, y0 = col * col_factor, row * row_factor
            sub = indices[y0:y0 + row_factor, x0:x0 + col_factor]
            out[y0:y0 + row_factor, x0:x0 + col_factor] = pal[sub]
    return Image.fromarray(out, mode="RGBA")


def build_land_atlas(tims: List[TIM]) -> Image.Image:
    """deling-style 4x5 land atlas (1024x1280): each TIM tile is gridImage(4,4)
    so the 16 CLUT palettes are baked spatially into 16 sub-tiles per TIM."""
    atlas = Image.new("RGBA", (LAND_ATLAS_W, LAND_ATLAS_H), (0, 0, 0, 0))
    for tim_idx, tim in enumerate(tims):
        col = tim_idx // LAND_ROWS
        row = tim_idx % LAND_ROWS
        atlas.paste(_render_tim_grid4x4(tim), (col * TILE_SIZE, row * TILE_SIZE))
    return atlas


def _tim_pixel_pos(tim: TIM) -> Tuple[int, int]:
    """VRAM pixel position of a TIM's image data (imgX is stored in 16-bit word
    units, so 4bpp multiplies by 4, 8bpp by 2)."""
    bpp = tim.header.bpp
    mult = 4 if bpp == 0 else 2 if bpp == 1 else 1
    return tim.header.img_x * mult, tim.header.img_y


def _render_tim_single_palette(tim: TIM, palette_index: int = 0) -> Image.Image:
    """Render a TIM at its full image size using a single palette — used for
    sea/road tiles which are small (≤64×64) with just one palette each."""
    if not tim.header.has_palette:
        w, h = tim.header.img_w, tim.header.img_h
        raw = np.frombuffer(tim.image_data, dtype=np.uint16)[:w * h].reshape(h, w)
        r = ((raw & 0x001F) * 255 // 31).astype(np.uint8)
        g = (((raw >> 5) & 0x001F) * 255 // 31).astype(np.uint8)
        b = (((raw >> 10) & 0x001F) * 255 // 31).astype(np.uint8)
        a = np.where(raw == 0, 0, 255).astype(np.uint8)
        return Image.fromarray(np.stack([r, g, b, a], axis=-1), mode="RGBA")
    indices = _decode_indices(tim)
    pal = _palette_rgba(tim, palette_index)
    return Image.fromarray(pal[indices], mode="RGBA")


def _build_composite(tims: List[TIM], width: int, height: int) -> Image.Image:
    """Mirrors deling's Map::composeTextureImage: paste each TIM at its VRAM
    pixel position relative to the union's top-left. Water/road polygon UVs
    address this composite directly, so neighbouring sea/beach tiles sit where
    FF8's art team laid them out — no tiling, proper coastal transitions."""
    if not tims:
        return Image.new("RGBA", (width, height), (0, 0, 0, 0))
    positions = [_tim_pixel_pos(t) for t in tims]
    min_x = min(px for px, _ in positions)
    min_y = min(py for _, py in positions)
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for tim, (px, py) in zip(tims, positions):
        tile = _render_tim_single_palette(tim)
        out.paste(tile, (px - min_x, py - min_y))
    return out


def build_sea_composite(world_tims: List[TIM]) -> Image.Image:
    """Deling's seaTextureImage: indices Sea1..Sea5 (with Cascade, Beach1, Beach2
    interleaved per SpecialTextureName enum) = wmset world TIMs 16..23 (the
    first 9 wmset TIMs are low-res menu textures, offset by OBJFILE_SPECIAL_TEX_OFFSET).
    Produces a 256×128 atlas of 4×2 × 64px tiles with shore/beach regions in the
    right spots so coastal polygons flow correctly."""
    return _build_composite(world_tims[16:24], SEA_COMPOSITE_W, SEA_COMPOSITE_H)


def build_road_composite(road_tims: List[TIM]) -> Image.Image:
    """Deling's roadTextureImage: composeTextureImage over the full road TIM list.
    Bounds work out to 192×64 in FF8's wmsetus.obj."""
    return _build_composite(road_tims, ROAD_COMPOSITE_W, ROAD_COMPOSITE_H)


def land_group_tile(wmset_textures_dir: Optional[str], group_id: int) -> Image.Image:
    """Experimental: one wmset world texture per region (group_id)."""
    tile = load_wmset_tile(wmset_textures_dir, LAND_GROUP_TILES.get(group_id, ("world", "world_0.png")))
    if tile is None:
        return Image.new("RGBA", (TILE_SIZE, TILE_SIZE), LAND_GROUP_FALLBACK_RGBA)
    return _tile_to_page(tile)
