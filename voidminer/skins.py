"""Skin/cape rendering (2D front/back with a turntable animation) and official skin/cape API calls."""
from __future__ import annotations
import hashlib, logging
import requests
from PIL import Image
from .paths import CACHE

log = logging.getLogger(__name__)
API = "https://api.minecraftservices.com/minecraft/profile"


def load_png(url: str) -> Image.Image:
    d = CACHE / "skins"
    d.mkdir(exist_ok=True)
    f = d / (hashlib.sha1(url.encode()).hexdigest() + ".png")
    if not f.exists():
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        f.write_bytes(r.content)
    return Image.open(f).convert("RGBA")


def _fix_legacy(s: Image.Image) -> Image.Image:
    if s.height != 32:
        return s
    n = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    n.paste(s, (0, 0))
    flip = lambda b: s.crop(b).transpose(Image.FLIP_LEFT_RIGHT)
    n.paste(flip((4, 20, 8, 32)), (20, 52)); n.paste(flip((12, 20, 16, 32)), (28, 52))
    n.paste(flip((44, 20, 48, 32)), (36, 52)); n.paste(flip((52, 20, 56, 32)), (44, 52))
    return n


def render(skin: Image.Image, slim=False, cape=None, view="front", scale=10) -> Image.Image:
    s = _fix_legacy(skin.convert("RGBA"))
    aw = 3 if slim else 4
    k = 1 if slim else 0
    if view == "front":
        b = dict(head=(8, 8, 16, 16), hat=(40, 8, 48, 16), body=(20, 20, 28, 32), jacket=(20, 36, 28, 48),
                 rleg=(4, 20, 8, 32), rpants=(4, 36, 8, 48), lleg=(20, 52, 24, 64), lpants=(4, 52, 8, 64),
                 rarm=(44, 20, 44 + aw, 32), rsl=(44, 36, 44 + aw, 48), larm=(36, 52, 36 + aw, 64), lsl=(52, 52, 52 + aw, 64))
    else:
        b = dict(head=(24, 8, 32, 16), hat=(56, 8, 64, 16), body=(32, 20, 40, 32), jacket=(32, 36, 40, 48),
                 rleg=(12, 20, 16, 32), rpants=(12, 36, 16, 48), lleg=(28, 52, 32, 64), lpants=(12, 52, 16, 64),
                 rarm=(52 - k, 20, 52 - k + aw, 32), rsl=(52 - k, 36, 52 - k + aw, 48),
                 larm=(44 - k, 52, 44 - k + aw, 64), lsl=(60 - k, 52, 60 - k + aw, 64))
    cv = Image.new("RGBA", (20, 32), (0, 0, 0, 0))
    ox = 2

    def put(keys, pos):
        for key in keys:
            cv.alpha_composite(s.crop(b[key]), (pos[0] + ox, pos[1]))

    put(["head", "hat"], (4, 0))
    put(["body", "jacket"], (4, 8))
    if view == "front":
        put(["rarm", "rsl"], (4 - aw, 8)); put(["larm", "lsl"], (12, 8))
        put(["rleg", "rpants"], (4, 20)); put(["lleg", "lpants"], (8, 20))
    else:
        put(["larm", "lsl"], (4 - aw, 8)); put(["rarm", "rsl"], (12, 8))
        put(["lleg", "lpants"], (4, 20)); put(["rleg", "rpants"], (8, 20))
        if cape is not None:
            cv.alpha_composite(cape.convert("RGBA").crop((1, 1, 11, 17)), (5, 8))
    return cv.resize((20 * scale, 32 * scale), Image.NEAREST)


def _hdr(token): return {"Authorization": f"Bearer {token}"}


def upload_skin(token: str, path: str, variant: str = "classic") -> None:
    with open(path, "rb") as fh:
        r = requests.post(f"{API}/skins", headers=_hdr(token), data={"variant": variant},
                          files={"file": ("skin.png", fh, "image/png")}, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Skin upload failed ({r.status_code}): {r.text[:200]}")


def set_cape(token: str, cape_id) -> None:
    if cape_id:
        r = requests.put(f"{API}/capes/active", headers=_hdr(token), json={"capeId": cape_id}, timeout=20)
    else:
        r = requests.delete(f"{API}/capes/active", headers=_hdr(token), timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"Cape change failed ({r.status_code}): {r.text[:200]}")
