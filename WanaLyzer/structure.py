import dataclasses

from PIL import ImageTk

PIXEL_SIZE = 0.242


class Rectungle:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.nw = (x, y)
        self.ne = (x + width - 1, y)
        self.se = (x + width - 1, y + height - 1)
        self.sw = (x, y + height - 1)
        self.width = width
        self.height = height
        self.center = (self.x + self.width / 2, self.y + self.height / 2)
        self.points = (self.nw, self.sw, self.se, self.ne)


@dataclasses.dataclass
class Circle:
    def __init__(self, x: int, y: int, r: int) -> None:
        self.r = r
        self.center = (x, y)


@dataclasses.dataclass
class Params:
    """
    ビームサイズはmmで指定
    ±5mmで照射野検出
    """

    def __init__(self, beam_size: int) -> None:
        self.beam_max = int((beam_size + 5) / PIXEL_SIZE)
        self.beam_min = int((beam_size - 5) / PIXEL_SIZE)


@dataclasses.dataclass
class ImageNameSet:
    img: ImageTk.PhotoImage
    name: str


if __name__ == "__main__":
    test = Rectungle(1, 1, 1, 1)
    print(test.nw)
