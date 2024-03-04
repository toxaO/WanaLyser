import numpy as np
from numpy._typing import _SupportsArray

class Index:
    def __index__(self) -> int: ...

a: np.flatiter[np.ndarray]
supports_array: _SupportsArray
