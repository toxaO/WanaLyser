from _typeshed import Incomplete
from numpy.distutils.ccompiler import simple_version_match as simple_version_match
from numpy.distutils.fcompiler import FCompiler as FCompiler, dummy_fortran_file as dummy_fortran_file

compilers: Incomplete

def intel_version_match(type): ...

class BaseIntelFCompiler(FCompiler):
    def update_executables(self) -> None: ...
    def runtime_library_dir_option(self, dir): ...

class IntelFCompiler(BaseIntelFCompiler):
    compiler_type: str
    compiler_aliases: Incomplete
    description: str
    version_match: Incomplete
    possible_executables: Incomplete
    executables: Incomplete
    pic_flags: Incomplete
    module_dir_switch: str
    module_include_switch: str
    def get_flags_free(self): ...
    def get_flags(self): ...
    def get_flags_opt(self): ...
    def get_flags_arch(self): ...
    def get_flags_linker_so(self): ...

class IntelItaniumFCompiler(IntelFCompiler):
    compiler_type: str
    compiler_aliases: Incomplete
    description: str
    version_match: Incomplete
    possible_executables: Incomplete
    executables: Incomplete

class IntelEM64TFCompiler(IntelFCompiler):
    compiler_type: str
    compiler_aliases: Incomplete
    description: str
    version_match: Incomplete
    possible_executables: Incomplete
    executables: Incomplete

class IntelVisualFCompiler(BaseIntelFCompiler):
    compiler_type: str
    description: str
    version_match: Incomplete
    def update_executables(self) -> None: ...
    ar_exe: str
    possible_executables: Incomplete
    executables: Incomplete
    compile_switch: str
    object_switch: str
    library_switch: str
    module_dir_switch: str
    module_include_switch: str
    def get_flags(self): ...
    def get_flags_free(self): ...
    def get_flags_debug(self): ...
    def get_flags_opt(self): ...
    def get_flags_arch(self): ...
    def runtime_library_dir_option(self, dir) -> None: ...

class IntelItaniumVisualFCompiler(IntelVisualFCompiler):
    compiler_type: str
    description: str
    version_match: Incomplete
    possible_executables: Incomplete
    ar_exe: Incomplete
    executables: Incomplete

class IntelEM64VisualFCompiler(IntelVisualFCompiler):
    compiler_type: str
    description: str
    version_match: Incomplete
    def get_flags_arch(self): ...
