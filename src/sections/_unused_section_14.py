from dataclasses import dataclass
from io import BytesIO


@dataclass(init=False)
class UnusedSection14:
    data: bytes

    def __init__(self, stream: BytesIO) -> None:
        self.data = stream.read()
