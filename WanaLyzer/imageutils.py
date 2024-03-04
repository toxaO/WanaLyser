import os
import numpy
import tkinter as tk
import customtkinter as ctk
import cv2

from PIL import Image, ImageTk
from tkinter import messagebox

import widgets
import structure as st

COLOR_GREEN = (0, 255, 0)


def pil_to_cv2(pil_image):
    'PIL -> CV2'

    # pil_imageをNumPy配列に変換
    pil_image_array = numpy.array(pil_image)

    # RGB -> BGR によりCV2画像オブジェクトに変換
    cv2_image = cv2.cvtColor(pil_image_array, cv2.COLOR_RGB2BGR)

    return cv2_image


def cv2_to_pil(cv2_image):
    'CV2 -> PIL'

    # BGR -> RGB
    rgb_cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)

    # NumPy配列からPIL画像オブジェクトを生成
    pil_image = Image.fromarray(rgb_cv2_image)

    return pil_image


def cv2_to_tk(cv2_image):
    'CV2 -> Tkinter'

    # BGR -> RGB
    rgb_cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)

    # NumPy配列からPIL画像オブジェクトを生成
    pil_image = Image.fromarray(rgb_cv2_image)

    # PIL画像オブジェクトをTkinter画像オブジェクトに変換
    tk_image = ImageTk.PhotoImage(pil_image)

    return tk_image


def cv2_to_resize_tk(cv2_image, size=(300, 300)):
    img = cv2_to_pil(cv2_image)
    resized_img = img.resize(size=size)
    tk_img = ImageTk.PhotoImage(resized_img)
    return tk_img


class ImageHolder:
    def __init__(self, image_path: str, beam_thresh: int = 0, ball_thresh: int=100) -> None:
        """
        元画像を二値化、グレー化して保持するクラス
        thresh=0で大津法、数値指定で閾値
        """
        filetype = os.path.splitext(image_path)[1] # 拡張子
        if filetype == ".dcm":
            messagebox.showinfo("まだ未対応")
            return
        elif filetype == ".bmp":
            img_pil = Image.open(image_path)
            self.img_raw = pil_to_cv2(img_pil)
            self.img_gray = cv2.cvtColor(self.img_raw, cv2.COLOR_BGR2GRAY)
            self.update_binary(beam_thresh, ball_thresh)
            self.img_name = os.path.basename(image_path)
        else:
            messagebox.showinfo("未対応")
            return

    def update_binary(self, beam_thresh, ball_thresh):
        if beam_thresh == 0:
            _, self.img_beam_binary = cv2.threshold(self.img_gray, 0, 255, cv2.THRESH_OTSU)
        else:
            _, self.img_beam_binary = cv2.threshold(self.img_gray, beam_thresh , 255, cv2.THRESH_BINARY)

        if ball_thresh == 0:
            _, self.img_ball_binary = cv2.threshold(self.img_gray, 0, 255, cv2.THRESH_OTSU)
        else:
            _, self.img_ball_binary = cv2.threshold(self.img_gray, ball_thresh , 255, cv2.THRESH_BINARY)

    def return_resize_imgaeTk(self):
        imgs = [self.img_raw, self.img_gray, self.img_beam_binary, self.img_ball_binary]
        resized_imgs = []
        for img in imgs:
            resized_img = cv2_to_pil(img).resize(size=(300, 300))
            tk_img = ImageTk.PhotoImage(resized_img)
            resized_imgs.append(tk_img)
        return resized_imgs

    def return_name_list(self):
        names = [self.img_name + "_raw", self.img_name + "_gray", self.img_name + "_beam_bi", self.img_name + "_ball_bi"]
        return names


class BeamContour:
    def __init__(self, img_beam_binary, params: st.Params):
        self.img_binary = img_beam_binary
        self.update_contours(params)

    def update_contours(self, params: st.Params):
        contours, _ = cv2.findContours(self.img_binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        for contour in contours:
            if cv2.contourArea(contour) > params.beam_min ** 2 \
                and cv2.contourArea(contour) < params.beam_max ** 2:
                x, y, w, h = cv2.boundingRect(contour)
                self.beam_range = st.Rectungle(x=x, y=y, width=w, height=h)
        self.draw_contour()

    def draw_contour(self):
        img_color = cv2.cvtColor(self.img_binary, cv2.COLOR_GRAY2BGR)
        self.img_contour = cv2.rectangle(img_color, self.beam_range.nw, self.beam_range.se, COLOR_GREEN, 1)

class BallContour:
    def __init__(self) -> None:
        pass


if __name__ == "__main__":
    img = "tests/img/testset/01.bmp"
    app = ctk.CTk()

    # path_frame
    path_frame = widgets.FolderPathFrame(app)
    path_frame.grid(row=0, column=0, sticky="nw")

    # param_frame
    param_list = ["beam_thresh", "ball_thresh"]
    default_val = [0, 100]
    param_frame = widgets.ParamsFrame(app, param_list=param_list, default_value=default_val)
    param_frame.grid(row=1, column=0, sticky="n")

    # canvas_frame
    image_frame = widgets.ImageFrame(app)
    image_frame.grid(row=0, column=1, rowspan=2)

    # run
    beam_thresh = int(param_frame.get_params()["beam_thresh"])
    ball_thresh = int(param_frame.get_params()["ball_thresh"])
    im_h = ImageHolder(img, beam_thresh=beam_thresh, ball_thresh=ball_thresh)

    # beam_param = st.Params(25)
    # beam = BeamContour(im_h.img_beam_binary, beam_param)
    # beam_resized_list = [cv2_to_resize_tk(beam.img_contour)]
    image_frame.set_from_ImageNameSet(im_h.return_resize_imgaeTk(), im_h.return_name_list())


    app.mainloop()
