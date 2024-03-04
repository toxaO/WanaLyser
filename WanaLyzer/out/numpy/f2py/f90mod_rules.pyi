from .auxfuncs import *
from . import capi_maps as capi_maps, func2subr as func2subr
from .crackfortran import undo_rmbadname as undo_rmbadname, undo_rmbadname1 as undo_rmbadname1
from _typeshed import Incomplete

__version__: Incomplete
f2py_version: str
options: Incomplete

def findf90modules(m): ...

fgetdims1: Incomplete
fgetdims2: str
fgetdims2_sa: str

def buildhooks(pymod): ...
