from _typeshed import Incomplete
from numpy.testing import assert_ as assert_

intel_32bit_version_strings: Incomplete
intel_64bit_version_strings: Incomplete

class TestIntelFCompilerVersions:
    def test_32bit_version(self) -> None: ...

class TestIntelEM64TFCompilerVersions:
    def test_64bit_version(self) -> None: ...
