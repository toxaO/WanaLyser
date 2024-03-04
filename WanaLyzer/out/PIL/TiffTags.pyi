from _typeshed import Incomplete
from typing import NamedTuple

class TagInfo(NamedTuple('_TagInfo', [('value', Incomplete), ('name', Incomplete), ('type', Incomplete), ('length', Incomplete), ('enum', Incomplete)])):
    def __new__(cls, value: Incomplete | None = None, name: str = 'unknown', type: Incomplete | None = None, length: Incomplete | None = None, enum: Incomplete | None = None): ...
    def cvt_enum(self, value): ...

def lookup(tag, group: Incomplete | None = None): ...

BYTE: int
ASCII: int
SHORT: int
LONG: int
RATIONAL: int
SIGNED_BYTE: int
UNDEFINED: int
SIGNED_SHORT: int
SIGNED_LONG: int
SIGNED_RATIONAL: int
FLOAT: int
DOUBLE: int
IFD: int
LONG8: int
TAGS_V2: Incomplete
TAGS_V2_GROUPS: Incomplete
TAGS: Incomplete
TYPES: Incomplete
LIBTIFF_CORE: Incomplete
