from . import util as util
from _typeshed import Incomplete
from numpy import array as array

class TestReturnLogical(util.F2PyTest):
    def check_function(self, t) -> None: ...

class TestFReturnLogical(TestReturnLogical):
    sources: Incomplete
    def test_all_f77(self, name) -> None: ...
    def test_all_f90(self, name) -> None: ...
