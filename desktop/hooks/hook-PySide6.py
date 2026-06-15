# PyInstaller hook — solo plugin Qt essenziali (no QML / no debug artifacts)
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("PySide6.QtCore") + collect_submodules("PySide6.QtGui") + collect_submodules("PySide6.QtWidgets")

datas = collect_data_files(
    "PySide6",
    includes=[
        "**/plugins/platforms/*.dll",
        "**/plugins/styles/*.dll",
        "**/plugins/iconengines/*.dll",
        "**/plugins/imageformats/*.dll",
    ],
)
