import glob
import os
import sys

import cv2

import utils


class Analyzer:
    def __init__(self, image_path) -> None:
        pass


if __name__ == "__main__":
    testset = "/Users/tokumasa/Projects/WanaLyzer3.0/test/testset"
    img_list = utils.get_img_path_list(testset, "bmp")
    print(sys.path)
