import numpy as np
from _typeshed import Incomplete
from typing import Any

class Object:
    def __ceil__(self) -> Object: ...
    def __floor__(self) -> Object: ...
    def __ge__(self, value: object) -> bool: ...
    def __array__(self) -> np.ndarray[Any, np.dtype[np.object_]]: ...

AR_LIKE_b: Incomplete
AR_LIKE_u: Incomplete
AR_LIKE_i: Incomplete
AR_LIKE_f: Incomplete
AR_LIKE_O: Incomplete
AR_U: np.ndarray[Any, np.dtype[np.str_]]
