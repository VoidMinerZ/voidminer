from __future__ import annotations
import json, logging
from pathlib import Path
from .paths import ROOT

log = logging.getLogger(__name__)

DEFAULTS = {
    "minecraft_dir": "", "java_path": "", "jvm_args": "", "ram_mb": 0,
    "width": 854, "height": 480, "fullscreen": False,
    "language": "English", "accent": "Electric Blue",
    "native_titlebar": False, "minimize_on_launch": True, "high_priority": True,
    "update_url": "", "auto_update_check": False, "client_id": "",
    "last_profile": "", "recent_versions": [], "default_mode": "low", "mode_detected": False,
}


class Settings:
    def __init__(self) -> None:
        self.path = ROOT / "settings.json"
        self.data = dict(DEFAULTS)
        try:
            if self.path.exists():
                self.data.update(json.loads(self.path.read_text("utf-8")))
        except Exception:
            log.exception("settings.json unreadable; using defaults")

    def get(self, key):
        return self.data.get(key, DEFAULTS.get(key))

    def set(self, key, value) -> None:
        self.data[key] = value
        self.save()

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2), "utf-8")
        tmp.replace(self.path)

    @property
    def mc_dir(self) -> Path:
        p = Path(self.get("minecraft_dir") or (ROOT / "minecraft"))
        p.mkdir(parents=True, exist_ok=True)
        return p
