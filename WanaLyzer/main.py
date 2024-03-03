import os
import sys
import widgets
import customtkinter


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("600x500")
        self.title("WanaLyzer3.0")

        self.path_frame = widgets.PathFrame(self)
        self.path_frame.grid(row=0, column=0)


if __name__ == "__main__":
    app = App()
    app.mainloop()

