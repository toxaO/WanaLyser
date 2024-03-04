from _typeshed import Incomplete
from numpy.distutils import customized_fcompiler as customized_fcompiler
from numpy.distutils.fcompiler import FCompiler as FCompiler

compilers: Incomplete

class NoneFCompiler(FCompiler):
    compiler_type: str
    description: str
    executables: Incomplete
    def find_executables(self) -> None: ...
