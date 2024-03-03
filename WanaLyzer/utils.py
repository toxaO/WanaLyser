import glob


def get_img_path_list(folder_path: str, img_type: str) -> list[str]:
    path_list = glob.glob(folder_path + "/*." + img_type)
    path_list.sort()
    return path_list


if __name__ == "__main__":
    testset = "/Users/tokumasa/Projects/WanaLyzer3.0/test/testset"
    print(get_img_path_list(testset, "bmp"))
