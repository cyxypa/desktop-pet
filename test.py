import glob,os,random
from PyQt5.QtWidgets import (QMainWindow, QLabel, QWidget, QVBoxLayout, 
                             QLineEdit, QTextEdit, QApplication, QPushButton,
                             QHBoxLayout, QSlider, QCheckBox, QSpinBox, 
                             QGroupBox, QFormLayout, QComboBox, QMenu)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QTransform
# 注：api_client 模块需自行实现，示例中注释相关依赖避免报错
# from api_client import ApiWorker, ApiClient  

# 新增：设置窗口类
class SettingsWindow(QWidget):
    # 定义信号，用于传递设置参数
    settings_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("桌宠设置")
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(400, 500)  # 固定窗口大小
        self.current_settings = current_settings or {}
        self.init_ui()
        
    def init_ui(self):
        # 整体布局
        main_layout = QVBoxLayout()
        
        # 1. 基础行为设置组
        behavior_group = QGroupBox("基础行为设置")
        behavior_layout = QFormLayout()
        
        # 移动速度滑块 (1-10)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(self.current_settings.get("speed", 2))
        self.speed_slider.setTickPosition(QSlider.TicksBelow)
        self.speed_slider.setTickInterval(1)
        behavior_layout.addRow("移动速度:", self.speed_slider)
        
        # 移动概率滑块 (0-100%)
        self.move_prob_slider = QSlider(Qt.Horizontal)
        self.move_prob_slider.setRange(0, 100)
        self.move_prob_slider.setValue(int(self.current_settings.get("move_probability", 0.35)*100))
        self.move_prob_slider.setTickPosition(QSlider.TicksBelow)
        self.move_prob_slider.setTickInterval(10)
        behavior_layout.addRow("自动移动概率 (%):", self.move_prob_slider)
        
        # 动画帧率 (10-60帧/秒)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 60)
        self.fps_spin.setValue(self.current_settings.get("fps", 50))  # 20ms ≈ 50fps
        behavior_layout.addRow("动画帧率 (帧/秒):", self.fps_spin)
        
        # 移动持续时间范围
        self.move_min_spin = QSpinBox()
        self.move_min_spin.setRange(1000, 20000)
        self.move_min_spin.setSuffix(" ms")
        self.move_min_spin.setValue(self.current_settings.get("move_duration_ms_min", 3000))
        behavior_layout.addRow("最小移动时长:", self.move_min_spin)
        
        self.move_max_spin = QSpinBox()
        self.move_max_spin.setRange(1000, 20000)
        self.move_max_spin.setSuffix(" ms")
        self.move_max_spin.setValue(self.current_settings.get("move_duration_ms_max", 8000))
        behavior_layout.addRow("最大移动时长:", self.move_max_spin)
        
        behavior_group.setLayout(behavior_layout)
        main_layout.addWidget(behavior_group)
        
        # 2. 窗口设置组
        window_group = QGroupBox("窗口设置")
        window_layout = QFormLayout()
        
        # 置顶开关
        self.always_on_top = QCheckBox()
        self.always_on_top.setChecked(self.current_settings.get("always_on_top", True))
        window_layout.addRow("窗口置顶:", self.always_on_top)
        
        # 桌宠尺寸
        self.pet_size_spin = QSpinBox()
        self.pet_size_spin.setRange(100, 800)
        self.pet_size_spin.setValue(self.current_settings.get("pet_size", 300))
        window_layout.addRow("桌宠尺寸 (像素):", self.pet_size_spin)
        
        window_group.setLayout(window_layout)
        main_layout.addWidget(window_group)
        
        # 3. 皮肤选择组（示例，需根据实际资源结构调整）
        skin_group = QGroupBox("皮肤设置")
        skin_layout = QFormLayout()
        
        self.skin_combo = QComboBox()
        # 模拟皮肤列表，实际需从Assets文件夹读取
        self.skin_combo.addItems(["于万千宇宙之中", "默认皮肤", "节日限定"])
        current_skin = self.current_settings.get("skin", "于万千宇宙之中")
        self.skin_combo.setCurrentText(current_skin)
        skin_layout.addRow("选择皮肤:", self.skin_combo)
        
        skin_group.setLayout(skin_layout)
        main_layout.addWidget(skin_group)
        
        # 4. 按钮组
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_settings)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    def save_settings(self):
        """保存设置并发送信号"""
        settings = {
            "speed": self.speed_slider.value(),
            "move_probability": self.move_prob_slider.value() / 100,
            "fps": self.fps_spin.value(),
            "move_duration_ms_min": self.move_min_spin.value(),
            "move_duration_ms_max": self.move_max_spin.value(),
            "always_on_top": self.always_on_top.isChecked(),
            "pet_size": self.pet_size_spin.value(),
            "skin": self.skin_combo.currentText()
        }
        self.settings_updated.emit(settings)
        self.close()
    
    def reset_settings(self):
        """恢复默认设置"""
        default_settings = {
            "speed": 2,
            "move_probability": 0.35,
            "fps": 50,
            "move_duration_ms_min": 3000,
            "move_duration_ms_max": 8000,
            "always_on_top": True,
            "pet_size": 300,
            "skin": "于万千宇宙之中"
        }
        self.speed_slider.setValue(default_settings["speed"])
        self.move_prob_slider.setValue(int(default_settings["move_probability"]*100))
        self.fps_spin.setValue(default_settings["fps"])
        self.move_min_spin.setValue(default_settings["move_duration_ms_min"])
        self.move_max_spin.setValue(default_settings["move_duration_ms_max"])
        self.always_on_top.setChecked(default_settings["always_on_top"])
        self.pet_size_spin.setValue(default_settings["pet_size"])
        self.skin_combo.setCurrentText(default_settings["skin"])

class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        # 注释API相关代码避免报错
        # self.api_client = ApiClient(
        #     api_key="YOUR_API_KEY",
        #     base_url="https://api.deepseek.com",
        #     history_file="chat_history.json"
        # )
        
        # 初始化变量
        self.input_dialog = None
        self.output_dialog = None
        self.api_worker = None
        self.output_timer = None
        self.leave_hover_timer = None
        self.is_viewing_history = False
        self.is_dragging = False
        self.input_hovered = False
        
        # 移动与位置相关参数
        self.speed = 2
        self.direction = 1
        self.screen_geometry = QApplication.desktop().availableGeometry()
        self.screen_width = self.screen_geometry.width()
        self.screen_mid = self.screen_width // 2
        self.is_moving = False
        
        # 行为参数
        self.relax_check_ms = 8000
        self.move_probability = 0.35
        self.move_duration_ms_min = 3000
        self.move_duration_ms_max = 8000

        # 行为定时器
        self.relax_timer = QTimer(self)
        self.relax_timer.setInterval(self.relax_check_ms)
        self.relax_timer.timeout.connect(self.try_start_move)
        self.relax_timer.start()

        self.move_timer = QTimer(self)
        self.move_timer.setSingleShot(True)
        self.move_timer.timeout.connect(self.stop_move)

        # 初始化 UI 和动画
        self.initUI()
        self.loadAnimations()
        self.setupAnimation()

    def initUI(self):
        # 窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 桌宠尺寸
        self.pet_width = 300
        self.pet_height = 300
        
        # 初始位置：左下角
        screen_height = self.screen_geometry.height()
        self.start_x = 20
        self.start_y = screen_height - self.pet_height - 20
        self.setGeometry(self.start_x, self.start_y, self.pet_width, self.pet_height)

        # 宠物显示标签
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, self.pet_width, self.pet_height)
        self.setCentralWidget(self.label)

        # 鼠标跟踪
        self.is_hovered = False
        self.setMouseTracking(True)

    def loadAnimations(self):
        base = os.path.dirname(os.path.abspath(__file__))
        assets_base = os.path.join(base, "Assets")
        character_name = "阿米娅"
        skin_name = "于万千宇宙之中"
        relax_pattern = os.path.join(assets_base, character_name, skin_name, "Relax", "*.png")
        move_pattern = os.path.join(assets_base, character_name, skin_name, "Move", "*.png")
        interact_pattern = os.path.join(assets_base, character_name, skin_name, "Interact", "*.png")
        sit_pattern = os.path.join(assets_base, character_name, skin_name, "Sit", "*.png")

        relax_files = sorted(glob.glob(relax_pattern))
        move_files = sorted(glob.glob(move_pattern))
        interact_files = sorted(glob.glob(interact_pattern))
        sit_files = sorted(glob.glob(sit_pattern))

        self.relax_frames = [QPixmap(p) for p in relax_files]
        self.move_frames = [QPixmap(p) for p in move_files]
        self.interact_frames = [QPixmap(p) for p in interact_files]
        self.sit_frames = [QPixmap(p) for p in sit_files]

        self.relax_frames = [px for px in self.relax_frames if not px.isNull()]
        self.move_frames = [px for px in self.move_frames if not px.isNull()]
        self.interact_frames = [px for px in self.interact_frames if not px.isNull()]
        self.sit_frames = [px for px in self.sit_frames if not px.isNull()]

    def setupAnimation(self):
        self.current_frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateAnimation)
        self.timer.start(20)  # 默认50fps（1000/50=20ms）

    def updateAnimation(self):
        if self.is_moving and not self.is_dragging and not self.is_hovered:
            self.move_horizontally()
        
        if self.is_hovered:
            frames = self.interact_frames
        else:
            if self.is_moving:
                frames = self.move_frames
            else:
                frames = self.relax_frames
        
        if frames:
            self.current_frame = (self.current_frame + 1) % len(frames)
            current_pixmap = frames[self.current_frame]
            
            if self.direction == -1:
                transform = QTransform()
                transform.scale(-1, 1)
                current_pixmap = current_pixmap.transformed(transform, Qt.SmoothTransformation)
            
            self.label.setPixmap(current_pixmap.scaled(
                self.pet_width, self.pet_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))

    def try_start_move(self):
        if self.is_moving:
            return
        if self.is_hovered or self.is_dragging:
            return
        if random.random() < self.move_probability:
            self.is_moving = True
            self.current_frame = 0
            dur = random.randint(self.move_duration_ms_min, self.move_duration_ms_max)
            self.direction = random.choice([-1, 1])
            self.move_timer.start(dur)

    def stop_move(self):
        self.is_moving = False
        self.current_frame = 0

    def move_horizontally(self):
        current_x = self.x()
        new_x = current_x + self.speed * self.direction
        
        if new_x <= 0:
            new_x = 0
            self.direction = 1
        elif new_x + self.pet_width >= self.screen_width:
            new_x = self.screen_width - self.pet_width
            self.direction = -1
        
        self.move(new_x, self.y())

    def enterEvent(self, event):
        self.is_hovered = True
        self.current_frame = 0

    def leaveEvent(self, event):
        self.is_hovered = False
        self.current_frame = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()
            self.is_dragging = False
            event.accept()
    def wheelEvent(self, event):
        """重写滚轮事件，悬停时调节桌宠大小（保持底部坐标固定）"""
        # 仅当鼠标悬停在桌宠上时响应滚轮
        if not self.is_hovered:
            return
        
        # 获取滚轮滚动方向（向上为正，向下为负）
        delta = event.angleDelta().y()
        if delta == 0:
            return
        
        # 定义每次滚轮滚动的尺寸步长
        step = 10
        # 保存旧尺寸（核心：先存旧值，用于计算位置）
        old_size = self.pet_width
        
        if delta > 0:
            # 滚轮向上，放大
            new_size = old_size + step
        else:
            # 滚轮向下，缩小
            new_size = old_size - step
        
        # 限制尺寸范围（100-800像素）
        new_size = max(100, min(new_size, 800))
        
        # 避免重复设置相同尺寸
        if new_size == old_size:
            return
        
        # ========== 核心修改：固定底部坐标 ==========
        # 1. 计算旧的底部坐标（固定不变）
        old_bottom = self.y() + old_size
        # 2. 新的y坐标 = 固定的底部坐标 - 新尺寸（保证底部不动）
        new_y = old_bottom - new_size
        # 3. 水平坐标微调（保持桌宠水平位置居中，避免左右偏移）
        new_x = self.x() - (new_size - old_size) // 2
        
        # 更新桌宠尺寸变量
        self.pet_width = new_size
        self.pet_height = new_size
        
        # 更新窗口和标签尺寸（应用新坐标）
        self.label.setGeometry(0, 0, self.pet_width, self.pet_height)
        self.setGeometry(new_x, new_y, self.pet_width, self.pet_height)
        
        # 强制重绘，确保视觉实时更新
        self.label.update()
        self.update()
        
        # 同步设置窗口的尺寸值（如果设置窗口打开）
        if hasattr(self, 'settings_window') and self.settings_window.isVisible():
            self.settings_window.pet_size_spin.setValue(new_size)
        
        # 标记事件已处理
        event.accept()
    # 新增：右键菜单事件（唤起设置窗口）
    def contextMenuEvent(self, event):
        # 先创建临时菜单（可选，也可直接唤起设置窗口）
        menu = QMenu(self)
        settings_action = menu.addAction("设置")
        quit_action = menu.addAction("退出")
        
        # 执行菜单选择
        action = menu.exec_(self.mapToGlobal(event.pos()))
        if action == settings_action:
            self.open_settings_window()
        elif action == quit_action:
            QApplication.quit()

    def open_settings_window(self):
        """打开设置窗口并绑定参数更新"""
        # 收集当前设置
        current_settings = {
            "speed": self.speed,
            "move_probability": self.move_probability,
            "fps": 1000 // self.timer.interval(),  # 从定时器反推帧率
            "move_duration_ms_min": self.move_duration_ms_min,
            "move_duration_ms_max": self.move_duration_ms_max,
            "always_on_top": self.windowFlags() & Qt.WindowStaysOnTopHint,
            "pet_size": self.pet_width,  # 宽高一致
            "skin": "于万千宇宙之中"  # 实际需从当前皮肤读取
        }
        
        # 创建设置窗口
        self.settings_window = SettingsWindow(self, current_settings)
        # 绑定设置更新信号
        self.settings_window.settings_updated.connect(self.apply_settings)
        self.settings_window.show()

    def apply_settings(self, new_settings):
        """应用新设置（同步底部固定逻辑）"""
        # 1. 移动相关参数
        self.speed = new_settings["speed"]
        self.move_probability = new_settings["move_probability"]
        self.move_duration_ms_min = new_settings["move_duration_ms_min"]
        self.move_duration_ms_max = new_settings["move_duration_ms_max"]
        
        # 2. 动画帧率
        fps = new_settings["fps"]
        self.timer.setInterval(1000 // fps)
        
        # 3. 窗口置顶
        if new_settings["always_on_top"]:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()  # 重新显示窗口使置顶设置生效
        
        # 4. 桌宠尺寸（核心：保持底部固定）
        old_size = self.pet_width  # 保存旧尺寸
        new_size = new_settings["pet_size"]  # 新尺寸
        
        # 计算固定底部的新坐标
        old_bottom = self.y() + old_size
        new_y = old_bottom - new_size
        new_x = self.x() - (new_size - old_size) // 2
        
        # 更新尺寸和位置
        self.pet_width = new_size
        self.pet_height = new_size
        self.label.setGeometry(0, 0, self.pet_width, self.pet_height)
        self.setGeometry(new_x, new_y, self.pet_width, self.pet_height)
        
        # 强制重绘
        self.label.update()
        self.update()
        
        # 5. 皮肤切换
        self.load_skin(new_settings["skin"])

    def load_skin(self, skin_name):
        """加载指定皮肤（需根据实际资源路径调整）"""
        base = os.path.dirname(os.path.abspath(__file__))
        assets_base = os.path.join(base, "Assets")
        character_name = "阿米娅"
        
        # 重新加载对应皮肤的动画帧
        relax_pattern = os.path.join(assets_base, character_name, skin_name, "Relax", "*.png")
        move_pattern = os.path.join(assets_base, character_name, skin_name, "Move", "*.png")
        interact_pattern = os.path.join(assets_base, character_name, skin_name, "Interact", "*.png")
        sit_pattern = os.path.join(assets_base, character_name, skin_name, "Sit", "*.png")

        relax_files = sorted(glob.glob(relax_pattern))
        move_files = sorted(glob.glob(move_pattern))
        interact_files = sorted(glob.glob(interact_pattern))
        sit_files = sorted(glob.glob(sit_pattern))

        self.relax_frames = [QPixmap(p) for p in relax_files if not QPixmap(p).isNull()]
        self.move_frames = [QPixmap(p) for p in move_files if not QPixmap(p).isNull()]
        self.interact_frames = [QPixmap(p) for p in interact_files if not QPixmap(p).isNull()]
        self.sit_frames = [QPixmap(p) for p in sit_files if not QPixmap(p).isNull()]

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.is_dragging = True
            self.move(self.pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()
            
            if self.input_dialog and self.input_dialog.isVisible():
                dialog_x = self.get_side_position(self.input_width)
                self.input_dialog.move(dialog_x, self.input_dialog.y())
                
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.is_dragging and self.is_hovered:
                self.showCustomDialog()
            self.is_dragging = False
            event.accept()

    def get_side_position(self, base_width):
        pet_center_x = self.geometry().x() + self.pet_width // 2
        if pet_center_x < self.screen_mid:
            return self.geometry().x() + self.pet_width + 10
        else:
            return self.geometry().x() - base_width - 10

    def get_output_y_position(self):
        return self.geometry().y() - self.output_height - 10

    def showCustomDialog(self):
        if self.input_dialog and self.input_dialog.isVisible():
            self.input_dialog.close()

        self.input_dialog = QWidget(self, Qt.Dialog | Qt.FramelessWindowHint)
        self.input_dialog.setStyleSheet("""
            background-color: rgba(255, 255, 255, 90);
            border: 2px solid rgba(0, 0, 0, 150);
            border-radius: 10px;
        """)

        screen_geometry = QApplication.desktop().screenGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        self.input_width = screen_width // 2
        self.input_height = screen_height // 2

        self.input_box = QLineEdit(self.input_dialog)
        self.input_box.setPlaceholderText("请输入内容...")
        font = QFont()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(12)
        self.input_box.setFont(font)
        self.input_box.setStyleSheet("""
            background-color: rgba(255, 255, 255, 100);
            border: 1px solid rgba(0, 0, 0, 100);
            padding: 10px;
            border-radius: 5px;
            color: #000000;
        """)
        self.input_box.returnPressed.connect(self.submitToDeepSeek)

        self.output_box = QTextEdit(self.input_dialog)
        self.output_box.setReadOnly(True)
        self.output_box.setStyleSheet("""
            background-color: rgba(255, 255, 255, 80);
            border: 1px solid rgba(0, 0, 0, 100);
            padding: 10px;
            border-radius: 5px;
            color: #000000;
        """)
        self.output_box.setPlaceholderText("等待回复...")

        send_btn = QPushButton("发送", self.input_dialog)
        send_btn.setStyleSheet("""
            background-color: rgba(0, 128, 0, 90);
            color: #FFFFFF;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
        """)
        send_btn.clicked.connect(self.submitToDeepSeek)

        close_btn = QPushButton("关闭", self.input_dialog)
        close_btn.setStyleSheet("""
            background-color: rgba(255, 0, 0, 90);
            color: #FFFFFF;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
        """)
        close_btn.clicked.connect(self.closeDialog)

        main_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_box)
        input_layout.addWidget(send_btn)
        input_layout.addWidget(close_btn)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.output_box)

        self.input_dialog.setLayout(main_layout)

        dialog_x = (screen_width - self.input_width) // 2
        dialog_y = (screen_height - self.input_height) // 2
        self.input_dialog.setGeometry(dialog_x, dialog_y, self.input_width, self.input_height)
        self.input_dialog.show()

    def closeDialog(self):
        if self.input_dialog and self.input_dialog.isVisible():
            self.input_dialog.close()
            self.input_dialog = None

    def submitToDeepSeek(self):
        """注释API相关逻辑避免报错"""
        text = self.input_box.text()
        if not text.strip():
            self.output_box.setText("请输入有效内容！")
            return
        self.output_box.setText("API功能已注释，如需使用请实现api_client模块")

    def handle_api_response(self, user_input, response):
        """注释API相关逻辑避免报错"""
        pass

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())