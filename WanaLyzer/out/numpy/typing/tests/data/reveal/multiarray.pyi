import datetime as dt
import numpy as np
import numpy.typing as npt
from _typeshed import Incomplete
from pathlib import Path as Path
from typing import Any

class SubClass(np.ndarray[Any, np.dtype[_SCT]]): ...

subclass: SubClass[np.float64]
AR_f8: npt.NDArray[np.float64]
AR_i8: npt.NDArray[np.int64]
AR_u1: npt.NDArray[np.uint8]
AR_m: npt.NDArray[np.timedelta64]
AR_M: npt.NDArray[np.datetime64]
AR_LIKE_f: list[float]
AR_LIKE_i: list[int]
m: np.timedelta64
M: np.datetime64
b_f8: Incomplete
b_i8_f8_f8: Incomplete
nditer_obj: np.nditer
date_scalar: dt.date
date_seq: list[dt.date]
timedelta_seq: list[dt.timedelta]

def func(a: int) -> bool: ...
