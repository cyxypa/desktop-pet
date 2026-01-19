# plugins/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from PyQt5.QtWidgets import QMenu
from pathlib import Path
import importlib


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

    def config_path(self) -> Path:
        """默认：插件目录/config.json"""
        mod = importlib.import_module(self.__class__.__module__)
        return Path(mod.__file__).resolve().parent / "config.json"

    def default_config(self) -> dict:
        """默认配置（用于首次生成或字段缺失时补齐）"""
        return {}

    def load_config(self, cfg: dict) -> None:
        """PluginManager 加载 json 后会调用，插件自行保存到 self.cfg"""
        self.cfg = cfg

    # --- 给 Settings “插件”页用 ---
    def create_settings_widget(self, parent=None):
        """返回一个 QWidget(通常是 QGroupBox)，用于塞进设置窗口的插件页"""
        return None

    def collect_config_from_widget(self) -> dict:
        """点击保存时调用：从控件读值，返回 dict，用于写回 config.json"""
        return getattr(self, "cfg", {}) if hasattr(self, "cfg") else {}
