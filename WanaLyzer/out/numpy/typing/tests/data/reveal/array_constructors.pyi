import numpy as np
import numpy.typing as npt
from typing import Any

class SubClass(np.ndarray[Any, np.dtype[_SCT]]): ...

i8: np.int64
A: npt.NDArray[np.float64]
B: SubClass[np.float64]
C: list[int]

def func(i: int, j: int, **kwargs: Any) -> SubClass[np.float64]: ...
