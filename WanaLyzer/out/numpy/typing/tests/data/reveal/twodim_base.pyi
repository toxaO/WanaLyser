import numpy as np
import numpy.typing as npt
from typing import Any

def func1(ar: npt.NDArray[_SCT], a: int) -> npt.NDArray[_SCT]: ...
def func2(ar: npt.NDArray[np.number[Any]], a: str) -> npt.NDArray[np.float64]: ...

AR_b: npt.NDArray[np.bool_]
AR_u: npt.NDArray[np.uint64]
AR_i: npt.NDArray[np.int64]
AR_f: npt.NDArray[np.float64]
AR_c: npt.NDArray[np.complex128]
AR_O: npt.NDArray[np.object_]
AR_LIKE_b: list[bool]
