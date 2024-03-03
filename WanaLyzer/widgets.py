import glob
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import ImageTk

testset = "test/testset"


class Test(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x600")
        self.title("Widget test")

        # self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.path_frame = PathFrame(master=self, init_dir=testset)
        self.path_frame.grid(row=0, column=0, sticky="n")

        imgs = self.path_frame.get_files("png")
        self.test_canvas = ImageFrame(self, imgs)
        self.test_canvas.grid(row=2, column=0)

        self.test_button = ctk.CTkButton(self, text="Test", command=self.canvas_work)
        self.test_button.grid(row=1, column=0, sticky="N")

    def test_message(self):
        message = self.path_frame.get_path()
        if message is None:
            message = "パスがありません"
        messagebox.showinfo(title="Test message", message=message)

    def canvas_work(self):
        imgs = self.path_frame.get_files("png")
        self.test_canvas.set_images(imgs)


class PathFrame(ctk.CTkFrame):
    def __init__(self, master, init_dir: str = "", **kwargs):
        super().__init__(master, **kwargs)

        self.iDirPath: str = init_dir

        self.label = ctk.CTkLabel(self, text="ファイルパスを選択してください")
        self.label.grid(row=0, column=0, padx=10)

        self.path_entry = ctk.CTkEntry(self, width=300)
        self.path_entry.insert(0, init_dir)
        self.path_entry.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.path_select = ctk.CTkButton(
            self, text="選択", command=self.dirdialog_clicked
        )
        self.path_select.grid(row=1, column=1, padx=10, pady=10, sticky="w")

    def dirdialog_clicked(self):
        iDir = self.path_entry.get()
        if iDir == "":
            iDir = os.path.abspath(os.path.dirname(__file__))
        self.iDirPath = filedialog.askdirectory(initialdir=iDir)
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, self.iDirPath)

    def get_path(self) -> str:
        if self.iDirPath == "":
            messagebox.showinfo(title="情報", message="フォルダを入力して下さい")
            return ""
        else:
            return self.iDirPath

    def get_files(self, filetype: str) -> list[str]:
        if self.iDirPath == "":
            return []
        img_path_list = glob.glob(self.iDirPath + "/*." + filetype)
        return img_path_list


class ImageFrame(ctk.CTkFrame):
    def __init__(self, master, img_path_list: list[str], **kwargs):
        super().__init__(master, **kwargs)

        self.canvas = ctk.CTkCanvas(self)
        self.canvas.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # select
        self.left_button = ctk.CTkButton(self, text="<", command=self.next_image)
        self.right_button = ctk.CTkButton(self, text=">", command=self.pre_image)
        self.left_button.grid(row=1, column=0)
        self.right_button.grid(row=1, column=1)

        # label
        self.image_name = ctk.CTkLabel(self, text="filename")
        self.image_name.grid(row=2, column=0, columnspan=2)
        self.image_name["text"] = "next"

        self.update()
        self.canvas_width = self.canvas.winfo_width()
        self.canvas_height = self.canvas.winfo_height()

    def set_images(self, img_path_list: list[str]):
        self.imgs = []
        for im in img_path_list:
            self.imgs.append(ImageTk.PhotoImage(file=im))
        self.img_path_list = img_path_list
        self.current_image = 0
        self.num_of_image = len(self.imgs)

        if self.imgs:
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                image=self.imgs[0],
            )

        self.image_name.configure(text=os.path.basename(self.img_path_list[0]))

    def next_image(self):
        self.current_image = self.current_image + 1
        if self.current_image > self.num_of_image - 1:
            self.current_image = 0

        if self.imgs:
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                image=self.imgs[self.current_image],
            )

        self.image_name.configure(
            text=os.path.basename(self.img_path_list[self.current_image])
        )

    def pre_image(self):
        self.current_image = self.current_image - 1
        if self.current_image < 0:
            self.current_image = self.num_of_image - 1

        if self.imgs:
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                image=self.imgs[self.current_image],
            )

        self.image_name.configure(
            text=os.path.basename(self.img_path_list[self.current_image])
        )


if __name__ == "__main__":
    app = Test()
    app.mainloop()
