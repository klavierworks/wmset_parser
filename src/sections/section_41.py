from dataclasses import dataclass
from typing import List
from utils.binary_reader import BinaryReader
from io import BytesIO
from .textures.tim import TIM

@dataclass(init=False)
class Section41:
  offsets: List[int]
  textures: List[TIM]

  def __init__(self, stream: BytesIO):
    self.offsets = self.parse_offsets(stream)
    self.textures = self.parse_textures(stream)

  def parse_offsets(self, stream: BytesIO) -> List[int]:
    offsets: List[int] = []
    while True:
      offset = BinaryReader.read_uint32(stream)
      if offset == 0:
        break
      offsets.append(offset)
    return offsets

  def parse_textures(self, stream: BytesIO) -> List[TIM]:
    textures: List[TIM] = []
    for i, offset in enumerate(self.offsets):
      end_offset = self.offsets[i + 1] if i + 1 < len(self.offsets) else len(stream.getbuffer())
      stream.seek(offset)
      textures.append(self.parse_tim(BytesIO(stream.read(end_offset - offset)), name=f"Texture_{i}"))
    return textures

  def parse_tim(self, stream: BytesIO, name: str) -> TIM:
    return TIM(stream=stream, name=name)