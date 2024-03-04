from _typeshed import Incomplete
from distutils.core import Command
from numpy.distutils import log as log

def show_fortran_compilers(_cache: Incomplete | None = None) -> None: ...

class config_fc(Command):
    description: str
    user_options: Incomplete
    help_options: Incomplete
    boolean_options: Incomplete
    fcompiler: Incomplete
    f77exec: Incomplete
    f90exec: Incomplete
    f77flags: Incomplete
    f90flags: Incomplete
    opt: Incomplete
    arch: Incomplete
    debug: Incomplete
    noopt: Incomplete
    noarch: Incomplete
    def initialize_options(self) -> None: ...
    def finalize_options(self) -> None: ...
    def run(self) -> None: ...

class config_cc(Command):
    description: str
    user_options: Incomplete
    compiler: Incomplete
    def initialize_options(self) -> None: ...
    def finalize_options(self) -> None: ...
    def run(self) -> None: ...
