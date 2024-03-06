import os
from tkinter import messagebox

import customtkinter as ctk
import cv2
import numpy
import structure as st
import widgets
from PIL import Image, ImageTk

COLOR_GREEN = (0, 255, 0)
COLOR_RED = (0, 0, 255)
PIXEL_SIZE = 0.242


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
    def __init__(
        self,
        img_path: str = "",
        beam_thresh: int = 0,
        ball_thresh: int = 100,
        pixel_size: float = PIXEL_SIZE,
    ) -> None:
        """
        読み込んだ画像の情報をまとめて保持するクラス
        1024x1024サイズのbmpを想定
        dcmはあとで対応
        """
        self.beam_thresh = beam_thresh
        self.ball_thresh = ball_thresh
        self.pixel_size = pixel_size
        self.setup(img_path, beam_thresh, ball_thresh)

    def setup(
        self,
        img_path: str,
        beam_thresh: int | None = None,
        ball_thresh: int | None = None,
    ):
        if beam_thresh is None:
            beam_thresh = self.beam_thresh
        if ball_thresh is None:
            ball_thresh = self.ball_thresh
        filetype = os.path.splitext(img_path)[1]  # 拡張子
        self.imread = False
        if filetype == ".dcm":
            # todo!
            # support dicom
            messagebox.showinfo("info", "dcm file is not yet applied")
            self.imread = False
            return
        elif filetype == "":
            return
        elif filetype == ".bmp":
            self.img_name = os.path.basename(img_path)
            # 日本語ファイル名対応のため、cv2.imread()は使用せず
            img_pil = Image.open(img_path)
            self.img_raw = pil_to_cv2(img_pil)
            self.update_images(beam_thresh, ball_thresh)
            self.imread = True
        else:
            messagebox.showinfo("info", "file type is not approriate")
            self.imread = False
            return

    def update_images(
        self, beam_thresh: int | None = None, ball_thresh: int | None = None
    ):
        if beam_thresh is not None:
            self.update_beam_threshold(beam_thresh)
        if ball_thresh is not None:
            self.update_ball_threshold(ball_thresh)
        if not self.beam_contour.rect_contour():
            self.rect_area = (0, 1023)
        self.draw_contour_imgage()

    def update_beam_threshold(self, threshold):
        self.beam_contour = Contour(self.img_raw, threshold)
        self.beam_pos = self.beam_contour.rect_contour()
        if self.beam_pos is not None:
            if self.beam_pos.width > self.beam_pos.height:
                self.rect_area = (
                    512 - int(self.beam_pos.width / 2) - 25,
                    512 + int(self.beam_pos.width / 2) + 25,
                )
            else:
                self.rect_area = (
                    512 - int(self.beam_pos.height / 2) - 25,
                    512 + int(self.beam_pos.height / 2) + 25,
                )
            if self.beam_pos.width > 1023 - 25 or self.beam_pos.height > 1023 - 25:
                self.rect_area = (0, 1023)
        else:
            self.rect_area = (0, 1023)

    def update_ball_threshold(self, threshold):
        self.ball_contour = Contour(self.img_raw, threshold)
        self.ball_pos = self.ball_contour.circle_contour()
        if self.ball_pos is not None:
            self.ball_area = (
                512 - int(self.ball_pos.width / 2) - 50,
                512 + int(self.ball_pos.width / 2) + 50,
            )
            if self.ball_pos.width > 1023 - 25:
                self.ball_area = (0, 1023)
        else:
            self.ball_area = (0, 1023)

    def draw_contour_imgage(self):
        self.beam_pos = self.beam_contour.rect_contour()
        self.ball_pos = self.ball_contour.circle_contour()
        self.img_all_contoured = self.img_raw.copy()
        img_beam_binary = self.beam_contour.img_binary.copy()
        img_ball_binary = self.ball_contour.img_binary.copy()
        self.img_beam_contoured = cv2.cvtColor(
                img_beam_binary, cv2.COLOR_GRAY2BGR)
        self.img_ball_contoured = cv2.cvtColor(
                img_ball_binary, cv2.COLOR_GRAY2BGR)
        if self.beam_pos is not None:
            # beam contour
            cv2.rectangle(
                self.img_beam_contoured, self.beam_pos.nw, self.beam_pos.se, COLOR_GREEN
            )
            cv2.rectangle(
                self.img_all_contoured, self.beam_pos.nw, self.beam_pos.se, COLOR_GREEN
            )
            # beam center line
            cv2.line(
                self.img_all_contoured,
                self.beam_pos.nw,
                self.beam_pos.se,
                COLOR_GREEN,
                1,
            )
            cv2.line(
                self.img_all_contoured,
                self.beam_pos.ne,
                self.beam_pos.sw,
                COLOR_GREEN,
                1,
            )

        if self.ball_pos is not None:
            cv2.circle(
                self.img_ball_contoured,
                self.ball_pos.center,
                self.ball_pos.r,
                COLOR_RED,
            )
            cv2.circle(
                self.img_all_contoured, self.ball_pos.center, self.ball_pos.r, COLOR_RED
            )
            cv2.line(
                self.img_all_contoured, self.ball_pos.n, self.ball_pos.s, COLOR_RED, 1
            )
            cv2.line(
                self.img_all_contoured, self.ball_pos.e, self.ball_pos.w, COLOR_RED, 1
            )
        # todo
        # 各コンツールの中心を把握するためのlineをひく
        if self.beam_pos is not None:
            self.img_beam_contoured = self.img_beam_contoured[
                self.rect_area[0] : self.rect_area[1],
                self.rect_area[0] : self.rect_area[1],
            ]
            self.img_ball_contoured = self.img_ball_contoured[
                self.ball_area[0] : self.ball_area[1],
                self.ball_area[0] : self.ball_area[1],
            ]
            self.img_all_contoured_focused = self.img_all_contoured[
                self.rect_area[0] : self.rect_area[1],
                self.rect_area[0] : self.rect_area[1],
            ]
        else:
            self.img_all_contoured_focused = self.img_all_contoured.copy()

    def return_resize_imgaeTk(self) -> list[ImageTk.PhotoImage]:
        imgs = [
            self.img_all_contoured_focused,
            self.img_all_contoured,
            self.img_beam_contoured,
            self.img_ball_contoured,
            self.img_raw,
        ]
        resized_imgs = []
        for img in imgs:
            resized_img = cv2_to_pil(img).resize(size=(300, 300))
            tk_img = ImageTk.PhotoImage(resized_img)
            resized_imgs.append(tk_img)
        return resized_imgs

    def return_name_list(self) -> list[str]:
        names = [
            self.img_name + "_focus",
            self.img_name + "_contour",
            self.img_name + "_beam_bi",
            self.img_name + "_ball_bi",
            self.img_name + "_raw",
        ]
        return names

    def return_center_sub(self) -> tuple[float, float] | None:
        if self.ball_pos is not None and self.beam_pos is not None:
            result = []
            for beam, ball in zip(self.beam_pos.center, self.ball_pos.center):
                # print((beam - ball) * self.pixel_size)
                result.append((beam - ball) * self.pixel_size)
            return tuple(result)
        else:
            return None


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
        if self.contours:
            self.min_contour = min(self.contours, key=lambda x: cv2.contourArea(x))
        else:
            self.min_contour = None

    def rect_contour(self) -> st.Rectungle | None:
        if self.min_contour is not None:
            x, y, w, h = cv2.boundingRect(self.min_contour)
            return st.Rectungle(x, y, w, h)
        else:
            return None

    def circle_contour(self) -> st.Circle | None:
        if self.min_contour is not None:
            (x, y), r = cv2.minEnclosingCircle(self.min_contour)
            return st.Circle(int(x), int(y), int(r))
        else:
            return None


def button_callback(idh: ImageDataHolder):
    def callback():
        img_path = filepath_frame.get_path()
        beam_thresh = slider_frame.get_value("beam_thresh")
        ball_thresh = slider_frame.get_value("ball_thresh")
        idh.setup(img_path, beam_thresh, ball_thresh)
        if idh.imread:
            image_frame.set_from_ImageNameSet(
                idh.return_resize_imgaeTk(), idh.return_name_list()
            )
            print(idh.return_center_sub())

    return callback


def beam_slider(val, idh):
    beam_thresh = val
    if idh.imread:
        idh.update_images(beam_thresh=beam_thresh)
        image_frame.set_from_ImageNameSet(
            idh.return_resize_imgaeTk(), idh.return_name_list()
        )
        idh.return_center_sub()


def ball_slider(val, idh):
    ball_thresh = val
    if idh.imread:
        idh.update_images(ball_thresh=ball_thresh)
        image_frame.set_from_ImageNameSet(
            idh.return_resize_imgaeTk(), idh.return_name_list()
        )
        idh.return_center_sub()


if __name__ == "__main__":
    img = "tests/img/testset/01.bmp"
    app = ctk.CTk()
    idh = ImageDataHolder()

    # filepath_frame
    filepath_frame = widgets.FilePathFrame(app, iFile=img)

    # canvas_frame
    image_frame = widgets.ImageFrame(app)

    # slider_frame
    slider_list = [
        widgets.SliderFrameParams("beam_thresh", 0, 255, 255, 0, beam_slider, [idh]),
        widgets.SliderFrameParams("ball_thresh", 0, 255, 255, 100, ball_slider, [idh]),
    ]
    slider_frame = widgets.SliderFrame(app, "閾値（値0ならOTSU法）", slider_list)

    # run button
    button = ctk.CTkButton(app, text="read", command=button_callback(idh))

    # result frame
    result_frame = ctk.CTkFrame(app)
    desc_label = ctk.CTkLabel(result_frame,
                              text="ballを基準に照射野中心は").pack()
    display_label = ctk.CTkLabel(result_frame).pack()

    # place widgets
    # row 0
    filepath_frame.grid(row=0, column=0)
    button.grid(row=0, column=1, padx=10, pady=10, sticky="news")

    # row 1
    image_frame.grid(row=1, column=0, rowspan=2)
    slider_frame.grid(row=1, column=1, padx=10, pady=10, sticky="n")

    # row 2
    result_frame.grid(row=2, column=1, sticky= "news", padx=10, pady=10)

    app.mainloop()
