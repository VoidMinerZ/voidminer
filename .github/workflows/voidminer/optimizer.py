"""Performance modes, JVM flags, options.txt tuning and recommendations.
Nothing here fakes numbers: it only produces settings; real usage is measured from the game process."""
from __future__ import annotations
import logging, shutil
from pathlib import Path

log = logging.getLogger(__name__)

MODES = {
    "potato": dict(label="Potato", ram=1536, render=4, sim=5, particles=2, graphics=0, fps=120, entity=0.5,
                   biome=0, mip=0, ao=False, clouds=False, gc_threads=True,
                   desc="Absolute minimum visuals and memory. For 4 GB machines or weak CPUs."),
    "low": dict(label="Low-End", ram=2048, render=6, sim=6, particles=2, graphics=0, fps=144, entity=0.6,
                biome=1, mip=0, ao=False, clouds=False, gc_threads=True,
                desc="Tuned for dual-core laptops with Intel HD graphics and 8 GB RAM."),
    "balanced": dict(label="Balanced", ram=3072, render=10, sim=8, particles=1, graphics=0, fps=200, entity=0.8,
                     biome=2, mip=2, ao=True, clouds=True, gc_threads=False,
                     desc="Good looks with solid FPS on mid-range PCs."),
    "high": dict(label="High FPS", ram=4096, render=12, sim=10, particles=1, graphics=0, fps=260, entity=1.0,
                 biome=2, mip=2, ao=True, clouds=True, gc_threads=False,
                 desc="Uncapped frame rate, fast graphics, more RAM for modern CPUs/GPUs."),
    "custom": dict(label="Custom", desc="You choose render distance, particles, graphics and FPS limit."),
}
MODE_ORDER = ["potato", "low", "balanced", "high", "custom"]
DEFAULT_CUSTOM = dict(render=8, sim=8, particles=1, graphics=0, fps=200)

_FAB = {
    "potato": ["sodium", "lithium", "ferrite-core", "entityculling", "immediatelyfast", "modernfix", "dynamic-fps", "sodium-extra"],
    "low": ["sodium", "lithium", "ferrite-core", "entityculling", "immediatelyfast", "modernfix", "dynamic-fps", "sodium-extra"],
    "balanced": ["sodium", "lithium", "ferrite-core", "entityculling", "modernfix", "sodium-extra"],
    "high": ["sodium", "lithium", "immediatelyfast", "entityculling", "modernfix", "sodium-extra"],
}
_FORGE = {
    "potato": ["embeddium", "ferrite-core", "entityculling", "immediatelyfast", "modernfix", "dynamic-fps"],
    "low": ["embeddium", "ferrite-core", "entityculling", "immediatelyfast", "modernfix", "dynamic-fps"],
    "balanced": ["embeddium", "ferrite-core", "entityculling", "modernfix"],
    "high": ["embeddium", "immediatelyfast", "entityculling", "modernfix"],
}


def perf_mods(mode: str, loader: str) -> list[str]:
    if loader == "vanilla":
        return []
    key = "balanced" if mode == "custom" else mode
    return list((_FAB if loader in ("fabric", "quilt") else _FORGE)[key])


def conf_for(profile) -> dict:
    if profile.mode == "custom":
        c = dict(MODES["balanced"])
        c.update({**DEFAULT_CUSTOM, **(profile.custom or {})})
        return c
    return dict(MODES.get(profile.mode, MODES["low"]))


def effective_ram(profile, settings, info) -> int:
    total = int((info or {}).get("ram_gb", 8) * 1024)
    hi = max(1024, int(total * 0.6))
    ram = profile.ram_mb or settings.get("ram_mb") or conf_for(profile).get("ram", 2048)
    return max(1024, min(int(ram), hi)) // 256 * 256


def build_jvm_args(profile, settings, info) -> list[str]:
    conf = conf_for(profile)
    ram = effective_ram(profile, settings, info)
    args = [f"-Xms{min(1024, ram)}M", f"-Xmx{ram}M",
            "-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=50",
            "-XX:+UnlockExperimentalVMOptions", "-XX:+DisableExplicitGC",
            "-XX:G1NewSizePercent=20", "-XX:G1ReservePercent=20", "-XX:G1HeapRegionSize=8M",
            "-XX:+PerfDisableSharedMem", "-XX:-UsePerfData"]
    if conf.get("gc_threads"):
        args += ["-XX:ParallelGCThreads=2", "-XX:ConcGCThreads=1"]
    for extra in (settings.get("jvm_args"), profile.jvm_args):
        if extra and extra.strip():
            args += extra.split()
    return args


def tweaks(conf: dict) -> dict:
    return {
        "renderDistance": conf["render"], "simulationDistance": conf["sim"], "particles": conf["particles"],
        "graphicsMode": conf["graphics"], "fancyGraphics": str(conf["graphics"] > 0).lower(),
        "maxFps": conf["fps"], "enableVsync": "false",
        "entityDistanceScaling": conf.get("entity", 1.0), "entityShadows": "false" if conf["render"] <= 8 else "true",
        "biomeBlendRadius": conf.get("biome", 1), "mipmapLevels": conf.get("mip", 0),
        "ao": str(conf.get("ao", False)).lower(), "renderClouds": "true" if conf.get("clouds") else "false",
    }


def apply_options(instance_dir: Path, conf: dict) -> Path | None:
    """Merge tuned values into options.txt, keeping every other key. Backs up the original once."""
    f = Path(instance_dir) / "options.txt"
    bak = f.with_name("options.txt.voidminer.bak")
    lines = f.read_text("utf-8", errors="replace").splitlines() if f.exists() else []
    if f.exists() and not bak.exists():
        shutil.copy2(f, bak)
    new = tweaks(conf)
    seen = set()
    out = []
    for ln in lines:
        k = ln.split(":", 1)[0]
        if k in new:
            out.append(f"{k}:{new[k]}")
            seen.add(k)
        else:
            out.append(ln)
    out += [f"{k}:{v}" for k, v in new.items() if k not in seen]
    f.write_text("\n".join(out) + "\n", "utf-8")
    return bak if bak.exists() else None


def recommendations(info: dict | None, conf: dict) -> list[str]:
    r = []
    if "render" in conf:
        r.append(f"Render distance {conf['render']} chunks, simulation distance {conf['sim']} chunks.")
        r.append("Particles: " + ["All", "Decreased", "Minimal"][conf["particles"]] +
                 ", graphics: " + ["Fast", "Fancy", "Fabulous"][min(2, conf["graphics"])] +
                 f", FPS limit {conf['fps'] if conf['fps'] < 260 else 'unlimited'}.")
    if info:
        if not info["dedicated_gpu"]:
            r.append("Integrated GPU detected: it shares system RAM, so keep Minecraft below ~50% of total RAM and "
                     "update the Intel graphics driver (large OpenGL gains).")
        if info["cores"] <= 2:
            r.append("Dual-core CPU: close browsers/launchers while playing; keep render distance low; "
                     "capping FPS avoids thermal throttling on laptops.")
    r.append("Keep V-Sync off in-game and plug in the laptop (Windows power plan: High performance).")
    return r
