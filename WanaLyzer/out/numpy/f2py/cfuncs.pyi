from . import __version__ as __version__
from _typeshed import Incomplete

f2py_version: Incomplete
errmess: Incomplete
outneeds: Incomplete
needs: Incomplete
includes0: Incomplete
includes: Incomplete
userincludes: Incomplete
typedefs: Incomplete
typedefs_generated: Incomplete
cppmacros: Incomplete
cfuncs: Incomplete
callbacks: Incomplete
f90modhooks: Incomplete
commonhooks: Incomplete

def buildcfuncs() -> None: ...
def append_needs(need, flag: int = 1): ...
def get_needs(): ...
