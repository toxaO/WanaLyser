import numpy as np
from _typeshed import Incomplete

class TestResolveDescriptors:
    method: Incomplete
    def test_invalid_arguments(self, args) -> None: ...

class TestSimpleStridedCall:
    method: Incomplete
    def test_invalid_arguments(self, args, error) -> None: ...

class TestClassGetItem:
    def test_class_getitem(self, cls: type[np.ndarray]) -> None: ...
    def test_subscript_tup(self, cls: type[np.ndarray], arg_len: int) -> None: ...
