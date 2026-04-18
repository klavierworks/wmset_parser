from dataclasses import dataclass
from typing import List, Optional
from io import BytesIO
from utils.binary_reader import BinaryReader
from .opcodes import OPCODES


@dataclass
class Opcode:
    code: str
    code_id: int
    param1: int = 0
    param2: int = 0
    description: str = ""


@dataclass
class Script:
    opcodes: List[Opcode]


@dataclass(init=False)
class GenericScriptSection:
  offsets: List[int]
  scripts: List[Script]

  def __init__(self, stream: BytesIO) -> None:
    self.offsets = self.parse_offsets(stream)
    self.scripts = self.parse_scripts(stream)

  def parse_offsets(self, stream: BytesIO) -> List[int]:
      offsets: List[int] = []
      while True:
          offset = BinaryReader.read_uint32(stream)
          if offset == 0:
              break
          offsets.append(offset)
      return offsets
  
  def parse_scripts(self, stream: BytesIO) -> List[Script]:
    scripts: List[Script] = []
    for i, offset in enumerate(self.offsets):
      stream.seek(offset)
      script = Script(opcodes=[])
      
      next_offset = self.offsets[i + 1] if i + 1 < len(self.offsets) else len(stream.getbuffer())
      script_data_size = next_offset - offset
      
      while stream.tell() < offset + script_data_size:
        opcode = self.parse_opcode(stream)
        script.opcodes.append(opcode)
        if opcode.code_id == -234:
            break
      scripts.append(script)
    return scripts
    
  def parse_opcode(self, stream: BytesIO) -> Opcode:
      code_id = BinaryReader.read_int16(stream)
      param1 = BinaryReader.read_uint8(stream)
      param2 = BinaryReader.read_uint8(stream)
      return Opcode(
          code=OPCODES.get(code_id, {"opcode": "UNRECOGNISED"})["opcode"],
          code_id=code_id,
          param1=param1,
          param2=param2,
          description=OPCODES.get(code_id, {"description": ""})["description"],
      )
