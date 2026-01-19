# Plugins/manager.py
from __future__ import annotations

import importlib
import json
import pkgutil
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Plugins.base import AppContext, PluginBase


def _save_json(path: Path, data: dict) -> None:
    """原子写入 JSON，避免写一半导致文件损坏"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load_json(path: Path, defaults: dict) -> dict:
    """读取 JSON（不存在就创建，损坏就备份并重建），并用 defaults 补齐缺失字段"""
    path.parent.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        _save_json(path, defaults)
        return dict(defaults)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config json is not an object")
        merged = dict(defaults)
        merged.update(data)
        return merged
    except Exception:
        bad = path.with_suffix(".bad.json")
        try:
            path.replace(bad)
        except Exception:
            pass
        _save_json(path, defaults)
        return dict(defaults)


class PluginManager:
    """
    扫描/加载 Plugins 目录下的所有插件包（每个插件是一个文件夹，且必须有 __init__.py）
    - 每个插件包必须提供 create_plugin() -> PluginBase
    - 每个插件可选提供：
        - config_path() -> Path
        - default_config() -> dict
        - load_config(cfg: dict) -> None
        - create_settings_widget(parent=None) -> QWidget | None
        - collect_config_from_widget() -> dict
    """

    def __init__(self, ctx: AppContext, plugins_package: str = "Plugins") -> None:
        self.ctx = ctx
        self.plugins_package = plugins_package
        self._plugins: Dict[str, PluginBase] = {}

    # ---------- discovery / load ----------

    def discover(self) -> List[str]:
        """扫描 Plugins 包目录下的子包（目录插件）"""
        pkg = importlib.import_module(self.plugins_package)
        pkg_path = Path(pkg.__file__).resolve().parent  # Plugins/
        names: List[str] = []
        for m in pkgutil.iter_modules([str(pkg_path)]):
            if m.ispkg:
                names.append(m.name)
        return sorted(names)

    def load_all(self) -> None:
        for name in self.discover():
            self.load_one(name)

    def load_one(self, name: str) -> None:
        """加载单个插件：Plugins.<name>"""
        full = f"{self.plugins_package}.{name}"
        try:
            mod = importlib.import_module(full)
            create = getattr(mod, "create_plugin", None)
            if not callable(create):
                self.ctx.logger(f"[plugins] skip {full}: no create_plugin()")
                return

            plugin: PluginBase = create()

            # ---- 读取插件配置（如果插件实现了相关方法）----
            cfg = None
            try:
                default_cfg = (
                    plugin.default_config() if hasattr(plugin, "default_config") else {}
                )
                if not isinstance(default_cfg, dict):
                    default_cfg = {}

                if hasattr(plugin, "config_path"):
                    cfg_path = plugin.config_path()
                else:
                    # fallback：插件目录/config.json
                    cfg_path = Path(mod.__file__).resolve().parent / "config.json"

                cfg = _load_json(cfg_path, default_cfg)

                if hasattr(plugin, "load_config"):
                    plugin.load_config(cfg)
                else:
                    setattr(plugin, "cfg", cfg)

            except Exception:
                self.ctx.logger(
                    f"[plugins] config load failed: {full}\n{traceback.format_exc()}"
                )

            # enabled 开关（约定：cfg["enabled"]）
            enabled = True
            if isinstance(cfg, dict):
                enabled = bool(cfg.get("enabled", True))
            setattr(plugin, "_enabled", enabled)

            # ---- 激活插件（enabled 才 activate；但无论是否 enabled 都登记，以便设置页显示）----
            if enabled:
                plugin.activate(self.ctx)
                self.ctx.logger(f"[plugins] loaded: {plugin.id} ({plugin.name})")
            else:
                self.ctx.logger(f"[plugins] disabled: {plugin.id} ({plugin.name})")

            self._plugins[plugin.id] = plugin

        except Exception:
            self.ctx.logger(f"[plugins] failed: {full}\n{traceback.format_exc()}")

    def unload_all(self) -> None:
        for p in list(self._plugins.values()):
            try:
                # 只对已激活插件执行 deactivate（按约定 _enabled=True 才激活）
                if getattr(p, "_enabled", True):
                    p.deactivate()
            except Exception:
                self.ctx.logger(
                    f"[plugins] deactivate failed: {p.id}\n{traceback.format_exc()}"
                )
        self._plugins.clear()

    # ---------- hooks ----------

    def extend_context_menu(self, menu) -> None:
        """桌宠构建右键菜单时调用，插件可扩展菜单项"""
        for p in self._plugins.values():
            if not getattr(p, "_enabled", True):
                continue
            try:
                p.extend_context_menu(menu)
            except Exception:
                self.ctx.logger(
                    f"[plugins] menu hook failed: {p.id}\n{traceback.format_exc()}"
                )

    # ---------- settings UI integration ----------

    def build_settings_panels(self, parent=None) -> List[Tuple[str, object]]:
        """
        给 Settings“插件”页用：
        返回 [(plugin_id, widget), ...]
        """
        panels: List[Tuple[str, object]] = []
        for pid, p in self._plugins.items():
            try:
                if hasattr(p, "create_settings_widget"):
                    w = p.create_settings_widget(parent)
                    if w is not None:
                        panels.append((pid, w))
            except Exception:
                self.ctx.logger(
                    f"[plugins] create_settings_widget failed: {pid}\n{traceback.format_exc()}"
                )
        return panels

    def save_all_plugin_configs(self) -> None:
        """
        点击“保存设置”时调用：
        - 从插件设置控件收集配置 dict
        - 写回插件目录下的 config.json（或插件自定义 config_path）
        - 更新插件内存中的 cfg
        注意：这里不会自动启用/停用插件（如需热启用可再扩展）。
        """
        for pid, p in self._plugins.items():
            try:
                if hasattr(p, "collect_config_from_widget"):
                    cfg = p.collect_config_from_widget()
                else:
                    cfg = getattr(p, "cfg", None)

                if not isinstance(cfg, dict):
                    continue

                # 写回路径
                if hasattr(p, "config_path"):
                    cfg_path = p.config_path()
                else:
                    # fallback：根据插件模块定位目录
                    mod = importlib.import_module(p.__class__.__module__)
                    cfg_path = Path(mod.__file__).resolve().parent / "config.json"

                _save_json(cfg_path, cfg)

                # 更新内存
                if hasattr(p, "load_config"):
                    p.load_config(cfg)
                else:
                    setattr(p, "cfg", cfg)

            except Exception:
                self.ctx.logger(
                    f"[plugins] save config failed: {pid}\n{traceback.format_exc()}"
                )

    # ---------- misc ----------

    def get_plugin(self, plugin_id: str) -> Optional[PluginBase]:
        return self._plugins.get(plugin_id)

    def all_plugins(self) -> List[PluginBase]:
        return list(self._plugins.values())
