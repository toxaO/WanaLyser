from mypy.nodes import MypyFile as MypyFile, Statement as Statement
from mypy.plugin import Plugin

MYPY_EX: None | ModuleNotFoundError
MYPY_EX = ex

class _NumpyPlugin(Plugin):
    def get_type_analyze_hook(self, fullname: str) -> None | _HookFunc: ...
    def get_additional_deps(self, file: MypyFile) -> list[tuple[int, str, int]]: ...

def plugin(version: str) -> type[_NumpyPlugin]: ...
