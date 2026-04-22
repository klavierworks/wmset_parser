from io import BytesIO
from typing import List

from sections.textures.tim import TIM

TEXL_SLOT_SIZE = 0x12800
TEXL_COUNT = 20


def parse_texl(filepath: str) -> List[TIM]:
    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) < TEXL_SLOT_SIZE * TEXL_COUNT:
        raise ValueError(
            f"texl.obj size {len(data)} too small for {TEXL_COUNT} slots of 0x{TEXL_SLOT_SIZE:x}"
        )
    tims: List[TIM] = []
    for i in range(TEXL_COUNT):
        start = i * TEXL_SLOT_SIZE
        slot = data[start:start + TEXL_SLOT_SIZE]
        tims.append(TIM(stream=BytesIO(slot), name=f"texl_{i}"))
    return tims
