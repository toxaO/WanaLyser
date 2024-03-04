from . import util as util
from _typeshed import Incomplete
from numpy.testing import IS_PYPY as IS_PYPY

class TestBlockDocString(util.F2PyTest):
    sources: Incomplete
    def test_block_docstring(self) -> None: ...
