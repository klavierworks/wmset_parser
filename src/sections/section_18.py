from dataclasses import dataclass
from typing import List
from io import BytesIO

@dataclass(init=False)
class Section18:
  region_location_ids: List[int]

  def __init__(self, stream: BytesIO):
    self.region_location_ids = self.parse_region_location_ids(stream)

  def parse_region_location_ids(self, stream: BytesIO) -> List[int]:
    data = stream.getbuffer()
    return list(data)
