import numpy as np
import numpy.typing as npt
from io import StringIO
from typing import Protocol

AR: npt.NDArray[np.float64]
AR_DICT: dict[str, npt.NDArray[np.float64]]
FILE: StringIO

def func(a: int) -> bool: ...

class FuncProtocol(Protocol):
    def __call__(self, a: int) -> bool: ...
