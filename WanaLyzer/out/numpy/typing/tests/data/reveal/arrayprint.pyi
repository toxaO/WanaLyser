import numpy as np
from collections.abc import Callable as Callable
from typing import Any

AR: np.ndarray[Any, Any]
func_float: Callable[[np.floating[Any]], str]
func_int: Callable[[np.integer[Any]], str]
