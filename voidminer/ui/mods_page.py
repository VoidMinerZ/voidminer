from __future__ import annotations
import os, tkinter.messagebox as mb
import customtkinter as ctk
from .. import mods, tasks
from ..i18n import t
from . import theme
from . import widgets as W


class VersionDialog(W.Modal):
    def __init__(self, app, hit, p, on_done):
        super().__init__(app, f"Versions - {hit['title']}", 520, 260)
        self.app, self.hit, self.p, self.on_done, self.vs = app, hit, p, on_done, []
        W.label(self, hit["title"], 16, "bold").pack(anchor="w", padx=24, pady=(20, 4))
        self.info = W.label(self, "Loading versions...", 12, color=theme.MUTED)
        self.info.pack(anchor="w", padx=24)
        self.m = W.menu(self, [" "], width=440)
        self.m.pack(anchor="w", padx=24, pady=10)
        self.btn = W.button(self, "Install this version", self._go, width=180)
        self.btn.pack(anchor="w", padx=24, pady=8)
        self.btn.configure(state="disabled")
        tasks.run_bg(lambda: mods.project_versions(hit["project_id"], p.mc_version, p.loader), self._loaded,
                     lambda e: self.info.configure(text=f"Failed: {e}"), "modvers")

    def _loaded(self, vs):
        self.vs = vs
        if not vs:
            self.info.configure(text="No compatible versions for this profile.")
            return
        labels = [f"{v['version_number']}  ({v['version_type']})  -  MC {', '.join(v['game_versions'][-2:])}" for v in vs]
        self.labels = labels
        self.m.configure(values=labels)
        self.m.set(labels[0])
        self.info.configure(text=f"{len(vs)} compatible version(s) for {self.p.mc_version} / {self.p.loader}")
        self.btn.configure(state="normal")

    def _go(self):
        v = self.vs[self.labels.index(self.m.get())]
        self.destroy()
        self.on_done(self.hit, v)


class ModsPage(W.Page):
    def build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        W.heading(self, t("mods"), "Installed from Modrinth with checksum verification.").grid(row=0, column=0, sticky="w", padx=28, pady=(24, 6))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=28, pady=4)
        self.info = W.label(bar, "", 12, color=theme.MUTED)
        self.info.pack(side="left")
        self.seg = ctk.CTkSegmentedButton(bar, values=["Installed", "Browse"], command=self._tab, selected_color=theme.ACCENT,
                                          unselected_color=theme.CARD2, font=theme.font(13, "bold"))
        self.seg.pack(side="right")
        self.seg.set("Installed")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(4, 14))
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(1, weight=1)
        self.warn = W.label(self.body, "", 12, color=theme.WARN, wraplength=800, justify="left")
        self.inst = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self.browse = ctk.CTkFrame(self.body, fg_color="transparent")
        sr = ctk.CTkFrame(self.browse, fg_color="transparent")
        sr.pack(fill="x", padx=10, pady=4)
        self.q = W.entry(sr, 420, placeholder_text="Search mods compatible with this profile...")
        self.q.pack(side="left")
        self.q.bind("<Return>", lambda e: self._search())
        W.button(sr, "Search", self._search, width=100).pack(side="left", padx=8)
        self.res = ctk.CTkScrollableFrame(self.browse, fg_color="transparent", height=480)
        self.res.pack(fill="both", expand=True)

    def _p(self):
        return self.app.current_profile()

    def on_show(self):
        p = self._p()
        if not p:
            self.info.configure(text="Create a profile first.")
            return
        self.info.configure(text=f"{p.name}  ·  {p.mc_version}  ·  {p.loader}")
        self._tab(self.seg.get())

    def _tab(self, which):
        p = self._p()
        for w in (self.warn, self.inst, self.browse):
            w.grid_forget()
        if not p:
            return
        if p.loader == "vanilla":
            self.warn.configure(text="This is a Vanilla profile. Edit it (Profiles page) and choose Fabric, Quilt, Forge or NeoForge to install mods.", text_color=theme.WARN)
            self.warn.grid(row=0, column=0, sticky="w", padx=14, pady=20)
            return
        if which == "Installed":
            self.warn.grid(row=0, column=0, sticky="w", padx=14, pady=4)
            self.inst.grid(row=1, column=0, sticky="nsew")
            self._list()
        else:
            self.browse.grid(row=0, column=0, rowspan=2, sticky="nsew")
            if not self.res.winfo_children():
                self._search()

    def _list(self):
        p = self._p()
        W.clear(self.inst)
        items = mods.list_installed(p.dir)
        cf = mods.conflicts(items)
        self.warn.configure(text=("⚠ " + "\n⚠ ".join(cf)) if cf else (f"{len(items)} mod(s) installed - no conflicts detected." if items else ""),
                            text_color=theme.WARN if cf else theme.MUTED)
        if not items:
            W.label(self.inst, "No mods yet. Use Browse, or Optimize → Install performance mods.", 13, color=theme.MUTED).pack(pady=30)
        for it in items:
            c = W.card(self.inst)
            c.pack(fill="x", padx=8, pady=4)
            sw = W.switch(c, "", lambda it=it: self._toggle(it))
            sw.pack(side="left", padx=(16, 4), pady=14)
            (sw.select if it["enabled"] else sw.deselect)()
            sw.configure(width=46)
            col = ctk.CTkFrame(c, fg_color="transparent")
            col.pack(side="left", pady=8)
            W.label(col, it["title"], 14, "bold").pack(anchor="w")
            W.label(col, f"{it['version']}" + ("" if it["managed"] else "  (not installed by VoidMiner)"), 11, color=theme.MUTED).pack(anchor="w")
            W.button(c, "Remove", lambda it=it: self._remove(it), "danger", width=84, height=30, size=12).pack(side="right", padx=14)

    def _toggle(self, it):
        try:
            mods.set_enabled(self._p().dir, it, not it["enabled"])
        except Exception as e:  # noqa
            mb.showerror("VoidMiner", f"Could not change mod state:\n{e}")
        self._list()

    def _remove(self, it):
        if self.app.game:
            self.app.toast("Close the game before removing mods.", "warn")
            return
        if mb.askyesno("Remove mod", f"Delete {it['title']}?"):
            mods.remove(self._p().dir, it)
            self._list()

    def _search(self):
        p = self._p()
        W.clear(self.res)
        W.label(self.res, "Searching Modrinth...", 13, color=theme.MUTED).pack(pady=20)
        q = self.q.get().strip()
        tasks.run_bg(lambda: mods.search(q, p.mc_version, p.loader), self._results,
                     lambda e: (W.clear(self.res), W.label(self.res, f"Search failed: {e}", 13, color=theme.BAD).pack(pady=20)), "modsearch")

    def _results(self, hits):
        W.clear(self.res)
        if not hits:
            W.label(self.res, "No compatible mods found for this version/loader.", 13, color=theme.MUTED).pack(pady=20)
        for h in hits:
            c = W.card(self.res)
            c.pack(fill="x", padx=8, pady=4)
            col = ctk.CTkFrame(c, fg_color="transparent")
            col.pack(side="left", padx=16, pady=10, fill="x", expand=True)
            W.label(col, h["title"], 14, "bold").pack(anchor="w")
            W.label(col, f"by {h.get('author', '?')}  ·  {h.get('downloads', 0):,} downloads", 11, color=theme.MUTED).pack(anchor="w")
            W.label(col, (h.get("description") or "")[:120], 12, wraplength=520, justify="left").pack(anchor="w")
            bf = ctk.CTkFrame(c, fg_color="transparent")
            bf.pack(side="right", padx=12)
            W.button(bf, "Install", lambda h=h: self._install(h, None), width=84, height=30, size=12).pack(pady=2)
            W.button(bf, "Versions", lambda h=h: VersionDialog(self.app, h, self._p(), self._install), "ghost", width=84, height=30, size=12).pack(pady=2)

    def _install(self, hit, ver):
        p, a = self._p(), self.app
        if a.game:
            a.toast("Close the game before installing mods.", "warn")
            return

        def work():
            return mods.install(p.dir, p.mc_version, p.loader, hit["project_id"], ver,
                                lambda s: tasks.ui(a.set_progress, s, None))

        def done(res):
            a.hide_progress()
            inst, warns = res
            a.toast("Installed: " + ", ".join(inst), "good")
            if warns:
                mb.showwarning("Mod warnings", "\n".join(warns))
            self._list()
        tasks.run_bg(work, done, lambda e: (a.hide_progress(), mb.showerror("VoidMiner", f"Install failed:\n{e}")), "modinstall")
        a.set_progress(f"Installing {hit['title']}...", None)
