import ctypes as ct
import numpy as np
import numpy.typing as npt
from numpy import ctypeslib as ctypeslib
from typing import Any

AR_bool: npt.NDArray[np.bool_]
AR_ubyte: npt.NDArray[np.ubyte]
AR_ushort: npt.NDArray[np.ushort]
AR_uintc: npt.NDArray[np.uintc]
AR_uint: npt.NDArray[np.uint]
AR_ulonglong: npt.NDArray[np.ulonglong]
AR_byte: npt.NDArray[np.byte]
AR_short: npt.NDArray[np.short]
AR_intc: npt.NDArray[np.intc]
AR_int: npt.NDArray[np.int_]
AR_longlong: npt.NDArray[np.longlong]
AR_single: npt.NDArray[np.single]
AR_double: npt.NDArray[np.double]
AR_longdouble: npt.NDArray[np.longdouble]
AR_void: npt.NDArray[np.void]
pointer: ct._Pointer[Any]
