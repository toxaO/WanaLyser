from ._array_object import Array as Array
from _typeshed import Incomplete
from numpy import dtype, float32, float64, int16, int32, int64, int8, uint16, uint32, uint64, uint8
from typing import Any, Protocol, Union

__all__ = ['Array', 'Device', 'Dtype', 'SupportsDLPack', 'SupportsBufferProtocol', 'PyCapsule']

class NestedSequence(Protocol[_T_co]):
    def __getitem__(self, key: int) -> _T_co | NestedSequence[_T_co]: ...
    def __len__(self) -> int: ...

Device: Incomplete
Dtype = dtype[Union[int8, int16, int32, int64, uint8, uint16, uint32, uint64, float32, float64]]
SupportsBufferProtocol = Any
PyCapsule = Any

class SupportsDLPack(Protocol):
    def __dlpack__(self, *, stream: None = ...) -> PyCapsule: ...
