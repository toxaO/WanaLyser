import enum
from _typeshed import Incomplete

__all__ = ['_NoValue', '_CopyMode']

class _NoValueType:
    def __new__(cls): ...

_NoValue: Incomplete

class _CopyMode(enum.Enum):
    ALWAYS: bool
    IF_NEEDED: bool
    NEVER: int
    def __bool__(self) -> bool: ...
