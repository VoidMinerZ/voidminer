import sys, traceback, logging
from voidminer.paths import setup_logging

def main():
    setup_logging()
    log = logging.getLogger("voidminer")
    sys.excepthook = lambda *a: log.critical("Unhandled", exc_info=a)
    try:
        from voidminer.ui.app import App
        App().mainloop()
    except Exception:
        log.exception("Fatal error")
        try:
            import tkinter.messagebox as mb
            mb.showerror("VoidMiner Client", "Fatal error:\n\n" + traceback.format_exc()[-1500:])
        except Exception:
            pass
        raise

if __name__ == "__main__":
    main()
