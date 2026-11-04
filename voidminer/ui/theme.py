from __future__ import annotations
import customtkinter as ctk

BG, SIDEBAR, CARD, CARD2, BORDER = "#06070D", "#0A0F1E", "#0F1730", "#16224A", "#1E2A55"
TEXT, MUTED, GOOD, WARN, BAD = "#EAF0FF", "#8190B8", "#3DDC97", "#FFB84D", "#FF5C7A"
ACCENTS = {"Electric Blue": ("#2F80FF", "#8B5CF6"), "Violet": ("#8B5CF6", "#2F80FF"), "Cyan": ("#22D3EE", "#6366F1")}
ACCENT, ACCENT2 = ACCENTS["Electric Blue"]
_fonts: dict = {}


def apply_accent(name: str) -> None:
    global ACCENT, ACCENT2
    ACCENT, ACCENT2 = ACCENTS.get(name, ACCENTS["Electric Blue"])


def darken(h: str, f: float = 0.78) -> str:
    r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))


def font(size: int = 13, weight: str = "normal"):
    key = (size, weight)
    if key not in _fonts:
        _fonts[key] = ctk.CTkFont(family="Segoe UI", size=size, weight=weight)
    return _fonts[key]
