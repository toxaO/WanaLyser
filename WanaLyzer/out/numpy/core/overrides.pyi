from .._utils import set_module as set_module
from .._utils._inspect import getargspec as getargspec
from _typeshed import Incomplete
from numpy.core._multiarray_umath import add_docstring as add_docstring
from typing import NamedTuple

ARRAY_FUNCTIONS: Incomplete
array_function_like_doc: str

def set_array_function_like_doc(public_api): ...

class ArgSpec(NamedTuple):
    args: Incomplete
    varargs: Incomplete
    keywords: Incomplete
    defaults: Incomplete

def verify_matching_signatures(implementation, dispatcher) -> None: ...
def array_function_dispatch(dispatcher: Incomplete | None = None, module: Incomplete | None = None, verify: bool = True, docs_from_dispatcher: bool = False): ...
def array_function_from_dispatcher(implementation, module: Incomplete | None = None, verify: bool = True, docs_from_dispatcher: bool = True): ...
