from _typeshed import Incomplete
from numpy.distutils.fcompiler import FCompiler as FCompiler

compilers: Incomplete

class LaheyFCompiler(FCompiler):
    compiler_type: str
    description: str
    version_pattern: str
    executables: Incomplete
    module_dir_switch: Incomplete
    module_include_switch: Incomplete
    def get_flags_opt(self): ...
    def get_flags_debug(self): ...
    def get_library_dirs(self): ...
    def get_libraries(self): ...
