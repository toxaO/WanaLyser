from . import util as util
from _typeshed import Incomplete

class TestString(util.F2PyTest):
    sources: Incomplete
    def test_char(self) -> None: ...

class TestDocStringArguments(util.F2PyTest):
    sources: Incomplete
    def test_example(self) -> None: ...

class TestFixedString(util.F2PyTest):
    sources: Incomplete
    def test_intent_in(self) -> None: ...
    def test_intent_inout(self) -> None: ...
