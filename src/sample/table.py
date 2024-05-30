# サンプルコード
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox

def select_record(event):
    # 選択行の判別
    record_id = tree.focus()
    # 選択行のレコードを取得
    record_values = tree.item(record_id, 'values')
    if tk.messagebox.showinfo(title="選択行の確認",
                              message="次の行が選択されました=> id："
                              + record_values[0]
                              + ",Name：" + record_values[1]
                              + ",Score：" + record_values[2]):
        tree.delete(record_id)
    else:
        pass

# 列の識別名を指定
column = ('ID', 'Name', 'Score')
# メインウィンドウの生成
root = tk.Tk()
root.title('Score List')
root.geometry('400x300')
# Treeviewの生成
tree = ttk.Treeview(root, columns=column)
tree.bind("<<TreeviewSelect>>", select_record)
# 列の設定
tree.column('#0',width=0, stretch='no')
tree.column('ID', anchor='center', width=80)
tree.column('Name',anchor='w', width=100)
tree.column('Score', anchor='center', width=80)
# 列の見出し設定
tree.heading('#0',text='')
tree.heading('ID', text='ID',anchor='center')
tree.heading('Name', text='Name', anchor='w')
tree.heading('Score',text='Score', anchor='center')
# レコードの追加
tree.insert(parent='', index='end', iid=0 ,values=(1, 'KAWASAKI',80))
tree.insert(parent='', index='end', iid=1 ,values=(2,'SHIMIZU', 90))
tree.insert(parent='', index='end', iid=2, values=(3,'TANAKA', 45))
tree.insert(parent='', index='end', iid=3, values=(4,'OKABE', 60))
tree.insert(parent='', index='end', iid=4, values=(5,'MIYAZAKI', 99))
# ウィジェットの配置
tree.pack(pady=10)

root.mainloop()
