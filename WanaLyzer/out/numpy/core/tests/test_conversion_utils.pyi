from _typeshed import Incomplete
from numpy.testing import IS_PYPY as IS_PYPY, assert_warns as assert_warns

class StringConverterTestCase:
    allow_bytes: bool
    case_insensitive: bool
    exact_match: bool
    warn: bool
    def test_wrong_type(self) -> None: ...
    def test_wrong_value(self) -> None: ...

class TestByteorderConverter(StringConverterTestCase):
    conv: Incomplete
    warn: bool
    def test_valid(self) -> None: ...

class TestSortkindConverter(StringConverterTestCase):
    conv: Incomplete
    warn: bool
    def test_valid(self) -> None: ...

class TestSelectkindConverter(StringConverterTestCase):
    conv: Incomplete
    case_insensitive: bool
    exact_match: bool
    def test_valid(self) -> None: ...

class TestSearchsideConverter(StringConverterTestCase):
    conv: Incomplete
    def test_valid(self) -> None: ...

class TestOrderConverter(StringConverterTestCase):
    conv: Incomplete
    warn: bool
    def test_valid(self) -> None: ...
    def test_flatten_invalid_order(self) -> None: ...

class TestClipmodeConverter(StringConverterTestCase):
    conv: Incomplete
    def test_valid(self) -> None: ...

class TestCastingConverter(StringConverterTestCase):
    conv: Incomplete
    case_insensitive: bool
    exact_match: bool
    def test_valid(self) -> None: ...

class TestIntpConverter:
    conv: Incomplete
    def test_basic(self) -> None: ...
    def test_none(self) -> None: ...
    def test_float(self) -> None: ...
    def test_too_large(self) -> None: ...
    def test_too_many_dims(self) -> None: ...
