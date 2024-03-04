from . import util as util
from _typeshed import Incomplete

class TestMultiline(util.F2PyTest):
    suffix: str
    module_name: str
    code: Incomplete
    def test_multiline(self) -> None: ...

class TestCallstatement(util.F2PyTest):
    suffix: str
    module_name: str
    code: Incomplete
    def test_callstatement(self) -> None: ...
