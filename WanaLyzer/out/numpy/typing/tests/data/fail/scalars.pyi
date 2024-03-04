import numpy as np

f2: np.float16
f8: np.float64
c8: np.complex64

class A:
    def __float__(self) -> float: ...

def func(a: np.float32) -> None: ...
