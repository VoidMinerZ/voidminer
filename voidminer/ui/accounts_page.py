from __future__ import annotations
import tkinter.messagebox as mb, webbrowser
import customtkinter as ctk
from .. import tasks
from ..accounts import AccountError
from ..i18n import t
from . import theme
from . import widgets as W


class AccountsPage(W.Page):
    def build(self):
        self.grid_columnconfigure(0, weight=1)
        W.heading(self, t("accounts"), "Official Microsoft sign-in. Passwords are never seen or stored by VoidMiner.").grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 8))
        self.listf = W.card(self)
        self.listf.grid(row=1, column=0, sticky="ew", padx=28, pady=6)
        c = W.card(self)
        c.grid(row=2, column=0, sticky="ew", padx=28, pady=6)
        W.label(c, "MICROSOFT APP (CLIENT ID)", 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 4))
        W.label(c, "Sign-in needs your own Azure app registration (free). Redirect URI: http://localhost  ·  Platform: Mobile/desktop  ·  "
                   "Allow public client flows: Yes. Mojang must also approve new app IDs for Minecraft services (README → Microsoft sign-in).",
                12, color=theme.MUTED, wraplength=820, justify="left").pack(anchor="w", padx=18)
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(anchor="w", padx=18, pady=10)
        self.cid = W.entry(r, 380, placeholder_text="Application (client) ID")
        self.cid.pack(side="left")
        W.button(r, "Save ID", self._save_id, "ghost", width=90).pack(side="left", padx=8)
        W.button(r, "Azure portal", lambda: webbrowser.open("https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade"),
                 "ghost", width=110).pack(side="left")
        self.add_btn = W.button(c, "+ Add Microsoft account", self.add, width=220, height=42)
        self.add_btn.pack(anchor="w", padx=18, pady=(4, 16))

    def on_show(self):
        a = self.app
        self.cid.delete(0, "end")
        self.cid.insert(0, a.accounts.client_id())
        W.clear(self.listf)
        accs = a.accounts.list()
        act = a.accounts.active()
        W.label(self.listf, "SIGNED-IN ACCOUNTS", 11, "bold", theme.MUTED).pack(anchor="w", padx=18, pady=(14, 4))
        if not accs:
            W.label(self.listf, "No accounts yet.", 13, color=theme.MUTED).pack(anchor="w", padx=18, pady=(0, 16))
        for x in accs:
            r = ctk.CTkFrame(self.listf, fg_color="transparent")
            r.pack(fill="x", padx=18, pady=4)
            is_act = act and act["uuid"] == x["uuid"]
            W.label(r, ("● " if is_act else "○ ") + x["name"], 15, "bold", theme.ACCENT if is_act else theme.TEXT).pack(side="left")
            W.button(r, "Log out", lambda x=x: self._logout(x), "danger", width=86, height=30, size=12).pack(side="right")
            if not is_act:
                W.button(r, "Use", lambda x=x: self._use(x), "ghost", width=70, height=30, size=12).pack(side="right", padx=6)
        W.label(self.listf, "", 4).pack(pady=4)

    def _save_id(self):
        self.app.settings.set("client_id", self.cid.get().strip())
        self.app.toast("Client ID saved", "good")

    def _use(self, x):
        self.app.accounts.set_active(x["uuid"])
        self.app.refresh_chip()
        self.on_show()

    def _logout(self, x):
        if mb.askyesno("Log out", f"Remove {x['name']} from this launcher?"):
            self.app.accounts.logout(x["uuid"])
            self.app.skin_imgs.pop(x["uuid"], None)
            self.app.refresh_chip()
            self.on_show()

    def add(self):
        a = self.app
        self._save_id()
        if not a.accounts.client_id():
            mb.showinfo("VoidMiner", "Paste your Azure application (client) ID first.")
            return
        self.add_btn.configure(state="disabled")
        a.set_progress("Opening Microsoft sign-in in your browser...", None)

        def work():
            return a.accounts.login(lambda s: tasks.ui(a.set_progress, s, None))

        def done(d):
            a.hide_progress()
            self.add_btn.configure(state="normal")
            a.toast(f"Signed in as {d['name']}", "good")
            a.refresh_chip()
            self.on_show()

        def err(e):
            a.hide_progress()
            self.add_btn.configure(state="normal")
            mb.showerror("Sign-in failed", str(e) if isinstance(e, AccountError) else f"{type(e).__name__}: {e}")
        tasks.run_bg(work, done, err, "login")
