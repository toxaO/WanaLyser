from _typeshed import Incomplete
from numpy.core._multiarray_umath import __cpu_features__ as __cpu_features__
from numpy.testing import assert_array_max_ulp as assert_array_max_ulp

UNARY_UFUNCS: Incomplete
UNARY_OBJECT_UFUNCS: Incomplete
IS_AVX: Incomplete
runtest: Incomplete
platform_skip: Incomplete

def convert(s, datatype: str = 'np.float32'): ...

str_to_float: Incomplete

class TestAccuracy:
    def test_validate_transcendentals(self): ...
    def test_validate_fp16_transcendentals(self, ufunc) -> None: ...
