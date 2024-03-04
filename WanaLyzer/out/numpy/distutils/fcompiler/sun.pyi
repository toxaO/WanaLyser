from _typeshed import Incomplete
from numpy.distutils.ccompiler import simple_version_match as simple_version_match
from numpy.distutils.fcompiler import FCompiler as FCompiler

compilers: Incomplete

class SunFCompiler(FCompiler):
    compiler_type: str
    description: str
    version_match: Incomplete
    executables: Incomplete
    module_dir_switch: str
    module_include_switch: str
    pic_flags: Incomplete
    def get_flags_f77(self): ...
    def get_opt(self): ...
    def get_arch(self): ...
    def get_libraries(self): ...
    def runtime_library_dir_option(self, dir): ...
