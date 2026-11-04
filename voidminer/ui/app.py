from __future__ import annotations
import logging, os, time, tkinter as tk, tkinter.messagebox as mb
import customtkinter as ctk
from .. import hardware, i18n, launcher, optimizer, tasks, updater, versions
from ..accounts import AccountManager
from ..i18n import t
from ..paths import APP_VERSION, resource
from ..profiles import ProfileManager
from ..settings import Settings
from . import theme
from . import widgets as W
from .accounts_page import AccountsPage
from .dashboard import DashboardPage
from .mods_page import ModsPage
from .optimize_page import OptimizePage
from .profiles_page import ProfilesPage
from .settings_page import SettingsPage
from .skins_page import SkinsPage

log = logging.getLogger(__name__)
NAV = [("dashboard", "⌂", DashboardPage), ("profiles", "☰", ProfilesPage), ("optimize", "⚡", OptimizePage),
       ("mods", "⬡", ModsPage), ("skins", "☺", SkinsPage), ("accounts", "⚑", AccountsPage),
       ("settings", "⚙", SettingsPage)]


class App(ctk.CTk):
    def __init__(self):
        self.settings = Settings()
        i18n.set_language(self.settings.get("language"))
        theme.apply_accent(self.settings.get("accent"))
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=theme.BG)
        self.profiles = ProfileManager()
        self.accounts = AccountManager(self.settings)
        self.versions, self.offline, self.hw = [], False, None
        self.game, self.busy = None, False
        self.skin_imgs, self.pages, self.nav_buttons, self.current = {}, {}, {}, None
        self._toast, self._maxed, self._prev_geo, self._minimized, self._stopped = None, False, None, False, False
        self.native = bool(self.settings.get("native_titlebar"))
        self.title("VoidMiner Client")
        self.geometry("1180x720+100+50")
        self.minsize(1020, 660)
        try:
            self.iconbitmap(str(resource("assets/icon.ico")))
        except Exception:
            pass
        self._shell()
        tasks.pump(self)
        self.show("dashboard", animate=False)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Map>", self._on_map)
        if not self.native:
            self.after(60, self._borderless)
        self.attributes("-alpha", 0.0)
        self.after(160, self._fade, 0.0)
        self._start_background()

    # ------------------------------------------------------------------ shell
    def _shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        if not self.native:
            tb = ctk.CTkFrame(self, height=38, fg_color=theme.SIDEBAR, corner_radius=0)
            tb.grid(row=0, column=0, columnspan=2, sticky="ew")
            tb.grid_propagate(False)
            tb.grid_columnconfigure(1, weight=1)
            W.label(tb, "  ◆ VoidMiner Client", 12, "bold", theme.MUTED).grid(row=0, column=0, padx=8, pady=6)
            drag = ctk.CTkLabel(tb, text="")
            drag.grid(row=0, column=1, sticky="nsew")
            for wdg in (tb, drag):
                wdg.bind("<ButtonPress-1>", self._drag_start)
                wdg.bind("<B1-Motion>", self._drag_move)
                wdg.bind("<Double-Button-1>", lambda e: self.toggle_max())
            for i, (txt, fn, hv) in enumerate((("—", self.minimize, theme.BORDER), ("▢", self.toggle_max, theme.BORDER),
                                               ("✕", self.close, "#C42B45"))):
                ctk.CTkButton(tb, text=txt, width=46, height=38, corner_radius=0, fg_color="transparent", hover_color=hv,
                              text_color=theme.TEXT, font=theme.font(13), command=fn).grid(row=0, column=2 + i)
        sb = ctk.CTkFrame(self, width=220, fg_color=theme.SIDEBAR, corner_radius=0)
        sb.grid(row=1, column=0, sticky="nsw")
        sb.grid_propagate(False)
        lg = ctk.CTkFrame(sb, fg_color="transparent")
        lg.pack(anchor="w", padx=22, pady=(24, 22))
        W.label(lg, "VOID", 22, "bold", theme.ACCENT2).pack(side="left")
        W.label(lg, "MINER", 22, "bold", theme.TEXT).pack(side="left")
        for key, icon, _ in NAV:
            b = ctk.CTkButton(sb, text=f"  {icon}   {t(key)}", anchor="w", height=42, corner_radius=12, fg_color="transparent",
                              hover_color=theme.CARD, text_color=theme.MUTED, font=theme.font(14, "bold"),
                              command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[key] = b
        self.chip = ctk.CTkButton(sb, text="", anchor="w", height=52, corner_radius=12, fg_color=theme.CARD,
                                  hover_color=theme.CARD2, text_color=theme.TEXT, font=theme.font(12, "bold"),
                                  command=lambda: self.show("accounts"))
        self.chip.pack(side="bottom", fill="x", padx=12, pady=14)
        self.refresh_chip()
        self.content = ctk.CTkFrame(self, fg_color=theme.BG, corner_radius=0)
        self.content.grid(row=1, column=1, sticky="nsew")
        self.status = ctk.CTkFrame(self, height=30, fg_color=theme.SIDEBAR, corner_radius=0)
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.status.grid_propagate(False)
        self.status.grid_columnconfigure(0, weight=1)
        self.status_lbl = W.label(self.status, "Ready", 11, color=theme.MUTED)
        self.status_lbl.grid(row=0, column=0, sticky="w", padx=14)
        self.bar = ctk.CTkProgressBar(self.status, width=280, height=8, progress_color=theme.ACCENT, fg_color=theme.BORDER)
        self.bar.grid(row=0, column=1, padx=(0, 30), pady=10)
        self.bar.grid_remove()
        if not self.native:
            g = ctk.CTkLabel(self.status, text="◢", text_color=theme.MUTED, cursor=("size_nw_se" if os.name == "nt" else "bottom_right_corner"), width=18)
            g.grid(row=0, column=2, sticky="e")
            g.bind("<ButtonPress-1>", self._rs_start)
            g.bind("<B1-Motion>", self._rs_move)

    # ---- custom window behaviour
    def _borderless(self):
        try:
            self.overrideredirect(True)
            if os.name == "nt":
                import ctypes
                u = ctypes.windll.user32
                hwnd = u.GetParent(self.winfo_id())
                style = u.GetWindowLongW(hwnd, -20)
                u.SetWindowLongW(hwnd, -20, (style & ~0x80) | 0x40000)
                self.withdraw()
                self.after(20, self.deiconify)
        except Exception:
            log.exception("borderless setup failed")

    def _on_map(self, e):
        if e.widget is self and self._minimized:
            self._minimized = False
            self.after(30, self._borderless)

    def _fade(self, a):
        a = min(1.0, a + 0.12)
        try:
            self.attributes("-alpha", a)
        except Exception:
            return
        if a < 1:
            self.after(16, self._fade, a)

    def minimize(self):
        if self.native:
            self.iconify()
            return
        self._minimized = True
        self.overrideredirect(False)
        self.update_idletasks()
        self.iconify()

    def _workarea(self):
        try:
            import ctypes
            from ctypes import wintypes
            r = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)
            return r.left, r.top, r.right - r.left, r.bottom - r.top
        except Exception:
            return 0, 0, self.winfo_screenwidth(), self.winfo_screenheight() - 40

    def toggle_max(self):
        if self.native:
            self.state("normal" if self.state() == "zoomed" else "zoomed")
            return
        if self._maxed and self._prev_geo:
            self.geometry(self._prev_geo)
            self._maxed = False
        else:
            self._prev_geo = self.geometry()
            x, y, w, h = self._workarea()
            s = self._get_window_scaling()
            self.geometry(f"{int(w / s)}x{int(h / s)}+{int(x / s)}+{int(y / s)}")
            self._maxed = True

    def _drag_start(self, e):
        self._dx, self._dy = e.x_root - self.winfo_x(), e.y_root - self.winfo_y()

    def _drag_move(self, e):
        if not self._maxed:
            tk.Tk.wm_geometry(self, f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _rs_start(self, e):
        self._rx, self._ry, self._rw, self._rh = e.x_root, e.y_root, self.winfo_width(), self.winfo_height()

    def _rs_move(self, e):
        s = self._get_window_scaling()
        w = max(1020, int((self._rw + e.x_root - self._rx) / s))
        h = max(660, int((self._rh + e.y_root - self._ry) / s))
        self.geometry(f"{w}x{h}")

    # ---- navigation
    def show(self, name, animate=True):
        if name not in self.pages:
            cls = next(c for k, _, c in NAV if k == name)
            self.pages[name] = cls(self.content, self)
        page = self.pages[name]
        if self.current and self.current != name:
            self.pages[self.current].place_forget()
        self.current = name
        for k, b in self.nav_buttons.items():
            b.configure(fg_color=theme.CARD2 if k == name else "transparent",
                        text_color=theme.ACCENT if k == name else theme.MUTED)
        page.on_show()
        if animate:
            self._slide(page, 0.03)
        else:
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _slide(self, page, off):
        if self.pages.get(self.current) is not page:
            return
        if off > 0.003:
            page.place(relx=off, rely=0, relwidth=1, relheight=1)
            self.after(14, self._slide, page, off * 0.55)
        else:
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def refresh_chip(self):
        acc = self.accounts.active()
        self.chip.configure(text=f"  ☺  {acc['name']}\n      Microsoft account" if acc else f"  ☺  {t('not_signed')}\n      Click to sign in")

    # ---- feedback helpers
    def toast(self, msg, kind="info"):
        if self._toast is not None:
            try:
                self._toast.destroy()
            except Exception:
                pass
        col = {"good": theme.GOOD, "warn": theme.WARN, "bad": theme.BAD}.get(kind, theme.ACCENT)
        self._toast = ctk.CTkLabel(self.content, text=f"  {msg}  ", font=theme.font(13, "bold"), text_color=col,
                                   fg_color=theme.CARD2, corner_radius=10, height=38)
        self._toast.place(relx=1, rely=1, x=-24, y=-20, anchor="se")
        tw = self._toast
        self.after(3600, lambda: tw.destroy() if tw.winfo_exists() else None)

    def set_progress(self, status, frac=None):
        self.status_lbl.configure(text=status or "Working...")
        self.bar.grid()
        if frac is None:
            if self.bar.cget("mode") != "indeterminate":
                self.bar.configure(mode="indeterminate")
                self.bar.start()
        else:
            if self.bar.cget("mode") != "determinate":
                self.bar.stop()
                self.bar.configure(mode="determinate")
            self.bar.set(frac)

    def hide_progress(self):
        try:
            self.bar.stop()
        except Exception:
            pass
        self.bar.grid_remove()
        self.status_lbl.configure(text="Ready")

    # ---- state
    def current_profile(self):
        ps = self.profiles.all()
        return next((p for p in ps if p.id == self.settings.get("last_profile")), ps[0] if ps else None)

    def select_profile(self, pid):
        self.settings.set("last_profile", pid)
        if self.current:
            self.pages[self.current].on_show()

    def _start_background(self):
        tasks.run_bg(versions.fetch, self._versions_ready,
                     lambda e: self.toast("Could not load the Minecraft version list (offline?)", "warn"), "versions")
        tasks.run_bg(hardware.get_info, self._hw_ready, None, "hardware")
        if self.settings.get("auto_update_check") and self.settings.get("update_url"):
            tasks.run_bg(lambda: updater.check(self.settings.get("update_url")),
                         lambda d: self.toast(f"Launcher update {d['version']} available (Settings)", "good") if d["newer"] else None,
                         None, "update")

    def _versions_ready(self, res):
        self.versions, self.offline = res
        if self.offline:
            self.toast("Offline - using cached version list", "warn")
        self._first_run()

    def _hw_ready(self, info):
        self.hw = info
        if not self.settings.get("mode_detected"):
            self.settings.set("default_mode", hardware.recommend_mode(info))
            self.settings.set("mode_detected", True)
        self._first_run()

    def _first_run(self):
        if self.versions and self.hw is not None and not self.profiles.all():
            v = versions.latest_release(self.versions)
            if v:
                p = self.profiles.create("Default", v, "vanilla", self.settings.get("default_mode"))
                self.settings.set("last_profile", p.id)
        if self.current:
            self.pages[self.current].on_show()

    # ------------------------------------------------------------------ play
    def play(self):
        p = self.current_profile()
        if self.game or self.busy:
            return
        if not p:
            self.toast("Create a profile first.", "warn")
            self.show("profiles")
            return
        acc = self.accounts.active()
        if not acc:
            self.toast("Sign in with Microsoft to play.", "warn")
            self.show("accounts")
            return
        self.busy = True
        self._stopped = False
        self.pages["dashboard"].on_show()
        cb = tasks.make_callback(self.set_progress)
        mc = self.settings.mc_dir

        def work():
            tasks.ui(self.set_progress, f"Preparing Minecraft {p.mc_version}...", None)
            launcher.ensure_installed(p, self.profiles, mc, cb)
            java = launcher.resolve_java(p, self.settings, mc, cb)
            tasks.ui(self.set_progress, "Signing in to Minecraft services...", None)
            session = self.accounts.session(acc["uuid"])
            if not p.tweaks_applied:
                try:
                    optimizer.apply_options(p.dir, optimizer.conf_for(p))
                    p.tweaks_applied = True
                except Exception:
                    log.exception("options tuning skipped")
            cmd = launcher.build_command(p, session, self.settings, self.hw, mc, java)
            proc, logp = launcher.start(cmd, p, bool(self.settings.get("high_priority")))
            self.profiles.save(p)
            return proc, logp

        def done(res):
            proc, logp = res
            self.busy = False
            self.hide_progress()
            self.game = {"proc": proc, "profile": p, "start": time.time(), "log": logp}
            rv = [p.version_id] + [v for v in self.settings.get("recent_versions") if v != p.version_id]
            self.settings.set("recent_versions", rv[:6])
            if self.settings.get("minimize_on_launch"):
                self.minimize()
            self.pages["dashboard"].on_show() if self.current == "dashboard" else None
            import threading
            threading.Thread(target=self._monitor, args=(proc,), daemon=True, name="game-monitor").start()

        def err(e):
            self.busy = False
            self.hide_progress()
            self.pages["dashboard"].on_show()
            mb.showerror("Launch failed", f"{e}\n\nDetails are in {os.path.join(str(self.settings.mc_dir), '..', 'logs', 'launcher.log')}")
        tasks.run_bg(work, done, err, "launch")

    def _monitor(self, proc):
        import psutil
        try:
            ps = psutil.Process(proc.pid)
            ps.cpu_percent(None)
        except Exception:
            ps = None
        n = psutil.cpu_count() or 1
        while proc.poll() is None:
            time.sleep(2)
            try:
                cpu, mem = ps.cpu_percent(None) / n, ps.memory_info().rss / 1048576
            except Exception:
                cpu = mem = 0.0
            tasks.ui(self._live, cpu, mem)
        tasks.ui(self._game_exited, proc.returncode)

    def _live(self, cpu, mem):
        if self.game:
            for k in ("dashboard", "optimize"):
                if k in self.pages:
                    self.pages[k].live(cpu, mem)

    def _game_exited(self, code):
        g, self.game = self.game, None
        if not g:
            return
        try:
            if self.state() == "iconic":
                self.deiconify()
        except Exception:
            pass
        self.refresh_chip()
        if "optimize" in self.pages:
            self.pages["optimize"].live_off()
        if self.current:
            self.pages[self.current].on_show()
        mins = (time.time() - g["start"]) / 60
        if code not in (0, None) and not self._stopped:
            mb.showwarning("Minecraft closed unexpectedly",
                           f"Exit code {code} after {mins:.1f} min.\n\nLast log lines:\n\n{launcher.tail(g['log'])}\n\nFull log: {g['log']}")
        else:
            self.toast(f"Game closed after {mins:.0f} min", "info")

    def stop_game(self):
        if self.game and mb.askyesno("Stop game", "Force-close Minecraft? Unsaved progress will be lost."):
            self._stopped = True
            try:
                self.game["proc"].terminate()
            except Exception:
                pass

    def close(self):
        if self.game and not mb.askyesno("VoidMiner", "Minecraft is still running. Close the launcher anyway?\n(The game keeps running.)"):
            return
        self.destroy()
