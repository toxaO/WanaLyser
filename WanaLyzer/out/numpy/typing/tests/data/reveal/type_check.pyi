import numpy as np
import numpy.typing as npt
from numpy._typing import _128Bit

f8: np.float64
f: float
AR_i8: npt.NDArray[np.int64]
AR_i4: npt.NDArray[np.int32]
AR_f2: npt.NDArray[np.float16]
AR_f8: npt.NDArray[np.float64]
AR_f16: npt.NDArray[np.floating[_128Bit]]
AR_c8: npt.NDArray[np.complex64]
AR_c16: npt.NDArray[np.complex128]
AR_LIKE_f: list[float]

class RealObj:
    real: slice

class ImagObj:
    imag: slice
