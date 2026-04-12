from dataclasses import dataclass
from typing import List
from utils.binary_reader import BinaryReader
from io import BytesIO

@dataclass
class DrawPoint:
  index: int
  x: int
  y: int
  magicId: int

@dataclass(init=False)
class Section16:
  offsets: List[int]
  draw_points: List[DrawPoint]

  def __init__(self, stream: BytesIO):
    self.offsets = self.parse_offsets(stream)
  
  def parse_offsets(self, stream: BytesIO) -> List[int]:
    offsets: List[int] = []
    while True:
      offset = BinaryReader.read_uint32(stream)
      if offset == 0:
        break
      offsets.append(offset)

    return offsets
    