from . import util as util
from _typeshed import Incomplete
from numpy import array as array

class TestReturnReal(util.F2PyTest):
    def check_function(self, t, tname) -> None: ...

class TestCReturnReal(TestReturnReal):
    suffix: str
    module_name: str
    code: str
    def test_all(self, name) -> None: ...

class TestFReturnReal(TestReturnReal):
    sources: Incomplete
    def test_all_f77(self, name) -> None: ...
    def test_all_f90(self, name) -> None: ...
