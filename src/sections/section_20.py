from dataclasses import dataclass
from io import BytesIO

AKAO_MAGIC = b'AKAO'

@dataclass(init=False)
class Section20:
  akao_data: bytes

  def __init__(self, stream: BytesIO):
    self.akao_data = self.parse_akao(stream)

  def parse_akao(self, stream: BytesIO) -> bytes:
    data = stream.read(4)
    if data != AKAO_MAGIC:
      raise ValueError(f"Expected AKAO magic, got {data!r}")
    stream.seek(0)
    return stream.read()
