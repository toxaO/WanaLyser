import numpy as np
import numpy.typing as npt

class SubClass(npt.NDArray[np.int64]): ...

i8: np.int64
AR_b: npt.NDArray[np.bool_]
AR_u8: npt.NDArray[np.uint64]
AR_i8: npt.NDArray[np.int64]
AR_f8: npt.NDArray[np.float64]
AR_c16: npt.NDArray[np.complex128]
AR_m: npt.NDArray[np.timedelta64]
AR_O: npt.NDArray[np.object_]
B: list[int]
C: SubClass
