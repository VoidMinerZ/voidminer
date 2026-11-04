from __future__ import annotations
import customtkinter as ctk
from . import theme


def card(master, **kw):
    kw.setdefault("fg_color", theme.CARD)
    return ctk.CTkFrame(master, corner_radius=16, border_width=1, border_color=theme.BORDER, **kw)


def label(master, text="", size=13, weight="normal", color=None, **kw):
    return ctk.CTkLabel(master, text=text, font=theme.font(size, weight), text_color=color or theme.TEXT, **kw)


def button(master, text, command=None, kind="primary", width=120, height=36, size=13, **kw):
    fg, hv, tc = {"primary": (theme.ACCENT, theme.darken(theme.ACCENT), "#FFFFFF"),
                  "ghost": (theme.CARD2, theme.BORDER, theme.TEXT),
                  "danger": ("#3A1220", "#5A1A30", theme.BAD),
                  "purple": (theme.ACCENT2, theme.darken(theme.ACCENT2), "#FFFFFF")}[kind]
    return ctk.CTkButton(master, text=text, command=command, width=width, height=height, corner_radius=10,
                         fg_color=fg, hover_color=hv, text_color=tc, font=theme.font(size, "bold"), **kw)


def entry(master, width=220, **kw):
    return ctk.CTkEntry(master, width=width, height=34, corner_radius=10, fg_color=theme.BG,
                        border_color=theme.BORDER, text_color=theme.TEXT, font=theme.font(13), **kw)


def menu(master, values, command=None, width=180, **kw):
    return ctk.CTkOptionMenu(master, values=list(values) or [" "], command=command, width=width, height=34,
                             corner_radius=10, fg_color=theme.CARD2, button_color=theme.BORDER,
                             button_hover_color=theme.ACCENT, dropdown_fg_color=theme.CARD2,
                             dropdown_hover_color=theme.ACCENT, text_color=theme.TEXT,
                             font=theme.font(13), dropdown_font=theme.font(13), **kw)


def switch(master, text, command=None, **kw):
    return ctk.CTkSwitch(master, text=text, command=command, progress_color=theme.ACCENT, font=theme.font(13),
                         text_color=theme.TEXT, **kw)


def slider(master, lo, hi, steps, command=None, width=260):
    return ctk.CTkSlider(master, from_=lo, to=hi, number_of_steps=steps, command=command, width=width,
                         progress_color=theme.ACCENT, button_color=theme.ACCENT, button_hover_color=theme.ACCENT2)


def heading(master, title, sub=""):
    f = ctk.CTkFrame(master, fg_color="transparent")
    label(f, title, 26, "bold").pack(anchor="w")
    if sub:
        label(f, sub, 13, color=theme.MUTED).pack(anchor="w")
    return f


def clear(frame) -> None:
    for w in frame.winfo_children():
        w.destroy()


class Page(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent", corner_radius=0)
        self.app = app
        self.build()

    def build(self): ...
    def on_show(self): ...


class Modal(ctk.CTkToplevel):
    def __init__(self, app, title, w=520, h=480):
        super().__init__(app, fg_color=theme.BG)
        self.title(title)
        self.resizable(False, False)
        x = app.winfo_rootx() + max(0, (app.winfo_width() - w) // 2)
        y = app.winfo_rooty() + max(0, (app.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.transient(app)
        self.after(150, self._grab)

    def _grab(self):
        try:
            self.grab_set()
            self.focus_set()
        except Exception:
            pass
