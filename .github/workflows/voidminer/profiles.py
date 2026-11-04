from __future__ import annotations
import json, logging, re, shutil, time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from .optimizer import DEFAULT_CUSTOM
from .paths import INSTANCES

log = logging.getLogger(__name__)
LOADERS = ["vanilla", "fabric", "quilt", "forge", "neoforge"]


@dataclass
class Profile:
    id: str
    name: str
    mc_version: str
    loader: str = "vanilla"
    loader_version: str = ""
    version_id: str = ""
    ram_mb: int = 0
    java_path: str = ""
    jvm_args: str = ""
    mode: str = "low"
    custom: dict = field(default_factory=lambda: dict(DEFAULT_CUSTOM))
    created: float = 0.0
    last_played: float = 0.0
    tweaks_applied: bool = False

    @property
    def dir(self) -> Path:
        return INSTANCES / self.id

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.dir / "profile.json.tmp"
        tmp.write_text(json.dumps(asdict(self), indent=2), "utf-8")
        tmp.replace(self.dir / "profile.json")


class ProfileManager:
    def all(self) -> list[Profile]:
        out = []
        for d in sorted(INSTANCES.iterdir()):
            f = d / "profile.json"
            if f.is_file():
                try:
                    data = json.loads(f.read_text("utf-8"))
                    names = {x.name for x in fields(Profile)}
                    out.append(Profile(**{k: v for k, v in data.items() if k in names}))
                except Exception:
                    log.exception("Skipping unreadable profile %s (left untouched)", f)
        out.sort(key=lambda p: p.created)
        return out

    def get(self, pid: str):
        return next((p for p in self.all() if p.id == pid), None)

    def save(self, p: Profile) -> None:
        p.save()

    def _unique_name(self, name: str, exclude: str = "") -> str:
        used = {p.name.lower() for p in self.all() if p.id != exclude}
        base, n = name.strip() or "Profile", 2
        cand = base
        while cand.lower() in used:
            cand = f"{base} {n}"
            n += 1
        return cand

    def _unique_id(self, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "profile"
        cand, n = slug, 2
        while (INSTANCES / cand).exists():
            cand = f"{slug}-{n}"
            n += 1
        return cand

    def create(self, name, mc_version, loader="vanilla", mode="low") -> Profile:
        name = self._unique_name(name)
        p = Profile(id=self._unique_id(name), name=name, mc_version=mc_version, loader=loader, mode=mode,
                    created=time.time())
        (p.dir / "mods").mkdir(parents=True, exist_ok=True)
        p.save()
        return p

    def rename(self, p: Profile, name: str) -> None:
        p.name = self._unique_name(name, p.id)
        p.save()

    def duplicate(self, p: Profile) -> Profile:
        name = self._unique_name(p.name + " copy")
        new_id = self._unique_id(name)
        dst = INSTANCES / new_id
        try:
            shutil.copytree(p.dir, dst)
        except Exception:
            shutil.rmtree(dst, ignore_errors=True)
            raise
        q = Profile(**{**asdict(p), "id": new_id, "name": name, "created": time.time(), "last_played": 0.0})
        q.save()
        return q

    def delete(self, p: Profile) -> None:
        d = p.dir.resolve()
        if INSTANCES.resolve() not in d.parents:
            raise RuntimeError("Refusing to delete outside the instances folder")
        shutil.rmtree(d)
