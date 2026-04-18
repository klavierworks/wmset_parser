from dataclasses import dataclass
from typing import List
from utils.binary_reader import BinaryReader
from io import BytesIO

@dataclass
class LocationRecord:
  x: int
  y: int
  location_id: int
  unknown: int
  value1: int
  value2: int

@dataclass(init=False)
class Section30:
  records: List[LocationRecord]

  def __init__(self, stream: BytesIO):
    self.records = self.parse_records(stream)

  def parse_records(self, stream: BytesIO) -> List[LocationRecord]:
    end_offset = BinaryReader.read_uint32(stream)
    record_count = (end_offset - 4) // 12
    records: List[LocationRecord] = []
    for _ in range(record_count):
      x = BinaryReader.read_uint8(stream)
      y = BinaryReader.read_uint8(stream)
      location_id = BinaryReader.read_uint8(stream)
      unknown = BinaryReader.read_uint8(stream)
      value1 = BinaryReader.read_int32(stream)
      value2 = BinaryReader.read_int32(stream)
      records.append(LocationRecord(x=x, y=y, location_id=location_id, unknown=unknown, value1=value1, value2=value2))
    return records
