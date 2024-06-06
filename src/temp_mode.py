import os
import imageutils
import widgets
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox


class Temp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.items = []
        self.selected_item = None

        # フォルダ選択
        self.fd = widgets.FolderPathFrame(master=self)
        self.fd.add_post_callback(self.correct_images)
        self.fd.grid(row=0, column=0, sticky="EW")

        # 解析画面
        self.bv = imageutils.BasicViewer(master=self)
        self.bv.grid(row=1, column=0)

        # 結果表示
        self.tb = widgets.ResultTable(master=self)
        self.tb.grid(row=1, column=1, sticky="NS")
        self.tb.add_post_select_item(self.select_table)
        self.bv.set_postupdate_func(self.update_button)

    def correct_images(self):
        # パス取得
        dir_path = self.fd.get_path()
        # bmpのみにフィルタリング
        files = [
            os.path.join(dir_path, f) for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))
            and os.path.splitext(f)[1] == ".bmp"
        ]
        files.sort()
        # item list初期化
        self.items = []
        self.tb.delete_all()
        # item class を使用してbmpファイルをlistにセット
        for f in files:
            item = Item_data(f)
            # selected_itemを解析
            self.analyze_item(item)
            # itemsに格納
            self.items.append(item)

        self.set_table()
        self.selected_item =  0
        # self.analyze_item(self.items[0])
        self.bv.register_image(self.items[self.selected_item].path,
                               self.items[self.selected_item].x,
                               self.items[self.selected_item].y)
        self.tb.tb.selection_set(self.items[0].path)

    def analyze_item(self, item):
        # selected_itemを解析してitemを更新
        self.bv.idh.setup(item.path,
                          beam_thresh=item.beam_thresh,
                          ball_thresh=item.ball_thresh)
        (item.x, item.y) = self.bv.idh.return_center_sub()

    def set_table(self):
        # self.itemsの内容を全てtableに反映する
        self.tb.delete_all()
        for i in self.items:
            self.tb.insert(i.name, i.x, i.y, i.path)

    def update_button(self):
        param = self.bv.return_params()
        iid = self.items[self.selected_item].path
        x = param[0]
        y = param[1]
        self.items[self.selected_item].x = param[0]
        self.items[self.selected_item].y = param[1]
        self.items[self.selected_item].beam_thresh = param[2]
        self.items[self.selected_item].ball_thresh = param[3]
        self.tb.update_params(iid, x, y)

    def select_table(self, e):
        iid = self.tb.tb.focus()
        self.selected_item = self.tb.tb.index(iid)
        self.analyze_item(self.items[self.selected_item])
        self.bv.register_image(self.items[self.selected_item].path,
                               self.items[self.selected_item].beam_thresh,
                               self.items[self.selected_item].ball_thresh)
        self.bv.set_beam_thresh(self.items[self.selected_item].beam_thresh)
        self.bv.set_ball_thresh(self.items[self.selected_item].ball_thresh)


# 各画像データの保持用クラス
class Item_data():
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.x = None
        self.y = None
        self.beam_thresh = 0
        self.ball_thresh = 100




if __name__ == "__main__":
    app = Temp()
    app.mainloop()
