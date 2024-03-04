from _typeshed import Incomplete
from numpy.distutils.fcompiler import FCompiler as FCompiler

compilers: Incomplete

class FujitsuFCompiler(FCompiler):
    compiler_type: str
    description: str
    possible_executables: Incomplete
    version_pattern: str
    executables: Incomplete
    pic_flags: Incomplete
    module_dir_switch: str
    module_include_switch: str
    def get_flags_opt(self): ...
    def get_flags_debug(self): ...
    def runtime_library_dir_option(self, dir): ...
    def get_libraries(self): ...
