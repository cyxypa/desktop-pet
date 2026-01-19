# Settings/settings_dialog.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import QSignalBlocker, pyqtSignal
from pathlib import Path
from Settings.settings_window_ui import Ui_settings_window
from Settings.settings_model import AppSettings
from Settings.settings_store import load_settings, save_settings


class SettingsDialog(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, current: dict | None = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_settings_window()
        self.ui.setupUi(self)
        if self.ui.scrollAreaWidgetContents_2.layout() is None:
            layout = QVBoxLayout(self.ui.scrollAreaWidgetContents_2)
            layout.setObjectName("pluginsLayout")
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)
        self.setWindowTitle("设置")
        current = load_settings().to_dict() if current is None else current
        self.populate_characters()  # 获取角色选项
        self.ui.character_comboBox.currentTextChanged.connect(
            self.on_character_changed
        )  # 角色变化
        self.apply_to_ui(current)

        self.ui.save_Button.clicked.connect(self.on_save_clicked)
        self.ui.restore_Button.clicked.connect(self.on_restore_clicked)

    def _assets_dir(self) -> Path:
        # Settings/settings_dialog.py 的上一级是 Settings，再上一级是项目根目录
        return Path(__file__).resolve().parents[1] / "Assets"

    def populate_characters(self) -> None:
        assets = self._assets_dir()

        with QSignalBlocker(self.ui.character_comboBox):  # type: ignore[arg-type]
            self.ui.character_comboBox.clear()

            if not assets.exists():
                self.ui.character_comboBox.addItem("（未找到 Assets 文件夹）")
                return

            chars = sorted(
                p.name
                for p in assets.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            )

            if not chars:
                self.ui.character_comboBox.addItem("（Assets 为空）")
                return

            self.ui.character_comboBox.addItems(chars)

    def populate_skins(self, character: str):
        skins_dir = self._assets_dir() / character
        with QSignalBlocker(self.ui.skin_comboBox):  # type: ignore[arg-type]
            self.ui.skin_comboBox.clear()
            if not skins_dir.exists():
                return
            skins = sorted(
                p.name
                for p in skins_dir.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            )
            self.ui.skin_comboBox.addItems(skins)

    def on_character_changed(self, character: str):
        self.populate_skins(character)

    def _set_combo_text(self, combo, text: str):
        """只在选项存在时选中；不存在则不改动选项列表"""
        if not text:
            return
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def apply_to_ui(self, s: dict) -> None:
        """把 settings dict 回填到界面控件"""
        blockers = [
            QSignalBlocker(self.ui.character_comboBox),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.skin_comboBox),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.ifmove_checkBox),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.speed_Slider),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.speedprobably_Slider),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.minmovetime_spinBox),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.maxmovetime_spinBox),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.fps_spinBox),  # type: ignore[arg-type]
            QSignalBlocker(self.ui.size_spinBox),  # type: ignore[arg-type]
        ]

        self._set_combo_text(self.ui.character_comboBox, s.get("character", ""))
        self.populate_skins(self.ui.character_comboBox.currentText())
        self._set_combo_text(self.ui.skin_comboBox, s.get("skin", ""))

        if "enable_move" in s:
            self.ui.ifmove_checkBox.setChecked(bool(s["enable_move"]))
        if "speed" in s:
            self.ui.speed_Slider.setValue(int(s["speed"]))
        if "move_probability" in s:
            self.ui.speedprobably_Slider.setValue(int(s["move_probability"]))
        if "move_duration_min" in s:
            self.ui.minmovetime_spinBox.setValue(int(s["move_duration_min"]))
        if "move_duration_max" in s:
            self.ui.maxmovetime_spinBox.setValue(int(s["move_duration_max"]))
        if "fps" in s:
            self.ui.fps_spinBox.setValue(int(s["fps"]))
        if "pet_size" in s:
            self.ui.size_spinBox.setValue(int(s["pet_size"]))

        del blockers

    def read_from_ui(self) -> AppSettings:
        return AppSettings(
            character=self.ui.character_comboBox.currentText(),
            skin=self.ui.skin_comboBox.currentText(),
            enable_move=self.ui.ifmove_checkBox.isChecked(),
            speed=self.ui.speed_Slider.value(),
            move_probability=self.ui.speedprobably_Slider.value(),  # 0~100
            move_duration_min=self.ui.minmovetime_spinBox.value(),
            move_duration_max=self.ui.maxmovetime_spinBox.value(),
            fps=self.ui.fps_spinBox.value(),
            pet_size=self.ui.size_spinBox.value(),
        )

    def on_save_clicked(self):
        s = self.read_from_ui()

        # 兜底校验：min <= max
        if s.move_duration_min > s.move_duration_max:
            s.move_duration_max = s.move_duration_min

        save_settings(s)  # 写入 Settings/config.json
        self.settings_saved.emit(s.to_dict())  # ✅ 只有这里才通知桌宠刷新
        self.accept()  # 关闭窗口（不想关就删掉）

    def on_restore_clicked(self):
        defaults = AppSettings()

        # 恢复默认只改 UI，不改桌宠（桌宠仍需点“保存设置”才刷新）
        # 为了让默认角色/皮肤能被正确选中，先刷新选项列表
        self.populate_characters()
        self._set_combo_text(self.ui.character_comboBox, defaults.character)
        self.on_character_changed(self.ui.character_comboBox.currentText())

        self.apply_to_ui(defaults.to_dict())

        # 如果你希望“恢复默认”也立刻生效，把下面两行取消注释即可：
        # save_settings(defaults)
        # self.settings_saved.emit(defaults.to_dict())
