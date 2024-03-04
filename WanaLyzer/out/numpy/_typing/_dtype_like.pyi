from _typeshed import Incomplete
from typing import Any, Protocol, Sequence, TypedDict

class _DTypeDictBase(TypedDict):
    names: Sequence[str]
    formats: Sequence[_DTypeLikeNested]

class _DTypeDict(_DTypeDictBase, total=False):
    offsets: Sequence[int]
    titles: Sequence[Any]
    itemsize: int
    aligned: bool

class _SupportsDType(Protocol[_DType_co]):
    @property
    def dtype(self) -> _DType_co: ...

DTypeLike: Incomplete
