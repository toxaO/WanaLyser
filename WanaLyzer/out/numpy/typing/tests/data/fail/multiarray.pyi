import numpy as np
import numpy.typing as npt

i8: np.int64
AR_b: npt.NDArray[np.bool_]
AR_u1: npt.NDArray[np.uint8]
AR_i8: npt.NDArray[np.int64]
AR_f8: npt.NDArray[np.float64]
AR_M: npt.NDArray[np.datetime64]
M: np.datetime64
AR_LIKE_f: list[float]

def func(a: int) -> None: ...
