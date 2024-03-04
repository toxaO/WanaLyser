import numpy as np
import numpy.typing as npt
from _typeshed import Incomplete
from numpy._typing import _128Bit
from typing import Any

f16: np.floating[_128Bit]
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
AR_b: npt.NDArray[np.bool_]
AR_u: npt.NDArray[np.uint32]
AR_i: npt.NDArray[np.int64]
AR_f: npt.NDArray[np.float64]
AR_c: npt.NDArray[np.complex128]
AR_m: npt.NDArray[np.timedelta64]
AR_M: npt.NDArray[np.datetime64]
AR_O: npt.NDArray[np.object_]
AR_number: npt.NDArray[np.number[Any]]
AR_LIKE_b: list[bool]
AR_LIKE_u: list[np.uint32]
AR_LIKE_i: list[int]
AR_LIKE_f: list[float]
AR_LIKE_c: list[complex]
AR_LIKE_m: list[np.timedelta64]
AR_LIKE_M: list[np.datetime64]
AR_LIKE_O: list[np.object_]
