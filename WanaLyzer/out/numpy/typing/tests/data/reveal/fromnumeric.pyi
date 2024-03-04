import numpy as np
import numpy.typing as npt

class NDArraySubclass(npt.NDArray[np.complex128]): ...

AR_b: npt.NDArray[np.bool_]
AR_f4: npt.NDArray[np.float32]
AR_c16: npt.NDArray[np.complex128]
AR_u8: npt.NDArray[np.uint64]
AR_i8: npt.NDArray[np.int64]
AR_O: npt.NDArray[np.object_]
AR_subclass: NDArraySubclass
b: np.bool_
f4: np.float32
i8: np.int64
f: float
