import numpy as np
import os
import csv
import sys
import shutil
from tqdm import tqdm
import datetime as dt
from matplotlib import pyplot as plt
from matplotlib import patches
from tkinter import messagebox
from matplotlib.backends.backend_pdf import PdfPages

indexes = [(0, "Ga : 180.1", "RL", 1),
           (1, "Ga : 270", "AP", 0),
           (2, "Ga : 0", "RL", 0),
           (3, "Ga : 90", "AP", 1),
           (4, "Ga : 179.9", "RL", 1),
           (5, "Coli : 270", "RL", 0),
           (6, "Coli : 0", "RL", 0),
           (7, "Coli : 90", "RL", 0),
           (8, "Coli : 180", "RL", 0),
           (9, "Couch : 90", "RL", 0),
           (10, "Couch : 45", "RL", 0),
           (11, "Couch : 0", "RL", 0),
           (12, "Couch : 315", "RL", 0),
           (13, "Couch : 270", "RL", 0)
           ]

image_index = ["01.bmp",
               "02.bmp",
               "03.bmp",
               "04.bmp",
               "05.bmp",
               "06.bmp",
               "07.bmp",
               "08.bmp",
               "09.bmp",
               "10.bmp",
               "11.bmp",
               "12.bmp",
               "13.bmp",
               "14.bmp",
               ]


class Orient:
    def __init__(self, index: int, angle: str, x, x_inverse: bool = False):
        self.index = index
        self.angle = angle
        if x == "RL":
            self.L = "270"
            self.R = "90"
            self.x_axis = "(-)270 ← → 90(+)"
        else:
            self.L = "P"
            self.R = "A"
            self.x_axis = "(-)P ← → A(+)"
        self.U = "G"
        self.D = "T"
        self.y_axis = "(-)T ← → G(+)"
        if x_inverse == True:
            self.inverse = True
        else:
            self.inverse = False


def prepare_fig(title: str):
    # fig準備
    fig = plt.figure(figsize=(8.27, 11.69), dpi=100)
    plt.style.use("ggplot")
    plt.subplots_adjust(left=0.1,
                        bottom=0.06,
                        right=0.97,
                        top=0.9,
                        wspace=0.1,
                        hspace=0.6)
    # plt.subplots_adjust(left=0.08,
    #                     bottom=0.15,
    #                     right=0.97,
    #                     top=0.9,
    #                     wspace=0.2,
    #                     hspace=0.5)
    fig.suptitle(title, fontsize=20)  # fig title
    return fig


def main_plot(fig: plt.figure,
              subplot,
              ylabel: str,
              title: str,
              np_data: np.array,
              array_no: int,
              inverse: bool = False,
              dist_mode: bool = False):
    ax = fig.add_subplot(*subplot)  # plot position
    if inverse:
        i = -1
    else:
        i = 1
    ax.axhline(0, color="gray", alpha=0.3)
    ax.plot(np_data[-30:, 0], i * np_data[-30:, array_no].astype(np.float64))  # plot_data 反転も考慮
    ax.xaxis.set_tick_params(rotation=60, labelsize=6)
    # ax.tick_params(labelsize=8)
    if dist_mode:
        ax.set_ylim(0, 1.2)
        ax.spines["left"].set_color("gray")
        ax.spines["bottom"].set_color("gray")
    else:
        ax.set_ylim(-1.4, 1.4)
    ax.set_ylabel(ylabel)  # y-label
    ax.set_title(title)  # graph title
    # ax.axhline(1)
    rect = patches.Rectangle(xy=(-5, -1), width=40, height=2, color="white", alpha=0.4)
    ax.add_patch(rect)
    ax.set_xlim(-0.5, len(np_data)-0.5)
    if len(np_data) > 30:
        ax.set_xlim(-0.5, 29.5)
    return ax


def position_plot(fig: plt.figure,
                  subplot,
                  data: np.array,
                  orient: Orient,
                  x_no, y_no,
                  x_inverse: bool = False):
    ax = fig.add_subplot(*subplot)
    ax.axis("square")
    ax.set_title("position")
    c = patches.Circle(xy=(0, 0), radius=1, fc="white", alpha=0.4, ec="white")
    ax.add_patch(c)
    ax.set_ylim(-1.4, 1.4)
    ax.set_xlim(-1.4, 1.4)
    i = 1
    if x_inverse:
        i = -1
    ax.scatter(i * data[-30:-5, x_no].astype(np.float64), data[-30:-5, y_no].astype(np.float64), s=10, c="black",
               alpha=0.5)
    ax.scatter(i * data[-5:-1, x_no].astype(np.float64), data[-5:-1, y_no].astype(np.float64), s=10, c="r", alpha=0.5)
    ax.scatter(i * data[-1:, x_no].astype(np.float64), data[-1:, y_no].astype(np.float64), s=50, c="r", marker="+")
    ax.text(0.5, 0.94, orient.U, va='center', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.05, orient.D, va='center', ha='center', transform=ax.transAxes)
    ax.text(0.08, 0.5, orient.L, va='center', ha='center', transform=ax.transAxes)
    ax.text(0.92, 0.5, orient.R, va='center', ha='center', transform=ax.transAxes)
    ax.tick_params(labelleft=False, left=False, labelbottom=False, bottom=False)
    ax.set_xticks([-1,0,1])
    ax.set_yticks([-1,0,1])
    return ax


def image_plot(fig: plt.figure,
               subplot,
               orient: Orient,
               image: str):
    ax = fig.add_subplot(*subplot)
    im = plt.imread(image)
    im = im[420:580, 420:580]
    ax.imshow(im)
    ax.set_yticks([])
    ax.set_xticks([])
    ax.spines[:].set_color("gray")
    ax.text(0.5, 0.94, orient.U, va='center', ha='center', transform=ax.transAxes)
    ax.text(0.5, 0.05, orient.D, va='center', ha='center', transform=ax.transAxes)
    if not orient.inverse:
        ax.text(0.08, 0.5, orient.L, va='center', ha='center', transform=ax.transAxes)
        ax.text(0.92, 0.5, orient.R, va='center', ha='center', transform=ax.transAxes)
    else:
        ax.text(0.08, 0.5, orient.R, va='center', ha='center', transform=ax.transAxes)
        ax.text(0.92, 0.5, orient.L, va='center', ha='center', transform=ax.transAxes)
    ax.set_title("image(zoom)")
    return ax

def table_plotter(fig, np_data:np.array, orient, inverse_mode:int = False):
    x_inv = 1
    if inverse_mode:
        x_inv = -1
    table_data = np.array([["x_axis", x_inv * np_data[-1][orient.index*3 + 1].astype(np.float64)],  # orient_x
                           ["y_axis", np_data[-1][orient.index*3 + 2]],  # orient_y
                           ["distance", np.round(np_data[-1][orient.index*3 + 3].astype(np.float64), 3)]])
    ax = fig.add_subplot(4, 4, 15)
    tb = ax.table(cellText=table_data, loc="center", cellLoc="center")
    tb.scale(1, 2)
    ax.axis("off")
    ax.axis("tight")
    ax.set_title("Value")
    return ax


def fig_generator(orient: Orient, data: np.array):
    fig = prepare_fig(orient.angle)

    ax1 = main_plot(fig, (4, 1, 1), orient.x_axis, orient.angle + " : x_axis", data,
                    orient.index*3 + 1, inverse=orient.inverse)  # orient_x
    ax2 = main_plot(fig, (4, 1, 2), orient.y_axis, orient.angle + " : y_axis", data,
                    orient.index *3+ 2)  # orient_y
    ax3 = main_plot(fig, (4, 1, 3), "", orient.angle + " : " + "distance", data,
                    orient.index*3 + 3, dist_mode=True)
    ax4 = position_plot(fig, (4, 4, 13), data, orient, orient.index*3 + 1, orient.index*3 + 2,
                        x_inverse=orient.inverse)  # orient_x
    ax5 = image_plot(fig, (4, 4, 14), orient, "output/newest/" + image_index[orient.index])  # image

    # x_inv = 1
    # if orient.inverse:
    #     x_inv = -1
    # table_data = np.array([["x_axis", x_inv * data[-1][orient.index*3 + 1].astype(np.float64)],  # orient_x
    #                        ["y_axis", data[-1][orient.index*3 + 2]],  # orient_y
    #                        ["distance", np.round(data[-1][orient.index*3 + 3].astype(np.float64), 3)]])
    # ax6 = fig.add_subplot(4, 4, 15)
    # tb = ax6.table(cellText=table_data, loc="center", cellLoc="center")
    # tb.scale(1, 2)
    # ax6.axis("off")
    # ax6.axis("tight")
    # ax6.set_title("Value")

    ax6 = table_plotter(fig, data, orient, orient.inverse)

    ax7 = fig.add_subplot(4, 4, 16)  # material_image
    imR = plt.imread("material/" + str(orient.index + 1) + ".png")
    ax7.imshow(imR)
    ax7.axis("off")
    return fig


def main():
    fld = os.path.dirname(__file__)
    os.chdir(fld)
    if os.path.exists("record.csv"):
        with open("record.csv", "rt") as rec:
            reader = csv.reader(rec)
            record_data = [row for row in reader]
            np_record_data = np.array(record_data[1:])
    else:
        messagebox.showerror("データが存在しません", "WanaLyser2.0フォルダにrecord.csvが存在しません")
        sys.exit()

    pdf = PdfPages("report.pdf")

    # orient = Orient(*indexes[0])
    # fig = fig_generator(orient, np_record_data)
    # pdf.savefig(fig)

    for a in tqdm(range(14)):
        orient = Orient(*indexes[a])
        fig = fig_generator(orient, np_record_data)
        pdf.savefig(fig)

    pdf.close()

    shutil.copy("report.pdf", "output/post_report/" + dt.date.today().strftime("%Y%m%d") + ".pdf")

if __name__ == "__main__":
    main()
