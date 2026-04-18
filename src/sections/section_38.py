from dataclasses import dataclass
from typing import List
from io import BytesIO
from .textures.tim import TIM
from .textures.parse_tim_archive import parse_tim_archive

@dataclass(init=False)
class Section38:
  offsets: List[int]
  textures: List[TIM]

  def __init__(self, stream: BytesIO):
    self.offsets, self.textures = parse_tim_archive(stream, name_prefix="RoadTex")
