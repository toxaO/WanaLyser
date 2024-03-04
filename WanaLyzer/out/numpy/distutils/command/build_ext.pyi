from _typeshed import Incomplete
from distutils.command.build_ext import build_ext as old_build_ext
from numpy.distutils import log as log
from numpy.distutils.ccompiler_opt import CCompilerOpt as CCompilerOpt, new_ccompiler_opt as new_ccompiler_opt
from numpy.distutils.command.config_compiler import show_fortran_compilers as show_fortran_compilers
from numpy.distutils.exec_command import filepath_from_subprocess_output as filepath_from_subprocess_output
from numpy.distutils.misc_util import filter_sources as filter_sources, get_ext_source_files as get_ext_source_files, get_numpy_include_dirs as get_numpy_include_dirs, has_cxx_sources as has_cxx_sources, has_f_sources as has_f_sources, is_sequence as is_sequence
from numpy.distutils.system_info import combine_paths as combine_paths

class build_ext(old_build_ext):
    description: str
    user_options: Incomplete
    help_options: Incomplete
    boolean_options: Incomplete
    fcompiler: Incomplete
    parallel: Incomplete
    warn_error: Incomplete
    cpu_baseline: Incomplete
    cpu_dispatch: Incomplete
    disable_optimization: Incomplete
    simd_test: Incomplete
    def initialize_options(self) -> None: ...
    include_dirs: Incomplete
    def finalize_options(self) -> None: ...
    compiler: Incomplete
    compiler_opt: Incomplete
    extra_dll_dir: Incomplete
    def run(self) -> None: ...
    def swig_sources(self, sources, extensions: Incomplete | None = None): ...
    def build_extension(self, ext) -> None: ...
    def get_source_files(self): ...
    def get_outputs(self): ...
