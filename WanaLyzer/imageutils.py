import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
import cv2
import numpy
import structure as st
import widgets
from PIL import Image, ImageTk

COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)


def pil_to_cv2(pil_image):
    "PIL -> CV2"

    # pil_imageをNumPy配列に変換
    pil_image_array = numpy.array(pil_image)

    # RGB -> BGR によりCV2画像オブジェクトに変換
    cv2_image = cv2.cvtColor(pil_image_array, cv2.COLOR_RGB2BGR)

    return cv2_image


def cv2_to_pil(cv2_image):
    "CV2 -> PIL"

    # BGR -> RGB
    rgb_cv2_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)

    # NumPy配列からPIL画像オブジェクトを生成
    pil_image = Image.fromarray(rgb_cv2_image)

    return pil_image


def cv2_to_tk(cv2_image):
    "CV2 -> Tkinter"

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


class ImageDataHolder:
    def __init__(self, image_path: str, beam_thresh: int, ball_thresh: int) -> None:
        """
        読み込んだ画像の情報をまとめて保持するクラス
        1024x1024サイズのbmpを想定
        dcmはあとで対応
        """
        filetype = os.path.splitext(image_path)[1]  # 拡張子
        self.imread = False
        if filetype == ".dcm":
            messagebox.showinfo("まだ未対応")
            self.imread = False
            return
        elif filetype == ".bmp":
            self.img_name = os.path.basename(image_path)
            # 日本語ファイル名対応のため、cv2.imread()は使用せず
            img_pil = Image.open(image_path)
            self.img_raw = pil_to_cv2(img_pil)
            self.update_images(beam_thresh, ball_thresh)
            self.imread = True
        else:
            messagebox.showinfo("未対応")
            self.imread = False
            return

    def update_images(self, beam_thresh, ball_thresh):
        self.update_beam_threshold(beam_thresh)
        self.update_ball_threshold(ball_thresh)
        self.draw_contour_imgage()

    def update_beam_threshold(self, threshold):
        self.beam_contour = Contour(self.img_raw, threshold)
        beam_pos = self.beam_contour.rect_contour()
        if beam_pos.width > beam_pos.height:
            self.focus_area = (
                512 - int(beam_pos.width / 2) - 25,
                512 + int(beam_pos.width / 2) + 25,
            )
        else:
            self.focus_area = (
                512 - int(beam_pos.height / 2) - 25,
                512 + int(beam_pos.height / 2) + 25,
            )
        if beam_pos.width > 1000 or beam_pos.height > 1000:
            self.focus_area = (0, 1023)

    def update_ball_threshold(self, threshold):
        self.ball_contour = Contour(self.img_raw, threshold)

    def draw_contour_imgage(self):
        beam_pos = self.beam_contour.rect_contour()
        ball_pos = self.ball_contour.circle_contour()
        self.img_all_contoured = self.img_raw.copy()
        cv2.rectangle(self.img_all_contoured, beam_pos.nw, beam_pos.se, COLOR_GREEN)
        cv2.circle(self.img_all_contoured, ball_pos.center, ball_pos.r, COLOR_RED)
        self.img_all_contoured_focused = self.img_all_contoured[
            self.focus_area[0] : self.focus_area[1],
            self.focus_area[0] : self.focus_area[1],
        ]

    def return_resize_imgaeTk(self) -> list[ImageTk.PhotoImage]:
        imgs = [
            self.img_raw,
            self.img_all_contoured,
            self.img_all_contoured_focused,
            self.beam_contour.img_binary,
            self.ball_contour.img_binary,
        ]
        resized_imgs = []
        for img in imgs:
            resized_img = cv2_to_pil(img).resize(size=(300, 300))
            tk_img = ImageTk.PhotoImage(resized_img)
            resized_imgs.append(tk_img)
        return resized_imgs

    def return_name_list(self) -> list[str]:
        names = [
            self.img_name + "_raw",
            self.img_name + "_contour",
            self.img_name + "_focus",
            self.img_name + "_beam_bi",
            self.img_name + "_ball_bi",
        ]
        return names


class Contour:
    """
    cv2_imgageとthresholdを与えると最小区域のコンツールを与えるクラス
    """

    def __init__(self, img, threshold):
        self.img = img
        self.update_binary(threshold)

    def update_binary(self, threshold):
        img_gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        if threshold == 0:
            _, self.img_binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_OTSU)
        else:
            _, self.img_binary = cv2.threshold(
                img_gray, threshold, 255, cv2.THRESH_BINARY
            )
        self.update_contours()

    def update_contours(self):
        self.contours, _ = cv2.findContours(
            self.img_binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        self.update_min_contour()

    def update_min_contour(self):
        self.min_contour = min(self.contours, key=lambda x: cv2.contourArea(x))

    def rect_contour(self):
        x, y, w, h = cv2.boundingRect(self.min_contour)
        return st.Rectungle(x, y, w, h)

    def circle_contour(self):
        (x, y), r = cv2.minEnclosingCircle(self.min_contour)
        return st.Circle(int(x), int(y), int(r))


def button_callback():
    img_path = filepath_frame.get_path()
    beam_thresh = slider_frame.get_value("beam_thresh")
    ball_thresh = slider_frame.get_value("ball_thresh")
    global idh
    idh = ImageDataHolder(img_path, beam_thresh, ball_thresh)
    image_frame.set_from_ImageNameSet(
        idh.return_resize_imgaeTk(), idh.return_name_list()
    )


def slider_callback(_):
    beam_thresh = slider_frame.get_value("beam_thresh")
    ball_thresh = slider_frame.get_value("ball_thresh")
    global idh
    if idh.imread:
        idh.update_images(beam_thresh, ball_thresh)
        image_frame.set_from_ImageNameSet(
            idh.return_resize_imgaeTk(), idh.return_name_list()
        )


if __name__ == "__main__":
    img = "tests/img/testset/01.bmp"
    app = ctk.CTk()
    img_read = False
    idh: ImageDataHolder

    # filepath_frame
    filepath_frame = widgets.FilePathFrame(app, iFile=img)
    filepath_frame.grid(row=0, column=0)

    # canvas_frame
    image_frame = widgets.ImageFrame(app)
    image_frame.grid(row=1, column=0)

    # slider_frame
    slider_list = [widgets.SliderFrameParams("beam_thresh", 0, 255, 255, 0, slider_callback),
                   widgets.SliderFrameParams("ball_thresh", 0, 255, 255, 100, slider_callback)]
    slider_frame = widgets.SliderFrame(app, "thresh", slider_list)
    slider_frame.grid(row=1, column=1, sticky="n")

    # run button
    button = ctk.CTkButton(app, text="read", command=button_callback)
    button.grid(row=0, column=1)

    app.mainloop()
