from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader


@dataclass
class AnimatedTextureFrame:
    offset: int


@dataclass
class AnimatedTextureDescriptor:
    phase_offset: int
    period: int
    half_frame_count: int
    flags: int
    tex_page: int
    v_coord: int
    frames: List[AnimatedTextureFrame]


@dataclass(init=False)
class Section16:
    offsets: List[int]
    descriptors: List[AnimatedTextureDescriptor]

    def __init__(self, stream: BytesIO) -> None:
        self.offsets = self.parse_offsets(stream)
        self.descriptors = self.parse_descriptors(stream)

    def parse_descriptors(self, stream: BytesIO) -> List[AnimatedTextureDescriptor]:
        descriptors: List[AnimatedTextureDescriptor] = []
        for offset in self.offsets:
            stream.seek(offset)
            descriptors.append(self.parse_descriptor(stream))
        return descriptors

    def parse_offsets(self, stream: BytesIO) -> List[int]:
        offsets: List[int] = []
        while True:
            offset = BinaryReader.read_uint32(stream)
            if offset == 0:
                break
            offsets.append(offset)
        return offsets

    def parse_descriptor(self, stream: BytesIO) -> AnimatedTextureDescriptor:
        phase_offset = BinaryReader.read_uint8(stream)
        period = BinaryReader.read_uint8(stream)
        half_frame_count = BinaryReader.read_uint8(stream)
        flags = BinaryReader.read_uint8(stream)
        tex_page = BinaryReader.read_uint16(stream)
        v_coord = BinaryReader.read_uint16(stream)
        frames = self.parse_frames(stream, half_frame_count)
        return AnimatedTextureDescriptor(
            phase_offset=phase_offset,
            period=period,
            half_frame_count=half_frame_count,
            flags=flags,
            tex_page=tex_page,
            v_coord=v_coord,
            frames=frames,
        )

    def parse_frames(
        self, stream: BytesIO, half_frame_count: int
    ) -> List[AnimatedTextureFrame]:
        frame_count = half_frame_count if half_frame_count > 0 else 1
        return [
            AnimatedTextureFrame(offset=BinaryReader.read_uint32(stream))
            for _ in range(frame_count)
        ]
