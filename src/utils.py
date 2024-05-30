import os
import glob
import structure as st

from PIL import ImageTk, Image


def get_img_path_list(folder_path: str, img_type: str) -> list[str]:
    path_list = glob.glob(folder_path + "/*." + img_type)
    path_list.sort()
    return path_list


def img_path_list_to_ImageNameSet(img_path_list: list[str], size=(300, 300)) -> list[st.ImageNameSet]:
    sets = []
    for im in img_path_list:
        resized_img = Image.open(im)
        resized_img = resized_img.resize(size)
        sets.append(st.ImageNameSet(ImageTk.PhotoImage(resized_img), os.path.basename(im)))
    return sets


if __name__ == "__main__":
    testset = "/Users/tokumasa/Projects/WanaLyzer3.0/test/testset"
    print(get_img_path_list(testset, "bmp"))
