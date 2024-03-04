import numpy as np
import numpy.typing as npt
from typing import Any

def func1(ar: npt.NDArray[Any], a: int) -> npt.NDArray[np.str_]: ...
def func2(ar: npt.NDArray[Any], a: float) -> float: ...

AR_b: npt.NDArray[np.bool_]
AR_m: npt.NDArray[np.timedelta64]
AR_LIKE_b: list[bool]
