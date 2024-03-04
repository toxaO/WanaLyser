from ._array_object import Array as Array
from typing import NamedTuple

class UniqueAllResult(NamedTuple):
    values: Array
    indices: Array
    inverse_indices: Array
    counts: Array

class UniqueCountsResult(NamedTuple):
    values: Array
    counts: Array

class UniqueInverseResult(NamedTuple):
    values: Array
    inverse_indices: Array

def unique_all(x: Array) -> UniqueAllResult: ...
def unique_counts(x: Array) -> UniqueCountsResult: ...
def unique_inverse(x: Array) -> UniqueInverseResult: ...
def unique_values(x: Array) -> Array: ...
