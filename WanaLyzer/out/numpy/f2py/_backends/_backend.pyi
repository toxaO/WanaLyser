import abc
from _typeshed import Incomplete
from abc import ABC, abstractmethod

class Backend(ABC, metaclass=abc.ABCMeta):
    modulename: Incomplete
    sources: Incomplete
    extra_objects: Incomplete
    build_dir: Incomplete
    include_dirs: Incomplete
    library_dirs: Incomplete
    libraries: Incomplete
    define_macros: Incomplete
    undef_macros: Incomplete
    f2py_flags: Incomplete
    sysinfo_flags: Incomplete
    fc_flags: Incomplete
    flib_flags: Incomplete
    setup_flags: Incomplete
    remove_build_dir: Incomplete
    extra_dat: Incomplete
    def __init__(self, modulename, sources, extra_objects, build_dir, include_dirs, library_dirs, libraries, define_macros, undef_macros, f2py_flags, sysinfo_flags, fc_flags, flib_flags, setup_flags, remove_build_dir, extra_dat) -> None: ...
    @abstractmethod
    def compile(self) -> None: ...
