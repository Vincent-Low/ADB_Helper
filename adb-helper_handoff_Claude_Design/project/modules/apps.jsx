// Module: Apps
const AppsModule = ({ ctx }) => {
  const { activeDevice, toast } = ctx;
  const [apps, setApps] = React.useState(MOCK_APPS);
  const [query, setQuery] = React.useState("");
  const [showSystem, setShowSystem] = React.useState(true);
  const [showDisabled, setShowDisabled] = React.useState(true);
  const [filter, setFilter] = React.useState("all");
  const [selected, setSelected] = React.useState(new Set());
  const [confirm, setConfirm] = React.useState(null);

  if (!activeDevice) return <NoDeviceEmpty label="Apps" />;

  const filtered = apps.filter((a) => {
    if (!showSystem && a.type === "system") return false;
    if (!showDisabled && a.status === "disabled") return false;
    if (filter === "user" && a.type !== "user") return false;
    if (filter === "system" && a.type !== "system") return false;
    const q = query.toLowerCase();
    return !q || a.name.toLowerCase().includes(q) || a.pkg.toLowerCase().includes(q);
  });

  const allSelected = filtered.length > 0 && filtered.every((a) => selected.has(a.pkg));
  const toggleAll = () => {
    if (allSelected) setSelected(new Set());else
    setSelected(new Set(filtered.map((a) => a.pkg)));
  };
  const toggleOne = (pkg) => {
    const next = new Set(selected);
    if (next.has(pkg)) next.delete(pkg);else next.add(pkg);
    setSelected(next);
  };

  const selectedApps = apps.filter((a) => selected.has(a.pkg));
  const anySystemSelected = selectedApps.some((a) => a.type === "system");
  const allDisabled = selectedApps.length > 0 && selectedApps.every((a) => a.status === "disabled");
  const allActive = selectedApps.length > 0 && selectedApps.every((a) => a.status === "active");

  const doAction = (kind) => {
    setApps((prev) => prev.map((a) => {
      if (!selected.has(a.pkg)) return a;
      if (kind === "uninstall" && a.type === "system") return a;
      if (kind === "uninstall") return null;
      if (kind === "disable") return { ...a, status: "disabled" };
      if (kind === "enable") return { ...a, status: "active" };
      return a;
    }).filter(Boolean));
    setSelected(new Set());
    setConfirm(null);
    const labels = { uninstall: "uninstalled", disable: "disabled", enable: "enabled" };
    toast({ kind: "success", title: `${selectedApps.length} app${selectedApps.length !== 1 ? "s" : ""} ${labels[kind]}` });
  };

  const ramTotal = activeDevice.ramTotal || 8192;
  const ramAvail = activeDevice.ramAvail || 3072;
  const ramUsed = ramTotal - ramAvail;
  const stTotal = activeDevice.storageTotal || 128000;
  const stAvail = activeDevice.storageAvail || 51200;
  const stUsed = stTotal - stAvail;

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", height: "100%", minHeight: 0 }}>
      <div className="usage-bars">
        <div className="usage-bar">
          <div className="top">
            <span className="lbl">RAM</span>
            <span className="val">Used {(ramUsed / 1024).toFixed(1)} GB / {(ramTotal / 1024).toFixed(1)} GB</span>
          </div>
          <div className="bar"><div className={`fill ${ramUsed / ramTotal > 0.85 ? "warn" : ""}`} style={{ width: `${ramUsed / ramTotal * 100}%` }} /></div>
        </div>
        <div className="usage-bar">
          <div className="top">
            <span className="lbl">Storage (/data)</span>
            <span className="val">Used {(stUsed / 1024).toFixed(1)} GB / {(stTotal / 1024).toFixed(1)} GB</span>
          </div>
          <div className="bar"><div className={`fill ${stUsed / stTotal > 0.85 ? "warn" : ""}`} style={{ width: `${stUsed / stTotal * 100}%` }} /></div>
        </div>
      </div>

      <div className="apps-toolbar">
        <div className="search">
          <Icon name="search" size={14} className="ico" />
          <input className="input" placeholder="Search by name or package…" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="seg">
          <button data-active={filter === "all"} onClick={() => setFilter("all")}>All</button>
          <button data-active={filter === "user"} onClick={() => setFilter("user")}>User</button>
          <button data-active={filter === "system"} onClick={() => setFilter("system")}>System</button>
        </div>
        <label className="h-stack" style={{ gap: 6, fontSize: 11, color: "var(--text-secondary)", cursor: "pointer" }}>
          <div className="cb" data-checked={showSystem} onClick={() => setShowSystem((s) => !s)} />
          Show system
        </label>
        <label className="h-stack" style={{ gap: 6, fontSize: 11, color: "var(--text-secondary)", cursor: "pointer" }}>
          <div className="cb" data-checked={showDisabled} onClick={() => setShowDisabled((s) => !s)} />
          Show disabled
        </label>
        <div style={{ marginLeft: "auto" }} className="h-stack">
          <span className="tag">{filtered.length} apps · {selected.size} selected</span>
          {selected.size > 0 &&
          <>
              <button className="btn sm danger"
            disabled={anySystemSelected}
            title={anySystemSelected ? "System apps can only be disabled" : ""}
            onClick={() => setConfirm({ kind: "uninstall", apps: selectedApps })}>
                <Icon name="trash" size={12} /> Uninstall
              </button>
              <button className="btn sm" disabled={!allActive}
            onClick={() => setConfirm({ kind: "disable", apps: selectedApps })}>
                Disable
              </button>
              <button className="btn sm" disabled={!allDisabled}
            onClick={() => setConfirm({ kind: "enable", apps: selectedApps })}>
                Enable
              </button>
            </>
          }
          <button className="btn sm ghost" data-comment-anchor="c729428fc9-button-118-11" style={{ display: "none" }} aria-hidden="true"></button>
          <button className="btn sm ghost icon-only" data-comment-anchor="68e5faadcb-button-119-11" style={{ display: "none" }} aria-hidden="true"></button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto" }}>
        <table className="table">
          <thead>
            <tr>
              <th style={{ width: 36 }}><div className="cb" data-checked={allSelected} onClick={toggleAll} /></th>
              <th>App Name</th>
              <th>Package</th>
              <th style={{ width: 110 }}>Type</th>
              <th style={{ width: 110 }}>Size</th>
              <th style={{ width: 110 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((a) =>
            <tr key={a.pkg}
            data-selected={selected.has(a.pkg)}
            className={a.status === "disabled" ? "row-disabled" : ""}
            onClick={() => toggleOne(a.pkg)}>
                <td><div className="cb" data-checked={selected.has(a.pkg)} /></td>
                <td>
                  <span style={{ fontWeight: 500 }}>{a.name}</span>
                </td>
                <td className="mono muted">{a.pkg}</td>
                <td><span className="pill">{a.type}</span></td>
                <td className="mono muted">{a.size} MB</td>
                <td>
                  {a.status === "active" ?
                <span className="pill online"><span className="pdot" />Active</span> :
                <span className="pill"><span className="pdot" />Disabled</span>}
                </td>
              </tr>
            )}
            {filtered.length === 0 &&
            <tr><td colSpan={6} style={{ textAlign: "center", padding: 40, color: "var(--text-muted)" }}>No apps match the current filter.</td></tr>
            }
          </tbody>
        </table>
      </div>

      {confirm &&
      <div className="modal-overlay" onClick={() => setConfirm(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="mhead">
              <h3>
                {confirm.kind === "uninstall" && "Uninstall apps?"}
                {confirm.kind === "disable" && "Disable apps?"}
                {confirm.kind === "enable" && "Enable apps?"}
              </h3>
            </div>
            <div className="mbody">
              <div style={{ marginBottom: 12 }}>
                {confirm.kind === "uninstall" && <>This will run <span className="tag">pm uninstall --user 0</span> for each app, sequentially. Only APK files can be backed up — app data cannot be saved without root.</>}
                {confirm.kind === "disable" && <>This will run <span className="tag">pm disable-user --user 0</span> for each app.</>}
                {confirm.kind === "enable" && <>This will run <span className="tag">pm enable</span> for each app.</>}
              </div>
              <div style={{ maxHeight: 120, overflow: "auto", border: "1px solid var(--border)", borderRadius: 4, padding: 8, background: "var(--surface-2)" }}>
                {confirm.apps.map((a) =>
              <div key={a.pkg} className="mono" style={{ fontSize: 11, padding: "2px 0", color: "var(--text-secondary)" }}>
                    {a.name} <span style={{ color: "var(--text-muted)" }}>— {a.pkg}</span>
                  </div>
              )}
              </div>
            </div>
            <div className="mfoot">
              <button className="btn ghost" onClick={() => setConfirm(null)}>Cancel</button>
              {confirm.kind === "uninstall" &&
            <button className="btn" onClick={() => doAction("uninstall")}>Back up & uninstall</button>
            }
              <button className={`btn primary ${confirm.kind === "uninstall" ? "danger" : ""}`}
            style={confirm.kind === "uninstall" ? { background: "var(--danger)", color: "#fff", boxShadow: "none" } : {}}
            onClick={() => doAction(confirm.kind)}>
                {confirm.kind === "uninstall" ? "Uninstall" : confirm.kind === "disable" ? "Disable" : "Enable"}
              </button>
            </div>
          </div>
        </div>
      }
    </div>);

};

window.AppsModule = AppsModule;