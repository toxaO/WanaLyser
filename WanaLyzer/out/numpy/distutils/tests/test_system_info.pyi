from _typeshed import Incomplete
from numpy.distutils import ccompiler as ccompiler, customized_ccompiler as customized_ccompiler
from numpy.distutils.system_info import AliasedOptionError as AliasedOptionError, ConfigParser as ConfigParser, default_include_dirs as default_include_dirs, default_lib_dirs as default_lib_dirs, mkl_info as mkl_info, system_info as system_info
from numpy.testing import assert_ as assert_, assert_equal as assert_equal, assert_raises as assert_raises

def get_class(name, notfound_action: int = 1): ...

simple_site: str
site_cfg = simple_site
fakelib_c_text: str

def have_compiler(): ...

HAVE_COMPILER: Incomplete

class _system_info(system_info):
    local_prefixes: Incomplete
    cp: Incomplete
    def __init__(self, default_lib_dirs=..., default_include_dirs=..., verbosity: int = 1) -> None: ...

class Temp1Info(_system_info):
    section: str

class Temp2Info(_system_info):
    section: str

class DuplicateOptionInfo(_system_info):
    section: str

class TestSystemInfoReading:
    c_default: Incomplete
    c_temp1: Incomplete
    c_temp2: Incomplete
    c_dup_options: Incomplete
    def setup_method(self): ...
    def teardown_method(self) -> None: ...
    def test_all(self) -> None: ...
    def test_temp1(self) -> None: ...
    def test_temp2(self) -> None: ...
    def test_duplicate_options(self) -> None: ...
    def test_compile1(self) -> None: ...
    def test_compile2(self) -> None: ...
    HAS_MKL: Incomplete
    def test_overrides(self) -> None: ...

def test_distutils_parse_env_order(monkeypatch) -> None: ...
