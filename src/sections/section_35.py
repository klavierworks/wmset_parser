from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader


@dataclass
class SpecialLocation:
    x: int
    z: int
    y: int
    type_code: int
    extra: int


@dataclass(init=False)
class Section35:
    locations: List[SpecialLocation]

    def __init__(self, stream: BytesIO):
        self.locations = self.parse_locations(stream)

    def parse_locations(self, stream: BytesIO) -> List[SpecialLocation]:
        record_count = len(stream.getbuffer()) // 12
        locations: List[SpecialLocation] = []
        for _ in range(record_count):
            x = BinaryReader.read_int32(stream)
            z = BinaryReader.read_int32(stream)
            y = BinaryReader.read_int16(stream)
            type_code = BinaryReader.read_uint8(stream)
            extra = BinaryReader.read_int8(stream)
            locations.append(SpecialLocation(
                x=x, z=z, y=y,
                type_code=type_code, extra=extra,
            ))
        return locations
