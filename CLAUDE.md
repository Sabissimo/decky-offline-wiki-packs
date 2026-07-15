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

## Status and known risks

Never run on real hardware yet. Riskiest assumption to verify on-Deck first: rendering arbitrary wiki HTML inside the narrow QAM panel (tables/infoboxes may overflow; may need width-constraining CSS).

## Releasing

Bump the version in `package.json`, push, then tag `v*` and push the tag separately (a tag pushed together with the branch may not trigger CI).
