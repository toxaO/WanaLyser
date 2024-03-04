import io
import numpy as np
import numpy.typing as npt
from typing import Any

AR_i8: npt.NDArray[np.int64]
REC_AR_V: np.recarray[Any, np.dtype[np.record]]
AR_LIST: list[npt.NDArray[np.int64]]
format_parser: np.format_parser
record: np.record
file_obj: io.BufferedIOBase
