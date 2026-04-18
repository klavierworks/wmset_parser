from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

@dataclass
class TrainExitPosition:
    x: int
    y: int
    z: int
    unknown_a: int
    unknown_b: int

@dataclass(init=False)
class Section12:
    positions: List[TrainExitPosition]

    def __init__(self, stream: BytesIO) -> None:
        self.positions = self.parse_positions(stream)

    def parse_positions(self, stream: BytesIO) -> List[TrainExitPosition]:
        record_count = (len(stream.getbuffer()) - 4) // 12
        positions: List[TrainExitPosition] = []
        for _ in range(record_count):
            x = BinaryReader.read_int32(stream)
            y = BinaryReader.read_int32(stream)
            z = BinaryReader.read_int16(stream)
            unknown_a = BinaryReader.read_uint8(stream)
            unknown_b = BinaryReader.read_uint8(stream)
            positions.append(TrainExitPosition(
                x=x, y=y, z=z,
                unknown_a=unknown_a, unknown_b=unknown_b,
            ))
        return positions
