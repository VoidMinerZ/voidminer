"""Microsoft -> Xbox -> XSTS -> Minecraft authentication via minecraft-launcher-lib (PKCE, no passwords handled).
Refresh tokens live in the Windows Credential Manager (keyring); they are never written to disk in plain text."""
from __future__ import annotations
import json, logging, os, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from .paths import ROOT

log = logging.getLogger(__name__)
SERVICE = "VoidMiner"


class AccountError(Exception):
    pass


def _kr():
    try:
        import keyring
        return keyring
    except Exception:
        return None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        if "code" in q or "error" in q:
            self.server.result = q
            self.server.done.set()
        body = (b"<html><body style='background:#06070D;color:#EAF0FF;font-family:Segoe UI;text-align:center;"
                b"padding-top:20vh'><h1>VoidMiner Client</h1><p>Sign-in complete. You can close this tab.</p></body></html>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class AccountManager:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.path = ROOT / "accounts.json"
        self._mem_tokens: dict[str, str] = {}
        self._cache: dict[str, tuple[float, dict]] = {}
        self.data = {"active": "", "accounts": []}
        try:
            if self.path.exists():
                self.data = json.loads(self.path.read_text("utf-8"))
        except Exception:
            log.exception("accounts.json unreadable")

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2), "utf-8")
        tmp.replace(self.path)

    def _set_token(self, uuid: str, token: str) -> None:
        self._mem_tokens[uuid] = token
        kr = _kr()
        if kr:
            try:
                kr.set_password(SERVICE, uuid, token)
            except Exception:
                log.exception("keyring unavailable; token kept in memory only")

    def _get_token(self, uuid: str):
        kr = _kr()
        if kr:
            try:
                t = kr.get_password(SERVICE, uuid)
                if t:
                    return t
            except Exception:
                log.exception("keyring read failed")
        return self._mem_tokens.get(uuid)

    def _remember(self, d: dict) -> None:
        meta = {"uuid": d["id"], "name": d["name"], "skins": d.get("skins", []), "capes": d.get("capes", [])}
        accs = [a for a in self.data["accounts"] if a["uuid"] != meta["uuid"]]
        accs.append(meta)
        self.data["accounts"] = accs
        self._save()
        self._set_token(d["id"], d["refresh_token"])

    def list(self) -> list[dict]:
        return self.data["accounts"]

    def active(self):
        a = next((x for x in self.list() if x["uuid"] == self.data.get("active")), None)
        return a or (self.list()[0] if self.list() else None)

    def set_active(self, uuid: str) -> None:
        self.data["active"] = uuid
        self._save()

    def client_id(self) -> str:
        return (self.settings.get("client_id") or os.environ.get("VOIDMINER_CLIENT_ID") or "").strip()

    def login(self, status=lambda s: None) -> dict:
        from minecraft_launcher_lib import microsoft_account as ma
        cid = self.client_id()
        if not cid:
            raise AccountError("No Microsoft client ID configured. Open Accounts and paste your Azure app's client ID.")
        server = None
        for port in range(8765, 8776):
            try:
                server = HTTPServer(("127.0.0.1", port), _Handler)
                break
            except OSError:
                continue
        if not server:
            raise AccountError("Could not open a local port (8765-8775) for the sign-in callback.")
        server.done, server.result = threading.Event(), {}
        threading.Thread(target=server.serve_forever, daemon=True).start()
        redirect = f"http://localhost:{port}"
        try:
            url, state, verifier = ma.get_secure_login_data(cid, redirect)
            status("Waiting for Microsoft sign-in in your browser...")
            webbrowser.open(url)
            if not server.done.wait(300):
                raise AccountError("Sign-in timed out.")
        finally:
            server.shutdown()
            server.server_close()
        q = server.result
        if "error" in q:
            raise AccountError(q.get("error_description", q["error"]))
        if q.get("state") != state:
            raise AccountError("Sign-in state mismatch (possible tampering). Try again.")
        status("Authenticating with Xbox Live and Minecraft services...")
        data = self._complete(lambda: ma.complete_login(cid, None, redirect, q["code"], verifier))
        self._remember(data)
        self.set_active(data["id"])
        self._cache[data["id"]] = (time.time(), data)
        return data

    def _complete(self, fn) -> dict:
        try:
            return fn()
        except Exception as e:  # noqa
            name = type(e).__name__
            if "NotOwn" in name:
                raise AccountError("This Microsoft account does not own Minecraft: Java Edition.") from e
            msg = str(e)
            if "403" in msg or "Invalid app registration" in msg:
                raise AccountError("Minecraft services rejected this Azure app (403 / invalid app registration). "
                                   "New Azure apps must be approved by Mojang first - see README, section "
                                   "'Microsoft sign-in'.") from e
            raise AccountError(f"{name}: {msg}") from e

    def session(self, uuid: str, force: bool = False) -> dict:
        """Fresh Minecraft session (access_token, name, id, skins, capes). Refreshes at most every 20 minutes."""
        from minecraft_launcher_lib import microsoft_account as ma
        c = self._cache.get(uuid)
        if c and not force and time.time() - c[0] < 1200:
            return c[1]
        token = self._get_token(uuid)
        if not token:
            raise AccountError("Saved sign-in not found. Please sign in again.")
        cid = self.client_id()
        if not cid:
            raise AccountError("No Microsoft client ID configured.")
        data = self._complete(lambda: ma.complete_refresh(cid, None, None, token))
        self._remember(data)
        self._cache[uuid] = (time.time(), data)
        return data

    def logout(self, uuid: str) -> None:
        kr = _kr()
        if kr:
            try:
                kr.delete_password(SERVICE, uuid)
            except Exception:
                pass
        self._mem_tokens.pop(uuid, None)
        self._cache.pop(uuid, None)
        self.data["accounts"] = [a for a in self.data["accounts"] if a["uuid"] != uuid]
        if self.data.get("active") == uuid:
            self.data["active"] = self.data["accounts"][0]["uuid"] if self.data["accounts"] else ""
        self._save()
