from ._backend import Backend as Backend
from numpy.distutils.core import Extension as Extension, setup as setup
from numpy.distutils.misc_util import dict_append as dict_append
from numpy.distutils.system_info import get_info as get_info
from numpy.exceptions import VisibleDeprecationWarning as VisibleDeprecationWarning

class DistutilsBackend(Backend):
    def __init__(sef, *args, **kwargs) -> None: ...
    def compile(self) -> None: ...
