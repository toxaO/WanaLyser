import numpy as np
from _typeshed import Incomplete
from typing import Any

class Index:
    def __index__(self) -> int: ...

class SubClass(np.ndarray): ...

def func(i: int, j: int, **kwargs: Any) -> SubClass: ...

i8: Incomplete
A: Incomplete
B: Incomplete
B_stack: Incomplete
C: Incomplete
