from . import FontFile as FontFile, Image as Image
from ._binary import i8 as i8
from _typeshed import Incomplete
from typing import BinaryIO, Callable

PCF_MAGIC: int
PCF_PROPERTIES: Incomplete
PCF_ACCELERATORS: Incomplete
PCF_METRICS: Incomplete
PCF_BITMAPS: Incomplete
PCF_INK_METRICS: Incomplete
PCF_BDF_ENCODINGS: Incomplete
PCF_SWIDTHS: Incomplete
PCF_GLYPH_NAMES: Incomplete
PCF_BDF_ACCELERATORS: Incomplete
BYTES_PER_ROW: list[Callable[[int], int]]

def sz(s: bytes, o: int) -> bytes: ...

class PcfFontFile(FontFile.FontFile):
    name: str
    charset_encoding: Incomplete
    toc: Incomplete
    fp: Incomplete
    info: Incomplete
    def __init__(self, fp: BinaryIO, charset_encoding: str = 'iso8859-1') -> None: ...
