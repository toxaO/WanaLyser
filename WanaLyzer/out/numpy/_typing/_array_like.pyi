from _typeshed import Incomplete
from collections.abc import Callable as Callable, Collection
from numpy import bool_ as bool_, bytes_ as bytes_, complexfloating as complexfloating, datetime64 as datetime64, dtype as dtype, floating as floating, generic as generic, integer as integer, ndarray as ndarray, number as number, object_ as object_, str_ as str_, timedelta64 as timedelta64, unsignedinteger as unsignedinteger, void as void
from typing import Any, Protocol

NDArray: Incomplete

class _SupportsArray(Protocol[_DType_co]):
    def __array__(self) -> ndarray[Any, _DType_co]: ...

class _SupportsArrayFunc(Protocol):
    def __array_function__(self, func: Callable[..., Any], types: Collection[type[Any]], args: tuple[Any, ...], kwargs: dict[str, Any]) -> object: ...

ArrayLike: Incomplete

class _UnknownType: ...
