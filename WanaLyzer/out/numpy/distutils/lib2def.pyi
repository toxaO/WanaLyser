from _typeshed import Incomplete

__doc__: str
__version__: str
py_ver: Incomplete
DEFAULT_NM: Incomplete
DEF_HEADER: Incomplete
FUNC_RE: Incomplete
DATA_RE: Incomplete

def parse_cmd(): ...
def getnm(nm_cmd=..., shell: bool = True): ...
def parse_nm(nm_output): ...
def output_def(dlist, flist, header, file=...) -> None: ...
