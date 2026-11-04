from __future__ import annotations
import os, subprocess, tkinter.messagebox as mb
import customtkinter as ctk
import psutil
from .. import hardware, mods, optimizer, tasks
from ..i18n import t
from . import theme
from . import widgets as W

PROTECTED = {"system", "registry", "svchost.exe", "explorer.exe", "dwm.exe", "csrss.exe", "winlogon.exe", "lsass.exe",
             "services.exe", "smss.exe", "wininit.exe", "memory compression", "system idle process", "msmpeng.exe",
             "python.exe", "pythonw.exe", "java.exe", "javaw.exe", "voidminer client.exe", "fontdrvhost.exe",
             "searchhost.exe", "sihost.exe", "ctfmon.exe", "taskhostw.exe"}


class OptimizePage(W.Page):
    def build(self):
        self.sc = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.sc.pack(fill="both", expand=True, padx=18, pady=(18, 10))
        W.heading(self.sc, t("optimize"), "Real settings, measured with real process data - no fake FPS numbers.").pack(anchor="w", padx=10, pady=(6, 10))
        self.prof = W.label(self.sc, "", 13, "bold", theme.ACCENT)
        self.prof.pack(anchor="w", padx=10)

        mc = W.card(self.sc)
        mc.pack(fill="x", padx=10, pady=8)
        top = ctk.CTkFrame(mc, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(16, 6))
        self.seg = ctk.CTkSegmentedButton(top, values=[optimizer.MODES[m]["label"] for m in optimizer.MODE_ORDER],
                                          command=self._mode, selected_color=theme.ACCENT, unselected_color=theme.CARD2,
                                          selected_hover_color=theme.ACCENT, unselected_hover_color=theme.BORDER,
                                          font=theme.font(13, "bold"), height=36)
        self.seg.pack(side="left")
        W.button(top, "Auto-detect best", self._auto, "purple", width=140, height=36).pack(side="left", padx=12)
        self.desc = W.label(mc, "", 12, color=theme.MUTED, wraplength=760, justify="left")
        self.desc.pack(anchor="w", padx=18, pady=(0, 6))

        self.custom = ctk.CTkFrame(mc, fg_color="transparent")
        self.cv = {}
        for key, lo, hi, txt in (("render", 2, 32, "Render distance"), ("sim", 5, 32, "Simulation distance"), ("fps", 30, 260, "FPS limit (260 = unlimited)")):
            r = ctk.CTkFrame(self.custom, fg_color="transparent")
            r.pack(fill="x", pady=2)
            W.label(r, txt, 12, color=theme.MUTED, width=190, anchor="w").pack(side="left")
            lbl = W.label(r, "", 12, "bold", width=40)
            s = W.slider(r, lo, hi, hi - lo, lambda v, k=key, l=lbl: self._cset(k, v, l), 300)
            s.pack(side="left")
            lbl.pack(side="left", padx=8)
            self.cv[key] = (s, lbl)
        r = ctk.CTkFrame(self.custom, fg_color="transparent")
        r.pack(fill="x", pady=4)
        self.m_part = W.menu(r, ["All", "Decreased", "Minimal"], lambda v: self._cset("particles", ["All", "Decreased", "Minimal"].index(v)), 140)
        self.m_part.pack(side="left")
        self.m_gfx = W.menu(r, ["Fast", "Fancy"], lambda v: self._cset("graphics", ["Fast", "Fancy"].index(v)), 120)
        self.m_gfx.pack(side="left", padx=10)

        rc = W.card(self.sc)
        rc.pack(fill="x", padx=10, pady=8)
        W.label(rc, "MEMORY & JAVA", 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 4))
        rr = ctk.CTkFrame(rc, fg_color="transparent")
        rr.pack(fill="x", padx=18)
        self.ram_auto = W.switch(rr, "Auto (use mode default)", self._ram_auto_toggle)
        self.ram_auto.pack(side="left")
        self.ram_sl = W.slider(rr, 1024, 4096, 12, self._ram_move, 280)
        self.ram_sl.pack(side="left", padx=16)
        self.ram_lbl = W.label(rr, "", 13, "bold")
        self.ram_lbl.pack(side="left")
        W.label(rc, "Extra JVM arguments for this profile", 12, color=theme.MUTED).pack(anchor="w", padx=18, pady=(10, 2))
        self.jvm_e = W.entry(rc, 560)
        self.jvm_e.pack(anchor="w", padx=18)
        W.label(rc, "Final JVM flags used at launch", 12, color=theme.MUTED).pack(anchor="w", padx=18, pady=(10, 2))
        self.jvm_box = ctk.CTkTextbox(rc, height=84, fg_color=theme.BG, border_color=theme.BORDER, border_width=1,
                                      font=ctk.CTkFont(family="Consolas", size=12), text_color=theme.TEXT)
        self.jvm_box.pack(fill="x", padx=18, pady=(0, 10))
        bf = ctk.CTkFrame(rc, fg_color="transparent")
        bf.pack(anchor="w", padx=18, pady=(0, 16))
        W.button(bf, "Apply to profile", self._apply, width=150).pack(side="left", padx=(0, 8))
        W.button(bf, "Apply in-game options now", self._tweaks, "ghost", width=190).pack(side="left", padx=8)
        W.button(bf, "Install performance mods", self._install_mods, "purple", width=200).pack(side="left", padx=8)

        mm = W.card(self.sc)
        mm.pack(fill="x", padx=10, pady=8)
        W.label(mm, "PERFORMANCE MODS FOR THIS PROFILE", 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 4))
        self.mods_lbl = W.label(mm, "", 13, wraplength=760, justify="left")
        self.mods_lbl.pack(anchor="w", padx=18, pady=(0, 14))

        rec = W.card(self.sc)
        rec.pack(fill="x", padx=10, pady=8)
        W.label(rec, "RECOMMENDATIONS", 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 4))
        self.rec_lbl = W.label(rec, "", 12, wraplength=760, justify="left")
        self.rec_lbl.pack(anchor="w", padx=18, pady=(0, 14))

        mon = W.card(self.sc)
        mon.pack(fill="x", padx=10, pady=8)
        W.label(mon, "PERFORMANCE MONITORING", 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 4))
        self.hw_lbl = W.label(mon, "Detecting hardware...", 12, color=theme.MUTED, wraplength=760, justify="left")
        self.hw_lbl.pack(anchor="w", padx=18)
        self.live_lbl = W.label(mon, "Game not running.", 13, "bold", theme.GOOD)
        self.live_lbl.pack(anchor="w", padx=18, pady=4)
        W.label(mon, "Exact FPS can only be read by the game itself: press F3 in-game"
                " (the Sodium Extra mod in your performance set adds an FPS overlay).\nThe launcher measures the game's real CPU and RAM use.",
                12, color=theme.MUTED, wraplength=760, justify="left").pack(anchor="w", padx=18, pady=(0, 10))
        pr = ctk.CTkFrame(mon, fg_color="transparent")
        pr.pack(anchor="w", padx=18, pady=(0, 6))
        W.button(pr, "Scan background apps", self._scan, "ghost", width=170, height=32).pack(side="left")
        W.button(pr, "Open Task Manager", lambda: subprocess.Popen(["taskmgr"]) if os.name == "nt" else None, "ghost",
                 width=160, height=32).pack(side="left", padx=8)
        self.proc_lbl = W.label(mon, "", 12, wraplength=760, justify="left")
        self.proc_lbl.pack(anchor="w", padx=18, pady=(4, 16))

    # ---- helpers
    def _p(self):
        return self.app.current_profile()

    def on_show(self):
        p = self._p()
        if not p:
            self.prof.configure(text="Create a profile first (Profiles page).")
            return
        self.prof.configure(text=f"Profile: {p.name}  ·  {p.mc_version}  ·  {p.loader}")
        self.seg.set(optimizer.MODES[p.mode]["label"])
        self._refresh_mode()
        hw = self.app.hw
        total = int((hw or {"ram_gb": 8})["ram_gb"] * 1024 * 0.6)
        self.ram_sl.configure(to=max(1280, total), number_of_steps=max(1, (max(1280, total) - 1024) // 256))
        auto = p.ram_mb == 0
        (self.ram_auto.select if auto else self.ram_auto.deselect)()
        self.ram_sl.set(p.ram_mb or optimizer.effective_ram(p, self.app.settings, hw))
        self.ram_sl.configure(state="disabled" if auto else "normal")
        self.jvm_e.delete(0, "end")
        self.jvm_e.insert(0, p.jvm_args)
        if hw:
            self.hw_lbl.configure(text=f"{hw['cpu']}  ·  {hw['cores']} cores / {hw['threads']} threads  ·  {hw['ram_gb']} GB RAM  ·  GPU: {', '.join(hw['gpus'])}")
        self._refresh_info()

    def _refresh_mode(self):
        p = self._p()
        m = optimizer.MODES[p.mode]
        self.desc.configure(text=m["desc"])
        if p.mode == "custom":
            self.custom.pack(fill="x", padx=18, pady=(0, 10))
            c = optimizer.conf_for(p)
            for k, (s, l) in self.cv.items():
                s.set(c[k])
                l.configure(text=str(int(c[k])))
            self.m_part.set(["All", "Decreased", "Minimal"][c["particles"]])
            self.m_gfx.set(["Fast", "Fancy"][min(1, c["graphics"])])
        else:
            self.custom.pack_forget()

    def _refresh_info(self):
        p = self._p()
        if not p:
            return
        tmp = self._preview_profile()
        self.jvm_box.configure(state="normal")
        self.jvm_box.delete("1.0", "end")
        self.jvm_box.insert("1.0", " ".join(optimizer.build_jvm_args(tmp, self.app.settings, self.app.hw)))
        self.jvm_box.configure(state="disabled")
        self.ram_lbl.configure(text=f"{optimizer.effective_ram(tmp, self.app.settings, self.app.hw)} MB")
        self.rec_lbl.configure(text="\n".join("• " + r for r in optimizer.recommendations(self.app.hw, optimizer.conf_for(p))))
        if p.loader == "vanilla":
            self.mods_lbl.configure(text="Vanilla profile: performance mods need a mod loader. Edit the profile and choose Fabric/Quilt "
                                         "(Sodium, Lithium...) or Forge/NeoForge (Embeddium...). JVM and options tuning still apply.")
        else:
            want = optimizer.perf_mods(p.mode, p.loader)
            have = mods.perf_status(p.dir, want)
            self.mods_lbl.configure(text="   ".join(("✓ " if s in have else "○ ") + s for s in want))

    def _preview_profile(self):
        import copy
        p = copy.copy(self._p())
        p.ram_mb = 0 if self.ram_auto.get() else int(self.ram_sl.get() // 256 * 256)
        p.jvm_args = self.jvm_e.get().strip()
        return p

    def _mode(self, label):
        p = self._p()
        if not p:
            return
        p.mode = next(k for k, v in optimizer.MODES.items() if v["label"] == label)
        self.app.profiles.save(p)
        self._refresh_mode()
        self._refresh_info()
        p.tweaks_applied = False
        self.app.profiles.save(p)

    def _auto(self):
        if not self.app.hw:
            self.app.toast("Hardware is still being detected...", "warn")
            return
        m = hardware.recommend_mode(self.app.hw)
        self.seg.set(optimizer.MODES[m]["label"])
        self._mode(optimizer.MODES[m]["label"])
        self.app.toast(f"Detected: {optimizer.MODES[m]['label']} mode suits this PC", "good")

    def _cset(self, key, val, lbl=None):
        p = self._p()
        if not p:
            return
        val = int(val)
        p.custom[key] = val
        if lbl:
            lbl.configure(text=str(val))
        p.tweaks_applied = False
        self.app.profiles.save(p)
        self._refresh_info()

    def _ram_auto_toggle(self):
        self.ram_sl.configure(state="disabled" if self.ram_auto.get() else "normal")
        self._refresh_info()

    def _ram_move(self, _):
        self.ram_lbl.configure(text=f"{int(self.ram_sl.get() // 256 * 256)} MB")
        self._refresh_info()

    def _apply(self):
        p = self._p()
        if not p:
            return
        t_ = self._preview_profile()
        p.ram_mb, p.jvm_args = t_.ram_mb, t_.jvm_args
        self.app.profiles.save(p)
        self._refresh_info()
        self.app.toast("Settings saved to profile", "good")

    def _tweaks(self):
        p = self._p()
        if not p:
            return
        if self.app.game and self.app.game["profile"].id == p.id:
            self.app.toast("Close the game first (it rewrites options.txt on exit).", "warn")
            return
        try:
            bak = optimizer.apply_options(p.dir, optimizer.conf_for(p))
            p.tweaks_applied = True
            self.app.profiles.save(p)
            self.app.toast("options.txt tuned" + (" (original backed up)" if bak else ""), "good")
        except Exception as e:  # noqa
            mb.showerror("VoidMiner", f"Could not update options.txt:\n{e}")

    def _install_mods(self):
        p = self._p()
        if not p:
            return
        if p.loader == "vanilla":
            mb.showinfo("VoidMiner", "This is a Vanilla profile. Edit it and pick Fabric, Quilt, Forge or NeoForge to use performance mods.")
            return
        slugs = optimizer.perf_mods(p.mode, p.loader)
        a = self.app

        def work():
            ok, skipped = [], []
            for i, s in enumerate(slugs):
                tasks.ui(a.set_progress, f"Installing {s} ({i + 1}/{len(slugs)})", i / len(slugs))
                try:
                    inst, warns = mods.install(p.dir, p.mc_version, p.loader, s)
                    ok += inst
                    skipped += warns
                except Exception as e:  # noqa
                    skipped.append(f"{s}: {e}")
            return ok, skipped

        def done(res):
            a.hide_progress()
            ok, skipped = res
            msg = f"Installed/updated: {', '.join(dict.fromkeys(ok)) or 'nothing'}"
            if skipped:
                msg += "\n\nSkipped (not available for this version/loader):\n- " + "\n- ".join(skipped)
            mb.showinfo("Performance mods", msg)
            self._refresh_info()
        a.busy = True
        tasks.run_bg(work, lambda r: (setattr(a, "busy", False), done(r)),
                     lambda e: (setattr(a, "busy", False), a.hide_progress(), mb.showerror("VoidMiner", str(e))), "permods")

    def _scan(self):
        self.proc_lbl.configure(text="Scanning...")

        def work():
            agg = {}
            for pr in psutil.process_iter(["name", "memory_info"]):
                try:
                    n = (pr.info["name"] or "").lower()
                    if n in PROTECTED or not pr.info["memory_info"]:
                        continue
                    agg[n] = agg.get(n, 0) + pr.info["memory_info"].rss
                except Exception:
                    continue
            return sorted(agg.items(), key=lambda x: -x[1])[:7]

        def done(rows):
            if not rows:
                self.proc_lbl.configure(text="Nothing heavy found.")
                return
            self.proc_lbl.configure(text="Close these while playing if you don't need them (largest first):\n" +
                                    "\n".join(f"• {n}  -  {b / 1048576:.0f} MB" for n, b in rows))
        tasks.run_bg(work, done, lambda e: self.proc_lbl.configure(text=f"Scan failed: {e}"), "scan")

    def live(self, cpu, mem):
        self.live_lbl.configure(text=f"Game running  ·  CPU {cpu:.0f}%  ·  RAM {mem:.0f} MB")

    def live_off(self):
        self.live_lbl.configure(text="Game not running.")
