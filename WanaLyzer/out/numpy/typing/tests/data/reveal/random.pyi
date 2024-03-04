import numpy as np
import numpy.typing as npt
from _typeshed import Incomplete
from numpy.random._generator import Generator as Generator
from numpy.random._mt19937 import MT19937 as MT19937
from numpy.random._pcg64 import PCG64 as PCG64
from numpy.random._philox import Philox as Philox
from numpy.random._sfc64 import SFC64 as SFC64
from numpy.random.bit_generator import SeedSequence as SeedSequence, SeedlessSeedSequence as SeedlessSeedSequence
from typing import Any

def_rng: Incomplete
seed_seq: Incomplete
mt19937: Incomplete
pcg64: Incomplete
sfc64: Incomplete
philox: Incomplete
seedless_seq: Incomplete
mt19937_jumped: Incomplete
mt19937_jumped3: Incomplete
mt19937_raw: Incomplete
mt19937_raw_arr: Incomplete
pcg64_jumped: Incomplete
pcg64_jumped3: Incomplete
pcg64_adv: Incomplete
pcg64_raw: Incomplete
pcg64_raw_arr: Incomplete
philox_jumped: Incomplete
philox_jumped3: Incomplete
philox_adv: Incomplete
philox_raw: Incomplete
philox_raw_arr: Incomplete
sfc64_raw: Incomplete
sfc64_raw_arr: Incomplete
def_gen: np.random.Generator
D_arr_0p1: npt.NDArray[np.float64]
D_arr_0p5: npt.NDArray[np.float64]
D_arr_0p9: npt.NDArray[np.float64]
D_arr_1p5: npt.NDArray[np.float64]
I_arr_10: np.ndarray[Any, np.dtype[np.int_]]
I_arr_20: np.ndarray[Any, np.dtype[np.int_]]
D_arr_like_0p1: list[float]
D_arr_like_0p5: list[float]
D_arr_like_0p9: list[float]
D_arr_like_1p5: list[float]
I_arr_like_10: list[int]
I_arr_like_20: list[int]
D_2D_like: list[list[float]]
D_2D: npt.NDArray[np.float64]
S_out: npt.NDArray[np.float32]
D_out: npt.NDArray[np.float64]
I_int64_100: np.ndarray[Any, np.dtype[np.int64]]
I_bool_low: npt.NDArray[np.bool_]
I_bool_low_like: list[int]
I_bool_high_open: npt.NDArray[np.bool_]
I_bool_high_closed: npt.NDArray[np.bool_]
I_u1_low: np.ndarray[Any, np.dtype[np.uint8]]
I_u1_low_like: list[int]
I_u1_high_open: np.ndarray[Any, np.dtype[np.uint8]]
I_u1_high_closed: np.ndarray[Any, np.dtype[np.uint8]]
I_u2_low: np.ndarray[Any, np.dtype[np.uint16]]
I_u2_low_like: list[int]
I_u2_high_open: np.ndarray[Any, np.dtype[np.uint16]]
I_u2_high_closed: np.ndarray[Any, np.dtype[np.uint16]]
I_u4_low: np.ndarray[Any, np.dtype[np.uint32]]
I_u4_low_like: list[int]
I_u4_high_open: np.ndarray[Any, np.dtype[np.uint32]]
I_u4_high_closed: np.ndarray[Any, np.dtype[np.uint32]]
I_u8_low: np.ndarray[Any, np.dtype[np.uint64]]
I_u8_low_like: list[int]
I_u8_high_open: np.ndarray[Any, np.dtype[np.uint64]]
I_u8_high_closed: np.ndarray[Any, np.dtype[np.uint64]]
I_i1_low: np.ndarray[Any, np.dtype[np.int8]]
I_i1_low_like: list[int]
I_i1_high_open: np.ndarray[Any, np.dtype[np.int8]]
I_i1_high_closed: np.ndarray[Any, np.dtype[np.int8]]
I_i2_low: npt.NDArray[np.int16]
I_i2_low_like: list[int]
I_i2_high_open: npt.NDArray[np.int16]
I_i2_high_closed: npt.NDArray[np.int16]
I_i4_low: np.ndarray[Any, np.dtype[np.int32]]
I_i4_low_like: list[int]
I_i4_high_open: np.ndarray[Any, np.dtype[np.int32]]
I_i4_high_closed: np.ndarray[Any, np.dtype[np.int32]]
I_i8_low: np.ndarray[Any, np.dtype[np.int64]]
I_i8_low_like: list[int]
I_i8_high_open: np.ndarray[Any, np.dtype[np.int64]]
I_i8_high_closed: np.ndarray[Any, np.dtype[np.int64]]
def_gen_state: Incomplete
random_st: np.random.RandomState
random_st_state: Incomplete
random_st_get_state: Incomplete
random_st_get_state_legacy: Incomplete
