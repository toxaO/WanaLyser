from . import util as util
from _typeshed import Incomplete
from numpy.f2py.crackfortran import crackfortran as crackfortran

class TestData(util.F2PyTest):
    sources: Incomplete
    def test_data_stmts(self) -> None: ...
    def test_crackedlines(self) -> None: ...

class TestDataF77(util.F2PyTest):
    sources: Incomplete
    def test_data_stmts(self) -> None: ...
    def test_crackedlines(self) -> None: ...

class TestDataMultiplierF77(util.F2PyTest):
    sources: Incomplete
    def test_data_stmts(self) -> None: ...

class TestDataWithCommentsF77(util.F2PyTest):
    sources: Incomplete
    def test_data_stmts(self) -> None: ...
