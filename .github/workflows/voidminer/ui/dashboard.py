from __future__ import annotations
import customtkinter as ctk
from .. import launcher, mods, optimizer, skins, tasks
from ..i18n import t
from . import theme
from . import widgets as W


class DashboardPage(W.Page):
    def build(self):
        a = self.app
        self.grid_columnconfigure(0, weight=3, uniform="c")
        self.grid_columnconfigure(1, weight=2, uniform="c")
        self.grid_rowconfigure(2, weight=1)
        W.heading(self, t("dashboard"), "Pick a profile and jump in.").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=28, pady=(24, 8))
        hero = W.card(self)
        hero.grid(row=1, column=0, sticky="nsew", padx=(28, 10), pady=6)
        W.label(hero, t("selected_profile").upper(), 11, "bold", theme.MUTED).pack(anchor="w", padx=24, pady=(20, 4))
        self.prof_menu = W.menu(hero, [" "], self._pick, width=320)
        self.prof_menu.pack(anchor="w", padx=24)
        self.ver_lbl = W.label(hero, "", 16, "bold")
        self.ver_lbl.pack(anchor="w", padx=24, pady=(14, 0))
        self.meta_lbl = W.label(hero, "", 12, color=theme.MUTED)
        self.meta_lbl.pack(anchor="w", padx=24, pady=(2, 10))
        row = ctk.CTkFrame(hero, fg_color="transparent")
        row.pack(anchor="w", padx=24, pady=(6, 6))
        self.play_btn = W.button(row, t("play"), a.play, width=250, height=58, size=19)
        self.play_btn.pack(side="left")
        self.stop_btn = W.button(row, t("stop"), a.stop_game, "danger", width=120, height=58)
        self.live_lbl = W.label(hero, "", 12, color=theme.GOOD)
        self.live_lbl.pack(anchor="w", padx=24, pady=(4, 18))

        pc = W.card(self)
        pc.grid(row=1, column=1, sticky="nsew", padx=(10, 28), pady=6)
        self.skin_lbl = ctk.CTkLabel(pc, text="", width=120, height=190)
        self.skin_lbl.pack(pady=(16, 4))
        self.name_lbl = W.label(pc, "", 17, "bold")
        self.name_lbl.pack()
        self.acc_lbl = W.label(pc, "", 12, color=theme.MUTED)
        self.acc_lbl.pack(pady=(0, 8))
        W.button(pc, "Accounts", lambda: a.show("accounts"), "ghost", width=140, height=32).pack(pady=(0, 16))

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=18, pady=0)
        stats.grid_rowconfigure(0, weight=1)
        self.stat = {}
        for i, (k, title) in enumerate([("fps", "FPS OPTIMIZATION"), ("ram", "RAM ALLOCATION"),
                                        ("inst", "MINECRAFT INSTALL"), ("java", "JAVA RUNTIME")]):
            stats.grid_columnconfigure(i, weight=1, uniform="s")
            c = W.card(stats)
            c.grid(row=0, column=i, sticky="nsew", padx=10, pady=6)
            W.label(c, title, 10, "bold", theme.MUTED).pack(anchor="w", padx=16, pady=(14, 2))
            self.stat[k] = W.label(c, "-", 14, "bold", wraplength=190, justify="left")
            self.stat[k].pack(anchor="w", padx=16, pady=(0, 14))

        rec = ctk.CTkFrame(self, fg_color="transparent")
        rec.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=18, pady=(0, 14))
        rec.grid_columnconfigure((0, 1), weight=1, uniform="r")
        self.rv, self.rp = W.card(rec), W.card(rec)
        self.rv.grid(row=0, column=0, sticky="nsew", padx=10)
        self.rp.grid(row=0, column=1, sticky="nsew", padx=10)

    def _pick(self, name):
        p = next((x for x in self.app.profiles.all() if x.name == name), None)
        if p:
            self.app.select_profile(p.id)

    def on_show(self):
        a = self.app
        ps = a.profiles.all()
        p = a.current_profile()
        names = [x.name for x in ps] or ["No profiles yet"]
        self.prof_menu.configure(values=names)
        self.prof_menu.set(p.name if p else names[0])
        run = a.game is not None
        self.play_btn.configure(text=t("playing") if run else t("play"),
                                state="disabled" if (run or a.busy or not p) else "normal")
        if run:
            self.stop_btn.pack(side="left", padx=10)
        else:
            self.stop_btn.pack_forget()
            self.live_lbl.configure(text="")
        if p:
            loader = "Vanilla" if p.loader == "vanilla" else p.loader.capitalize()
            self.ver_lbl.configure(text=f"Minecraft {p.mc_version}  ·  {loader}")
            conf = optimizer.MODES.get(p.mode, {})
            ram = optimizer.effective_ram(p, a.settings, a.hw)
            self.meta_lbl.configure(text=f"{conf.get('label', p.mode)} mode  ·  {ram} MB RAM  ·  instance: {p.id}")
            self.stat["ram"].configure(text=f"{ram} MB" + (f" of {int(a.hw['ram_gb'] * 1024)} MB" if a.hw else ""))
            self.stat["inst"].configure(
                text="Installed" if launcher.is_installed(a.settings.mc_dir, p.version_id) else "Downloads on first Play",
                text_color=theme.GOOD if launcher.is_installed(a.settings.mc_dir, p.version_id) else theme.WARN)
            comp = launcher.java_component(a.settings.mc_dir, p.version_id) if p.version_id else None
            self.stat["java"].configure(text=("Bundled " + comp) if comp else "Auto (downloaded with the version)")
            if p.loader == "vanilla":
                self.stat["fps"].configure(text=f"{conf.get('label', '')} · JVM + settings tuning")
            else:
                want = optimizer.perf_mods(p.mode, p.loader)
                have = mods.perf_status(p.dir, want)
                self.stat["fps"].configure(text=f"{conf.get('label', '')} · {len(have)}/{len(want)} perf mods")
        else:
            self.ver_lbl.configure(text="Create a profile to begin")
            self.meta_lbl.configure(text="")
            for k in self.stat.values():
                k.configure(text="-")
        acc = a.accounts.active()
        self.name_lbl.configure(text=acc["name"] if acc else t("not_signed"))
        self.acc_lbl.configure(text="Microsoft account" if acc else "Sign in to play")
        self._skin(acc)
        self._recents(ps)

    def _skin(self, acc):
        if not acc:
            self.skin_lbl.configure(image=None, text="No skin")
            return
        cached = self.app.skin_imgs.get(acc["uuid"])
        if cached:
            self.skin_lbl.configure(image=cached, text="")
            return

        def work():
            data = self.app.accounts.session(acc["uuid"])
            act = next((s for s in data.get("skins", []) if s.get("state") == "ACTIVE"), (data.get("skins") or [None])[0])
            if not act:
                return None
            img = skins.render(skins.load_png(act["url"]), act.get("variant", "").upper() == "SLIM", None, "front", 6)
            return ctk.CTkImage(img, size=(120, 192))

        def done(ci):
            if ci:
                self.app.skin_imgs[acc["uuid"]] = ci
                self.skin_lbl.configure(image=ci, text="")
        tasks.run_bg(work, done, lambda e: self.skin_lbl.configure(text="Skin unavailable"), "skin")

    def _recents(self, ps):
        W.clear(self.rv)
        W.clear(self.rp)
        W.label(self.rv, t("recent_versions").upper(), 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 6))
        W.label(self.rp, t("recent_profiles").upper(), 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 6))
        rv = self.app.settings.get("recent_versions") or []
        if not rv:
            W.label(self.rv, "Nothing played yet", 12, color=theme.MUTED).pack(anchor="w", padx=18)
        for v in rv[:4]:
            b = W.button(self.rv, v, lambda v=v: self._by_version(v), "ghost", width=200, height=28, size=12)
            b.pack(anchor="w", padx=18, pady=2)
        played = sorted([p for p in ps if p.last_played], key=lambda p: -p.last_played)[:4]
        if not played:
            W.label(self.rp, "Nothing played yet", 12, color=theme.MUTED).pack(anchor="w", padx=18)
        for p in played:
            W.button(self.rp, p.name, lambda p=p: self.app.select_profile(p.id), "ghost", width=200, height=28,
                     size=12).pack(anchor="w", padx=18, pady=2)

    def _by_version(self, vid):
        p = next((x for x in self.app.profiles.all() if x.version_id == vid or x.mc_version == vid), None)
        if p:
            self.app.select_profile(p.id)
        else:
            self.app.toast("No profile uses that version any more.", "warn")

    def live(self, cpu, mem):
        self.live_lbl.configure(text=f"Game running  ·  CPU {cpu:.0f}%  ·  RAM {mem:.0f} MB")
