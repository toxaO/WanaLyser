from . import util as util
from _typeshed import Incomplete
from numpy.testing import IS_PYPY as IS_PYPY

class TestMixed(util.F2PyTest):
    sources: Incomplete
    def test_all(self) -> None: ...
    def test_docstring(self) -> None: ...
