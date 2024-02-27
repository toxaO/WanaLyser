import os
import sys
import tkinter
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk


class Test(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x600")
        self.title("Widget test")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.path_frame = PathFrame(master=self)
        self.path_frame.grid(row=0, column=0)


class PathFrame(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.label = ctk.CTkLabel(self, text="ファイルパスを選択してください")
        self.label.grid(row=0, column=0, padx=10)

        self.path_entry = ctk.CTkEntry(self, width=300)
        self.path_entry.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.path_select = ctk.CTkButton(
            self, text="選択", command=self.dirdialog_clicked
        )
        self.path_select.grid(row=1, column=1, padx=10, pady=10, sticky="w")

    def dirdialog_clicked(self, iDir: str = ""):
        if iDir == "":
            iDir = os.path.abspath(os.path.dirname(__file__))
        iDirPath = filedialog.askdirectory(initialdir=iDir)
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, iDirPath)


if __name__ == "__main__":
    app = Test()
    app.mainloop()
