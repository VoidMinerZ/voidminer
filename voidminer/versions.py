from __future__ import annotations
import json, logging
from .paths import CACHE

log = logging.getLogger(__name__)


def fetch() -> tuple[list[dict], bool]:
    """Official Mojang version manifest. Falls back to the last cached copy when offline."""
    from minecraft_launcher_lib import utils
    cache = CACHE / "versions.json"
    try:
        raw = utils.get_version_list()
        data = [{"id": v["id"], "type": v["type"], "releaseTime": str(v.get("releaseTime", ""))} for v in raw]
        cache.write_text(json.dumps(data), "utf-8")
        return data, False
    except Exception:
        log.exception("version manifest fetch failed")
        if cache.exists():
            return json.loads(cache.read_text("utf-8")), True
        raise


def filter_versions(data, release=True, snapshot=False, old=False) -> list[str]:
    want = set()
    if release: want.add("release")
    if snapshot: want.add("snapshot")
    if old: want |= {"old_beta", "old_alpha"}
    return [v["id"] for v in data if v["type"] in want]


def latest_release(data) -> str | None:
    return next((v["id"] for v in data if v["type"] == "release"), None)


def loader_supported(loader: str, mc: str):
    """True/False from the loader's own metadata, None if it could not be verified."""
    if loader == "vanilla":
        return True
    try:
        from minecraft_launcher_lib import mod_loader
        return bool(mod_loader.get_mod_loader(loader).is_minecraft_version_supported(mc))
    except Exception:
        log.exception("loader support check failed")
        return None
