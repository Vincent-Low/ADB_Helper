// ====== ADB_Helper main App ======

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "dark",
  "accent": "teal",
  "density": "compact",
  "sidebar": "expanded",
  "statusBar": true
} /*EDITMODE-END*/;

const ACCENTS = {
  teal: { h: 180, c: 0.13 },
  green: { h: 145, c: 0.16 },
  blue: { h: 230, c: 0.16 },
  amber: { h: 75, c: 0.14 },
  pink: { h: 0, c: 0.16 }
};

const App = () => {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [activeModule, setActiveModule] = React.useState("connections");
  const [devices, setDevices] = React.useState(MOCK_DEVICES);
  const [activeSerial, setActiveSerial] = React.useState(MOCK_DEVICES[0].serial);
  const [paired, setPaired] = React.useState(MOCK_PAIRED);
  const [toasts, setToasts] = React.useState([]);
  const [infoRefreshKey, setInfoRefreshKey] = React.useState(0);
  const [appsRefreshKey, setAppsRefreshKey] = React.useState(0);

  const activeDevice = devices.find((d) => d.serial === activeSerial) || null;

  React.useEffect(() => {
    const root = document.documentElement;
    const t = tweaks.theme === "system" ? "dark" : tweaks.theme;
    root.setAttribute("data-theme", t);
    root.setAttribute("data-density", tweaks.density);
    const a = ACCENTS[tweaks.accent] || ACCENTS.teal;
    root.style.setProperty("--accent", `oklch(0.78 ${a.c} ${a.h})`);
    root.style.setProperty("--accent-soft", `oklch(0.78 ${a.c} ${a.h} / 0.15)`);
    root.style.setProperty("--accent-faint", `oklch(0.78 ${a.c} ${a.h} / 0.08)`);
  }, [tweaks.theme, tweaks.accent, tweaks.density]);

  const toast = React.useCallback((t) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { ...t, id }]);
    setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 3800);
  }, []);

  const disconnect = (serial) => {
    setDevices((prev) => prev.filter((d) => d.serial !== serial));
    if (activeSerial === serial) setActiveSerial(null);
    toast({ kind: "warn", title: "Device disconnected", msg: serial });
  };

  const ctx = {
    devices, setDevices,
    activeDevice, activeSerial, setActiveSerial,
    paired, setPaired,
    toast, disconnect,
    tweaks, setTweak
  };

  const renderModule = () => {
    switch (activeModule) {
      case "connections":return <ConnectionsModule ctx={ctx} />;
      case "terminal":return <TerminalModule ctx={ctx} />;
      case "installer":return <InstallerModule ctx={ctx} />;
      case "scrcpy":return <ScrcpyModule ctx={ctx} />;
      case "buttons":return <DeviceButtonsModule ctx={ctx} />;
      case "info":return <InfoModule ctx={ctx} key={infoRefreshKey} />;
      case "apps":return <AppsModule ctx={ctx} key={appsRefreshKey} />;
      case "logcat":return <LogcatModule ctx={ctx} />;
      case "settings":return <SettingsModule ctx={ctx} />;
      default:return null;
    }
  };

  const exportDeviceInfoTxt = () => {
    if (!activeDevice) {
      toast({ kind: "warn", title: "No active device", msg: "Select a device first" });
      return;
    }
    const fname = `device_info_${activeDevice.model.replace(/\s+/g, "_")}_${new Date().toISOString().slice(0, 10)}.txt`;
    toast({ kind: "success", title: "Device info exported", msg: fname });
  };

  const refreshDeviceInfo = () => {
    setInfoRefreshKey((k) => k + 1);
    toast({ kind: "info", title: "Refreshing device info", msg: activeDevice ? activeDevice.serial : "no device" });
  };

  const refreshApps = () => {
    setAppsRefreshKey((k) => k + 1);
    toast({ kind: "info", title: "Refreshing app list", msg: activeDevice ? activeDevice.serial : "no device" });
  };

  const exportAppsCsv = () => {
    if (!activeDevice) {
      toast({ kind: "warn", title: "No active device", msg: "Select a device first" });
      return;
    }
    const fname = `apps_${activeDevice.model.replace(/\s+/g, "_")}_${new Date().toISOString().slice(0, 10)}.csv`;
    toast({ kind: "success", title: "App list exported", msg: fname });
  };

  const collapsed = tweaks.sidebar === "collapsed";
  const allMods = [...MODULES, ...SECONDARY_MODULES];
  const currentMod = allMods.find((m) => m.id === activeModule);

  return (
    <>
      <div className="app-root">
        <div className="titlebar">
          <div className="traffic">
            <div className="tl r" /><div className="tl y" /><div className="tl g" />
          </div>
          <div className="title">ADB_Helper</div>
          <div className="right">
            <button title="Minimise"><Icon name="chevron_down" size={13} /></button>
            <button title="Maximise"><Icon name="square" size={11} /></button>
            <button title="Close"><Icon name="x" size={13} /></button>
          </div>
        </div>

        <div className="app-body">
          <aside className="sidebar" data-collapsed={collapsed}>
            <div className="sb-brand">
              <div className="logo">A_</div>
              <div className="name">ADB_Helper <span></span></div>
            </div>
            <nav className="sb-nav">
              <div className="sb-section-label">Workspace</div>
              {MODULES.map((m) =>
              <div key={m.id} className="sb-item"
              data-active={activeModule === m.id}
              onClick={() => setActiveModule(m.id)}
              title={collapsed ? m.label : ""}>
                  <Icon name={m.icon} className="ico" />
                  <span className="lbl">{m.label}</span>
                  {m.id === "connections" &&
                <span className="badge">{devices.filter((d) => d.status === "online").length}</span>
                }
                </div>
              )}
              <div className="sb-section-label">System</div>
              {SECONDARY_MODULES.map((m) =>
              <div key={m.id} className="sb-item"
              data-active={activeModule === m.id}
              onClick={() => setActiveModule(m.id)}
              title={collapsed ? m.label : ""}>
                  <Icon name={m.icon} className="ico" />
                  <span className="lbl">{m.label}</span>
                </div>
              )}
            </nav>
            <div className="sb-foot">
              <button className="collapse-btn"
              onClick={() => setTweak("sidebar", collapsed ? "expanded" : "collapsed")}>
                <Icon name="panel_left" size={14} />
                {!collapsed && <span>Collapse</span>}
              </button>
            </div>
          </aside>

          <main className="main">
            <div className="module-header" data-comment-anchor="6bb5d9424e-div-135-13">
              <h1>{currentMod?.label}</h1>
              <span className="crumb">/ {activeModule}</span>
              <div className="actions">
                {activeModule === "info" &&
                <>
                    <button className="btn sm" onClick={refreshDeviceInfo} title="Refresh all fields">
                      <Icon name="refresh" size={12} /> Refresh
                    </button>
                    <button className="btn sm" onClick={exportDeviceInfoTxt} title="Export to .txt">
                      <Icon name="download" size={12} /> Export TXT
                    </button>
                  </>
                }
                {activeModule === "apps" &&
                <>
                    <button className="btn sm" onClick={refreshApps} title="Reload installed apps">
                      <Icon name="refresh" size={12} /> Refresh
                    </button>
                    <button className="btn sm" onClick={exportAppsCsv} title="Export visible list to .csv">
                      <Icon name="download" size={12} /> Export CSV
                    </button>
                  </>
                }
              </div>
            </div>
            <div className="module-body" key={activeModule}>
              {renderModule()}
            </div>
          </main>
        </div>

        {tweaks.statusBar &&
        <div className="statusbar">
            <div className="sb-cell">
              <span className={`dot ${activeDevice?.status === "online" ? "online" : "offline"}`} />
              <span>ADB Server</span>
              <span style={{ color: "var(--text-muted)" }}>v35.0.2</span>
            </div>
            <div className="sep" />
            {activeDevice ?
          <>
                <div className="sb-cell">
                  <Icon name="smartphone" size={11} />
                  <span style={{ color: "var(--text-primary)" }}>{activeDevice.model}</span>
                  <span style={{ color: "var(--text-muted)" }}>· {activeDevice.serial}</span>
                </div>
                <div className="sep" />
                <div className="sb-cell">
                  <Icon name={activeDevice.connection === "wifi" ? "wifi" : "usb"} size={11} />
                  <span style={{ textTransform: "uppercase" }}>{activeDevice.connection}</span>
                </div>
              </> :

          <div className="sb-cell" style={{ color: "var(--text-muted)" }}>
                No active device · choose one in Connections
              </div>
          }
            <div className="right">
              <div className="sb-cell">
                <span>{devices.filter((d) => d.status === "online").length} online</span>
              </div>
              <div className="sb-cell" style={{ color: "var(--text-muted)" }}>
                logs: ~/adb_helper/logs/adb_helper_{new Date().toISOString().slice(0, 10)}.log
              </div>
            </div>
          </div>
        }
      </div>

      {/* Toasts */}
      <div className="toast-wrap">
        {toasts.map((t) =>
        <div key={t.id} className={`toast ${t.kind || ""}`}>
            <Icon name={t.kind === "error" ? "warn" : t.kind === "warn" ? "warn" : t.kind === "success" ? "check" : "info"} className="ti" />
            <div>
              <div className="tt">{t.title}</div>
              {t.msg && <div className="tm mono">{t.msg}</div>}
            </div>
          </div>
        )}
      </div>

      {/* Tweaks panel — self-managed (toggled by toolbar) */}
      <TweaksPanel title="Tweaks">
        <TweakSection label="Appearance" />
        <TweakRadio label="Theme" value={tweaks.theme}
        options={[{ value: "dark", label: "Dark" }, { value: "light", label: "Light" }, { value: "system", label: "Auto" }]}
        onChange={(v) => setTweak("theme", v)} />
        <TweakColor label="Accent" value={accentColorFor(tweaks.accent)}
        options={Object.keys(ACCENTS).map(accentColorFor)}
        onChange={(v) => {
          const name = Object.keys(ACCENTS).find((k) => accentColorFor(k) === v) || "teal";
          setTweak("accent", name);
        }} />
        <TweakSection label="Layout" />
        <TweakRadio label="Density" value={tweaks.density}
        options={[{ value: "comfortable", label: "Comfy" }, { value: "compact", label: "Compact" }]}
        onChange={(v) => setTweak("density", v)} />
        <TweakRadio label="Sidebar" value={tweaks.sidebar}
        options={[{ value: "expanded", label: "Expanded" }, { value: "collapsed", label: "Icons" }]}
        onChange={(v) => setTweak("sidebar", v)} />
        <TweakToggle label="Status bar" value={tweaks.statusBar} onChange={(v) => setTweak("statusBar", v)} />
        <TweakSection label="Mock state" />
        <TweakSelect label="Active module" value={activeModule}
        options={allMods.map((m) => ({ value: m.id, label: m.label }))}
        onChange={(v) => setActiveModule(v)} />
        <TweakSelect label="Active device" value={activeSerial || ""}
        options={[{ value: "", label: "— none —" }, ...devices.map((d) => ({ value: d.serial, label: `${d.model} (${d.connection})` }))]}
        onChange={(v) => setActiveSerial(v || null)} />
      </TweaksPanel>
    </>);

};

// The accent options need to map name → color but display a single swatch.
// Since TweakColor expects color strings, give it color values keyed by name.
const accentColorFor = (name) => {
  const a = ACCENTS[name] || ACCENTS.teal;
  return `oklch(0.78 ${a.c} ${a.h})`;
};

ReactDOM.createRoot(document.getElementById("root")).render(<App />);