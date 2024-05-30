import dataclasses

from PIL import ImageTk


class Rectungle:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.n = y
        self.e = x
        self.w = x + width - 1
        self.s = y + height - 1
        self.nw = (self.w, self.n)
        self.ne = (self.e, self.n)
        self.se = (self.e, self.s)
        self.sw = (self.w, self.s)
        self.width = width
        self.height = height
        self.center = (self.x + self.width / 2, self.y + self.height / 2)


class Circle:
    def __init__(self, x: int, y: int, r: int) -> None:
        self.r = r
        self.center = (x, y)
        self.width = 2 * r
        self.height = 2 * r
        self.n = (x, y - r)
        self.e = (x + r, y)
        self.w = (x - r, y)
        self.s = (x, y + r)


@dataclasses.dataclass
class ImageNameSet:
    img: ImageTk.PhotoImage
    name: str


if __name__ == "__main__":
    test = Rectungle(1, 1, 1, 1)
    print(test.nw)
