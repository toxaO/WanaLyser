from collections.abc import Iterable
from numpy import ndarray as ndarray
from numpy._typing import DTypeLike as DTypeLike, _SupportsArrayFunc
from typing import Any, overload

@overload
def require(a: _ArrayType, dtype: None = ..., requirements: None | _Requirements | Iterable[_Requirements] = ..., *, like: _SupportsArrayFunc = ...) -> _ArrayType: ...
@overload
def require(a: object, dtype: DTypeLike = ..., requirements: _E | Iterable[_RequirementsWithE] = ..., *, like: _SupportsArrayFunc = ...) -> ndarray[Any, Any]: ...
@overload
def require(a: object, dtype: DTypeLike = ..., requirements: None | _Requirements | Iterable[_Requirements] = ..., *, like: _SupportsArrayFunc = ...) -> ndarray[Any, Any]: ...
