# plugins/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from PyQt5.QtWidgets import QMenu


@dataclass
class AppContext:
    """给插件用的上下文：只暴露必要对象，避免耦合。"""

    pet: Any  # 你的 DesktopPet 实例（QMainWindow）
    services: Dict[str, Any] = field(default_factory=dict)
    logger: Any = print  # 简单日志接口


class PluginBase:
    """所有插件需继承的基类"""

    id: str = "base"
    name: str = "Base Plugin"
    version: str = "0.0.0"

    def __init__(self) -> None:
        self.ctx: Optional[AppContext] = None

    def activate(self, ctx: AppContext) -> None:
        """加载插件时调用"""
        self.ctx = ctx

    def deactivate(self) -> None:
        """卸载插件时调用"""
        self.ctx = None

    def extend_context_menu(self, menu: QMenu) -> None:
        """桌宠右键菜单构建时调用，插件可往里加 action"""
        return
