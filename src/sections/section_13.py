from dataclasses import dataclass
from typing import List
from utils.binary_reader import BinaryReader
from io import BytesIO
from utils.char_table import CharTable

@dataclass(init=False)
class Section13:
  offsets: List[int]
  dialog: List[str]

  def __init__(self, stream: BytesIO):
    self.offsets = self.parse_text_offsets(stream)
    self.dialog = self.parse_dialog(stream)
  
  def parse_text_offsets(self, stream: BytesIO) -> List[int]:
    offsets: List[int] = []
    while True:
      offset = BinaryReader.read_uint32(stream)
      if offset == 0:
        break
      offsets.append(offset)

    return offsets
    
  def parse_dialog(self, stream: BytesIO) -> List[str]:
    dialogs: List[str] = []
    
    for i, offset in enumerate(self.offsets):
        start_offset = offset
        end_offset = self.offsets[i + 1] if i + 1 < len(self.offsets) else len(stream.getbuffer())
        stream.seek(start_offset)
        
        text_bytes = stream.read(end_offset - start_offset)
        
        text = CharTable.getTextFromBytes(text_bytes)
        dialogs.append(text)
    
    return dialogs