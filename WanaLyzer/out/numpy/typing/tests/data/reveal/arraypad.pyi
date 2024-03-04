import numpy as np
import numpy.typing as npt
from collections.abc import Mapping
from typing import Any, SupportsIndex

def mode_func(ar: npt.NDArray[np.number[Any]], width: tuple[int, int], iaxis: SupportsIndex, kwargs: Mapping[str, Any]) -> None: ...

AR_i8: npt.NDArray[np.int64]
AR_f8: npt.NDArray[np.float64]
AR_LIKE: list[int]
