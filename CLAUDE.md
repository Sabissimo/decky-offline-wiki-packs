# Offline Wiki Packs

Decky Loader (Steam Deck) plugin: download a game's PCGamingWiki page while online, read it offline from the Quick Access menu.

## Commands

```bash
npm ci                        # install (npm, not pnpm; lockfile is package-lock.json)
npm run build                 # rollup: src/index.tsx -> dist/index.js
python3 -m py_compile main.py # backend syntax check (no test suite yet)
```

CI (`.github/workflows/build.yml`) runs the build + syntax check on push/PR, assembles the plugin zip, uploads it as an artifact, and attaches it to a Release on `v*` tags.

## Architecture

- `main.py` — backend, pure stdlib. Resolves Steam appid → PCGamingWiki page via the MediaWiki cargo API (`Infobox_game.Steam_AppID`), fetches rendered HTML with `action=parse`, strips scripts/images/external links, stores each pack as JSON under `DECKY_PLUGIN_SETTINGS_DIR/packs/`.
- `src/index.tsx` — frontend renders the stored (sanitized) HTML in the QAM panel; installed games enumerated from `appmanifest_*.acf` across all Steam libraries.

## Status and Deck-runtime facts (live-debugged on real hardware, 2026-07-15)

Working end-to-end on the user's Deck: game list, selection, download,
offline reading. Hard-won facts — do not regress:

- Backend paths use `decky.DECKY_USER_HOME`, never `expanduser("~")` (the
  backend doesn't run as the deck user; the scan silently found nothing).
- `_fetch` loads the SteamOS CA bundle explicitly (Decky's embedded Python
  can't verify HTTPS otherwise) and falls back to system curl on
  403/429/503: Cloudflare TLS-fingerprints the embedded Python. The curl
  call scrubs the loader's pyinstaller `LD_LIBRARY_PATH` (poisons curl
  with an incompatible libssl) and uses the absolute path (plugin env has
  no PATH).
- On the Deck, closing a dropdown's full-screen menu REMOUNTS the QAM
  content and resets useState — the selected game lives at module scope
  (`rememberedAppId`). The download button is always rendered (disabled
  until a pick); a conditionally-rendered control can silently never
  appear.
- `note()` callable logs frontend breadcrumbs to the backend log — the QAM
  has no visible console; keep it for future debugging.

Remaining cosmetic risk: wide wiki tables/infoboxes may overflow the
narrow panel; width-constraining CSS if it bothers.

## Releasing

Bump the version in `package.json`, push, then tag `v*` and push the tag separately (a tag pushed together with the branch may not trigger CI).
