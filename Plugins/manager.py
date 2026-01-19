# plugins/manager.py
from __future__ import annotations
import importlib
import pkgutil
import traceback
from pathlib import Path
from typing import Dict, List, Optional

from Plugins.base import AppContext, PluginBase


class PluginManager:
    def __init__(self, ctx: AppContext, plugins_package: str = "plugins") -> None:
        self.ctx = ctx
        self.plugins_package = plugins_package
        self._plugins: Dict[str, PluginBase] = {}

    def discover(self) -> List[str]:
        """扫描 plugins/ 下所有“包插件”（目录且包含 __init__.py）"""
        pkg = importlib.import_module(self.plugins_package)
        pkg_path = Path(pkg.__file__).resolve().parent  # plugins/
        names: List[str] = []
        for m in pkgutil.iter_modules([str(pkg_path)]):
            # 只收集子包（目录插件），排除 base/manager 等文件模块
            if m.ispkg:
                names.append(m.name)
        return sorted(names)

    def load_all(self) -> None:
        for name in self.discover():
            self.load_one(name)

    def load_one(self, name: str) -> None:
        """加载单个插件：plugins.<name> 必须提供 create_plugin()"""
        full = f"{self.plugins_package}.{name}"
        try:
            mod = importlib.import_module(full)
            create = getattr(mod, "create_plugin", None)
            if not callable(create):
                self.ctx.logger(f"[plugins] skip {full}: no create_plugin()")
                return

            plugin: PluginBase = create()
            plugin.activate(self.ctx)
            self._plugins[plugin.id] = plugin
            self.ctx.logger(f"[plugins] loaded: {plugin.id} ({plugin.name})")

        except Exception:
            self.ctx.logger(f"[plugins] failed: {full}\n{traceback.format_exc()}")

    def unload_all(self) -> None:
        for p in list(self._plugins.values()):
            try:
                p.deactivate()
            except Exception:
                self.ctx.logger(
                    f"[plugins] deactivate failed: {p.id}\n{traceback.format_exc()}"
                )
        self._plugins.clear()

    def extend_context_menu(self, menu) -> None:
        for p in self._plugins.values():
            try:
                p.extend_context_menu(menu)
            except Exception:
                self.ctx.logger(
                    f"[plugins] menu hook failed: {p.id}\n{traceback.format_exc()}"
                )
