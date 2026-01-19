# 调用方式（其它插件/主程序）
#   say(text: str, close_after: int = 5)  # close_after 单位：秒，默认 5 秒自动关闭
#
# 使用示例：
# say = ctx.services.get("speech_bubble.say")  # 推荐（带命名空间）
# # 或：say = ctx.services.get("say")          # 兼容别名
# if callable(say):
#     say("你好，我在说话~", 5)


# plugins/speech_bubble/__init__.py
from __future__ import annotations
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtWidgets import QAction

from Plugins.base import PluginBase, AppContext
from .bubble import SpeechBubble


class SpeechBubblePlugin(PluginBase):
    id = "speech_bubble"
    name = "Speech Bubble"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        self._bubble = SpeechBubble()

    def activate(self, ctx: AppContext) -> None:
        super().activate(ctx)

        # ✅ 对外只暴露这一条函数：say(text, close_after=5)
        def say(text: str, close_after: int = 5) -> None:
            pet = ctx.pet

            # 推荐：用可见区域当锚点（你之前已经加过 get_visible_rect_global 的话）
            if hasattr(pet, "get_visible_rect_global"):
                rect = pet.get_visible_rect_global()
            else:
                top_left = pet.mapToGlobal(QPoint(0, 0))
                rect = QRect(top_left, pet.size())

            self._bubble.show_text(text, rect, close_after=close_after)

        # 你想怎么叫都行：这里给个通用名 + 一个带命名空间的别名
        ctx.services["say"] = say
        ctx.services["speech_bubble.say"] = say

    def extend_context_menu(self, menu):
        # 右键菜单里加一个“说一句话”的示例
        act = QAction("说一句话", menu)
        act.triggered.connect(lambda: self.ctx.services["say"]("咕咕嘎嘎", 5))
        menu.addAction(act)


def create_plugin():
    return SpeechBubblePlugin()
