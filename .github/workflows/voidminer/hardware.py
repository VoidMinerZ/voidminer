from __future__ import annotations
import logging, os, platform, re, subprocess
import psutil

log = logging.getLogger(__name__)
_info: dict | None = None


def _ps(cmd: str) -> str:
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                       timeout=20, creationflags=0x08000000)
    return r.stdout


def get_info(refresh: bool = False) -> dict:
    global _info
    if _info and not refresh:
        return _info
    cpu, gpus = platform.processor() or "Unknown CPU", []
    if os.name == "nt":
        try:
            cpu = _ps("(Get-CimInstance Win32_Processor).Name").strip() or cpu
            gpus = [l.strip() for l in _ps("(Get-CimInstance Win32_VideoController).Name").splitlines() if l.strip()]
        except Exception:
            log.exception("hardware probe failed")
    dedicated = any(re.search(r"nvidia|geforce|rtx|gtx|radeon rx|radeon pro|arc a\d", g, re.I) for g in gpus)
    _info = dict(cpu=cpu, cores=psutil.cpu_count(logical=False) or 1, threads=psutil.cpu_count() or 1,
                 ram_gb=round(psutil.virtual_memory().total / 1024 ** 3, 1), gpus=gpus or ["Unknown GPU"],
                 dedicated_gpu=dedicated)
    return _info


def recommend_mode(i: dict) -> str:
    if i["ram_gb"] <= 4.5 or i["cores"] <= 1:
        return "potato"
    if not i["dedicated_gpu"] and (i["cores"] <= 2 or i["ram_gb"] <= 8.5):
        return "low"
    if not i["dedicated_gpu"]:
        return "balanced"
    return "high" if i["ram_gb"] >= 15 else "balanced"
