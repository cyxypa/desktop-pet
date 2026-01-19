# settings_model.py
from dataclasses import dataclass, asdict


@dataclass
class AppSettings:
    character: str = "阿米娅"
    skin: str = "默认"

    enable_move: bool = True
    speed: int = 2
    move_probability: int = 35  # 0~100
    move_duration_min: int = 3000  # ms
    move_duration_max: int = 8000  # ms

    fps: int = 30
    pet_size: int = 300

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "AppSettings":
        s = AppSettings()
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s
