import abc
from collections.abc import Callable as Callable, Mapping, Sequence
from numpy import dtype as dtype, ndarray as ndarray, uint32 as uint32, uint64 as uint64
from numpy._typing import _ArrayLikeInt_co, _ShapeLike
from threading import Lock
from typing import Any, Literal, NamedTuple, TypedDict, overload

class _SeedSeqState(TypedDict):
    entropy: None | int | Sequence[int]
    spawn_key: tuple[int, ...]
    pool_size: int
    n_children_spawned: int

class _Interface(NamedTuple):
    state_address: Any
    state: Any
    next_uint64: Any
    next_uint32: Any
    next_double: Any
    bit_generator: Any

class ISeedSequence(abc.ABC, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def generate_state(self, n_words: int, dtype: _DTypeLikeUint32 | _DTypeLikeUint64 = ...) -> ndarray[Any, dtype[uint32 | uint64]]: ...

class ISpawnableSeedSequence(ISeedSequence, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def spawn(self, n_children: int) -> list[_T]: ...

class SeedlessSeedSequence(ISpawnableSeedSequence):
    def generate_state(self, n_words: int, dtype: _DTypeLikeUint32 | _DTypeLikeUint64 = ...) -> ndarray[Any, dtype[uint32 | uint64]]: ...
    def spawn(self, n_children: int) -> list[_T]: ...

class SeedSequence(ISpawnableSeedSequence):
    entropy: None | int | Sequence[int]
    spawn_key: tuple[int, ...]
    pool_size: int
    n_children_spawned: int
    pool: ndarray[Any, dtype[uint32]]
    def __init__(self, entropy: None | int | Sequence[int] | _ArrayLikeInt_co = ..., *, spawn_key: Sequence[int] = ..., pool_size: int = ..., n_children_spawned: int = ...) -> None: ...
    @property
    def state(self) -> _SeedSeqState: ...
    def generate_state(self, n_words: int, dtype: _DTypeLikeUint32 | _DTypeLikeUint64 = ...) -> ndarray[Any, dtype[uint32 | uint64]]: ...
    def spawn(self, n_children: int) -> list[SeedSequence]: ...

class BitGenerator(abc.ABC, metaclass=abc.ABCMeta):
    lock: Lock
    def __init__(self, seed: None | _ArrayLikeInt_co | SeedSequence = ...) -> None: ...
    def __reduce__(self) -> tuple[Callable[[str], BitGenerator], tuple[str], tuple[dict[str, Any]]]: ...
    @abc.abstractmethod
    @property
    def state(self) -> Mapping[str, Any]: ...
    @state.setter
    def state(self, value: Mapping[str, Any]) -> None: ...
    @property
    def seed_seq(self) -> ISeedSequence: ...
    def spawn(self, n_children: int) -> list[BitGenerator]: ...
    @overload
    def random_raw(self, size: None = ..., output: Literal[True] = ...) -> int: ...
    @overload
    def random_raw(self, size: _ShapeLike = ..., output: Literal[True] = ...) -> ndarray[Any, dtype[uint64]]: ...
    @overload
    def random_raw(self, size: None | _ShapeLike = ..., output: Literal[False] = ...) -> None: ...
    @property
    def ctypes(self) -> _Interface: ...
    @property
    def cffi(self) -> _Interface: ...
