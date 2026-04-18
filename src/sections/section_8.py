from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

@dataclass
class FieldLandingPosition:
    x: int
    y: int
    z: int
    player_yaw: int
    vehicle_yaw: int

@dataclass(init=False)
class Section8:
    positions: List[FieldLandingPosition]

    def __init__(self, stream: BytesIO) -> None:
        self.positions = self.parse_positions(stream)

    def parse_positions(self, stream: BytesIO) -> List[FieldLandingPosition]:
        record_count = (len(stream.getbuffer()) - 4) // 12
        positions: List[FieldLandingPosition] = []
        for _ in range(record_count):
            x = BinaryReader.read_int32(stream)
            y = BinaryReader.read_int32(stream)
            z = BinaryReader.read_int16(stream)
            player_yaw = BinaryReader.read_uint8(stream)
            vehicle_yaw = BinaryReader.read_uint8(stream)
            positions.append(FieldLandingPosition(
                x=x, y=y, z=z,
                player_yaw=player_yaw, vehicle_yaw=vehicle_yaw,
            ))
        return positions
