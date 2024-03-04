import numpy as np
from _typeshed import Incomplete
from typing import Any

SEED_NONE: Incomplete
SEED_INT: int
SEED_ARR: np.ndarray[Any, np.dtype[np.int64]]
SEED_ARRLIKE: list[int]
SEED_SEED_SEQ: np.random.SeedSequence
SEED_MT19937: np.random.MT19937
SEED_PCG64: np.random.PCG64
SEED_PHILOX: np.random.Philox
SEED_SFC64: np.random.SFC64
seed_seq: np.random.bit_generator.SeedSequence
def_gen: np.random.Generator
D_arr_0p1: np.ndarray[Any, np.dtype[np.float64]]
D_arr_0p5: np.ndarray[Any, np.dtype[np.float64]]
D_arr_0p9: np.ndarray[Any, np.dtype[np.float64]]
D_arr_1p5: np.ndarray[Any, np.dtype[np.float64]]
I_arr_10: np.ndarray[Any, np.dtype[np.int_]]
I_arr_20: np.ndarray[Any, np.dtype[np.int_]]
D_arr_like_0p1: list[float]
D_arr_like_0p5: list[float]
D_arr_like_0p9: list[float]
D_arr_like_1p5: list[float]
I_arr_like_10: list[int]
I_arr_like_20: list[int]
D_2D_like: list[list[float]]
D_2D: np.ndarray[Any, np.dtype[np.float64]]
S_out: np.ndarray[Any, np.dtype[np.float32]]
D_out: np.ndarray[Any, np.dtype[np.float64]]
I_int64_100: np.ndarray[Any, np.dtype[np.int64]]
I_bool_low: np.ndarray[Any, np.dtype[np.bool_]]
I_bool_low_like: list[int]
I_bool_high_open: np.ndarray[Any, np.dtype[np.bool_]]
I_bool_high_closed: np.ndarray[Any, np.dtype[np.bool_]]
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
I_i2_low: np.ndarray[Any, np.dtype[np.int16]]
I_i2_low_like: list[int]
I_i2_high_open: np.ndarray[Any, np.dtype[np.int16]]
I_i2_high_closed: np.ndarray[Any, np.dtype[np.int16]]
I_i4_low: np.ndarray[Any, np.dtype[np.int32]]
I_i4_low_like: list[int]
I_i4_high_open: np.ndarray[Any, np.dtype[np.int32]]
I_i4_high_closed: np.ndarray[Any, np.dtype[np.int32]]
I_i8_low: np.ndarray[Any, np.dtype[np.int64]]
I_i8_low_like: list[int]
I_i8_high_open: np.ndarray[Any, np.dtype[np.int64]]
I_i8_high_closed: np.ndarray[Any, np.dtype[np.int64]]
def_gen_state: dict[str, Any]
random_st: np.random.RandomState
bg: np.random.BitGenerator
random_st_state: Incomplete
random_st_get_state: Incomplete
random_st_get_state_legacy: Incomplete
