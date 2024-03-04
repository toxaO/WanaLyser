from . import util as util
from _typeshed import Incomplete

class TestIntentInOut(util.F2PyTest):
    sources: Incomplete
    def test_inout(self) -> None: ...

class TestNegativeBounds(util.F2PyTest):
    sources: Incomplete
    def test_negbound(self): ...

class TestNumpyVersionAttribute(util.F2PyTest):
    sources: Incomplete
    def test_numpy_version_attribute(self) -> None: ...

def test_include_path() -> None: ...

class TestModuleAndSubroutine(util.F2PyTest):
    module_name: str
    sources: Incomplete
    def test_gh25337(self) -> None: ...
