from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

REGION_GRID_WIDTH = 32
REGION_GRID_HEIGHT = 24

@dataclass(init=False)
class Section1:
    region_ids: List[int]
    width: int
    height: int

    def __init__(self, stream: BytesIO) -> None:
        self.width = REGION_GRID_WIDTH
        self.height = REGION_GRID_HEIGHT
        self.region_ids = self.parse_region_ids(stream)

    def parse_region_ids(self, stream: BytesIO) -> List[int]:
        return [BinaryReader.read_uint8(stream) for _ in range(self.width * self.height)]

    def get_region_at(self, grid_x: int, grid_y: int) -> int:
        return self.region_ids[grid_y * self.width + grid_x]
