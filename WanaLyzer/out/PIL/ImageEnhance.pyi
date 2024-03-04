from . import Image as Image, ImageFilter as ImageFilter, ImageStat as ImageStat
from _typeshed import Incomplete

class _Enhance:
    def enhance(self, factor): ...

class Color(_Enhance):
    image: Incomplete
    intermediate_mode: str
    degenerate: Incomplete
    def __init__(self, image) -> None: ...

class Contrast(_Enhance):
    image: Incomplete
    degenerate: Incomplete
    def __init__(self, image) -> None: ...

class Brightness(_Enhance):
    image: Incomplete
    degenerate: Incomplete
    def __init__(self, image) -> None: ...

class Sharpness(_Enhance):
    image: Incomplete
    degenerate: Incomplete
    def __init__(self, image) -> None: ...
