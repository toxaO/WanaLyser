import numpy as np
import numpy.typing as npt
from typing import Any

vectorized_func: np.vectorize
f8: np.float64
AR_LIKE_f8: list[float]
AR_i8: npt.NDArray[np.int64]
AR_f8: npt.NDArray[np.float64]
AR_c16: npt.NDArray[np.complex128]
AR_m: npt.NDArray[np.timedelta64]
AR_M: npt.NDArray[np.datetime64]
AR_O: npt.NDArray[np.object_]
AR_b: npt.NDArray[np.bool_]
AR_U: npt.NDArray[np.str_]
CHAR_AR_U: np.chararray[Any, np.dtype[np.str_]]

def func(*args: Any, **kwargs: Any) -> Any: ...
