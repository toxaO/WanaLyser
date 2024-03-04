import numpy as np
import numpy.typing as npt
from _typeshed import Incomplete

class SubClass(npt.NDArray[np.object_]): ...

f8: np.float64
B: SubClass
AR_f8: npt.NDArray[np.float64]
AR_i8: npt.NDArray[np.int64]
AR_U: npt.NDArray[np.str_]
AR_V: npt.NDArray[np.void]
ctypes_obj: Incomplete
