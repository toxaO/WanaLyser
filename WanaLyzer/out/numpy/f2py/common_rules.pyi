from . import __version__ as __version__, capi_maps as capi_maps, func2subr as func2subr
from .auxfuncs import getuseblocks as getuseblocks, hasbody as hasbody, hascommon as hascommon, hasnote as hasnote, isintent_hide as isintent_hide, outmess as outmess
from .crackfortran import rmbadname as rmbadname
from _typeshed import Incomplete

f2py_version: Incomplete

def findcommonblocks(block, top: int = 1): ...
def buildhooks(m): ...
