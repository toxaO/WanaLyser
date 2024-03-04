import numpy as np
from _typeshed import Incomplete
from typing import Any

c16: Incomplete
f8: Incomplete
i8: Incomplete
u8: Incomplete
c8: Incomplete
f4: Incomplete
i4: Incomplete
u4: Incomplete
dt: Incomplete
td: Incomplete
b_: Incomplete
b: Incomplete
c: Incomplete
f: Incomplete
i: Incomplete

class Object:
    def __array__(self) -> np.ndarray[Any, np.dtype[np.object_]]: ...
    def __sub__(self, value: Any) -> Object: ...
    def __rsub__(self, value: Any) -> Object: ...
    def __floordiv__(self, value: Any) -> Object: ...
    def __rfloordiv__(self, value: Any) -> Object: ...
    def __mul__(self, value: Any) -> Object: ...
    def __rmul__(self, value: Any) -> Object: ...
    def __pow__(self, value: Any) -> Object: ...
    def __rpow__(self, value: Any) -> Object: ...

AR_b: np.ndarray[Any, np.dtype[np.bool_]]
AR_u: np.ndarray[Any, np.dtype[np.uint32]]
AR_i: np.ndarray[Any, np.dtype[np.int64]]
AR_f: np.ndarray[Any, np.dtype[np.float64]]
AR_c: np.ndarray[Any, np.dtype[np.complex128]]
AR_m: np.ndarray[Any, np.dtype[np.timedelta64]]
AR_M: np.ndarray[Any, np.dtype[np.datetime64]]
AR_O: np.ndarray[Any, np.dtype[np.object_]]
AR_LIKE_b: Incomplete
AR_LIKE_u: Incomplete
AR_LIKE_i: Incomplete
AR_LIKE_f: Incomplete
AR_LIKE_c: Incomplete
AR_LIKE_m: Incomplete
AR_LIKE_M: Incomplete
AR_LIKE_O: Incomplete
