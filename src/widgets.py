from dataclasses import field, dataclass
import glob
import os
import sys
import csv
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import customtkinter as ctk
import structure as st
import utils
from PIL import ImageTk

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

        self.test_table = ResultTable(master=self)
        self.test_table.grid(row=3, column=1, sticky="NS")

        self.test_button = ctk.CTkButton(self, text="Test", command=self.canvas_work)
        self.test_button.grid(row=2, column=0, sticky="N")

        # set param frame
        self.test_param_frame = ParamsFrame(
            self, "entry params", ["a", "b", "c"], [1, 2, 3]
        )
        self.test_param_frame.grid(row=0, column=1)
        self.test_param_frame.get_params()

        # set slider frame
        slider_setting = [
            SliderFrameParams("a", 0, 5, 5, 3, print),
            SliderFrameParams("b", 0, 10, 10, 3, print),
            SliderFrameParams("c", 0, 100, 100, 50, print),
        ]
        self.test_slider_frame = SliderFrame(self, "slider params", slider_setting)
        self.test_slider_frame.grid(row=1, column=1)
        # set slider callback
        # for slider_param in slider_setting:
        #     slider_master = getattr(self.test_slider_frame, slider_param.param)
        #     slider_master.slider.configure(command=self.update_value(slider_param))
        #     # slider_master.textbox.bind("<Return>", self.enter_value(slider))
        # slider_master = getattr(self.test_slider_frame, slider_setting[0][0])
        # slider_master.slider.configure(command=self.update_value(slider_setting[0]))
        # commandに関数をreturnする関数を登録することで引数を含めて登録可能だが、
        # 引数は登録時点の値になるので注意
        # slider_setting[0][0]の値で直接属性選択をすることも可能だが、LSP上ではエラーが発生する
        # 気にしなくてもいいが、気になるならgetattrを使用のこと

    def update_value(self, slider):
        def callback(value):
            print(slider[0], value)

        return callback

    def enter_value(self, slider):
        def callback(event):
            entry = event.widget
            print(slider[0], entry.get())

        return callback

    def test_message(self):
        message = self.dirpath_frame.get_path()
        if message is None:
            message = "パスがありません"
        messagebox.showinfo(title="Test message", message=message)

    def canvas_work(self):
        imgs = self.dirpath_frame.get_files("png")
        self.test_canvas.set_from_imagepath(imgs)


class ParamsFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        title: str,
        param_list: list[str],
        default_value: list[int],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.param_list = param_list
        title_label = ctk.CTkLabel(self, text=title)
        title_label.pack()
        for param, value in zip(param_list, default_value):
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


@dataclass
class SliderFrameParams:
    param: str
    from_: int
    to: int
    number_of_steps: int
    default: int
    callback: Callable = lambda: None
    args: list = field(default_factory=list)


class SliderFrame(ctk.CTkFrame):
    def __init__(
        self, master, title: str, slider_param_list: list[SliderFrameParams], **kwargs
    ):
        super().__init__(master, **kwargs)
        # スライダーのパラメータリスト
        self.slider_list = slider_param_list
        # タイトルラベル
        title_label = ctk.CTkLabel(self, text=title)
        title_label.pack()

        # スライダーの敷き詰め
        for slider_param in slider_param_list:
            # ラベルとスライダーとエントリ用のフレーム
            # 名前としてパラメータの１番目を使用
            # self."slider[0]".slider等で使用可能が、
            # getattrを使用した方が良い
            setattr(self, slider_param.param, ctk.CTkFrame(self))
            # masterは実質self."slider[0]"
            master = getattr(self, slider_param.param)
            # paramの名前表示
            master.label = ctk.CTkLabel(master, text=slider_param.param)
            master.var = tk.IntVar()
            # defaultの入力
            master.var.set(slider_param.default)
            # sliderの値の一時保持
            master.val = master.var.get()
            # entry
            master.textbox = ctk.CTkEntry(
                master, state="disable", width=10, textvariable=master.var
            )
            # sliderの設定
            master.slider = ctk.CTkSlider(
                master,
                from_=slider_param.from_,
                to=slider_param.to,
                number_of_steps=slider_param.number_of_steps,
                variable=master.var,
                command=self.update_value(master, slider_param),
            )
            # less_button
            master.less_button = ctk.CTkButton(
                master,
                width=5,
                text="<",
                command=self.decrement_value(master.var, slider_param),
            )
            # more_button
            master.more_button = ctk.CTkButton(
                master,
                width=5,
                text=">",
                command=self.increment_value(master.var, slider_param),
            )
            # 配置
            master.label.grid(pady=5, row=0, column=0, sticky="ew")
            master.less_button.grid(pady=5, row=0, column=1, sticky="e")
            master.textbox.grid(pady=5, row=0, column=2, sticky="ew")
            master.more_button.grid(pady=3, row=0, column=3, sticky="w")

            master.slider.grid(pady=5, row=1, column=0, columnspan=4)
            master.pack()

    def increment_value(self, widget, param: SliderFrameParams):
        def callback():
            if widget.get() + 1 <= param.to:
                widget.set(widget.get() + 1)
            if param.args:
                param.callback(widget.get(), *param.args)
            else:
                param.callback(widget.get())
        return callback

    def decrement_value(self, widget, param: SliderFrameParams):
        def callback():
            if widget.get() - 1 >= param.from_:
                widget.set(widget.get() - 1)
            if param.args:
                param.callback(widget.get(), *param.args)
            else:
                param.callback(widget.get())
        return callback

    def update_value(self, master, param:SliderFrameParams):
        def callback(value):
            old_val = master.val
            value = int(float(value))
            if old_val != value:
                if param.args:
                    param.callback(value, *param.args)
                else:
                    param.callback(value)
                master.val = value
        return callback
    # !callbackの際には第1引数にmaster.varの値が入る

    def get_value(self, attr: str) -> int:
        master = getattr(self, attr)
        value = master.textbox.get()
        value = int(float(value))
        return value

    def set_value(self, attr: str, val):
        master = getattr(self, attr)
        master.var.set(val)


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
        iFilePath = filedialog.askopenfilename(filetypes=fTyp, initialdir=iFile)
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

        # デフォルトフォルダ
        self.iDirPath: str = init_dir

        # callback登録用
        self.pre_func = lambda: None
        self.post_func = lambda: None

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
        self.pre_func()

        iDir = self.path_entry.get()
        if iDir == "":
            iDir = os.path.abspath(os.path.dirname(__file__))
        iDirPath = filedialog.askdirectory(initialdir=iDir)
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, iDirPath)

        self.post_func()

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

    def add_pre_callback(self, func):
        self.pre_func = func

    def add_post_callback(self, func):
        self.post_func = func


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
        self.current_image = 0

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
        self.num_of_image = len(self.imgs)

        if self.imgs:
            self.canvas.delete("all")
            self.canvas.create_image(
                self.canvas_width / 2,
                self.canvas_height / 2,
                image=self.imgs[self.current_image].img,
            )

        self.image_name.configure(text=imgs[self.current_image].name)

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


class ResultTable(ctk.CTkFrame):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # self.post_func = lambda e: None
        self.post_func = lambda e: print("a")
        self.export_func = lambda: None

        self.tb = ttk.Treeview(self, columns=("file", "x", "y"), selectmode="browse")

        self.tb.column("#0", width=0, stretch="no")
        self.tb.column("file", width=100)
        self.tb.column("x", width=80)
        self.tb.column("y", width=80)

        self.tb.heading("file", text="file")
        self.tb.heading("x", text="x")
        self.tb.heading("y", text="y")

        self.bt_frame = ctk.CTkFrame(self)
        self.bt_i = ctk.CTkButton(self.bt_frame, text="export", command=self.export_callback)
        self.bt_d = ctk.CTkButton(self.bt_frame, text="delete", command=self.delete_selection)

        self.tb.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        self.bt_frame.pack(padx=5, pady=5)
        self.bt_i.grid(row=0, column=0)
        self.bt_d.grid(row=0, column=1)


    def insert(self, name, x, y, iid=None):
        self.tb.insert(parent="", iid=iid, index="end", values=(name, x, y))

    def delete_selection(self):
        iid = self.tb.selection()
        if len(iid) != 0:
            self.tb.delete(iid)

    def delete_all(self):
        self.tb.delete(*self.tb.get_children())

    def export_callback(self):
        items = self.tb.get_children()
        data = []
        for i in items:
            val = self.tb.item(i)["values"]
            data.append(val)
        file = filedialog.asksaveasfilename()
        with open(file + ".csv", "w") as f:
            writer = csv.writer(f)
            writer.writerows(data)

    def add_post_select_item(self, func):
        self.post_func = func
        self.tb.bind("<<TreeviewSelect>>", self.post_func)

    def update_params(self, iid, x, y):
        self.tb.set(iid, column="x", value=x)
        self.tb.set(iid, column="y", value=y)


if __name__ == "__main__":
    app = Test()
    app.mainloop()
