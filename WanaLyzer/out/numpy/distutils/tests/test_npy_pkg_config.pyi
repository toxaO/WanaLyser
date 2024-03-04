from _typeshed import Incomplete
from numpy.distutils.npy_pkg_config import parse_flags as parse_flags, read_config as read_config
from numpy.testing import assert_ as assert_, temppath as temppath

simple: str
simple_d: Incomplete
simple_variable: str
simple_variable_d: Incomplete

class TestLibraryInfo:
    def test_simple(self) -> None: ...
    def test_simple_variable(self) -> None: ...

class TestParseFlags:
    def test_simple_cflags(self) -> None: ...
    def test_simple_lflags(self) -> None: ...
