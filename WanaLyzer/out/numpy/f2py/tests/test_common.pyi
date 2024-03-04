from . import util as util
from _typeshed import Incomplete

class TestCommonBlock(util.F2PyTest):
    sources: Incomplete
    def test_common_block(self) -> None: ...

class TestCommonWithUse(util.F2PyTest):
    sources: Incomplete
    def test_common_gh19161(self) -> None: ...
