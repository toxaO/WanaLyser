from collections.abc import Sequence
from numpy._typing import _NestedSequence
from typing import Any

a: Sequence[int]
b: Sequence[Sequence[int]]
c: Sequence[Sequence[Sequence[int]]]
d: Sequence[Sequence[Sequence[Sequence[int]]]]
e: Sequence[bool]
f: tuple[int, ...]
g: list[int]
h: Sequence[Any]

def func(a: _NestedSequence[int]) -> None: ...
