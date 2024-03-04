from _typeshed import Incomplete

class ModeDescriptor:
    mode: Incomplete
    bands: Incomplete
    basemode: Incomplete
    basetype: Incomplete
    typestr: Incomplete
    def __init__(self, mode: str, bands: tuple[str, ...], basemode: str, basetype: str, typestr: str) -> None: ...

def getmode(mode: str) -> ModeDescriptor: ...
