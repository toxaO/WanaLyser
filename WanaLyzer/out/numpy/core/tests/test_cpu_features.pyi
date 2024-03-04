from _typeshed import Incomplete
from numpy.core._multiarray_umath import __cpu_baseline__ as __cpu_baseline__, __cpu_dispatch__ as __cpu_dispatch__, __cpu_features__ as __cpu_features__

def assert_features_equal(actual, desired, fname) -> None: ...

class AbstractTest:
    features: Incomplete
    features_groups: Incomplete
    features_map: Incomplete
    features_flags: Incomplete
    def load_flags(self) -> None: ...
    def test_features(self) -> None: ...
    def cpu_have(self, feature_name): ...
    def load_flags_cpuinfo(self, magic_key) -> None: ...
    def get_cpuinfo_item(self, magic_key): ...
    def load_flags_auxv(self) -> None: ...

class TestEnvPrivation:
    cwd: Incomplete
    env: Incomplete
    SUBPROCESS_ARGS: Incomplete
    unavailable_feats: Incomplete
    UNAVAILABLE_FEAT: Incomplete
    BASELINE_FEAT: Incomplete
    SCRIPT: str
    file: Incomplete
    def setup_class(self, tmp_path_factory) -> None: ...
    def setup_method(self) -> None: ...
    def test_runtime_feature_selection(self) -> None: ...
    def test_both_enable_disable_set(self, enabled, disabled) -> None: ...
    def test_variable_too_long(self, action) -> None: ...
    def test_impossible_feature_disable(self) -> None: ...
    def test_impossible_feature_enable(self) -> None: ...

is_linux: Incomplete
is_cygwin: Incomplete
machine: Incomplete
is_x86: Incomplete

class Test_X86_Features(AbstractTest):
    features: Incomplete
    features_groups: Incomplete
    features_map: Incomplete
    def load_flags(self) -> None: ...

is_power: Incomplete

class Test_POWER_Features(AbstractTest):
    features: Incomplete
    features_map: Incomplete
    def load_flags(self) -> None: ...

is_zarch: Incomplete

class Test_ZARCH_Features(AbstractTest):
    features: Incomplete
    def load_flags(self) -> None: ...

is_arm: Incomplete

class Test_ARM_Features(AbstractTest):
    features: Incomplete
    features_groups: Incomplete
    features_map: Incomplete
    def load_flags(self) -> None: ...
