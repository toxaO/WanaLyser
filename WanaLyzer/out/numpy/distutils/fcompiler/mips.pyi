from _typeshed import Incomplete
from numpy.distutils.cpuinfo import cpu as cpu
from numpy.distutils.fcompiler import FCompiler as FCompiler

compilers: Incomplete

class MIPSFCompiler(FCompiler):
    compiler_type: str
    description: str
    version_pattern: str
    executables: Incomplete
    module_dir_switch: Incomplete
    module_include_switch: Incomplete
    pic_flags: Incomplete
    def get_flags(self): ...
    def get_flags_opt(self): ...
    def get_flags_arch(self): ...
    def get_flags_arch_f77(self): ...
    def get_flags_arch_f90(self): ...
