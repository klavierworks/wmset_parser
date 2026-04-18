from dataclasses import dataclass
from io import BytesIO
from utils.binary_reader import BinaryReader

AKAO_MAGIC = b'AKAO'


@dataclass(init=False)
class GenericAkaoSection:
  akao_data: bytes

  def __init__(self, stream: BytesIO) -> None:
    self.akao_data = self.parse_akao(stream)

  def parse_akao(self, stream: BytesIO) -> bytes:
    magic = BinaryReader.read_bytes(stream, 4)
    if magic != AKAO_MAGIC:
      raise ValueError(f"Expected AKAO magic, got {magic!r}")
    body = stream.read()
    return magic + body
