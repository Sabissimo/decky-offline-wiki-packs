# 📖 Offline Wiki Packs

**Take the wiki with you.** Download a game's wiki page while you're online,
read it later from the Quick Access menu — on the plane, in the tent, on the
train, wherever the internet isn't.

- 🎮 One tap to grab the wiki for the **game you're playing right now**
- 📚 Or pick any **installed game** from a list
- 📴 Read saved packs **fully offline**, without leaving your game
- 🗑 Delete packs when you're done

Wiki content comes from [PCGamingWiki](https://www.pcgamingwiki.com) —
fixes, settings, save locations, and known issues for almost every PC game.

## How to use

1. While online: open Decky → **Offline Wiki Packs**
2. Tap **Get wiki for <current game>** (or pick a game from the dropdown)
3. Later, offline: open the same panel and tap any saved pack to read it

## Installation

Not on the Decky store yet. To install:

1. In Decky settings, enable **Developer mode**
2. In the **Developer** tab, choose **Install Plugin from URL** and paste:

   ```
   https://github.com/Sabissimo/decky-offline-wiki-packs/releases/latest/download/decky-offline-wiki-packs.zip
   ```

## Roadmap

- More sources (game-specific Fandom/wiki.gg wikis, full multi-page packs)
- Images in packs (downloaded and embedded)
- Search within a saved pack

<details>
<summary>🛠 For developers</summary>

The Python backend resolves a Steam appid to a PCGamingWiki page via the
MediaWiki cargo API (`Infobox_game.Steam_AppID`), fetches rendered HTML with
`action=parse`, strips scripts/images/links for safe offline rendering, and
stores each pack as JSON under `DECKY_PLUGIN_SETTINGS_DIR/packs/`.

The frontend renders stored HTML in the panel; installed games are
enumerated from `appmanifest_*.acf` across all Steam libraries.

```bash
npm install   # or pnpm i
npm run build # outputs dist/index.js
```

</details>

## License

MIT
