from dataclasses import dataclass
from typing import List
from utils.binary_reader import BinaryReader
from io import BytesIO

@dataclass
class EntityRecord:
  value1: int
  value2: int
  value3: int
  type: int
  unknown: int

@dataclass(init=False)
class Section35:
  records: List[EntityRecord]

  def __init__(self, stream: BytesIO):
    self.records = self.parse_records(stream)

  def parse_records(self, stream: BytesIO) -> List[EntityRecord]:
    record_count = len(stream.getbuffer()) // 12
    records: List[EntityRecord] = []
    for _ in range(record_count):
      value1 = BinaryReader.read_int32(stream)
      value2 = BinaryReader.read_int32(stream)
      value3 = BinaryReader.read_int16(stream)
      entity_type = BinaryReader.read_uint8(stream)
      unknown = BinaryReader.read_int8(stream)
      records.append(EntityRecord(value1=value1, value2=value2, value3=value3, type=entity_type, unknown=unknown))
    return records
