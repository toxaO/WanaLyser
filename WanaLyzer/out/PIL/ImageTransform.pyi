from . import Image as Image
from _typeshed import Incomplete
from typing import Sequence

class Transform(Image.ImageTransformHandler):
    method: Image.Transform
    data: Incomplete
    def __init__(self, data: Sequence[int]) -> None: ...
    def getdata(self) -> tuple[int, Sequence[int]]: ...
    def transform(self, size: tuple[int, int], image: Image.Image, **options: dict[str, str | int | tuple[int, ...] | list[int]]) -> Image.Image: ...

class AffineTransform(Transform):
    method: Incomplete

class ExtentTransform(Transform):
    method: Incomplete

class QuadTransform(Transform):
    method: Incomplete

class MeshTransform(Transform):
    method: Incomplete
