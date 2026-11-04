from __future__ import annotations
import requests
from .paths import APP_VERSION


def _v(s): return tuple(int(x) for x in str(s).lstrip("v").split(".") if x.isdigit())


def check(url: str) -> dict:
    """Expects JSON: {"version": "1.2.0", "url": "https://...", "notes": "..."}"""
    if not url:
        raise ValueError("No update URL configured in Settings.")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    d = r.json()
    d["newer"] = _v(d["version"]) > _v(APP_VERSION)
    return d
