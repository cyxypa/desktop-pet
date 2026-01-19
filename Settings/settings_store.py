# Settings/settings_store.py
import json
from pathlib import Path
from Settings.settings_model import AppSettings


def get_config_path() -> Path:
    return Path(__file__).resolve().parent / "config.json"


def load_settings() -> AppSettings:
    path = get_config_path()
    if not path.exists():
        s = AppSettings()
        save_settings(s)  # 关键：落盘创建 config.json
        return s

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings.from_dict(data)
    except Exception:
        # ✅ 解析失败：备份坏文件并重建
        bad = path.with_suffix(".bad.json")
        try:
            path.replace(bad)
        except Exception:
            pass
        s = AppSettings()
        save_settings(s)
        return s


def save_settings(s: AppSettings) -> None:
    path = get_config_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(s.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)
