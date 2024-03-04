from collections.abc import Mapping, Sequence
from numpy import matrix as matrix
from numpy._typing import ArrayLike as ArrayLike, DTypeLike as DTypeLike, NDArray as NDArray
from typing import Any

def bmat(obj: str | Sequence[ArrayLike] | NDArray[Any], ldict: None | Mapping[str, Any] = ..., gdict: None | Mapping[str, Any] = ...) -> matrix[Any, Any]: ...
def asmatrix(data: ArrayLike, dtype: DTypeLike = ...) -> matrix[Any, Any]: ...
mat = asmatrix
