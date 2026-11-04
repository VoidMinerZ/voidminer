from __future__ import annotations
import logging, queue, threading, time

log = logging.getLogger(__name__)
_Q: "queue.Queue" = queue.Queue()


def ui(fn, *a, **k) -> None:
    """Schedule fn on the Tk main thread."""
    _Q.put((fn, a, k))


def pump(root, interval: int = 120) -> None:
    try:
        while True:
            fn, a, k = _Q.get_nowait()
            try:
                fn(*a, **k)
            except Exception:
                log.exception("UI callback failed")
    except queue.Empty:
        pass
    root.after(interval, pump, root, interval)


def run_bg(work, on_done=None, on_error=None, name: str = "voidminer-task") -> None:
    def target():
        try:
            res = work()
        except Exception as e:  # noqa
            log.exception("Background task failed: %s", name)
            if on_error:
                ui(on_error, e)
        else:
            if on_done:
                ui(on_done, res)
    threading.Thread(target=target, name=name, daemon=True).start()


def make_callback(update) -> dict:
    """minecraft-launcher-lib callback dict -> update(status, fraction) on the UI thread (throttled)."""
    st = {"s": "", "m": 1, "v": 0, "t": 0.0}

    def push(force=False):
        now = time.monotonic()
        if force or now - st["t"] > 0.08:
            st["t"] = now
            ui(update, st["s"], min(1.0, max(0.0, st["v"] / st["m"] if st["m"] else 0)))

    def set_status(s): st["s"] = str(s); push(True)
    def set_progress(v): st["v"] = v; push()
    def set_max(m): st["m"] = m or 1; push(True)
    return {"setStatus": set_status, "setProgress": set_progress, "setMax": set_max}
