"""Installing versions/loaders/Java runtimes and starting the game (official Mojang data via minecraft-launcher-lib)."""
from __future__ import annotations
import json, logging, os, shutil, subprocess, time
from pathlib import Path
from . import optimizer
from .paths import APP_NAME, APP_VERSION

log = logging.getLogger(__name__)


class LaunchError(Exception):
    pass


def is_installed(mc_dir, vid: str) -> bool:
    return bool(vid) and (Path(mc_dir) / "versions" / vid / f"{vid}.json").exists()


def java_component(mc_dir, vid, depth=0):
    p = Path(mc_dir) / "versions" / vid / f"{vid}.json"
    if depth > 5 or not p.exists():
        return None
    d = json.loads(p.read_text("utf-8"))
    jv = d.get("javaVersion") or {}
    if jv.get("component"):
        return jv["component"]
    return java_component(mc_dir, d["inheritsFrom"], depth + 1) if d.get("inheritsFrom") else None


def ensure_java(mc_dir, vid, cb=None):
    """Mojang's bundled Java runtime for this version (downloaded once, never touches system Java)."""
    from minecraft_launcher_lib import runtime
    comp = java_component(mc_dir, vid)
    if not comp:
        return None
    exe = runtime.get_executable_path(comp, str(mc_dir))
    if not exe:
        runtime.install_jvm_runtime(comp, str(mc_dir), callback=cb)
        exe = runtime.get_executable_path(comp, str(mc_dir))
    return exe


def ensure_installed(p, pm, mc_dir, cb=None) -> str:
    from minecraft_launcher_lib import install, mod_loader
    if is_installed(mc_dir, p.version_id):
        return p.version_id
    mc = str(mc_dir)
    if p.loader == "vanilla":
        install.install_minecraft_version(p.mc_version, mc, callback=cb)
        vid = p.mc_version
    else:
        L = mod_loader.get_mod_loader(p.loader)
        if not L.is_minecraft_version_supported(p.mc_version):
            raise LaunchError(f"{L.get_name()} does not support Minecraft {p.mc_version}.")
        if not is_installed(mc_dir, p.mc_version):
            install.install_minecraft_version(p.mc_version, mc, callback=cb)
        java = ensure_java(mc_dir, p.mc_version, cb)
        vid = L.install(p.mc_version, mc, loader_version=p.loader_version or None, callback=cb, java=java)
    p.version_id = vid
    pm.save(p)
    return vid


def resolve_java(p, settings, mc_dir, cb=None) -> str:
    for cand in (p.java_path, settings.get("java_path")):
        if cand:
            if not Path(cand).exists():
                raise LaunchError(f"Configured Java not found: {cand}")
            return cand
    exe = ensure_java(mc_dir, p.version_id, cb)
    if exe:
        return exe
    found = shutil.which("javaw") or shutil.which("java")
    if not found:
        raise LaunchError("No Java found. Pick a Java executable in Settings.")
    return found


def build_command(p, session, settings, info, mc_dir, java_exe) -> list[str]:
    from minecraft_launcher_lib import command
    opts = {
        "username": session["name"], "uuid": session["id"], "token": session["access_token"],
        "executablePath": java_exe, "jvmArguments": optimizer.build_jvm_args(p, settings, info),
        "launcherName": APP_NAME, "launcherVersion": APP_VERSION, "gameDirectory": str(p.dir),
    }
    w, h = int(settings.get("width") or 0), int(settings.get("height") or 0)
    if w and h and not settings.get("fullscreen"):
        opts.update(customResolution=True, resolutionWidth=str(w), resolutionHeight=str(h))
    cmd = command.get_minecraft_command(p.version_id, str(mc_dir), opts)
    if settings.get("fullscreen"):
        cmd.append("--fullscreen")
    return cmd


def start(cmd, p, high_priority=True):
    logs = p.dir / "logs"
    logs.mkdir(exist_ok=True)
    log_path = logs / "voidminer-launch.log"
    safe = ["***" if i and cmd[i - 1] == "--accessToken" else a for i, a in enumerate(cmd)]
    with open(log_path, "wb") as lf:
        lf.write(("# " + " ".join(safe) + "\n").encode("utf-8", "replace"))
        proc = subprocess.Popen(cmd, cwd=str(p.dir), stdout=lf, stderr=subprocess.STDOUT,
                                creationflags=0x08000000 if os.name == "nt" else 0)
    if high_priority and os.name == "nt":
        try:
            import psutil
            psutil.Process(proc.pid).nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
        except Exception:
            log.warning("could not raise process priority")
    p.last_played = time.time()
    return proc, log_path


def tail(path, n=25) -> str:
    try:
        return "\n".join(Path(path).read_text("utf-8", errors="replace").splitlines()[-n:])
    except Exception:
        return ""
