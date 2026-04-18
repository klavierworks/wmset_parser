from typing import List, Tuple
from io import BytesIO
from utils.binary_reader import BinaryReader
from .tim import TIM

def parse_tim_archive(stream: BytesIO, name_prefix: str) -> Tuple[List[int], List[TIM]]:
  offsets: List[int] = []
  while True:
    offset = BinaryReader.read_uint32(stream)
    if offset == 0:
      break
    offsets.append(offset)

  textures: List[TIM] = []
  for i, offset in enumerate(offsets):
    end_offset = offsets[i + 1] if i + 1 < len(offsets) else len(stream.getbuffer())
    stream.seek(offset)
    textures.append(TIM(stream=BytesIO(stream.read(end_offset - offset)), name=f"{name_prefix}_{i}"))

  return offsets, textures
