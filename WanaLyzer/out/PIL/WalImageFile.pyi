from . import Image as Image, ImageFile as ImageFile
from _typeshed import Incomplete

class WalImageFile(ImageFile.ImageFile):
    format: str
    format_description: str
    im: Incomplete
    def load(self): ...

def open(filename): ...

quake2palette: bytes
