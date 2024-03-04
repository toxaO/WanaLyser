from .._utils import set_module as set_module
from _typeshed import Incomplete

class UFuncTypeError(TypeError):
    ufunc: Incomplete
    def __init__(self, ufunc) -> None: ...

class _UFuncNoLoopError(UFuncTypeError):
    dtypes: Incomplete
    def __init__(self, ufunc, dtypes) -> None: ...

class _UFuncBinaryResolutionError(_UFuncNoLoopError):
    def __init__(self, ufunc, dtypes) -> None: ...

class _UFuncCastingError(UFuncTypeError):
    casting: Incomplete
    from_: Incomplete
    to: Incomplete
    def __init__(self, ufunc, casting, from_, to) -> None: ...

class _UFuncInputCastingError(_UFuncCastingError):
    in_i: Incomplete
    def __init__(self, ufunc, casting, from_, to, i) -> None: ...

class _UFuncOutputCastingError(_UFuncCastingError):
    out_i: Incomplete
    def __init__(self, ufunc, casting, from_, to, i) -> None: ...

class _ArrayMemoryError(MemoryError):
    shape: Incomplete
    dtype: Incomplete
    def __init__(self, shape, dtype) -> None: ...
