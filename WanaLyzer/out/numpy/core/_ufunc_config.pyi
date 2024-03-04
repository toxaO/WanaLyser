from numpy import _SupportsWrite
from typing import TypedDict

class _ErrDict(TypedDict):
    divide: _ErrKind
    over: _ErrKind
    under: _ErrKind
    invalid: _ErrKind

class _ErrDictOptional(TypedDict, total=False):
    all: None | _ErrKind
    divide: None | _ErrKind
    over: None | _ErrKind
    under: None | _ErrKind
    invalid: None | _ErrKind

def seterr(all: None | _ErrKind = ..., divide: None | _ErrKind = ..., over: None | _ErrKind = ..., under: None | _ErrKind = ..., invalid: None | _ErrKind = ...) -> _ErrDict: ...
def geterr() -> _ErrDict: ...
def setbufsize(size: int) -> int: ...
def getbufsize() -> int: ...
def seterrcall(func: None | _ErrFunc | _SupportsWrite[str]) -> None | _ErrFunc | _SupportsWrite[str]: ...
def geterrcall() -> None | _ErrFunc | _SupportsWrite[str]: ...
