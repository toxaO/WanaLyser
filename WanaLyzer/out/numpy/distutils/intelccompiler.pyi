from _typeshed import Incomplete
from distutils.unixccompiler import UnixCCompiler
from numpy.distutils.ccompiler import simple_version_match as simple_version_match
from numpy.distutils.exec_command import find_executable as find_executable
from numpy.distutils.msvc9compiler import MSVCCompiler as MSVCCompiler

class IntelCCompiler(UnixCCompiler):
    compiler_type: str
    cc_exe: str
    cc_args: str
    def __init__(self, verbose: int = 0, dry_run: int = 0, force: int = 0) -> None: ...

class IntelItaniumCCompiler(IntelCCompiler):
    compiler_type: str

class IntelEM64TCCompiler(UnixCCompiler):
    compiler_type: str
    cc_exe: str
    cc_args: str
    def __init__(self, verbose: int = 0, dry_run: int = 0, force: int = 0) -> None: ...

class IntelCCompilerW(MSVCCompiler):
    compiler_type: str
    compiler_cxx: str
    def __init__(self, verbose: int = 0, dry_run: int = 0, force: int = 0) -> None: ...
    cc: Incomplete
    lib: Incomplete
    linker: Incomplete
    compile_options: Incomplete
    compile_options_debug: Incomplete
    def initialize(self, plat_name: Incomplete | None = None) -> None: ...

class IntelEM64TCCompilerW(IntelCCompilerW):
    compiler_type: str
    def __init__(self, verbose: int = 0, dry_run: int = 0, force: int = 0) -> None: ...
