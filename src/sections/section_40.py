from dataclasses import dataclass
from io import BytesIO

@dataclass(init=False)
class Section40:
  raw_data: bytes

  def __init__(self, stream: BytesIO):
    self.raw_data = stream.read()
