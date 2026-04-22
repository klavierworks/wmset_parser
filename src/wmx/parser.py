from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional

from utils.binary_reader import BinaryReader

SEGMENT_SIZE = 0x9000
BLOCKS_PER_SEGMENT = 16
BLOCK_GRID_DIM = 4
BLOCK_SIZE_UNITS = 2048
SEGMENT_GRID_COLS = 32
SEGMENT_GRID_ROWS = 24
WORLD_SEGMENT_COUNT = SEGMENT_GRID_COLS * SEGMENT_GRID_ROWS  # 768; remainder are story variants


@dataclass
class WmxVertex:
    x: int   # east-west   (raw bytes[0:2])
    y: int   # elevation   (raw bytes[2:4]; negative = higher terrain)
    z: int   # north-south (raw bytes[4:6]; negative = south)


@dataclass
class WmxNormal:
    x: int
    y: int
    z: int


@dataclass
class WmxPolygon:
    v1: int
    v2: int
    v3: int
    n1: int
    n2: int
    n3: int
    u1: int
    t1: int
    u2: int
    t2: int
    u3: int
    t3: int
    tex_page: int
    clut_id: int
    ground_type: int
    flags1: int
    flags2: int

    @property
    def is_water(self) -> bool:
        return (self.flags1 & 0x60) == 0x40

    @property
    def is_road(self) -> bool:
        return bool(self.flags1 & 0x20)

    @property
    def is_transparent(self) -> bool:
        return bool(self.flags1 & 0x10)

    @property
    def is_city(self) -> bool:
        return bool(self.flags1 & 0x08)


@dataclass
class WmxBlock:
    polygon_count: int
    vertex_count: int
    normal_count: int
    polygons: List[WmxPolygon]
    vertices: List[WmxVertex]
    normals: List[WmxNormal]


@dataclass
class WmxSegment:
    group_id: int
    block_offsets: List[int]
    blocks: List[Optional[WmxBlock]]


@dataclass
class WmxFile:
    segments: List[WmxSegment]


def _parse_vertex(stream: BytesIO) -> WmxVertex:
    x = BinaryReader.read_int16(stream)
    y = BinaryReader.read_int16(stream)
    z = BinaryReader.read_int16(stream)
    BinaryReader.read_int16(stream)
    return WmxVertex(x=x, y=y, z=z)


def _parse_normal(stream: BytesIO) -> WmxNormal:
    x = BinaryReader.read_int16(stream)
    y = BinaryReader.read_int16(stream)
    z = BinaryReader.read_int16(stream)
    BinaryReader.read_int16(stream)
    return WmxNormal(x=x, y=y, z=z)


def _parse_polygon(stream: BytesIO) -> WmxPolygon:
    v1 = BinaryReader.read_uint8(stream)
    v2 = BinaryReader.read_uint8(stream)
    v3 = BinaryReader.read_uint8(stream)
    n1 = BinaryReader.read_uint8(stream)
    n2 = BinaryReader.read_uint8(stream)
    n3 = BinaryReader.read_uint8(stream)
    u1 = BinaryReader.read_uint8(stream)
    t1 = BinaryReader.read_uint8(stream)
    u2 = BinaryReader.read_uint8(stream)
    t2 = BinaryReader.read_uint8(stream)
    u3 = BinaryReader.read_uint8(stream)
    t3 = BinaryReader.read_uint8(stream)
    texi = BinaryReader.read_uint8(stream)
    ground = BinaryReader.read_uint8(stream)
    flags1 = BinaryReader.read_uint8(stream)
    flags2 = BinaryReader.read_uint8(stream)
    return WmxPolygon(
        v1=v1, v2=v2, v3=v3,
        n1=n1, n2=n2, n3=n3,
        u1=u1, t1=t1, u2=u2, t2=t2, u3=u3, t3=t3,
        tex_page=(texi >> 4) & 0x0F,
        clut_id=texi & 0x0F,
        ground_type=ground,
        flags1=flags1, flags2=flags2,
    )


def _parse_block(stream: BytesIO) -> WmxBlock:
    polygon_count = BinaryReader.read_uint8(stream)
    vertex_count = BinaryReader.read_uint8(stream)
    normal_count = BinaryReader.read_uint8(stream)
    BinaryReader.read_uint8(stream)
    polygons = [_parse_polygon(stream) for _ in range(polygon_count)]
    vertices = [_parse_vertex(stream) for _ in range(vertex_count)]
    normals = [_parse_normal(stream) for _ in range(normal_count)]
    return WmxBlock(
        polygon_count=polygon_count,
        vertex_count=vertex_count,
        normal_count=normal_count,
        polygons=polygons,
        vertices=vertices,
        normals=normals,
    )


def _parse_segment(segment_bytes: bytes) -> WmxSegment:
    stream = BytesIO(segment_bytes)
    group_id = BinaryReader.read_uint32(stream)
    block_offsets = [BinaryReader.read_uint32(stream) for _ in range(BLOCKS_PER_SEGMENT)]

    blocks: List[Optional[WmxBlock]] = []
    for offset in block_offsets:
        if offset == 0 or offset >= SEGMENT_SIZE:
            blocks.append(None)
            continue
        stream.seek(offset)
        blocks.append(_parse_block(stream))
    return WmxSegment(group_id=group_id, block_offsets=block_offsets, blocks=blocks)


def parse_wmx(filepath: str) -> WmxFile:
    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) % SEGMENT_SIZE != 0:
        raise ValueError(
            f"wmx.obj size {len(data)} is not a multiple of segment size {SEGMENT_SIZE}"
        )
    total_segments = len(data) // SEGMENT_SIZE
    segments = [
        _parse_segment(data[i * SEGMENT_SIZE:(i + 1) * SEGMENT_SIZE])
        for i in range(total_segments)
    ]
    return WmxFile(segments=segments)
