from . import util as util
from _typeshed import Incomplete
from numpy.f2py import crackfortran as crackfortran
from numpy.testing import IS_WASM as IS_WASM
from pathlib import Path as Path

class TestAbstractInterface(util.F2PyTest):
    sources: Incomplete
    skip: Incomplete
    def test_abstract_interface(self) -> None: ...
    def test_parse_abstract_interface(self) -> None: ...
