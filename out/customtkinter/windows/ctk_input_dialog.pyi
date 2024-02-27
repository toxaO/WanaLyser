from .ctk_toplevel import CTkToplevel as CTkToplevel
from .widgets import CTkButton as CTkButton, CTkEntry as CTkEntry, CTkLabel as CTkLabel
from .widgets.font import CTkFont as CTkFont
from .widgets.theme import ThemeManager as ThemeManager
from typing import Optional, Tuple, Union

class CTkInputDialog(CTkToplevel):
    def __init__(self, fg_color: Optional[Union[str, Tuple[str, str]]] = ..., text_color: Optional[Union[str, Tuple[str, str]]] = ..., button_fg_color: Optional[Union[str, Tuple[str, str]]] = ..., button_hover_color: Optional[Union[str, Tuple[str, str]]] = ..., button_text_color: Optional[Union[str, Tuple[str, str]]] = ..., entry_fg_color: Optional[Union[str, Tuple[str, str]]] = ..., entry_border_color: Optional[Union[str, Tuple[str, str]]] = ..., entry_text_color: Optional[Union[str, Tuple[str, str]]] = ..., title: str = ..., font: Optional[Union[tuple, CTkFont]] = ..., text: str = ...) -> None: ...
    def get_input(self): ...
