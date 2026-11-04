"""Mod manager backed by the Modrinth API (official, trusted source; checksums verified)."""
from __future__ import annotations
import hashlib, json, logging, os, tempfile
from pathlib import Path
import requests
from .paths import APP_VERSION

log = logging.getLogger(__name__)
API = "https://api.modrinth.com/v2"
_S = requests.Session()
_S.headers["User-Agent"] = f"VoidMiner/{APP_VERSION} (desktop launcher)"
KNOWN_CONFLICTS = [("sodium", "optifine"), ("embeddium", "optifine"), ("sodium", "embeddium"),
                   ("sodium", "rubidium"), ("embeddium", "rubidium"), ("iris", "optifine"),
                   ("lithium", "canary"), ("lithium", "radium")]


class ModError(Exception):
    pass


def loaders_for(loader: str) -> list[str]:
    return ["quilt", "fabric"] if loader == "quilt" else [loader]


def _get(path, **params):
    r = _S.get(API + path, params=params, timeout=20)
    if r.status_code == 404:
        raise ModError("Not found on Modrinth")
    r.raise_for_status()
    return r.json()


def search(query, mc, loader, offset=0, limit=20):
    facets = [["project_type:mod"], [f"versions:{mc}"], [f"categories:{l}" for l in loaders_for(loader)]]
    return _get("/search", query=query, facets=json.dumps(facets), limit=limit, offset=offset,
                index="relevance" if query else "downloads")["hits"]


def project_versions(project, mc, loader):
    vs = _get(f"/project/{project}/version", loaders=json.dumps(loaders_for(loader)), game_versions=json.dumps([mc]))
    vs.sort(key=lambda v: {"release": 0, "beta": 1, "alpha": 2}.get(v.get("version_type"), 3))  # stable sort
    return vs


def _idx_path(d): return Path(d) / "voidminer_mods.json"


def _load(d) -> dict:
    try:
        return json.loads(_idx_path(d).read_text("utf-8"))
    except Exception:
        return {"mods": {}}


def _save(d, idx) -> None:
    tmp = _idx_path(d).with_suffix(".tmp")
    tmp.write_text(json.dumps(idx, indent=2), "utf-8")
    tmp.replace(_idx_path(d))


def _sha1(p) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def _download(url, target: Path, sha1):
    if target.exists() and sha1 and _sha1(target) == sha1:
        return
    fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".part")
    os.close(fd)
    try:
        h = hashlib.sha1()
        with _S.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(tmp, "wb") as out:
                for chunk in r.iter_content(65536):
                    out.write(chunk)
                    h.update(chunk)
        if sha1 and h.hexdigest() != sha1:
            raise ModError("Checksum mismatch - download discarded")
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def install(inst_dir, mc, loader, project, version=None, status=None, _seen=None, _depth=0):
    """Install a mod (+ its required dependencies). Returns (installed_titles, warnings)."""
    seen = _seen if _seen is not None else set()
    proj = _get(f"/project/{project}")
    pid = proj["id"]
    if pid in seen:
        return [], []
    seen.add(pid)
    ver = version
    if ver is None:
        vs = project_versions(pid, mc, loader)
        if not vs:
            raise ModError(f"{proj['title']}: no version for Minecraft {mc} ({loader})")
        ver = vs[0]
    files = ver["files"]
    f = next((x for x in files if x.get("primary")), files[0])
    mods_dir = Path(inst_dir) / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)
    if status:
        status(f"Downloading {proj['title']}")
    _download(f["url"], mods_dir / f["filename"], f.get("hashes", {}).get("sha1"))
    installed, warns, req, inc = [proj["title"]], [], [], []
    for d in ver.get("dependencies", []):
        typ, did = d.get("dependency_type"), d.get("project_id")
        if not did:
            continue
        if typ == "incompatible":
            inc.append(did)
        elif typ == "required":
            req.append(did)
            if did in _load(inst_dir)["mods"] or did in seen or _depth >= 4:
                continue
            dv = None
            if d.get("version_id"):
                try:
                    dv = _get(f"/version/{d['version_id']}")
                except Exception:
                    dv = None
            try:
                i2, w2 = install(inst_dir, mc, loader, did, dv, status, seen, _depth + 1)
                installed += i2
                warns += w2
            except ModError as e:
                warns.append(f"Required dependency failed: {e}")
    idx = _load(inst_dir)
    old = idx["mods"].get(pid)
    if old and old["file"] != f["filename"]:
        for suffix in ("", ".disabled"):
            try:
                (mods_dir / (old["file"] + suffix)).unlink()
            except FileNotFoundError:
                pass
    idx["mods"][pid] = dict(slug=proj["slug"], title=proj["title"], version_id=ver["id"],
                            version_number=ver["version_number"], file=f["filename"], required=req, incompatible=inc)
    _save(inst_dir, idx)
    return installed, warns


def list_installed(inst_dir) -> list[dict]:
    mods_dir = Path(inst_dir) / "mods"
    if not mods_dir.is_dir():
        return []
    by_file = {m["file"]: (pid, m) for pid, m in _load(inst_dir)["mods"].items()}
    out = []
    for f in sorted(mods_dir.iterdir(), key=lambda x: x.name.lower()):
        n = f.name
        if n.endswith(".jar"):
            enabled, base = True, n
        elif n.endswith(".jar.disabled"):
            enabled, base = False, n[:-9]
        else:
            continue
        pid, m = by_file.get(base, (None, None))
        out.append(dict(file=n, base=base, enabled=enabled, project_id=pid, managed=bool(m),
                        title=m["title"] if m else base, version=m["version_number"] if m else "manual file",
                        slug=m["slug"] if m else base.lower(),
                        required=m.get("required", []) if m else [], incompatible=m.get("incompatible", []) if m else []))
    return out


def set_enabled(inst_dir, item, enable: bool) -> None:
    d = Path(inst_dir) / "mods"
    src, dst = d / item["file"], d / (item["base"] if enable else item["base"] + ".disabled")
    if src != dst:
        src.rename(dst)


def remove(inst_dir, item) -> None:
    (Path(inst_dir) / "mods" / item["file"]).unlink(missing_ok=True)
    idx = _load(inst_dir)
    if item.get("project_id") in idx["mods"]:
        del idx["mods"][item["project_id"]]
        _save(inst_dir, idx)


def conflicts(items) -> list[str]:
    act = [i for i in items if i["enabled"]]
    ids = {i["project_id"]: i["title"] for i in act if i["project_id"]}
    w = []
    for i in act:
        for x in i["incompatible"]:
            if x in ids:
                w.append(f"{i['title']} is marked incompatible with {ids[x]}.")
        for r in i["required"]:
            if r not in ids:
                w.append(f"{i['title']} needs a dependency that is missing or disabled (id {r}).")
    keys = [(i["slug"] + " " + i["base"]).lower() for i in act]
    for a, b in KNOWN_CONFLICTS:
        if any(a in k for k in keys) and any(b in k for k in keys):
            w.append(f"Known conflict: {a} and {b} should not be used together.")
    return w


def perf_status(inst_dir, slugs) -> set:
    have = {i["slug"] for i in list_installed(inst_dir) if i["enabled"]}
    return {s for s in slugs if s in have}
