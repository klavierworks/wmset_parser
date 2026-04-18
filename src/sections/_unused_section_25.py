from dataclasses import dataclass
from io import BytesIO

@dataclass(init=False)
class UnusedSection25:
  def __init__(self, stream: BytesIO):
    pass
