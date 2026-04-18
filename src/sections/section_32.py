from dataclasses import dataclass
from typing import List, Tuple
from io import BytesIO
from utils.binary_reader import BinaryReader


@dataclass
class SkyColorZone:
    x: int
    y: int
    transition_range: int
    light_color_1: Tuple[int, int, int]
    light_color_2: Tuple[int, int, int]
    fog_color_1: Tuple[int, int, int]
    fog_color_2: Tuple[int, int, int]
    fog_color_3: Tuple[int, int, int]
    atmosphere: List[int]


@dataclass(init=False)
class Section32:
    offsets: List[int]
    zones: List[SkyColorZone]

    def __init__(self, stream: BytesIO):
        self.offsets = self.parse_offsets(stream)
        self.zones = self.parse_zones(stream)

    def parse_offsets(self, stream: BytesIO) -> List[int]:
        offsets: List[int] = []
        while True:
            offset = BinaryReader.read_uint32(stream)
            if offset == 0:
                break
            offsets.append(offset)
        return offsets

    def parse_zones(self, stream: BytesIO) -> List[SkyColorZone]:
        zones: List[SkyColorZone] = []
        for offset in self.offsets:
            stream.seek(offset)
            zones.append(self.parse_zone(stream))
        return zones

    def parse_zone(self, stream: BytesIO) -> SkyColorZone:
        x = BinaryReader.read_int32(stream)
        y = BinaryReader.read_int32(stream)
        transition_range = BinaryReader.read_int32(stream)
        light_color_1 = self.parse_rgb_padded(stream)
        light_color_2 = self.parse_rgb_padded(stream)
        fog_color_1 = self.parse_rgb_padded(stream)
        fog_color_2 = self.parse_rgb_padded(stream)
        fog_color_3 = self.parse_rgb_padded(stream)
        atmosphere = [BinaryReader.read_int16(stream) for _ in range(9)]
        return SkyColorZone(
            x=x,
            y=y,
            transition_range=transition_range,
            light_color_1=light_color_1,
            light_color_2=light_color_2,
            fog_color_1=fog_color_1,
            fog_color_2=fog_color_2,
            fog_color_3=fog_color_3,
            atmosphere=atmosphere,
        )

    def parse_rgb_padded(self, stream: BytesIO) -> Tuple[int, int, int]:
        r = BinaryReader.read_uint8(stream)
        g = BinaryReader.read_uint8(stream)
        b = BinaryReader.read_uint8(stream)
        stream.read(1)
        return (r, g, b)
