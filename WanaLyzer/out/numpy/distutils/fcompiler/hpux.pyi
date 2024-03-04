from _typeshed import Incomplete
from numpy.distutils.fcompiler import FCompiler as FCompiler

compilers: Incomplete

class HPUXFCompiler(FCompiler):
    compiler_type: str
    description: str
    version_pattern: str
    executables: Incomplete
    module_dir_switch: Incomplete
    module_include_switch: Incomplete
    pic_flags: Incomplete
    def get_flags(self): ...
    def get_flags_opt(self): ...
    def get_libraries(self): ...
    def get_library_dirs(self): ...
    def get_version(self, force: int = 0, ok_status=[256, 0, 1]): ...
