# Settings/settings_dialog.py
from PyQt5.QtWidgets import QDialog
from Settings.Ui_settings_window import Ui_settings_window  # 注意路径


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_settings_window()
        self.ui.setupUi(self)  # 只负责把控件“搭出来”
        self.setWindowTitle("设置")
