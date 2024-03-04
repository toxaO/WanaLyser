from _typeshed import Incomplete
from numpy.distutils.fcompiler.gnu import GnuFCompiler as GnuFCompiler

compilers: Incomplete

class VastFCompiler(GnuFCompiler):
    compiler_type: str
    compiler_aliases: Incomplete
    description: str
    version_pattern: str
    object_switch: str
    executables: Incomplete
    module_dir_switch: Incomplete
    module_include_switch: Incomplete
    def find_executables(self) -> None: ...
    def get_version_cmd(self): ...
    version: Incomplete
    def get_flags_arch(self): ...
