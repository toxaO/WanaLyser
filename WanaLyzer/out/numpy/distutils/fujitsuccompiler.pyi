from distutils.unixccompiler import UnixCCompiler

class FujitsuCCompiler(UnixCCompiler):
    compiler_type: str
    cc_exe: str
    cxx_exe: str
    def __init__(self, verbose: int = 0, dry_run: int = 0, force: int = 0) -> None: ...
