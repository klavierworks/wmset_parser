from dataclasses import dataclass
from typing import List
from io import BytesIO
from utils.binary_reader import BinaryReader

NUM_FORMATION_GROUPS = 16


@dataclass
class EncounterFormationGroup:
  formation_offsets: List[int]


@dataclass(init=False)
class Section17:
  groups: List[EncounterFormationGroup]

  def __init__(self, stream: BytesIO) -> None:
    self.groups = self.parse_groups(stream)

  def parse_groups(self, stream: BytesIO) -> List[EncounterFormationGroup]:
    group_offsets = [BinaryReader.read_uint32(stream) for _ in range(NUM_FORMATION_GROUPS)]
    return [self.parse_group(BytesIO(stream.getbuffer()[o:])) for o in group_offsets]

  def parse_group(self, stream: BytesIO) -> EncounterFormationGroup:
    formation_group = EncounterFormationGroup(formation_offsets=[])
    while True:
      offset = BinaryReader.read_uint32(stream)
      if offset == 0:
          break
      formation_group.formation_offsets.append(offset)
    return formation_group
