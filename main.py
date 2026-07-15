import glob
import json
import os
import re
import shutil
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request

import decky

PACKS_DIR = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "packs")
API = "https://www.pcgamingwiki.com/w/api.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# The backend runs as root under Decky, so expanduser("~") is /root and the
# Steam library silently comes up empty. Decky provides the real user home.
USER_HOME = (
    getattr(decky, "DECKY_USER_HOME", None)
    or getattr(decky, "HOME", None)
    or "/home/deck"
)
STEAM_ROOT = os.path.join(USER_HOME, ".local", "share", "Steam")
SKIP_NAME_PREFIXES = ("Proton", "Steam Linux Runtime", "Steamworks Common")


def _ssl_context() -> ssl.SSLContext:
    """Decky's bundled Python has OpenSSL default CA paths that don't exist
    on SteamOS - load the system bundle explicitly or HTTPS dies with
    CERTIFICATE_VERIFY_FAILED."""
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca"):
        return ctx  # default verify paths worked (dev machines)
    for cafile in (
        os.environ.get("SSL_CERT_FILE"),
        "/etc/ssl/certs/ca-certificates.crt",  # SteamOS / Arch
        "/etc/ssl/cert.pem",
    ):
        if cafile and os.path.isfile(cafile):
            try:
                ctx.load_verify_locations(cafile)
                return ctx
            except ssl.SSLError:
                continue
    return ctx


_SSL_CONTEXT = _ssl_context()


def _curl_fetch(url: str, timeout: int = 20) -> str:
    """System-curl fallback for Cloudflare bot blocks. Decky's embedded
    Python gets TLS-fingerprinted (403); SteamOS curl passes. Plugin
    subprocesses inherit the loader's pyinstaller LD_LIBRARY_PATH (curl
    would load the wrong libssl and die) and have no PATH - scrub the env
    and use the absolute path."""
    curl = shutil.which("curl") or (
        "/usr/bin/curl" if os.path.isfile("/usr/bin/curl") else None
    )
    if not curl:
        raise OSError("curl not available")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME")
    }
    proc = subprocess.run(
        [
            curl, "-sL", "--compressed", "--max-time", str(timeout),
            "-A", HEADERS["User-Agent"],
            "-H", f"Accept: {HEADERS['Accept']}",
            url,
        ],
        capture_output=True,
        timeout=timeout + 10,
        env=env,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", errors="replace").strip()[:200]
        raise OSError(f"curl exit {proc.returncode}: {detail}")
    return proc.stdout.decode("utf-8", "replace")


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429, 503):
            try:
                return _curl_fetch(url)
            except Exception as curl_err:
                raise OSError(
                    f"HTTP {e.code}; curl fallback failed: "
                    f"{type(curl_err).__name__}: {curl_err}"
                ) from None
        raise


def _sanitize(html: str) -> str:
    # Offline viewer: drop scripts, remote images, and dead links
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<img[^>]*>", "", html, flags=re.I)
    html = re.sub(r'href="[^"]*"', "", html)
    return html


def _pack_path(appid) -> str:
    return os.path.join(PACKS_DIR, "%s.json" % int(appid))


class Plugin:
    async def list_installed(self):
        """Installed games (appid + name) from Steam appmanifests."""
        games = []
        libs = [os.path.join(STEAM_ROOT, "steamapps")]
        vdf = os.path.join(libs[0], "libraryfolders.vdf")
        try:
            with open(vdf, "r", encoding="utf-8", errors="replace") as f:
                for p in re.findall(r'"path"\s+"([^"]+)"', f.read()):
                    sp = os.path.join(p, "steamapps")
                    if os.path.isdir(sp) and sp not in libs:
                        libs.append(sp)
        except OSError:
            pass
        for lib in libs:
            for acf in glob.glob(os.path.join(lib, "appmanifest_*.acf")):
                try:
                    with open(acf, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                except OSError:
                    continue
                name_m = re.search(r'"name"\s+"([^"]*)"', text)
                appid_m = re.search(r'"appid"\s+"(\d+)"', text)
                if not name_m or not appid_m:
                    continue
                name = name_m.group(1)
                if name.startswith(SKIP_NAME_PREFIXES):
                    continue
                games.append({"appid": int(appid_m.group(1)), "name": name})
        games.sort(key=lambda g: g["name"].lower())
        return games

    async def download_pack(self, appid, name):
        try:
            # Resolve PCGamingWiki page title from the Steam appid
            where = urllib.parse.quote('Infobox_game.Steam_AppID HOLDS "%d"' % int(appid))
            q = (
                f"{API}?action=cargoquery&tables=Infobox_game"
                f"&fields=Infobox_game._pageName%3DPage&where={where}&format=json"
            )
            rows = json.loads(_fetch(q)).get("cargoquery", [])
            title = rows[0]["title"]["Page"] if rows else name

            parse_url = (
                f"{API}?action=parse&page={urllib.parse.quote(title)}"
                f"&prop=text&redirects=1&format=json"
            )
            data = json.loads(_fetch(parse_url))
            if "error" in data:
                return {"ok": False, "error": data["error"].get("info", "page not found")}

            os.makedirs(PACKS_DIR, exist_ok=True)
            pack = {
                "appid": int(appid),
                "name": name,
                "title": data["parse"]["title"],
                "source": "PCGamingWiki",
                "html": _sanitize(data["parse"]["text"]["*"]),
            }
            with open(_pack_path(appid), "w", encoding="utf-8") as f:
                json.dump(pack, f)
            return {"ok": True, "title": pack["title"]}
        except Exception as e:
            decky.logger.exception("download_pack failed")
            return {"ok": False, "error": str(e)}

    async def list_packs(self):
        packs = []
        for path in glob.glob(os.path.join(PACKS_DIR, "*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    p = json.load(f)
                packs.append({"appid": p["appid"], "name": p["name"], "title": p["title"]})
            except (OSError, ValueError, KeyError):
                continue
        packs.sort(key=lambda p: p["name"].lower())
        return packs

    async def get_pack(self, appid):
        try:
            with open(_pack_path(appid), "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    async def delete_pack(self, appid):
        try:
            os.remove(_pack_path(appid))
        except OSError:
            pass

    async def note(self, msg):
        """Frontend breadcrumb -> backend log. The QAM has no visible
        console, so UI-side events are invisible without this."""
        decky.logger.info("ui: %s", msg)

    async def _main(self):
        decky.logger.info("Offline Wiki Packs loaded")

    async def _unload(self):
        decky.logger.info("Offline Wiki Packs unloaded")
