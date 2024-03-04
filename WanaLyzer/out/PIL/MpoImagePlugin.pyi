from . import ExifTags as ExifTags, Image as Image, ImageFile as ImageFile, ImageSequence as ImageSequence, JpegImagePlugin as JpegImagePlugin, TiffImagePlugin as TiffImagePlugin
from ._binary import o32le as o32le
from _typeshed import Incomplete

class MpoImageFile(JpegImagePlugin.JpegImageFile):
    format: str
    format_description: str
    def load_seek(self, pos) -> None: ...
    fp: Incomplete
    offset: Incomplete
    tile: Incomplete
    def seek(self, frame) -> None: ...
    def tell(self): ...
    @staticmethod
    def adopt(jpeg_instance, mpheader: Incomplete | None = None): ...
