from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

@dataclass
class EncounterIdSupplierEntry:
    region_id: int
    ground_id: int
    esi: int

@dataclass(init=False)
class Section0:
    entries: List[EncounterIdSupplierEntry]

    def __init__(self, stream: BytesIO) -> None:
        self.entries = self.parse_entries(stream)

    def parse_entries(self, stream: BytesIO) -> List[EncounterIdSupplierEntry]:
        stream.seek(0)
        entries_size = BinaryReader.read_uint32(stream)
        entry_count = entries_size // 4
        entries: List[EncounterIdSupplierEntry] = []
        for _ in range(entry_count):
            region_id = BinaryReader.read_uint8(stream)
            ground_id = BinaryReader.read_uint8(stream)
            esi = BinaryReader.read_uint16(stream)
            entries.append(EncounterIdSupplierEntry(
                region_id=region_id,
                ground_id=ground_id,
                esi=esi,
            ))
        return entries
