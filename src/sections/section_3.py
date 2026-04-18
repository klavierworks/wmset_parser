from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

ENCOUNTERS_PER_GROUP = 8

@dataclass
class EncounterGroup:
    encounter_ids: List[int]

@dataclass(init=False)
class Section3:
    groups: List[EncounterGroup]

    def __init__(self, stream: BytesIO) -> None:
        self.groups = self.parse_groups(stream)

    def parse_groups(self, stream: BytesIO) -> List[EncounterGroup]:
        group_size_bytes = ENCOUNTERS_PER_GROUP * 2
        group_count = len(stream.getbuffer()) // group_size_bytes
        groups: List[EncounterGroup] = []
        for _ in range(group_count):
            encounter_ids = [BinaryReader.read_uint16(stream) for _ in range(ENCOUNTERS_PER_GROUP)]
            groups.append(EncounterGroup(encounter_ids=encounter_ids))
        return groups
