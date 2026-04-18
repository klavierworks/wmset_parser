from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader


PALETTE_HEADER_SIZE = 20
PALETTE_WIDTH = 256
PALETTE_BYTES_PER_PIXEL = 2
PALETTE_DATA_SIZE = PALETTE_WIDTH * PALETTE_BYTES_PER_PIXEL


@dataclass
class PaletteAnimationFrame:
    header: bytes
    palette_data: bytes


@dataclass
class PaletteAnimation:
    flags: int
    unknown_1: int
    frame_count: int
    unknown_2: int
    value_a: int
    value_b: int
    vram_x: int
    vram_y: int
    frames: List[PaletteAnimationFrame]


@dataclass(init=False)
class Section40:
    offsets: List[int]
    animations: List[PaletteAnimation]

    def __init__(self, stream: BytesIO):
        self.offsets = self.parse_offsets(stream)
        self.animations = self.parse_animations(stream)

    def parse_offsets(self, stream: BytesIO) -> List[int]:
        offsets: List[int] = []
        while True:
            offset = BinaryReader.read_uint32(stream)
            if offset == 0:
                break
            offsets.append(offset)
        return offsets

    def parse_animations(self, stream: BytesIO) -> List[PaletteAnimation]:
        animations: List[PaletteAnimation] = []
        for offset in self.offsets:
            stream.seek(offset)
            animations.append(self.parse_animation(stream, offset))
        return animations

    def parse_animation(self, stream: BytesIO, record_offset: int) -> PaletteAnimation:
        flags = BinaryReader.read_uint8(stream)
        unknown_1 = BinaryReader.read_uint8(stream)
        frame_count = BinaryReader.read_uint8(stream)
        unknown_2 = BinaryReader.read_uint8(stream)
        value_a = BinaryReader.read_uint16(stream)
        value_b = BinaryReader.read_uint16(stream)
        vram_x = BinaryReader.read_uint16(stream)
        vram_y = BinaryReader.read_uint16(stream)

        frame_table_offset = record_offset + 12
        frame_rel_offsets = [BinaryReader.read_uint32(stream) for _ in range(frame_count)]

        frames = [
            self.parse_frame(stream, frame_table_offset + rel_offset)
            for rel_offset in frame_rel_offsets
        ]

        return PaletteAnimation(
            flags=flags,
            unknown_1=unknown_1,
            frame_count=frame_count,
            unknown_2=unknown_2,
            value_a=value_a,
            value_b=value_b,
            vram_x=vram_x,
            vram_y=vram_y,
            frames=frames,
        )

    def parse_frame(self, stream: BytesIO, frame_offset: int) -> PaletteAnimationFrame:
        stream.seek(frame_offset)
        header = stream.read(PALETTE_HEADER_SIZE)
        palette_data = stream.read(PALETTE_DATA_SIZE)
        return PaletteAnimationFrame(header=header, palette_data=palette_data)
