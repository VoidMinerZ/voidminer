from __future__ import annotations
import logging, os, sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "VoidMiner"
APP_VERSION = "1.0.0"


def _root() -> Path:
    base = os.environ.get("APPDATA") or os.path.join(Path.home(), ".local", "share")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


ROOT = _root()
LOGS = ROOT / "logs"
CACHE = ROOT / "cache"
INSTANCES = ROOT / "instances"
for _d in (LOGS, CACHE, INSTANCES):
    _d.mkdir(parents=True, exist_ok=True)


def resource(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / rel


def setup_logging() -> None:
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return
    root.setLevel(logging.INFO)
    fh = RotatingFileHandler(LOGS / "launcher.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(fh)
