from . import FontFile as FontFile, Image as Image
from _typeshed import Incomplete
from typing import BinaryIO

bdf_slant: Incomplete
bdf_spacing: Incomplete

def bdf_char(f: BinaryIO) -> tuple[str, int, tuple[tuple[int, int], tuple[int, int, int, int], tuple[int, int, int, int]], Image.Image] | None: ...

class BdfFontFile(FontFile.FontFile):
    def __init__(self, fp: BinaryIO) -> None: ...
