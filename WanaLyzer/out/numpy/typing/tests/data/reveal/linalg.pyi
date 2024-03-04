import numpy as np
import numpy.typing as npt
from numpy.linalg.linalg import EigResult as EigResult, EighResult as EighResult, QRResult as QRResult, SVDResult as SVDResult, SlogdetResult as SlogdetResult

AR_i8: npt.NDArray[np.int64]
AR_f8: npt.NDArray[np.float64]
AR_c16: npt.NDArray[np.complex128]
AR_O: npt.NDArray[np.object_]
AR_m: npt.NDArray[np.timedelta64]
AR_S: npt.NDArray[np.str_]
