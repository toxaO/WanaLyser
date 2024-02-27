from typing import Union

class FontManager:
    linux_font_path: str
    @classmethod
    def init_font_manager(cls): ...
    @classmethod
    def windows_load_font(cls, font_path: Union[str, bytes], private: bool = ..., enumerable: bool = ...) -> bool: ...
    @classmethod
    def load_font(cls, font_path: str) -> bool: ...
