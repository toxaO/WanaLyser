from _typeshed import Incomplete
from distutils.command.install_data import install_data as old_install_data

have_setuptools: Incomplete

class install_data(old_install_data):
    def run(self) -> None: ...
    def finalize_options(self) -> None: ...
