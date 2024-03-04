import numpy as np
import numpy.typing as npt
from typing import TypeVar

T1 = TypeVar('T1', bound=npt.NBitBase)
T2 = TypeVar('T2', bound=npt.NBitBase)

def add(a: np.floating[T1], b: np.integer[T2]) -> np.floating[T1 | T2]: ...

i8: np.int64
i4: np.int32
f8: np.float64
f4: np.float32
