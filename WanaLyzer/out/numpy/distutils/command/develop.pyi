from _typeshed import Incomplete
from setuptools.command.develop import develop as old_develop

class develop(old_develop):
    __doc__: Incomplete
    def install_for_development(self) -> None: ...
