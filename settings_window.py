from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSlider, QCheckBox, QLineEdit, QPushButton, 
                             QFormLayout, QGroupBox)
from PyQt5.QtCore import Qt, pyqtSignal

class SettingsWindow(QDialog):
    # 定义一个信号，当用户点击保存时，将配置字典传回给主窗口
    settings_changed = pyqtSignal(dict)

    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("桌宠设置")
        self.resize(300, 400)
        self.current_settings = current_settings
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # --- 外观设置 ---
        appearance_group = QGroupBox("外观设置")
        appearance_layout = QFormLayout()

        # 1. 尺寸缩放 (50% - 200%)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(50, 200)
        self.size_slider.setValue(int(self.current_settings.get('scale', 1.0) * 100))
        self.size_label = QLabel(f"{self.size_slider.value()}%")
        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(f"{v}%"))
        appearance_layout.addRow("缩放比例:", self._create_slider_layout(self.size_slider, self.size_label))

        # 2. 透明度 (20% - 100%)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(int(self.current_settings.get('opacity', 1.0) * 100))
        self.opacity_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        appearance_layout.addRow("透明度:", self._create_slider_layout(self.opacity_slider, self.opacity_label))

        # 3. 始终置顶
        self.topmost_cb = QCheckBox("始终在最前")
        self.topmost_cb.setChecked(self.current_settings.get('topmost', True))
        appearance_layout.addRow(self.topmost_cb)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        # --- 行为设置 ---
        behavior_group = QGroupBox("行为设置")
        behavior_layout = QFormLayout()

        # 4. 允许自动移动
        self.auto_move_cb = QCheckBox("允许自由走动")
        self.auto_move_cb.setChecked(self.current_settings.get('auto_move', True))
        behavior_layout.addRow(self.auto_move_cb)

        # 5. API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password) # 隐藏显示
        self.api_key_edit.setText(self.current_settings.get('api_key', ''))
        self.api_key_edit.setPlaceholderText("在此输入 DeepSeek API Key")
        behavior_layout.addRow("API Key:", self.api_key_edit)

        behavior_group.setLayout(behavior_layout)
        layout.addWidget(behavior_group)

        # --- 底部按钮 ---
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存生效")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 美化一下设置窗口
        self.setStyleSheet("""
            QDialog { background-color: #f0f0f0; }
            QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
        """)

    def _create_slider_layout(self, slider, label):
        """辅助函数：创建滑块和标签的水平布局"""
        h_layout = QHBoxLayout()
        h_layout.addWidget(slider)
        h_layout.addWidget(label)
        container = QDialog() # 仅用作容器 widget，不是真正的 dialog
        # 注意：这里用 QWidget 做容器更好，但为了偷懒直接返回布局对象给 addRow 也可以，
        # 不过 PyQt addRow 支持 layout，所以我们需要把这个 h_layout 包装进一个 widget 或者直接返回 layout
        # 标准做法是返回 Layout，QFormLayout.addRow 支持 Layout
        return h_layout

    def save_settings(self):
        """收集当前设置并发送信号"""
        new_settings = {
            'scale': self.size_slider.value() / 100.0,
            'opacity': self.opacity_slider.value() / 100.0,
            'topmost': self.topmost_cb.isChecked(),
            'auto_move': self.auto_move_cb.isChecked(),
            'api_key': self.api_key_edit.text().strip()
        }
        self.settings_changed.emit(new_settings)
        self.accept()