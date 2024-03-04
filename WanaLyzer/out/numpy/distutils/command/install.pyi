from _typeshed import Incomplete

have_setuptools: bool
old_install: Incomplete

class install(old_install):
    sub_commands: Incomplete
    install_lib: Incomplete
    def finalize_options(self) -> None: ...
    def setuptools_run(self): ...
    def run(self): ...
