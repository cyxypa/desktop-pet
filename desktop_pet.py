import glob, os, random
from PyQt5.QtWidgets import (
    QMainWindow,
    QLabel,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QTextEdit,
    QApplication,
    QPushButton,
    QHBoxLayout,
    QMenu,
)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QFont, QTransform
from api_client import ApiWorker, ApiClient  # 需确保 api_client 模块及类正确
from Settings.settings_dialog import SettingsDialog


class DesktopPet(QMainWindow):
    def __init__(self):
        super().__init__()
        # API 客户端初始化
        # self.api_client = ApiClient(
        #    api_key="YOUR_API_KEY",
        #    base_url="https://api.deepseek.com",
        #    history_file="chat_history.json"
        # )

        # 初始化变量
        self.input_dialog = None
        self.output_dialog = None
        self.api_worker = None
        self.output_timer = None  # 输出框自身的自动关闭定时器
        self.leave_hover_timer = None  # 离开桌宠后的延迟关闭定时器
        self.is_viewing_history = False
        self.is_dragging = False  # 标记是否正在拖动
        self.input_hovered = False  # 标记输入框是否被鼠标悬停
        self._settings_dialog = None

        # 移动与位置相关参数
        self.speed = 2  # 移动速度（像素/帧）
        self.direction = 1  # 1:向右，-1:向左
        self.screen_geometry = QApplication.desktop().availableGeometry()
        self.screen_width = self.screen_geometry.width()
        self.screen_mid = self.screen_width // 2  # 屏幕中线（左右分界）
        self.is_moving = False  # 移动状态标记
        # ---------- 行为参数（可按体感调）----------
        self.relax_check_ms = 8000  # Relax 状态下：每 8 秒触发一次概率判定
        self.move_probability = 0.35  # 判定为 True 的概率（35%）
        self.move_duration_ms_min = 3000  # Move 最短持续 3 秒
        self.move_duration_ms_max = 8000  # Move 最长持续 8 秒

        # ---------- 行为定时器 ----------
        # 1) Relax 判定计时器：周期性触发“是否开始 Move”
        self.relax_timer = QTimer(self)
        self.relax_timer.setInterval(self.relax_check_ms)  # 设定计时时间
        self.relax_timer.timeout.connect(self.try_start_move)  # 绑定回调函数
        self.relax_timer.start()  # 开启定时器

        # 2) Move 持续计时器：到点结束 Move 并回 Relax
        self.move_timer = QTimer(self)
        self.move_timer.setSingleShot(True)  # 是否单次触发
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

        # 初始位置：左下角（留出 20px 边距）
        screen_height = self.screen_geometry.height()
        self.start_x = 20  # 左边距
        self.start_y = screen_height - self.pet_height - 20  # 底边距
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
        character_name = "阿米娅"  # 假设资源文件夹命名为 "Pet"
        skin_name = "于万千宇宙之中"  # 假设皮肤命名为 "Default"
        relax_pattern = os.path.join(
            assets_base, character_name, skin_name, "Relax", "*.png"
        )
        move_pattern = os.path.join(
            assets_base, character_name, skin_name, "Move", "*.png"
        )
        interact_pattern = os.path.join(
            assets_base, character_name, skin_name, "Interact", "*.png"
        )
        sit_pattern = os.path.join(
            assets_base, character_name, skin_name, "Sit", "*.png"
        )

        relax_files = sorted(glob.glob(relax_pattern))
        move_files = sorted(glob.glob(move_pattern))
        interact_files = sorted(glob.glob(interact_pattern))
        sit_files = sorted(glob.glob(sit_pattern))

        self.relax_frames = [QPixmap(p) for p in relax_files]
        self.move_frames = [QPixmap(p) for p in move_files]
        self.interact_frames = [QPixmap(p) for p in interact_files]
        self.sit_frames = [QPixmap(p) for p in sit_files]

        # 过滤掉加载失败的帧（文件损坏/不是有效PNG时 QPixmap 会 isNull）
        self.relax_frames = [px for px in self.relax_frames if not px.isNull()]
        self.move_frames = [px for px in self.move_frames if not px.isNull()]
        self.interact_frames = [px for px in self.interact_frames if not px.isNull()]
        self.sit_frames = [px for px in self.sit_frames if not px.isNull()]

        # 确保关键动画帧存在
        if not self.move_frames or not self.interact_frames:
            raise FileNotFoundError(
                "请确保'Assets'文件夹中包含 PNG 图片\n"
                f"cwd={os.getcwd()}\n"
                f"base={base}\n"
                f"Move匹配={move_pattern}, 文件数={len(move_files)}\n"
                f"Interact匹配={interact_pattern}, 文件数={len(interact_files)}"
            )

    def setupAnimation(self):
        # 动画和移动定时器（每 20ms 更新一次）
        self.current_frame = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateAnimation)
        self.timer.start(20)

    def updateAnimation(self):
        # 1. 处理水平移动（仅当移动状态为 True 且不在拖动时）
        if self.is_moving and not self.is_dragging and not self.is_hovered:
            self.move_horizontally()

        # 2. 处理动画帧（根据方向翻转贴图）
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

            # 根据移动方向翻转贴图
            if self.direction == -1:
                transform = QTransform()
                transform.scale(-1, 1)  # 水平翻转
                current_pixmap = current_pixmap.transformed(
                    transform, Qt.SmoothTransformation
                )

            self.label.setPixmap(
                current_pixmap.scaled(
                    self.pet_width,
                    self.pet_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )

    def try_start_move(self):
        """
        Relax 判定计时器回调：
        到点 -> 做一次概率判定 -> 命中则进入 Move，并启动 Move 持续计时器
        """
        # 已经在 Move 就不判定
        if self.is_moving:
            return

        # 正在交互/拖拽时，不进入 Move（避免体验突兀）
        if self.is_hovered or self.is_dragging:
            return

        if random.random() < self.move_probability:
            self.is_moving = True
            self.current_frame = 0

            # Move 持续时间可以随机，显得更自然
            dur = random.randint(self.move_duration_ms_min, self.move_duration_ms_max)
            self.direction = random.choice([-1, 1])  # 随机选择移动方向
            self.move_timer.start(dur)

    def stop_move(self):
        """Move 持续到点：回到 Relax"""
        self.is_moving = False
        self.current_frame = 0

    def move_horizontally(self):
        # 计算新位置
        current_x = self.x()
        new_x = current_x + self.speed * self.direction

        # 边界检测（左右边缘）
        if new_x <= 0:  # 左边缘
            new_x = 0
            self.direction = 1  # 转向右
        elif new_x + self.pet_width >= self.screen_width:  # 右边缘
            new_x = self.screen_width - self.pet_width
            self.direction = -1  # 转向左

        # 更新窗口位置
        self.move(new_x, self.y())

    def enterEvent(self, event):
        # 鼠标悬停桌宠：停止移动，切换动画
        self.is_hovered = True
        # self.is_moving = False
        self.current_frame = 0

    def leaveEvent(self, event):
        """离开桌宠悬停：恢复移动（移除自动关闭对话框的逻辑）"""
        self.is_hovered = False
        # self.is_moving = True
        self.current_frame = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.show_context_menu(event.globalPos())
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            self.dragPos = event.globalPos()
            self.is_dragging = False
            event.accept()

    def show_context_menu(self, global_pos):
        menu = QMenu(self)
        act_settings = menu.addAction("设置")
        act_exit = menu.addAction("退出")

        chosen = menu.exec_(global_pos)
        if chosen == act_settings:
            self.open_settings()
        elif chosen == act_exit:
            QApplication.quit()

    def open_settings(self):
        # 只显示界面，不做任何槽连接
        self._settings_dialog = SettingsDialog(parent=self)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            # 标记为正在拖动
            self.is_dragging = True
            # 拖动桌宠
            self.move(self.pos() + event.globalPos() - self.dragPos)
            self.dragPos = event.globalPos()

            # 同步移动输入框
            if self.input_dialog and self.input_dialog.isVisible():
                dialog_x = self.get_side_position(self.input_width)
                self.input_dialog.move(dialog_x, self.input_dialog.y())

            event.accept()

    def mouseReleaseEvent(self, event):
        # 鼠标释放时检查是否是点击（非拖动）
        if event.button() == Qt.LeftButton:
            # 如果不是拖动状态且处于悬停状态，才显示自定义交互界面
            if not self.is_dragging and self.is_hovered:
                self.showCustomDialog()
            # 重置拖动状态
            self.is_dragging = False
            event.accept()

    def get_side_position(self, base_width):
        """计算对话框的 X 坐标位置（左右侧自动切换）"""
        pet_center_x = self.geometry().x() + self.pet_width // 2  # 桌宠中心点 X 坐标

        if pet_center_x < self.screen_mid:
            # 左半边：对话框在桌宠右侧
            return self.geometry().x() + self.pet_width + 10  # 右侧 +10px 间距
        else:
            # 右半边：对话框在桌宠左侧
            return self.geometry().x() - base_width - 10  # 左侧 - 宽度 -10px 间距

    def get_output_y_position(self):
        """计算输出框 Y 坐标（桌宠头顶位置）"""
        return self.geometry().y() - self.output_height - 10  # 桌宠顶部向上 10px

    def showCustomDialog(self):
        """显示自定义交互界面，包含输入框、输出框和关闭按钮"""
        if self.input_dialog and self.input_dialog.isVisible():
            self.input_dialog.close()

        self.input_dialog = QWidget(self, Qt.Dialog | Qt.FramelessWindowHint)
        self.input_dialog.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 90);  /* 半透明白色背景 */
            border: 2px solid rgba(0, 0, 0, 150);       /* 黑色边框 */
            border-radius: 10px;                        /* 圆角 */
        """
        )

        # 获取屏幕大小
        screen_geometry = QApplication.desktop().screenGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # 设置输入框和输出框大小占屏幕的一半
        self.input_width = screen_width // 2
        self.input_height = screen_height // 2

        # 输入框
        self.input_box = QLineEdit(self.input_dialog)
        self.input_box.setPlaceholderText("请输入内容...")
        font = QFont()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(12)
        self.input_box.setFont(font)
        self.input_box.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 100); /* 半透明白色背景 */
            border: 1px solid rgba(0, 0, 0, 100);       /* 黑色边框 */
            padding: 10px;                              /* 内边距 */
            border-radius: 5px;                         /* 圆角 */
            color: #000000;                             /* 黑色字体 */
        """
        )
        self.input_box.returnPressed.connect(self.submitToDeepSeek)

        # 输出框
        self.output_box = QTextEdit(self.input_dialog)
        self.output_box.setReadOnly(True)
        self.output_box.setStyleSheet(
            """
            background-color: rgba(255, 255, 255, 80); /* 半透明白色背景 */
            border: 1px solid rgba(0, 0, 0, 100);       /* 黑色边框 */
            padding: 10px;                              /* 内边距 */
            border-radius: 5px;                         /* 圆角 */
            color: #000000;                             /* 黑色字体 */
        """
        )
        self.output_box.setPlaceholderText("等待回复...")

        # 发送按钮
        send_btn = QPushButton("发送", self.input_dialog)
        send_btn.setStyleSheet(
            """
            background-color: rgba(0, 128, 0, 90);      /* 半透明绿色背景 */
            color: #FFFFFF;                             /* 白色字体 */
            border: none;                               /* 无边框 */
            padding: 8px 16px;                          /* 内边距 */
            border-radius: 5px;                         /* 圆角 */
        """
        )
        send_btn.clicked.connect(self.submitToDeepSeek)

        # 关闭按钮
        close_btn = QPushButton("关闭", self.input_dialog)
        close_btn.setStyleSheet(
            """
            background-color: rgba(255, 0, 0, 90);      /* 半透明红色背景 */
            color: #FFFFFF;                             /* 白色字体 */
            border: none;                               /* 无边框 */
            padding: 8px 16px;                          /* 内边距 */
            border-radius: 5px;                         /* 圆角 */
        """
        )
        close_btn.clicked.connect(self.closeDialog)

        # 布局
        main_layout = QVBoxLayout()
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_box)
        input_layout.addWidget(send_btn)
        input_layout.addWidget(close_btn)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.output_box)

        self.input_dialog.setLayout(main_layout)

        # 调整输入框和输出框的位置和大小（居中显示）
        dialog_x = (screen_width - self.input_width) // 2
        dialog_y = (screen_height - self.input_height) // 2
        self.input_dialog.setGeometry(
            dialog_x, dialog_y, self.input_width, self.input_height
        )
        self.input_dialog.show()

    def closeDialog(self):
        """关闭输入框和输出框"""
        if self.input_dialog and self.input_dialog.isVisible():
            self.input_dialog.close()
            self.input_dialog = None  # 清理引用

    def submitToDeepSeek(self):
        """处理输入框内容并发送到 API"""
        text = self.input_box.text()
        if not text.strip():
            self.output_box.setText("请输入有效内容！")
            return

        self.output_box.setText("正在处理，请稍候...")

        if text.strip() == "查看历史":
            self.is_viewing_history = True
            history_text = self.api_client.get_history_text()
            self.output_box.setHtml(history_text)
            return

        self.is_viewing_history = False
        self.api_worker = ApiWorker(
            self.api_client.client, text, self.api_client.history_file
        )
        self.api_worker.result_ready.connect(
            lambda response: self.handle_api_response(text, response)
        )
        self.api_worker.start()

    def handle_api_response(self, user_input, response):
        """处理 API 响应并更新输出框内容"""
        self.api_client.save_to_history(user_input, response)
        self.output_box.setText(response)
        self.api_worker = None


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    pet = DesktopPet()
    pet.show()
    sys.exit(app.exec_())
