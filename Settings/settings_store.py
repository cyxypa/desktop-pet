# settings_store.py
import json
from pathlib import Path
from PyQt5.QtCore import QStandardPaths

from settings_model import AppSettings


def get_config_path() -> Path:
    # Windows: C:\Users\xxx\AppData\Roaming\<AppName>\
    base = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"


def load_settings() -> AppSettings:
    path = get_config_path()
    if not path.exists():
        return AppSettings()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings.from_dict(data)
    except Exception:
        # 文件损坏/格式不对：回退默认（也可以改成备份后重建）
        return AppSettings()


def save_settings(s: AppSettings) -> None:
    path = get_config_path()
    tmp = path.with_suffix(".json.tmp")

    tmp.write_text(
        json.dumps(s.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    tmp.replace(path)  # 原子替换：避免半写入导致 config.json 损坏
