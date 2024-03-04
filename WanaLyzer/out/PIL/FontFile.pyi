from . import Image as Image
from _typeshed import Incomplete
from typing import BinaryIO

WIDTH: int

def puti16(fp: BinaryIO, values: tuple[int, int, int, int, int, int, int, int, int, int]) -> None: ...

class FontFile:
    bitmap: Image.Image | None
    info: Incomplete
    glyph: Incomplete
    def __init__(self) -> None: ...
    def __getitem__(self, ix: int) -> tuple[tuple[int, int], tuple[int, int, int, int], tuple[int, int, int, int], Image.Image] | None: ...
    ysize: Incomplete
    metrics: Incomplete
    def compile(self) -> None: ...
    def save(self, filename: str) -> None: ...
