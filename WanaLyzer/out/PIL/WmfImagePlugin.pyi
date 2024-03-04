from . import Image as Image, ImageFile as ImageFile
from _typeshed import Incomplete

def register_handler(handler) -> None: ...

class WmfHandler:
    bbox: Incomplete
    def open(self, im) -> None: ...
    def load(self, im): ...

class WmfStubImageFile(ImageFile.StubImageFile):
    format: str
    format_description: str
    def load(self, dpi: Incomplete | None = None): ...
