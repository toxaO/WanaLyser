from collections.abc import Sequence
from numpy._typing import _NestedSequence

a: Sequence[float]
b: list[complex]
c: tuple[str, ...]
d: int
e: str

def func(a: _NestedSequence[int]) -> None: ...
