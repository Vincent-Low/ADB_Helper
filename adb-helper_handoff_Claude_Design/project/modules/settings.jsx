// Module: Settings
const SettingsModule = ({ ctx }) => {
  const { toast, tweaks, setTweak } = ctx;

  const DEPS = [
  { name: "ADB (platform-tools)", installed: "35.0.2", latest: "35.0.2", status: "ok" },
  { name: "scrcpy", installed: "4.0", latest: "4.0", status: "ok" },
  { name: "bundletool", installed: "1.17.0", latest: "1.17.2", status: "update" },
  { name: "JRE 17 (Adoptium)", installed: "17.0.10", latest: "—", status: "ok", bundled: true }];


  return (
    <div className="v-stack" style={{ gap: "var(--gap)" }}>
      <div className="card">
        <div className="card-head"><h3>About</h3></div>
        <div className="card-body" style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 16, alignItems: "center" }}>
          <div style={{
            width: 56, height: 56, borderRadius: 12,
            background: "linear-gradient(135deg, var(--accent), oklch(0.78 0.13 200))",
            display: "grid", placeItems: "center", color: "#051116", fontWeight: 700,
            fontFamily: "var(--font-mono)", fontSize: 22, letterSpacing: "-0.04em"
          }}>A_</div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600 }}>ADB_Helper</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 2 }}>
              Version <span className="mono">1.1.0</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Installed Dependencies</h3>
          <div className="head-actions">
            <button className="btn sm" data-comment-anchor="2bde07cc61-button-36-13"><Icon name="refresh" size={12} /> Check for updates</button>
          </div>
        </div>
        <div className="dep-row" style={{ background: "var(--bg-elev)", color: "var(--text-muted)", fontSize: 10, textTransform: "uppercase", letterSpacing: 0.05, fontWeight: 500, padding: "6px 14px" }}>
          <div>Component</div><div>Installed</div><div>Latest</div><div>Status</div><div></div>
        </div>
        {DEPS.map((d) =>
        <div key={d.name} className="dep-row">
            <div className="nm">{d.name} {d.bundled && <span className="tag" style={{ marginLeft: 6 }}>bundled</span>}</div>
            <div className="vr">{d.installed}</div>
            <div className="vr">{d.latest}</div>
            <div>
              {d.status === "ok" && <span className="pill online"><Icon name="check" size={10} /> Up to date</span>}
              {d.status === "update" && <span className="pill warn"><span className="pdot" />Update available</span>}
            </div>
            <div style={{ textAlign: "right" }}>
              <button className="btn sm" disabled={d.status === "ok"}
            onClick={() => toast({ kind: "success", title: `Updating ${d.name}`, msg: `${d.installed} → ${d.latest}` })}>
                <Icon name="download" size={11} /> Update
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head"><h3>General</h3></div>
        <div className="setting-row">
          <div>
            <div className="label">Theme</div>
            <div className="desc">Match system or override. Live preview applied.</div>
          </div>
          <div className="seg" style={{ justifySelf: "end" }}>
            <button data-active={tweaks.theme === "system"} onClick={() => setTweak("theme", "system")}>System</button>
            <button data-active={tweaks.theme === "light"} onClick={() => setTweak("theme", "light")}>Light</button>
            <button data-active={tweaks.theme === "dark"} onClick={() => setTweak("theme", "dark")}>Dark</button>
          </div>
        </div>
        <div className="setting-row">
          <div>
            <div className="label">Screenshots folder</div>
            <div className="desc">Default save location for captured screenshots.</div>
          </div>
          <div className="h-stack" style={{ justifySelf: "stretch" }}>
            <input className="input mono" defaultValue="~/.config/adb_helper/screenshots/" />
            <button className="btn icon-only"><Icon name="folder" size={13} /></button>
          </div>
        </div>
        <div className="setting-row">
          <div>
            <div className="label">Logcat folder</div>
            <div className="desc">Where logcat exports are saved.</div>
          </div>
          <div className="h-stack" style={{ justifySelf: "stretch" }}>
            <input className="input mono" defaultValue="~/.config/adb_helper/logcat/" />
            <button className="btn icon-only"><Icon name="folder" size={13} /></button>
          </div>
        </div>
        <div className="setting-row">
          <div>
            <div className="label">Application data folder</div>
            <div className="desc">Root directory for settings, database, logs, and bundled binaries.</div>
          </div>
          <div className="h-stack" style={{ justifySelf: "stretch" }}>
            <input className="input mono" defaultValue="~/.config/adb_helper/" readOnly />
            <button className="btn icon-only" title="Open data folder"><Icon name="folder" size={13} /></button>
          </div>
        </div>
        <div className="setting-row">
          <div>
            <div className="label">ADB command timeout</div>
            <div className="desc">Per-command timeout in seconds. Default 30.</div>
          </div>
          <input type="number" className="input mono" defaultValue={30} style={{ justifySelf: "end", width: 100 }} />
        </div>
        <div className="setting-row">
          <div>
            <div className="label">Log level</div>
            <div className="desc">Verbosity of session log files in ~/.config/adb_helper/logs/.</div>
          </div>
          <select className="select" defaultValue="Error" style={{ justifySelf: "end", width: 160 }}>
            <option>Debug</option><option>Info</option><option>Warning</option><option>Error</option>
          </select>
        </div>
      </div>
    </div>);

};

window.SettingsModule = SettingsModule;