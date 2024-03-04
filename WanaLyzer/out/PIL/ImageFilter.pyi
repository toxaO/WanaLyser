from _typeshed import Incomplete

class Filter: ...
class MultibandFilter(Filter): ...

class BuiltinFilter(MultibandFilter):
    def filter(self, image): ...

class Kernel(BuiltinFilter):
    name: str
    filterargs: Incomplete
    def __init__(self, size, kernel, scale: Incomplete | None = None, offset: int = 0) -> None: ...

class RankFilter(Filter):
    name: str
    size: Incomplete
    rank: Incomplete
    def __init__(self, size, rank) -> None: ...
    def filter(self, image): ...

class MedianFilter(RankFilter):
    name: str
    size: Incomplete
    rank: Incomplete
    def __init__(self, size: int = 3) -> None: ...

class MinFilter(RankFilter):
    name: str
    size: Incomplete
    rank: int
    def __init__(self, size: int = 3) -> None: ...

class MaxFilter(RankFilter):
    name: str
    size: Incomplete
    rank: Incomplete
    def __init__(self, size: int = 3) -> None: ...

class ModeFilter(Filter):
    name: str
    size: Incomplete
    def __init__(self, size: int = 3) -> None: ...
    def filter(self, image): ...

class GaussianBlur(MultibandFilter):
    name: str
    radius: Incomplete
    def __init__(self, radius: int = 2) -> None: ...
    def filter(self, image): ...

class BoxBlur(MultibandFilter):
    name: str
    radius: Incomplete
    def __init__(self, radius) -> None: ...
    def filter(self, image): ...

class UnsharpMask(MultibandFilter):
    name: str
    radius: Incomplete
    percent: Incomplete
    threshold: Incomplete
    def __init__(self, radius: int = 2, percent: int = 150, threshold: int = 3) -> None: ...
    def filter(self, image): ...

class BLUR(BuiltinFilter):
    name: str
    filterargs: Incomplete

class CONTOUR(BuiltinFilter):
    name: str
    filterargs: Incomplete

class DETAIL(BuiltinFilter):
    name: str
    filterargs: Incomplete

class EDGE_ENHANCE(BuiltinFilter):
    name: str
    filterargs: Incomplete

class EDGE_ENHANCE_MORE(BuiltinFilter):
    name: str
    filterargs: Incomplete

class EMBOSS(BuiltinFilter):
    name: str
    filterargs: Incomplete

class FIND_EDGES(BuiltinFilter):
    name: str
    filterargs: Incomplete

class SHARPEN(BuiltinFilter):
    name: str
    filterargs: Incomplete

class SMOOTH(BuiltinFilter):
    name: str
    filterargs: Incomplete

class SMOOTH_MORE(BuiltinFilter):
    name: str
    filterargs: Incomplete

class Color3DLUT(MultibandFilter):
    name: str
    size: Incomplete
    channels: Incomplete
    mode: Incomplete
    table: Incomplete
    def __init__(self, size, table, channels: int = 3, target_mode: Incomplete | None = None, **kwargs) -> None: ...
    @classmethod
    def generate(cls, size, callback, channels: int = 3, target_mode: Incomplete | None = None): ...
    def transform(self, callback, with_normals: bool = False, channels: Incomplete | None = None, target_mode: Incomplete | None = None): ...
    def filter(self, image): ...
