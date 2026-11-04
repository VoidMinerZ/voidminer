from __future__ import annotations
import os, subprocess, sys, tkinter.filedialog as fd, tkinter.messagebox as mb
import customtkinter as ctk
from .. import i18n, tasks, updater
from ..i18n import t
from ..paths import APP_VERSION, LOGS, ROOT
from . import theme
from . import widgets as W


class SettingsPage(W.Page):
    def build(self):
        s = self.app.settings
        sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        sc.pack(fill="both", expand=True, padx=18, pady=(18, 10))
        W.heading(sc, t("settings"), f"VoidMiner Client {APP_VERSION}").pack(anchor="w", padx=10, pady=(6, 8))

        def group(title):
            c = W.card(sc)
            c.pack(fill="x", padx=10, pady=8)
            W.label(c, title, 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 4))
            return c

        def row(c, text):
            r = ctk.CTkFrame(c, fg_color="transparent")
            r.pack(fill="x", padx=18, pady=4)
            W.label(r, text, 13, width=200, anchor="w").pack(side="left")
            return r

        g = group("GAME")
        r = row(g, "Default RAM (MB, 0 = by mode)")
        self.ram = W.entry(r, 100)
        self.ram.pack(side="left")
        self.ram.insert(0, str(s.get("ram_mb")))
        self.ram.bind("<FocusOut>", lambda e: self._int("ram_mb", self.ram))
        r = row(g, "Java executable")
        self.java = W.entry(r, 380, placeholder_text="Automatic (bundled Mojang runtime)")
        self.java.pack(side="left")
        if s.get("java_path"):
            self.java.insert(0, s.get("java_path"))
        self.java.bind("<FocusOut>", lambda e: s.set("java_path", self.java.get().strip()))
        W.button(r, "Browse", self._java, "ghost", 80, 34).pack(side="left", padx=8)
        r = row(g, "Extra JVM arguments")
        self.jvm = W.entry(r, 480)
        self.jvm.pack(side="left")
        self.jvm.insert(0, s.get("jvm_args"))
        self.jvm.bind("<FocusOut>", lambda e: s.set("jvm_args", self.jvm.get().strip()))
        r = row(g, "Minecraft directory")
        self.mcd = W.entry(r, 380, placeholder_text=str(ROOT / "minecraft"))
        self.mcd.pack(side="left")
        if s.get("minecraft_dir"):
            self.mcd.insert(0, s.get("minecraft_dir"))
        W.button(r, "Browse", self._mcdir, "ghost", 80, 34).pack(side="left", padx=8)
        W.label(g, "Holds shared versions, libraries, assets and Java. Existing files are never overwritten; profiles keep their own game folders. "
                   "Applies on next launch.", 11, color=theme.MUTED, wraplength=760, justify="left").pack(anchor="w", padx=18, pady=(0, 6))
        r = row(g, "Window size")
        self.w = W.entry(r, 80)
        self.w.pack(side="left")
        self.w.insert(0, str(s.get("width")))
        W.label(r, "×", 13).pack(side="left", padx=6)
        self.h = W.entry(r, 80)
        self.h.pack(side="left")
        self.h.insert(0, str(s.get("height")))
        for e, k in ((self.w, "width"), (self.h, "height")):
            e.bind("<FocusOut>", lambda ev, e=e, k=k: self._int(k, e))
        W.switch(g, "Fullscreen", lambda: s.set("fullscreen", bool(self.fs.get()))).pack(anchor="w", padx=18, pady=6)
        self.fs = g.winfo_children()[-1]
        (self.fs.select if s.get("fullscreen") else self.fs.deselect)()
        self._sw(g, "Minimize launcher while playing (saves resources)", "minimize_on_launch")
        self._sw(g, "Raise game process priority (Above Normal)", "high_priority")
        W.label(g, "", 4).pack(pady=2)

        g = group("APPEARANCE")
        r = row(g, "Language")
        W.menu(r, list(i18n.LANGS), lambda v: self._restart_set("language", v), 180).pack(side="left")
        r.winfo_children()[-1].set(s.get("language"))
        r = row(g, "Accent theme")
        W.menu(r, list(theme.ACCENTS), lambda v: self._restart_set("accent", v), 180).pack(side="left")
        r.winfo_children()[-1].set(s.get("accent"))
        self._sw(g, "Use native Windows title bar (needs restart)", "native_titlebar", restart=True)
        W.button(g, "Restart launcher", self._restart, "ghost", width=150, height=32).pack(anchor="w", padx=18, pady=(4, 16))

        g = group("LAUNCHER UPDATES")
        r = row(g, "Update info URL (JSON)")
        self.upd = W.entry(r, 440, placeholder_text='https://example.com/voidminer.json  {"version":"1.1.0","url":"..."}')
        self.upd.pack(side="left")
        if s.get("update_url"):
            self.upd.insert(0, s.get("update_url"))
        self.upd.bind("<FocusOut>", lambda e: s.set("update_url", self.upd.get().strip()))
        self._sw(g, "Check for updates on startup", "auto_update_check")
        W.button(g, "Check now", self._check, width=120, height=32).pack(anchor="w", padx=18, pady=(4, 16))

        g = group("DATA")
        bf = ctk.CTkFrame(g, fg_color="transparent")
        bf.pack(anchor="w", padx=18, pady=(0, 16))
        W.button(bf, "Open logs", lambda: self._open(LOGS), "ghost", width=110, height=32).pack(side="left")
        W.button(bf, "Open data folder", lambda: self._open(ROOT), "ghost", width=150, height=32).pack(side="left", padx=8)

    def _sw(self, parent, text, key, restart=False):
        s = self.app.settings
        sw = W.switch(parent, text, lambda: s.set(key, bool(sw.get())))
        sw.pack(anchor="w", padx=18, pady=6)
        (sw.select if s.get(key) else sw.deselect)()

    def _int(self, key, e):
        try:
            self.app.settings.set(key, max(0, int(e.get().strip() or 0)))
        except ValueError:
            e.delete(0, "end")
            e.insert(0, str(self.app.settings.get(key)))

    def _java(self):
        f = fd.askopenfilename(title="Select java.exe / javaw.exe", filetypes=[("Java", "java*.exe"), ("All", "*.*")])
        if f:
            self.java.delete(0, "end")
            self.java.insert(0, f)
            self.app.settings.set("java_path", f)

    def _mcdir(self):
        d = fd.askdirectory(title="Select Minecraft directory")
        if d:
            self.mcd.delete(0, "end")
            self.mcd.insert(0, d)
            self.app.settings.set("minecraft_dir", d)

    def _restart_set(self, k, v):
        self.app.settings.set(k, v)
        self.app.toast("Saved - restart the launcher to apply.", "info")

    def _open(self, p):
        if os.name == "nt":
            os.startfile(str(p))  # noqa
        else:
            self.app.toast(str(p))

    def _restart(self):
        try:
            cmd = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, sys.argv[0]]
            subprocess.Popen(cmd)
        finally:
            self.app.destroy()

    def _check(self):
        url = self.upd.get().strip()
        self.app.settings.set("update_url", url)

        def done(d):
            if d["newer"]:
                if mb.askyesno("Update available", f"Version {d['version']} is available.\n{d.get('notes', '')}\n\nOpen the download page?"):
                    import webbrowser
                    webbrowser.open(d["url"])
            else:
                self.app.toast("You're up to date.", "good")
        tasks.run_bg(lambda: updater.check(url), done, lambda e: mb.showerror("Update check", str(e)), "update")
