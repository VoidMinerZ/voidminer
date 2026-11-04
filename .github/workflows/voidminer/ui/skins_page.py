from __future__ import annotations
import math, tkinter.filedialog as fd, tkinter.messagebox as mb
import customtkinter as ctk
from PIL import Image
from .. import skins, tasks
from ..i18n import t
from . import theme
from . import widgets as W


class SkinsPage(W.Page):
    def build(self):
        self.grid_columnconfigure(0, weight=1)
        W.heading(self, t("skins"), "Your official Minecraft skin and capes. Changes go through Mojang's services.").grid(
            row=0, column=0, sticky="w", padx=28, pady=(24, 8))
        c = W.card(self)
        c.grid(row=1, column=0, sticky="nw", padx=28, pady=6)
        left = ctk.CTkFrame(c, fg_color="transparent")
        left.pack(side="left", padx=30, pady=24)
        self.prev = ctk.CTkLabel(left, text="Sign in to see your skin", width=200, height=320)
        self.prev.pack()
        W.button(left, "⟳ Rotate", self.rotate, "ghost", width=120, height=32).pack(pady=(10, 0))
        right = ctk.CTkFrame(c, fg_color="transparent")
        right.pack(side="left", padx=30, pady=24, anchor="n")
        self.name = W.label(right, "", 20, "bold")
        self.name.pack(anchor="w")
        self.var_lbl = W.label(right, "", 12, color=theme.MUTED)
        self.var_lbl.pack(anchor="w", pady=(0, 14))
        W.label(right, "CHANGE SKIN", 11, "bold", theme.MUTED).pack(anchor="w")
        r = ctk.CTkFrame(right, fg_color="transparent")
        r.pack(anchor="w", pady=6)
        self.variant = W.menu(r, ["Classic", "Slim"], width=110)
        self.variant.pack(side="left")
        W.button(r, "Upload skin (.png)...", self.upload, width=170).pack(side="left", padx=8)
        W.label(right, "CAPES YOU OWN", 11, "bold", theme.MUTED).pack(anchor="w", pady=(16, 0))
        r2 = ctk.CTkFrame(right, fg_color="transparent")
        r2.pack(anchor="w", pady=6)
        self.cape_menu = W.menu(r2, ["No cape"], width=200)
        self.cape_menu.pack(side="left")
        W.button(r2, "Apply cape", self.apply_cape, width=120).pack(side="left", padx=8)
        W.label(right, "Only capes owned by your account are listed - nothing is faked.", 12, color=theme.MUTED).pack(anchor="w")
        W.button(right, "Refresh from Mojang", lambda: self.on_show(True), "ghost", width=170, height=32).pack(anchor="w", pady=(20, 0))
        self.imgs = {}
        self.view = "front"
        self._anim = False
        self.capes = []

    def _acc(self):
        return self.app.accounts.active()

    def on_show(self, force=False):
        acc = self._acc()
        if not acc:
            self.name.configure(text="Not signed in")
            self.var_lbl.configure(text="Go to Accounts to sign in with Microsoft.")
            return
        self.name.configure(text=acc["name"])
        self.var_lbl.configure(text="Loading...")

        def work():
            d = self.app.accounts.session(acc["uuid"], force=force)
            sk = next((s for s in d.get("skins", []) if s.get("state") == "ACTIVE"), (d.get("skins") or [None])[0])
            skin = skins.load_png(sk["url"]) if sk else None
            capes = d.get("capes", [])
            act = next((c for c in capes if c.get("state") == "ACTIVE"), None)
            cape_img = skins.load_png(act["url"]) if act else None
            return sk, skin, capes, act, cape_img

        def done(r):
            sk, skin, capes, act, cape_img = r
            self.capes = capes
            names = ["No cape"] + [c.get("alias", c["id"]) for c in capes]
            self.cape_menu.configure(values=names)
            self.cape_menu.set(act.get("alias", act["id"]) if act else "No cape")
            if skin:
                slim = (sk.get("variant", "") or "").upper() == "SLIM"
                self.imgs = {v: skins.render(skin, slim, cape_img, v, 10) for v in ("front", "back")}
                self.view = "front"
                self._show(self.imgs["front"])
                self.var_lbl.configure(text=("Slim" if slim else "Classic") + " model" + (f"  ·  cape: {act.get('alias')}" if act else ""))
            else:
                self.var_lbl.configure(text="No skin data returned.")
        tasks.run_bg(work, done, lambda e: self.var_lbl.configure(text=f"Failed: {e}"), "skinload")

    def _show(self, img, width=None):
        w, h = img.size
        if width:
            img = img.resize((max(2, int(w * width)), h), Image.NEAREST)
        ci = ctk.CTkImage(img, size=(img.size[0], img.size[1]))
        self.prev.configure(image=ci, text="")
        self.prev._ci = ci

    def rotate(self):
        if not self.imgs or self._anim:
            return
        self._anim = True
        self._step(0)

    def _step(self, i, n=14):
        other = "back" if self.view == "front" else "front"
        th = math.pi * i / n
        self._show(self.imgs[self.view if th < math.pi / 2 else other], abs(math.cos(th)))
        if i < n:
            self.after(30, self._step, i + 1)
        else:
            self.view, self._anim = other, False

    def upload(self):
        acc = self._acc()
        if not acc:
            self.app.toast("Sign in first.", "warn")
            return
        f = fd.askopenfilename(parent=self.app, title="Choose a 64x64 skin PNG", filetypes=[("PNG", "*.png")])
        if not f:
            return
        v = self.variant.get().lower()

        def work():
            d = self.app.accounts.session(acc["uuid"])
            skins.upload_skin(d["access_token"], f, v)
        self.app.set_progress("Uploading skin...", None)

        def done(_):
            self.app.hide_progress()
            self.app.skin_imgs.pop(acc["uuid"], None)
            self.app.toast("Skin updated", "good")
            self.on_show(True)
        tasks.run_bg(work, done, lambda e: (self.app.hide_progress(), mb.showerror("VoidMiner", str(e))), "skinup")

    def apply_cape(self):
        acc = self._acc()
        if not acc:
            return
        sel = self.cape_menu.get()
        cid = next((c["id"] for c in self.capes if c.get("alias", c["id"]) == sel), None)

        def work():
            d = self.app.accounts.session(acc["uuid"])
            skins.set_cape(d["access_token"], cid)
        tasks.run_bg(work, lambda _: (self.app.toast("Cape updated", "good"), self.on_show(True)),
                     lambda e: mb.showerror("VoidMiner", str(e)), "cape")
