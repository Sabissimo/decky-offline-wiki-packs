import {
  ButtonItem,
  DropdownItem,
  Field,
  PanelSection,
  PanelSectionRow,
  Router,
  staticClasses,
} from "@decky/ui";
import { callable, definePlugin, toaster } from "@decky/api";
import { useEffect, useState } from "react";
import { FaBookOpen } from "react-icons/fa";

interface Game {
  appid: number;
  name: string;
}

interface PackMeta {
  appid: number;
  name: string;
  title: string;
}

interface Pack extends PackMeta {
  source: string;
  html: string;
}

const listInstalled = callable<[], Game[]>("list_installed");
const downloadPack = callable<
  [number, string],
  { ok: boolean; title?: string; error?: string }
>("download_pack");
const listPacks = callable<[], PackMeta[]>("list_packs");
const getPack = callable<[number], Pack | null>("get_pack");
const deletePack = callable<[number], void>("delete_pack");

function Content() {
  const [games, setGames] = useState<Game[]>([]);
  const [packs, setPacks] = useState<PackMeta[]>([]);
  const [selected, setSelected] = useState<Game | null>(null);
  const [busy, setBusy] = useState(false);
  const [viewing, setViewing] = useState<Pack | null>(null);

  const [loadError, setLoadError] = useState("");

  const refresh = () =>
    listPacks()
      .then(setPacks)
      .catch((e) => setLoadError(String(e).slice(0, 140)));

  useEffect(() => {
    // Never swallow load failures: a dead backend must be visible, not an
    // empty panel that looks like "no games installed".
    listInstalled()
      .then(setGames)
      .catch((e) => setLoadError(String(e).slice(0, 140)));
    refresh();
  }, []);

  const download = async (game: Game) => {
    setBusy(true);
    try {
      const res = await downloadPack(game.appid, game.name);
      toaster.toast({
        title: "Offline Wiki Packs",
        body: res.ok
          ? `Saved "${res.title}" for offline reading`
          : `Failed: ${res.error}`,
      });
      refresh();
    } catch (e) {
      toaster.toast({
        title: "Offline Wiki Packs",
        body: `Download failed: ${String(e).slice(0, 140)}`,
      });
    } finally {
      setBusy(false);
    }
  };

  if (viewing) {
    return (
      <PanelSection title={viewing.title}>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => setViewing(null)}>
            ← Back to packs
          </ButtonItem>
        </PanelSectionRow>
        <div
          style={{
            fontSize: "12px",
            lineHeight: "1.4",
            overflowWrap: "break-word",
            padding: "0 8px",
          }}
          dangerouslySetInnerHTML={{ __html: viewing.html }}
        />
      </PanelSection>
    );
  }

  const running = Router.MainRunningApp;

  return (
    <>
      {loadError && (
        <PanelSection title="Backend not responding">
          <PanelSectionRow>
            <div style={{ fontSize: "0.85em", overflowWrap: "break-word" }}>
              {loadError} — restart Decky Loader; if it persists check
              homebrew/logs on the Deck.
            </div>
          </PanelSectionRow>
        </PanelSection>
      )}
      <PanelSection title="Download a pack">
        {running && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={busy}
              onClick={() =>
                download({
                  appid: Number(running.appid),
                  name: running.display_name,
                })
              }
            >
              {busy ? "Downloading..." : `Get wiki for ${running.display_name}`}
            </ButtonItem>
          </PanelSectionRow>
        )}
        <PanelSectionRow>
          <DropdownItem
            label="Installed game"
            rgOptions={games.map((g) => ({ data: g.appid, label: g.name }))}
            selectedOption={selected?.appid ?? null}
            onChange={(opt) =>
              setSelected(games.find((g) => g.appid === opt.data) ?? null)
            }
          />
        </PanelSectionRow>
        {selected && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={busy}
              onClick={() => download(selected)}
            >
              {busy ? "Downloading..." : `Download "${selected.name}" wiki`}
            </ButtonItem>
          </PanelSectionRow>
        )}
      </PanelSection>

      <PanelSection title={`Saved packs (${packs.length})`}>
        {packs.length === 0 && (
          <PanelSectionRow>
            <Field label="Nothing saved yet">
              download a pack while you're online
            </Field>
          </PanelSectionRow>
        )}
        {packs.map((p) => (
          <PanelSectionRow key={p.appid}>
            <ButtonItem
              layout="below"
              onClick={async () => {
                const pack = await getPack(p.appid).catch(() => null);
                if (pack) {
                  setViewing(pack);
                } else {
                  toaster.toast({
                    title: "Offline Wiki Packs",
                    body: "Pack file is missing or corrupt — download it again",
                  });
                }
              }}
            >
              📖 {p.name}
            </ButtonItem>
          </PanelSectionRow>
        ))}
        {packs.length > 0 && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={async () => {
                for (const p of packs) await deletePack(p.appid);
                refresh();
              }}
            >
              Delete all packs
            </ButtonItem>
          </PanelSectionRow>
        )}
      </PanelSection>
    </>
  );
}

export default definePlugin(() => ({
  name: "Offline Wiki Packs",
  titleView: <div className={staticClasses.Title}>Offline Wiki Packs</div>,
  content: <Content />,
  icon: <FaBookOpen />,
}));
