import numpy as np
from numpy._typing import ArrayLike as ArrayLike, _SupportsArray
from typing import Any

x1: ArrayLike
x2: ArrayLike
x3: ArrayLike
x4: ArrayLike
x5: ArrayLike
x6: ArrayLike
x7: ArrayLike
x8: ArrayLike
x9: ArrayLike
x10: ArrayLike
x11: ArrayLike
x12: ArrayLike

class A:
    def __array__(self, dtype: None | np.dtype[Any] = None) -> np.ndarray: ...

x13: ArrayLike
scalar: _SupportsArray
array: _SupportsArray
a: _SupportsArray
object_array_scalar: Any
