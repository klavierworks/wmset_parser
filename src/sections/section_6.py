from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

@dataclass
class TextureLookup:
    tpage: int
    clut: int

@dataclass(init=False)
class Section6:
    entries: List[TextureLookup]

    def __init__(self, stream: BytesIO) -> None:
        self.entries = self.parse_entries(stream)

    def parse_entries(self, stream: BytesIO) -> List[TextureLookup]:
        record_count = (len(stream.getbuffer()) - 4) // 4
        entries: List[TextureLookup] = []
        stream.seek(0)
        for _ in range(record_count):
            tpage = BinaryReader.read_uint16(stream)
            clut = BinaryReader.read_uint16(stream)
            entries.append(TextureLookup(tpage=tpage, clut=clut))
        return entries
