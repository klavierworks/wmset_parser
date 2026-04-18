from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

@dataclass(init=False)
class Section2:
    encounter_flags: List[int]

    def __init__(self, stream: BytesIO) -> None:
        self.encounter_flags = self.parse_flags(stream)

    def parse_flags(self, stream: BytesIO) -> List[int]:
        size = len(stream.getbuffer())
        return [BinaryReader.read_uint8(stream) for _ in range(size)]
