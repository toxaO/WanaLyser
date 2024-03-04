import numpy as np
import numpy.typing as npt
import pathlib
from numpy.lib.npyio import BagObj as BagObj, NpzFile as NpzFile
from numpy.ma.mrecords import MaskedRecords as MaskedRecords
from typing import IO

str_path: str
pathlib_path: pathlib.Path
str_file: IO[str]
bytes_file: IO[bytes]
bag_obj: BagObj[int]
npz_file: NpzFile
AR_i8: npt.NDArray[np.int64]
AR_LIKE_f8: list[float]

class BytesWriter:
    def write(self, data: bytes) -> None: ...

class BytesReader:
    def read(self, n: int = ...) -> bytes: ...
    def seek(self, offset: int, whence: int = ...) -> int: ...

bytes_writer: BytesWriter
bytes_reader: BytesReader
