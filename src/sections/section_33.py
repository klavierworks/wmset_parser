from dataclasses import dataclass
from typing import List, Union
from io import BytesIO
from utils.binary_reader import BinaryReader


@dataclass
class DictWordToken:
    dict_index: int


@dataclass
class ArgSubstToken:
    arg_index: int


TextTemplateToken = Union[DictWordToken, ArgSubstToken]


@dataclass
class TextTemplate:
    tokens: List[TextTemplateToken]


@dataclass(init=False)
class Section33:
    offsets: List[int]
    templates: List[TextTemplate]

    def __init__(self, stream: BytesIO):
        self.offsets = self.parse_offsets(stream)
        self.templates = self.parse_templates(stream)

    def parse_offsets(self, stream: BytesIO) -> List[int]:
        offsets: List[int] = []
        while True:
            offset = BinaryReader.read_uint32(stream)
            if offset == 0:
                break
            offsets.append(offset)
        return offsets

    def parse_templates(self, stream: BytesIO) -> List[TextTemplate]:
        return [self.parse_template(stream, offset) for offset in self.offsets]

    def parse_template(self, stream: BytesIO, offset: int) -> TextTemplate:
        stream.seek(offset)
        tokens: List[TextTemplateToken] = []
        while True:
            byte = BinaryReader.read_uint8(stream)
            if byte == 0x0A:
                next_byte = BinaryReader.read_uint8(stream)
                if next_byte == 0xFF:
                    break
                if next_byte >= 0x20:
                    tokens.append(ArgSubstToken(arg_index=next_byte - 0x20))
            else:
                tokens.append(DictWordToken(dict_index=byte))
        return TextTemplate(tokens=tokens)
