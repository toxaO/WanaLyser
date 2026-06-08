import logging
from pathlib import Path

logger = logging.getLogger("WanaLyzer")
logger.setLevel(logging.DEBUG)

format = "%(levelname)-9s  %(asctime)s [%(filename)s:%(lineno)d] %(message)s"

st_handler = logging.StreamHandler()
st_handler.setLevel(logging.DEBUG)
# StreamHandlerによる出力フォーマットを先で定義した'format'に設定
st_handler.setFormatter(logging.Formatter(format))

Path("log").mkdir(exist_ok=True)
fl_handler = logging.FileHandler(filename="log/WanaLyzer.log", encoding="utf-8")
fl_handler.setLevel(logging.WARNING)
# FileHandlerによる出力フォーマットを先で定義した'format'に設定
fl_handler.setFormatter(logging.Formatter(format))

logger.addHandler(st_handler)
logger.addHandler(fl_handler)

# logger.info("I am info log.")
# logger.warning("I am warning log.")

