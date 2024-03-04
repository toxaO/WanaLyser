from _typeshed import Incomplete
from distutils.errors import DistutilsError

__all__ = ['system_info']

class NotFoundError(DistutilsError): ...
class AliasedOptionError(DistutilsError): ...
class AtlasNotFoundError(NotFoundError): ...
class FlameNotFoundError(NotFoundError): ...
class LapackNotFoundError(NotFoundError): ...
class LapackSrcNotFoundError(LapackNotFoundError): ...
class LapackILP64NotFoundError(NotFoundError): ...
class BlasOptNotFoundError(NotFoundError): ...
class BlasNotFoundError(NotFoundError): ...
class BlasILP64NotFoundError(NotFoundError): ...
class BlasSrcNotFoundError(BlasNotFoundError): ...
class FFTWNotFoundError(NotFoundError): ...
class DJBFFTNotFoundError(NotFoundError): ...
class NumericNotFoundError(NotFoundError): ...
class X11NotFoundError(NotFoundError): ...
class UmfpackNotFoundError(NotFoundError): ...

class system_info:
    dir_env_var: Incomplete
    search_static_first: int
    section: str
    saved_results: Incomplete
    notfounderror = NotFoundError
    local_prefixes: Incomplete
    cp: Incomplete
    files: Incomplete
    def __init__(self, default_lib_dirs=..., default_include_dirs=...) -> None: ...
    def parse_config_files(self) -> None: ...
    def calc_libraries_info(self): ...
    def set_info(self, **info) -> None: ...
    def get_option_single(self, *options): ...
    def has_info(self): ...
    def calc_extra_info(self): ...
    def get_info(self, notfound_action: int = 0): ...
    def get_paths(self, section, key): ...
    def get_lib_dirs(self, key: str = 'library_dirs'): ...
    def get_runtime_lib_dirs(self, key: str = 'runtime_library_dirs'): ...
    def get_include_dirs(self, key: str = 'include_dirs'): ...
    def get_src_dirs(self, key: str = 'src_dirs'): ...
    def get_libs(self, key, default): ...
    def get_libraries(self, key: str = 'libraries'): ...
    def library_extensions(self): ...
    def check_libs(self, lib_dirs, libs, opt_libs=[]): ...
    def check_libs2(self, lib_dirs, libs, opt_libs=[]): ...
    def combine_paths(self, *args): ...

class fft_opt_info(system_info):
    def calc_info(self) -> None: ...

class fftw_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = FFTWNotFoundError
    ver_info: Incomplete
    def calc_ver_info(self, ver_param): ...
    def calc_info(self) -> None: ...

class fftw2_info(fftw_info):
    section: str
    dir_env_var: str
    notfounderror = FFTWNotFoundError
    ver_info: Incomplete

class fftw3_info(fftw_info):
    section: str
    dir_env_var: str
    notfounderror = FFTWNotFoundError
    ver_info: Incomplete

class fftw3_armpl_info(fftw_info):
    section: str
    dir_env_var: str
    notfounderror = FFTWNotFoundError
    ver_info: Incomplete

class dfftw_info(fftw_info):
    section: str
    dir_env_var: str
    ver_info: Incomplete

class sfftw_info(fftw_info):
    section: str
    dir_env_var: str
    ver_info: Incomplete

class fftw_threads_info(fftw_info):
    section: str
    dir_env_var: str
    ver_info: Incomplete

class dfftw_threads_info(fftw_info):
    section: str
    dir_env_var: str
    ver_info: Incomplete

class sfftw_threads_info(fftw_info):
    section: str
    dir_env_var: str
    ver_info: Incomplete

class djbfft_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = DJBFFTNotFoundError
    def get_paths(self, section, key): ...
    def calc_info(self) -> None: ...

class mkl_info(system_info):
    section: str
    dir_env_var: str
    def get_mkl_rootdir(self): ...
    def __init__(self) -> None: ...
    def calc_info(self) -> None: ...

class lapack_mkl_info(mkl_info): ...
class blas_mkl_info(mkl_info): ...

class ssl2_info(system_info):
    section: str
    dir_env_var: str
    def get_tcsds_rootdir(self): ...
    def __init__(self) -> None: ...
    def calc_info(self) -> None: ...

class lapack_ssl2_info(ssl2_info): ...
class blas_ssl2_info(ssl2_info): ...

class armpl_info(system_info):
    section: str
    dir_env_var: str
    def calc_info(self) -> None: ...

class lapack_armpl_info(armpl_info): ...
class blas_armpl_info(armpl_info): ...

class atlas_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = AtlasNotFoundError
    def get_paths(self, section, key): ...
    def calc_info(self) -> None: ...

class atlas_blas_info(atlas_info):
    def calc_info(self) -> None: ...

class atlas_threads_info(atlas_info):
    dir_env_var: Incomplete

class atlas_blas_threads_info(atlas_blas_info):
    dir_env_var: Incomplete

class lapack_atlas_info(atlas_info): ...
class lapack_atlas_threads_info(atlas_threads_info): ...
class atlas_3_10_info(atlas_info): ...

class atlas_3_10_blas_info(atlas_3_10_info):
    def calc_info(self) -> None: ...

class atlas_3_10_threads_info(atlas_3_10_info):
    dir_env_var: Incomplete

class atlas_3_10_blas_threads_info(atlas_3_10_blas_info):
    dir_env_var: Incomplete

class lapack_atlas_3_10_info(atlas_3_10_info): ...
class lapack_atlas_3_10_threads_info(atlas_3_10_threads_info): ...

class lapack_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = LapackNotFoundError
    def calc_info(self) -> None: ...

class lapack_src_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = LapackSrcNotFoundError
    def get_paths(self, section, key): ...
    def calc_info(self) -> None: ...

class lapack_opt_info(system_info):
    notfounderror = LapackNotFoundError
    lapack_order: Incomplete
    order_env_var_name: str
    def calc_info(self) -> None: ...

class _ilp64_opt_info_mixin:
    symbol_suffix: Incomplete
    symbol_prefix: Incomplete

class lapack_ilp64_opt_info(lapack_opt_info, _ilp64_opt_info_mixin):
    notfounderror = LapackILP64NotFoundError
    lapack_order: Incomplete
    order_env_var_name: str

class lapack_ilp64_plain_opt_info(lapack_ilp64_opt_info):
    symbol_prefix: str
    symbol_suffix: str

class lapack64__opt_info(lapack_ilp64_opt_info):
    symbol_prefix: str
    symbol_suffix: str

class blas_opt_info(system_info):
    notfounderror = BlasNotFoundError
    blas_order: Incomplete
    order_env_var_name: str
    def calc_info(self) -> None: ...

class blas_ilp64_opt_info(blas_opt_info, _ilp64_opt_info_mixin):
    notfounderror = BlasILP64NotFoundError
    blas_order: Incomplete
    order_env_var_name: str

class blas_ilp64_plain_opt_info(blas_ilp64_opt_info):
    symbol_prefix: str
    symbol_suffix: str

class blas64__opt_info(blas_ilp64_opt_info):
    symbol_prefix: str
    symbol_suffix: str

class cblas_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = BlasNotFoundError

class blas_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = BlasNotFoundError
    def calc_info(self) -> None: ...
    def get_cblas_libs(self, info): ...

class openblas_info(blas_info):
    section: str
    dir_env_var: str
    notfounderror = BlasNotFoundError
    @property
    def symbol_prefix(self): ...
    @property
    def symbol_suffix(self): ...
    def calc_info(self) -> None: ...
    def check_msvc_gfortran_libs(self, library_dirs, libraries): ...
    def check_symbols(self, info): ...

class openblas_lapack_info(openblas_info):
    section: str
    dir_env_var: str
    notfounderror = BlasNotFoundError

class openblas_clapack_info(openblas_lapack_info): ...

class openblas_ilp64_info(openblas_info):
    section: str
    dir_env_var: str
    notfounderror = BlasILP64NotFoundError

class openblas_ilp64_lapack_info(openblas_ilp64_info): ...

class openblas64__info(openblas_ilp64_info):
    section: str
    dir_env_var: str
    symbol_suffix: str
    symbol_prefix: str

class openblas64__lapack_info(openblas_ilp64_lapack_info, openblas64__info): ...

class blis_info(blas_info):
    section: str
    dir_env_var: str
    notfounderror = BlasNotFoundError
    def calc_info(self) -> None: ...

class flame_info(system_info):
    section: str
    notfounderror = FlameNotFoundError
    def check_embedded_lapack(self, info): ...
    def calc_info(self) -> None: ...

class accelerate_info(system_info):
    section: str
    notfounderror = BlasNotFoundError
    def calc_info(self) -> None: ...

class accelerate_lapack_info(accelerate_info): ...

class blas_src_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = BlasSrcNotFoundError
    def get_paths(self, section, key): ...
    def calc_info(self) -> None: ...

class x11_info(system_info):
    section: str
    notfounderror = X11NotFoundError
    def __init__(self) -> None: ...
    def calc_info(self) -> None: ...

class _numpy_info(system_info):
    section: str
    modulename: str
    notfounderror = NumericNotFoundError
    def __init__(self) -> None: ...
    def calc_info(self) -> None: ...

class numarray_info(_numpy_info):
    section: str
    modulename: str

class Numeric_info(_numpy_info):
    section: str
    modulename: str

class numpy_info(_numpy_info):
    section: str
    modulename: str

class numerix_info(system_info):
    section: str
    def calc_info(self) -> None: ...

class f2py_info(system_info):
    def calc_info(self) -> None: ...

class boost_python_info(system_info):
    section: str
    dir_env_var: str
    def get_paths(self, section, key): ...
    def calc_info(self) -> None: ...

class agg2_info(system_info):
    section: str
    dir_env_var: str
    def get_paths(self, section, key): ...
    def calc_info(self) -> None: ...

class _pkg_config_info(system_info):
    section: Incomplete
    config_env_var: str
    default_config_exe: str
    append_config_exe: str
    version_macro_name: Incomplete
    release_macro_name: Incomplete
    version_flag: str
    cflags_flag: str
    def get_config_exe(self): ...
    def get_config_output(self, config_exe, option): ...
    def calc_info(self) -> None: ...

class wx_info(_pkg_config_info):
    section: str
    config_env_var: str
    default_config_exe: str
    append_config_exe: str
    version_macro_name: str
    release_macro_name: str
    version_flag: str
    cflags_flag: str

class gdk_pixbuf_xlib_2_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class gdk_pixbuf_2_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class gdk_x11_2_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class gdk_2_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class gdk_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class gtkp_x11_2_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class gtkp_2_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class xft_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class freetype2_info(_pkg_config_info):
    section: str
    append_config_exe: str
    version_macro_name: str

class amd_info(system_info):
    section: str
    dir_env_var: str
    def calc_info(self) -> None: ...

class umfpack_info(system_info):
    section: str
    dir_env_var: str
    notfounderror = UmfpackNotFoundError
    def calc_info(self) -> None: ...
