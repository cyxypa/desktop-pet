from __future__ import annotations
from dataclasses import dataclass

from PyQt5.QtCore import Qt, QTimer, QPoint, QRect, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPainterPath, QColor, QFontMetrics, QPolygonF
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QGuiApplication


@dataclass
class BubbleTiming:
    base_ms: int = 800
    per_char_ms: int = 55
    min_ms: int = 1200
    max_ms: int = 9000


class SpeechBubble(QWidget):
    def __init__(
        self,
        *,
        max_text_width: int = 260,
        padding: int = 10,
        radius: int = 12,
        tail: int = 10,
        timing: BubbleTiming = BubbleTiming(),
        gap_to_anchor: int = 0,  # ✅ 气泡尾巴尖尖距离桌宠的“竖直间隙”，越小越贴近
        corner_offset: int = 10,  # ✅ 尾巴距气泡左右边缘的偏移（越小越靠角落）
    ):
        super().__init__(None)

        self._max_text_width = max_text_width
        self._padding = padding
        self._radius = radius
        self._tail = tail
        self._timing = timing
        self._gap_to_anchor = gap_to_anchor
        self._corner_offset = corner_offset

        # ✅ 尾巴模式：'bottom_left' or 'bottom_right'
        self._tail_mode = "bottom_left"

        self._bg = QColor(255, 255, 255, 235)
        self._border = QColor(30, 30, 30, 80)
        self._text = QColor(20, 20, 20)

        self.setWindowFlags(
            Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setStyleSheet(
            f"QLabel{{color: rgba({self._text.red()},{self._text.green()},{self._text.blue()},255);}}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(padding, padding, padding, padding + tail)
        lay.addWidget(self.label)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)

    def show_text(
        self, text: str, anchor_rect_global: QRect, close_after: int = 5
    ) -> None:
        self.label.setText(text)
        self._recompute_size()
        self._place(anchor_rect_global)

        # close_after 单位：秒（默认 5s）
        ms = int(close_after) * 1000
        if ms <= 0:
            ms = self._duration_ms(text)  # 可选：<=0 时回退“按文本长度”
        self._timer.start(ms)

        self.show()
        self.raise_()

    def _duration_ms(self, text: str) -> int:
        n = len(text.strip())
        ms = self._timing.base_ms + n * self._timing.per_char_ms
        return max(self._timing.min_ms, min(ms, self._timing.max_ms))

    def _recompute_size(self) -> None:
        # ✅ 这里必须用 QRect（QFontMetrics.boundingRect 不收 QRectF）
        fm = QFontMetrics(self.label.font())
        rect = fm.boundingRect(
            QRect(0, 0, self._max_text_width, 10000), Qt.TextWordWrap, self.label.text()
        )
        w = rect.width() + self._padding * 2 + 6
        h = rect.height() + self._padding * 2 + self._tail + 4
        self.setFixedSize(w, h)

    def _available_geo(self, p: QPoint) -> QRect:
        screen = QGuiApplication.screenAt(p) or QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

    def _place(self, anchor: QRect) -> None:
        """
        ✅ 右上角 / 左上角布局：
        - 若右侧空间足够：气泡“贴右上角”，尾巴在气泡左下角
        - 否则贴左上角，尾巴在气泡右下角
        """
        bubble_w = self.width()
        bubble_h = self.height()

        geo = self._available_geo(anchor.center())

        # 计算左右可用空间（以桌宠上边为基准）
        space_right = geo.right() - anchor.right()
        space_left = anchor.left() - geo.left()

        # 优先选择“放得下”的一侧；都放不下就选空间更大的一侧
        place_right = (space_right >= bubble_w) or (space_right >= space_left)

        if place_right:
            # ✅ 气泡在桌宠右上角外侧一点：尾巴在气泡左下角，尖尖指向桌宠右上角
            self._tail_mode = "bottom_left"
            target = anchor.topRight()  # 指向桌宠右上角

            tip_x = self._corner_offset + self._tail  # 尾巴尖尖 x（相对气泡）
            x = target.x() - tip_x
        else:
            # ✅ 气泡在桌宠左上角外侧一点：尾巴在气泡右下角，尖尖指向桌宠左上角
            self._tail_mode = "bottom_right"
            target = anchor.topLeft()

            tip_x = bubble_w - (self._corner_offset + self._tail)
            x = target.x() - tip_x

        # ✅ 竖直位置：让尾巴尖尖“贴着”桌宠顶部（gap_to_anchor 控制距离）
        y = target.y() - self._gap_to_anchor - bubble_h

        # 防止出屏幕（只夹住气泡窗口本体）
        x = max(geo.left(), min(x, geo.right() - bubble_w))
        y = max(geo.top(), min(y, geo.bottom() - bubble_h))

        self.move(int(x), int(y))

    def paintEvent(self, _):
        w = float(self.width())
        h = float(self.height())
        tail = float(self._tail)
        radius = float(self._radius)

        bubble_rect = QRectF(0.0, 0.0, w, h - tail)
        path = QPainterPath()
        path.addRoundedRect(bubble_rect, radius, radius)

        # ✅ 尾巴位置：右上角→尾巴左下；左上角→尾巴右下
        if self._tail_mode == "bottom_left":
            base_left = float(self._corner_offset)
            base_right = float(self._corner_offset) + 2.0 * tail
            tip_x = float(self._corner_offset) + tail
        else:  # bottom_right
            base_right = w - float(self._corner_offset)
            base_left = w - float(self._corner_offset) - 2.0 * tail
            tip_x = w - float(self._corner_offset) - tail

        tri = QPolygonF(
            [
                QPointF(base_left, h - tail),
                QPointF(base_right, h - tail),
                QPointF(tip_x, h),
            ]
        )
        path.addPolygon(tri)

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillPath(path, self._bg)
        p.setPen(self._border)
        p.drawPath(path)
        p.end()
