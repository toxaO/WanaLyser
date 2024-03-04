from collections.abc import Callable
from contextlib import _GeneratorContextManager
from numpy import bool_ as bool_, bytes_ as bytes_, clongdouble as clongdouble, complexfloating as complexfloating, datetime64 as datetime64, floating as floating, generic as generic, integer as integer, longdouble as longdouble, ndarray as ndarray, str_ as str_, timedelta64 as timedelta64, void as void
from numpy._typing import ArrayLike as ArrayLike, _CharLike_co, _FloatLike_co
from types import TracebackType as TracebackType
from typing import Any, Literal, SupportsIndex, TypedDict

class _FormatDict(TypedDict, total=False):
    bool: Callable[[bool_], str]
    int: Callable[[integer[Any]], str]
    timedelta: Callable[[timedelta64], str]
    datetime: Callable[[datetime64], str]
    float: Callable[[floating[Any]], str]
    longfloat: Callable[[longdouble], str]
    complexfloat: Callable[[complexfloating[Any, Any]], str]
    longcomplexfloat: Callable[[clongdouble], str]
    void: Callable[[void], str]
    numpystr: Callable[[_CharLike_co], str]
    object: Callable[[object], str]
    all: Callable[[object], str]
    int_kind: Callable[[integer[Any]], str]
    float_kind: Callable[[floating[Any]], str]
    complex_kind: Callable[[complexfloating[Any, Any]], str]
    str_kind: Callable[[_CharLike_co], str]

class _FormatOptions(TypedDict):
    precision: int
    threshold: int
    edgeitems: int
    linewidth: int
    suppress: bool
    nanstr: str
    infstr: str
    formatter: None | _FormatDict
    sign: Literal['-', '+', ' ']
    floatmode: _FloatMode
    legacy: Literal[False, '1.13', '1.21']

def set_printoptions(precision: None | SupportsIndex = ..., threshold: None | int = ..., edgeitems: None | int = ..., linewidth: None | int = ..., suppress: None | bool = ..., nanstr: None | str = ..., infstr: None | str = ..., formatter: None | _FormatDict = ..., sign: Literal[None, '-', '+', ' '] = ..., floatmode: None | _FloatMode = ..., *, legacy: Literal[None, False, '1.13', '1.21'] = ...) -> None: ...
def get_printoptions() -> _FormatOptions: ...
def array2string(a: ndarray[Any, Any], max_line_width: None | int = ..., precision: None | SupportsIndex = ..., suppress_small: None | bool = ..., separator: str = ..., prefix: str = ..., *, formatter: None | _FormatDict = ..., threshold: None | int = ..., edgeitems: None | int = ..., sign: Literal[None, '-', '+', ' '] = ..., floatmode: None | _FloatMode = ..., suffix: str = ..., legacy: Literal[None, False, '1.13', '1.21'] = ...) -> str: ...
def format_float_scientific(x: _FloatLike_co, precision: None | int = ..., unique: bool = ..., trim: Literal['k', '.', '0', '-'] = ..., sign: bool = ..., pad_left: None | int = ..., exp_digits: None | int = ..., min_digits: None | int = ...) -> str: ...
def format_float_positional(x: _FloatLike_co, precision: None | int = ..., unique: bool = ..., fractional: bool = ..., trim: Literal['k', '.', '0', '-'] = ..., sign: bool = ..., pad_left: None | int = ..., pad_right: None | int = ..., min_digits: None | int = ...) -> str: ...
def array_repr(arr: ndarray[Any, Any], max_line_width: None | int = ..., precision: None | SupportsIndex = ..., suppress_small: None | bool = ...) -> str: ...
def array_str(a: ndarray[Any, Any], max_line_width: None | int = ..., precision: None | SupportsIndex = ..., suppress_small: None | bool = ...) -> str: ...
def set_string_function(f: None | Callable[[ndarray[Any, Any]], str], repr: bool = ...) -> None: ...
def printoptions(precision: None | SupportsIndex = ..., threshold: None | int = ..., edgeitems: None | int = ..., linewidth: None | int = ..., suppress: None | bool = ..., nanstr: None | str = ..., infstr: None | str = ..., formatter: None | _FormatDict = ..., sign: Literal[None, '-', '+', ' '] = ..., floatmode: None | _FloatMode = ..., *, legacy: Literal[None, False, '1.13', '1.21'] = ...) -> _GeneratorContextManager[_FormatOptions]: ...
