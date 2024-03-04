from _typeshed import Incomplete

__all__ = ['cpu']

class CPUInfoBase:
    def __getattr__(self, name): ...

class LinuxCPUInfo(CPUInfoBase):
    info: Incomplete
    def __init__(self) -> None: ...

class IRIXCPUInfo(CPUInfoBase):
    info: Incomplete
    def __init__(self) -> None: ...
    def get_ip(self): ...

class DarwinCPUInfo(CPUInfoBase):
    info: Incomplete
    def __init__(self) -> None: ...

class SunOSCPUInfo(CPUInfoBase):
    info: Incomplete
    def __init__(self) -> None: ...

class Win32CPUInfo(CPUInfoBase):
    info: Incomplete
    pkey: str
    def __init__(self) -> None: ...
cpuinfo = DarwinCPUInfo
cpu: Incomplete
