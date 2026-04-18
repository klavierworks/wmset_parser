from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

@dataclass
class EntityPosition:
    x: int
    y: int
    z: int
    yaw: int
    unused_angle: int

@dataclass(init=False)
class Section10:
    positions: List[EntityPosition]

    def __init__(self, stream: BytesIO) -> None:
        self.positions = self.parse_positions(stream)

    def parse_positions(self, stream: BytesIO) -> List[EntityPosition]:
        record_count = len(stream.getbuffer()) // 16 ## note: divide to int
        positions: List[EntityPosition] = []
        stream.seek(0)
        for _ in range(record_count):
            x = BinaryReader.read_int32(stream)
            y = BinaryReader.read_int32(stream)
            z = BinaryReader.read_int32(stream)
            angle_lo = BinaryReader.read_int16(stream)
            angle_hi = BinaryReader.read_int16(stream)
            positions.append(EntityPosition(
                x=x, y=y, z=z,
                yaw=angle_lo, unused_angle=angle_hi,
            ))
        return positions
