from dataclasses import dataclass
from typing import List
from utils.binary_reader import BinaryReader
from io import BytesIO

AKAO_MAGIC = b'AKAO'
NUM_AKAO_OFFSETS = 6

@dataclass(init=False)
class Section19:
  akao_count: int
  akao_header_size: int
  akao_entries: List[bytes]

  def __init__(self, stream: BytesIO):
    self.akao_count = BinaryReader.read_uint32(stream)
    self.akao_header_size = BinaryReader.read_uint32(stream)
    offsets = [BinaryReader.read_uint32(stream) for _ in range(NUM_AKAO_OFFSETS)]
    self.akao_entries = self.parse_akao_entries(stream, offsets)

  def parse_akao_entries(self, stream: BytesIO, offsets: List[int]) -> List[bytes]:
    entries: List[bytes] = []
    for i in range(len(offsets) - 1):
      size = offsets[i + 1] - offsets[i]
      entry = stream.read(size)
      if not entry.startswith(AKAO_MAGIC):
        raise ValueError(f"Expected AKAO magic at entry {i}, got {entry[:4]!r}")
      entries.append(entry)
    last = stream.read()
    if not last.startswith(AKAO_MAGIC):
      raise ValueError(f"Expected AKAO magic at final entry, got {last[:4]!r}")
    entries.append(last)
    return entries
