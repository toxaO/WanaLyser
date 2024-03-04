import glob
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import ImageTk

import structure as st
import utils

testset = "test/testset"


class Test(ctk.CTk):
    """
        実験用
    """
    def __init__(self):
        super().__init__()
        self.geometry("1000x800")
        self.title("Widget test")


        self.dirpath_frame = FolderPathFrame(master=self, init_dir=testset)
        self.dirpath_frame.grid(row=0, column=0, sticky="n")

        self.filepath_frame = FilePathFrame(master=self)
        self.filepath_frame.grid(row=1, column=0)

        self.test_canvas = ImageFrame(self)
        self.test_canvas.grid(row=3, column=0)

        self.test_button = ctk.CTkButton(self, text="Test", command=self.canvas_work)
        self.test_button.grid(row=2, column=0, sticky="N")

        # set param frame
        self.test_param_frame = ParamsFrame(self, ["a", "b", "c"], [1, 2, 3])
        self.test_param_frame.grid(row=0, column=1)
        self.test_param_frame.get_params()

    def test_message(self):
        message = self.dirpath_frame.get_path()
        if message is None:
            message = "パスがありません"
        messagebox.showinfo(title="Test message", message=message)

    def canvas_work(self):
        imgs = self.dirpath_frame.get_files("png")
        self.test_canvas.set_from_imagepath(imgs)


class ParamsFrame(ctk.CTkFrame):
    def __init__(self, master, param_list: list[str], default_value: list[int], **kwargs):
        super().__init__(master, **kwargs)
        self.param_list = param_list
        title = ctk.CTkLabel(self, text="Parameters")
        title.pack()
        for (param, value) in zip(param_list, default_value):
            setattr(self, param, ctk.CTkFrame(self))
            master = getattr(self, param)
            master.label = ctk.CTkLabel(master, text=param)
            master.var = tk.StringVar(value=str(value))
            master.textbox = ctk.CTkEntry(master, textvariable=master.var)
            master.label.pack(padx=10, side=tk.LEFT)
            master.textbox.pack(padx=10, side=tk.LEFT)
            master.pack()

    def get_params(self):
        params = {}
        for key in self.param_list:
            value = getattr(self, key).textbox.get()
            params[key] = value
        return params


class FilePathFrame(ctk.CTkFrame):
    """
    ファイルパス選択用ウィジェット
    """
    def __init__(self, master, iFile: str = "", **kwargs):
        super().__init__(master, **kwargs)

        self.iFile: str = iFile

        self.label = ctk.CTkLabel(self, text="ファイルを選択")
        self.label.grid(row=0, column=0, padx=10)

        self.path_entry = ctk.CTkEntry(self, width=300)
        self.path_entry.insert(0, iFile)
        self.path_entry.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.path_select = ctk.CTkButton(
            self, text="選択", command=self.filedialog_clicked
        )
        self.path_select.grid(row=1, column=1, padx=10, pady=10, sticky="w")

    def filedialog_clicked(self):
        fTyp = [("", "*")]
        iFile = self.path_entry.get()
        if iFile == "":
            iFile = os.path.abspath(os.path.dirname(__file__))
        iFilePath = filedialog.askopenfilename(filetypes = fTyp, initialdir=iFile)
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, iFilePath)

    def get_path(self) -> str:
        path = self.path_entry.get()
        if path == "":
            messagebox.showinfo(title="情報", message="ファイルを入力して下さい")
            return ""
        else:
            return path



class FolderPathFrame(ctk.CTkFrame):
    """
    フォルダパス選択用ウィジェット
    """
    def __init__(self, master, init_dir: str = "", **kwargs):
        super().__init__(master, **kwargs)

        self.iDirPath: str = init_dir

        self.label = ctk.CTkLabel(self, text="フォルダを選択")
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
        iDirPath = filedialog.askdirectory(initialdir=iDir)
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, iDirPath)

    def get_path(self) -> str:
        iDirPath = self.path_entry.get()
        if iDirPath == "":
            messagebox.showinfo(title="情報", message="フォルダを入力して下さい")
            return ""
        else:
            return iDirPath

    def get_files(self, filetype: str) -> list[str]:
        iDirPath = self.path_entry.get()
        if iDirPath == "":
            return []
        img_path_list = glob.glob(iDirPath + "/*." + filetype)
        return img_path_list


class ImageFrame(ctk.CTkFrame):
    """
    画像表示用ウィジェット
    set_from_imagepathかset_from_ImageNameSetを呼びだして使用
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.canvas = ctk.CTkCanvas(self, width=350, height=350)
        self.canvas.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # select
        self.left_button = ctk.CTkButton(self, text="<", command=self.next_image)
        self.right_button = ctk.CTkButton(self, text=">", command=self.pre_image)
        self.left_button.grid(row=1, column=0)
        self.right_button.grid(row=1, column=1)

        self.imgs = []

        # label
        self.image_name = ctk.CTkLabel(self, text="filename")
        self.image_name.grid(row=2, column=0, columnspan=2)

        self.update()
        self.canvas_width = self.canvas.winfo_width()
        self.canvas_height = self.canvas.winfo_height()

    def set_from_imagepath(self, img_path_list: list[str]):
        imgs = utils.img_path_list_to_ImageNameSet(img_path_list)
        self.set_images(imgs)

    def set_from_ImageNameSet(
        self, img_list: list[ImageTk.PhotoImage], img_name: list[str] = []
    ):
        img_name_set_list = []
        if img_name == []:
            for i in range(len(img_list)):
                img_name.append("img: " + str(i))
        for i in range(len(img_list)):
            in_set = st.ImageNameSet(img_list[i], img_name[i])
            img_name_set_list.append(in_set)
        self.set_images(img_name_set_list)

    def set_images(self, imgs: list[st.ImageNameSet]):
        self.imgs = imgs
        self.current_image = 0
        self.num_of_image = len(self.imgs)

        if self.imgs:
            self.canvas.delete("all")
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                image=self.imgs[0].img,
            )

        self.image_name.configure(text=imgs[0].name)

    def next_image(self):
        self.current_image = self.current_image + 1
        if self.current_image > self.num_of_image - 1:
            self.current_image = 0

        if self.imgs:
            self.canvas.delete("all")
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                image=self.imgs[self.current_image].img,
            )

        self.image_name.configure(text=self.imgs[self.current_image].name)

    def pre_image(self):
        self.current_image = self.current_image - 1
        if self.current_image < 0:
            self.current_image = self.num_of_image - 1

        if self.imgs:
            self.canvas.delete("all")
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                image=self.imgs[self.current_image].img,
            )

        self.image_name.configure(text=self.imgs[self.current_image].name)


if __name__ == "__main__":
    app = Test()
    app.mainloop()
