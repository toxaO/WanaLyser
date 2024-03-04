from _typeshed import Incomplete
from distutils.core import Distribution

class NumpyDistribution(Distribution):
    scons_data: Incomplete
    installed_libraries: Incomplete
    installed_pkg_config: Incomplete
    def __init__(self, attrs: Incomplete | None = None) -> None: ...
    def has_scons_scripts(self): ...
