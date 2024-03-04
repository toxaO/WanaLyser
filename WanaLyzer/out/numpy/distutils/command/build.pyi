from _typeshed import Incomplete
from distutils.command.build import build as old_build
from numpy.distutils.command.config_compiler import show_fortran_compilers as show_fortran_compilers

class build(old_build):
    sub_commands: Incomplete
    user_options: Incomplete
    help_options: Incomplete
    fcompiler: Incomplete
    warn_error: bool
    cpu_baseline: str
    cpu_dispatch: str
    disable_optimization: bool
    simd_test: str
    def initialize_options(self) -> None: ...
    build_scripts: Incomplete
    def finalize_options(self) -> None: ...
    def run(self) -> None: ...
