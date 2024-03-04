from numpy.testing import assert_ as assert_, assert_array_equal as assert_array_equal, assert_equal as assert_equal

def buffer_length(arr): ...

ucs2_value: str
ucs4_value: str

def test_string_cast() -> None: ...

class CreateZeros:
    def content_check(self, ua, ua_scalar, nbytes) -> None: ...
    def test_zeros0D(self) -> None: ...
    def test_zerosSD(self) -> None: ...
    def test_zerosMD(self) -> None: ...

class TestCreateZeros_1(CreateZeros):
    ulen: int

class TestCreateZeros_2(CreateZeros):
    ulen: int

class TestCreateZeros_1009(CreateZeros):
    ulen: int

class CreateValues:
    def content_check(self, ua, ua_scalar, nbytes) -> None: ...
    def test_values0D(self) -> None: ...
    def test_valuesSD(self) -> None: ...
    def test_valuesMD(self) -> None: ...

class TestCreateValues_1_UCS2(CreateValues):
    ulen: int
    ucs_value = ucs2_value

class TestCreateValues_1_UCS4(CreateValues):
    ulen: int
    ucs_value = ucs4_value

class TestCreateValues_2_UCS2(CreateValues):
    ulen: int
    ucs_value = ucs2_value

class TestCreateValues_2_UCS4(CreateValues):
    ulen: int
    ucs_value = ucs4_value

class TestCreateValues_1009_UCS2(CreateValues):
    ulen: int
    ucs_value = ucs2_value

class TestCreateValues_1009_UCS4(CreateValues):
    ulen: int
    ucs_value = ucs4_value

class AssignValues:
    def content_check(self, ua, ua_scalar, nbytes) -> None: ...
    def test_values0D(self) -> None: ...
    def test_valuesSD(self) -> None: ...
    def test_valuesMD(self) -> None: ...

class TestAssignValues_1_UCS2(AssignValues):
    ulen: int
    ucs_value = ucs2_value

class TestAssignValues_1_UCS4(AssignValues):
    ulen: int
    ucs_value = ucs4_value

class TestAssignValues_2_UCS2(AssignValues):
    ulen: int
    ucs_value = ucs2_value

class TestAssignValues_2_UCS4(AssignValues):
    ulen: int
    ucs_value = ucs4_value

class TestAssignValues_1009_UCS2(AssignValues):
    ulen: int
    ucs_value = ucs2_value

class TestAssignValues_1009_UCS4(AssignValues):
    ulen: int
    ucs_value = ucs4_value

class ByteorderValues:
    def test_values0D(self) -> None: ...
    def test_valuesSD(self) -> None: ...
    def test_valuesMD(self) -> None: ...
    def test_values_cast(self) -> None: ...
    def test_values_updowncast(self) -> None: ...

class TestByteorder_1_UCS2(ByteorderValues):
    ulen: int
    ucs_value = ucs2_value

class TestByteorder_1_UCS4(ByteorderValues):
    ulen: int
    ucs_value = ucs4_value

class TestByteorder_2_UCS2(ByteorderValues):
    ulen: int
    ucs_value = ucs2_value

class TestByteorder_2_UCS4(ByteorderValues):
    ulen: int
    ucs_value = ucs4_value

class TestByteorder_1009_UCS2(ByteorderValues):
    ulen: int
    ucs_value = ucs2_value

class TestByteorder_1009_UCS4(ByteorderValues):
    ulen: int
    ucs_value = ucs4_value
