import re
from _pytest.mark.structures import ParameterSet as ParameterSet
from _typeshed import Incomplete
from collections import defaultdict
from collections.abc import Iterator

RUN_MYPY: Incomplete
pytestmark: Incomplete
NO_MYPY: bool
DATA_DIR: Incomplete
PASS_DIR: Incomplete
FAIL_DIR: Incomplete
REVEAL_DIR: Incomplete
MISC_DIR: Incomplete
MYPY_INI: Incomplete
CACHE_DIR: Incomplete
OUTPUT_MYPY: defaultdict[str, list[str]]

def strip_func(match: re.Match[str]) -> str: ...
def run_mypy() -> None: ...
def get_test_cases(directory: str) -> Iterator[ParameterSet]: ...
def test_success(path) -> None: ...
def test_fail(path: str) -> None: ...
def test_reveal(path: str) -> None: ...
def test_code_runs(path: str) -> None: ...

LINENO_MAPPING: Incomplete

def test_extended_precision() -> None: ...
