from __future__ import annotations
import os, time, tkinter.filedialog as fd, tkinter.messagebox as mb
import customtkinter as ctk
from .. import optimizer, tasks, versions
from ..i18n import t
from ..profiles import LOADERS
from . import theme
from . import widgets as W


class ProfileDialog(W.Modal):
    def __init__(self, app, profile=None, on_done=None):
        super().__init__(app, "Edit profile" if profile else "New profile", 560, 600)
        self.app, self.p, self.on_done, self.supported = app, profile, on_done, None
        pad = dict(padx=24, anchor="w")
        W.label(self, "Name", 12, "bold", theme.MUTED).pack(pady=(18, 2), **pad)
        self.name = W.entry(self, 300)
        self.name.pack(**pad)
        self.name.insert(0, profile.name if profile else "My profile")
        W.label(self, "Mod loader", 12, "bold", theme.MUTED).pack(pady=(12, 2), **pad)
        self.loader = W.menu(self, LOADERS, lambda _: self._check(), width=200)
        self.loader.pack(**pad)
        self.loader.set(profile.loader if profile else "vanilla")
        W.label(self, "Minecraft version (from Mojang's official manifest)", 12, "bold", theme.MUTED).pack(pady=(12, 2), **pad)
        fr = ctk.CTkFrame(self, fg_color="transparent")
        fr.pack(**pad)
        self.v_rel, self.v_snap, self.v_old = ctk.BooleanVar(value=True), ctk.BooleanVar(), ctk.BooleanVar()
        for txt, var in (("Releases", self.v_rel), ("Snapshots", self.v_snap), ("Old versions", self.v_old)):
            ctk.CTkCheckBox(fr, text=txt, variable=var, command=self._refill, font=theme.font(12),
                            fg_color=theme.ACCENT, width=20).pack(side="left", padx=(0, 12))
        self.ver = ctk.CTkComboBox(self, width=300, height=34, corner_radius=10, fg_color=theme.BG,
                                   border_color=theme.BORDER, button_color=theme.BORDER, dropdown_fg_color=theme.CARD2,
                                   font=theme.font(13), command=lambda _: self._check())
        self.ver.pack(pady=(6, 0), **pad)
        self.sup_lbl = W.label(self, "", 12, color=theme.MUTED)
        self.sup_lbl.pack(pady=(4, 0), **pad)
        W.label(self, "RAM", 12, "bold", theme.MUTED).pack(pady=(12, 2), **pad)
        total = int((app.hw or {}).get("ram_gb", 8) * 1024 * 0.6)
        self.ram_opts = ["Auto (by mode)"] + [f"{m} MB" for m in range(1024, max(1280, total) + 1, 512)]
        self.ram = W.menu(self, self.ram_opts, width=200)
        self.ram.pack(**pad)
        cur = f"{profile.ram_mb} MB" if profile and profile.ram_mb else self.ram_opts[0]
        self.ram.set(cur if cur in self.ram_opts else self.ram_opts[0])
        W.label(self, "Custom Java executable (optional)", 12, "bold", theme.MUTED).pack(pady=(12, 2), **pad)
        jr = ctk.CTkFrame(self, fg_color="transparent")
        jr.pack(**pad)
        self.java = W.entry(jr, 360)
        self.java.pack(side="left")
        self.java.insert(0, profile.java_path if profile else "")
        W.button(jr, "Browse", self._browse, "ghost", 80, 34).pack(side="left", padx=8)
        W.label(self, "Extra JVM arguments (optional)", 12, "bold", theme.MUTED).pack(pady=(12, 2), **pad)
        self.jvm = W.entry(self, 470)
        self.jvm.pack(**pad)
        self.jvm.insert(0, profile.jvm_args if profile else "")
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(side="bottom", pady=16)
        W.button(bar, "Save", self._save, width=140).pack(side="left", padx=6)
        W.button(bar, "Cancel", self.destroy, "ghost", width=100).pack(side="left", padx=6)
        self._refill(initial=True)

    def _browse(self):
        f = fd.askopenfilename(parent=self, title="Select java.exe / javaw.exe", filetypes=[("Java", "java*.exe"), ("All", "*.*")])
        if f:
            self.java.delete(0, "end")
            self.java.insert(0, f)

    def _refill(self, initial=False):
        data = self.app.versions
        vals = versions.filter_versions(data, self.v_rel.get(), self.v_snap.get(), self.v_old.get()) or ["(loading...)"]
        if initial and self.p and self.p.mc_version not in vals:
            vals = [self.p.mc_version] + vals
        self.ver.configure(values=vals)
        self.ver.set(self.p.mc_version if initial and self.p else vals[0])
        self._check()

    def _check(self):
        loader, mc = self.loader.get(), self.ver.get()
        if loader == "vanilla" or mc.startswith("("):
            self.supported = True
            self.sup_lbl.configure(text="", text_color=theme.MUTED)
            return
        self.sup_lbl.configure(text=f"Checking {loader} support for {mc}...", text_color=theme.MUTED)
        key = (loader, mc)
        self._key = key

        def done(res):
            if getattr(self, "_key", None) != key or not self.winfo_exists():
                return
            self.supported = res
            self.sup_lbl.configure(
                text={True: f"✓ {loader} is available for {mc}", False: f"✗ {loader} has no build for {mc}",
                      None: "Could not verify (offline?) - will be checked on Play"}[res],
                text_color={True: theme.GOOD, False: theme.BAD, None: theme.WARN}[res])
        tasks.run_bg(lambda: versions.loader_supported(loader, mc), done, lambda e: done(None), "loadercheck")

    def _save(self):
        name, mc, loader = self.name.get().strip(), self.ver.get().strip(), self.loader.get()
        if not name or mc.startswith("("):
            mb.showwarning("VoidMiner", "Enter a name and pick a Minecraft version.", parent=self)
            return
        if self.supported is False:
            mb.showwarning("VoidMiner", f"{loader} is not available for Minecraft {mc}. Pick another combination.", parent=self)
            return
        a = self.app
        ram = 0 if self.ram.get().startswith("Auto") else int(self.ram.get().split()[0])
        try:
            if self.p:
                p = self.p
                if p.mc_version != mc or p.loader != loader:
                    p.version_id, p.loader_version = "", ""
                p.mc_version, p.loader = mc, loader
                a.profiles.rename(p, name) if name != p.name else None
            else:
                p = a.profiles.create(name, mc, loader, a.settings.get("default_mode"))
            p.ram_mb, p.java_path, p.jvm_args = ram, self.java.get().strip(), self.jvm.get().strip()
            a.profiles.save(p)
        except Exception as e:  # noqa
            mb.showerror("VoidMiner", f"Could not save profile:\n{e}", parent=self)
            return
        if not self.p:
            a.select_profile(p.id)
        self.destroy()
        if self.on_done:
            self.on_done()


class ProfilesPage(W.Page):
    def build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 8))
        W.heading(top, t("profiles"), "Each profile has its own version, loader, mods, saves and RAM.").pack(side="left")
        W.button(top, "+ " + t("new_profile"), self.new, width=150).pack(side="right")
        self.listf = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.listf.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 14))

    def new(self):
        if not self.app.versions:
            self.app.toast("Version list not loaded yet - check your connection.", "warn")
            return
        ProfileDialog(self.app, None, self.on_show)

    def on_show(self):
        W.clear(self.listf)
        cur = self.app.current_profile()
        ps = self.app.profiles.all()
        if not ps:
            W.label(self.listf, "No profiles yet. Create one to start playing.", 14, color=theme.MUTED).pack(pady=40)
        for p in ps:
            c = W.card(self.listf)
            c.pack(fill="x", padx=10, pady=6)
            c.grid_columnconfigure(1, weight=1)
            sel = cur and cur.id == p.id
            W.label(c, "●" if sel else "○", 16, color=theme.ACCENT if sel else theme.MUTED).grid(row=0, column=0, rowspan=2, padx=(18, 8), pady=14)
            W.label(c, p.name, 16, "bold").grid(row=0, column=1, sticky="w", pady=(12, 0))
            lp = time.strftime("%Y-%m-%d %H:%M", time.localtime(p.last_played)) if p.last_played else "never played"
            W.label(c, f"{p.mc_version} · {p.loader} · {optimizer.MODES.get(p.mode, {}).get('label', p.mode)} · {lp}",
                    12, color=theme.MUTED).grid(row=1, column=1, sticky="w", pady=(0, 12))
            bf = ctk.CTkFrame(c, fg_color="transparent")
            bf.grid(row=0, column=2, rowspan=2, padx=12)
            for txt, fn, kind in (("Select", lambda p=p: self._sel(p), "primary"), ("Edit", lambda p=p: self._edit(p), "ghost"),
                                  ("Duplicate", lambda p=p: self._dup(p), "ghost"), ("Folder", lambda p=p: self._open(p), "ghost"),
                                  ("Delete", lambda p=p: self._del(p), "danger")):
                W.button(bf, txt, fn, kind, width=78, height=30, size=12).pack(side="left", padx=3)

    def _sel(self, p):
        self.app.select_profile(p.id)
        self.on_show()

    def _edit(self, p):
        if self.app.game and self.app.game["profile"].id == p.id:
            self.app.toast("Stop the game before editing this profile.", "warn")
            return
        ProfileDialog(self.app, p, self.on_show)

    def _open(self, p):
        p.dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(p.dir))  # noqa
        else:
            self.app.toast(str(p.dir))

    def _dup(self, p):
        self.app.set_progress(f"Duplicating {p.name}...", 0.5)

        def work():
            return self.app.profiles.duplicate(p)

        def done(q):
            self.app.hide_progress()
            self.app.toast(f"Created {q.name}", "good")
            self.on_show()

        def err(e):
            self.app.hide_progress()
            mb.showerror("VoidMiner", f"Duplicate failed:\n{e}")
        tasks.run_bg(work, done, err, "duplicate")

    def _del(self, p):
        if self.app.game and self.app.game["profile"].id == p.id:
            self.app.toast("Stop the game first.", "warn")
            return
        if not mb.askyesno("Delete profile", f"Delete '{p.name}' and ALL its worlds, mods and settings?\nThis cannot be undone."):
            return
        try:
            self.app.profiles.delete(p)
        except Exception as e:  # noqa
            mb.showerror("VoidMiner", f"Delete failed:\n{e}")
            return
        if self.app.settings.get("last_profile") == p.id:
            self.app.settings.set("last_profile", "")
        self.on_show()
