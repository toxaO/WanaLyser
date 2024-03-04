from enum import Enum

__all__ = ['show']

class DisplayModes(Enum):
    stdout: str
    dicts: str

def show(mode=...): ...
