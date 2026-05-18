// Module: Installer
const InstallerModule = ({ ctx }) => {
  const { devices, toast } = ctx;
  const [files, setFiles] = React.useState(MOCK_INSTALL_FILES);
  const [selectedDevices, setSelectedDevices] = React.useState(new Set());
  const [running, setRunning] = React.useState(false);
  const [queue, setQueue] = React.useState([]); // [{file, device, state}]

  const onlineDevices = devices.filter(d => d.status === "online");
  const toggleDev = (s) => {
    const next = new Set(selectedDevices);
    if (next.has(s)) next.delete(s); else next.add(s);
    setSelectedDevices(next);
  };

  const startInstall = () => {
    if (!files.length || !selectedDevices.size) return;
    const targetDevs = onlineDevices.filter(d => selectedDevices.has(d.serial));
    const q = [];
    files.forEach(f => targetDevs.forEach(d => q.push({ file: f.name, device: d.model, state: "queued" })));
    setQueue(q);
    setRunning(true);
    // simulate
    let i = 0;
    const step = () => {
      if (i >= q.length) {
        setRunning(false);
        toast({ kind: "success", title: "Install complete", msg: `${q.length} operations finished` });
        return;
      }
      setQueue(prev => prev.map((it, idx) => idx === i ? { ...it, state: "running" } : it));
      setTimeout(() => {
        const success = Math.random() > 0.15;
        setQueue(prev => prev.map((it, idx) => idx === i ? { ...it, state: success ? "success" : "failed" } : it));
        i++;
        step();
      }, 900);
    };
    setTimeout(step, 200);
  };

  const removeFile = (idx) => setFiles(f => f.filter((_, i) => i !== idx));

  return (
    <div className="inst-grid">
      <div className="v-stack" style={{ gap: "var(--gap)", minHeight: 0, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <div className="card">
          <div className="card-head">
            <h3>Files to install</h3>
            <div className="head-actions">
              <span className="tag">{files.length} file{files.length !== 1 ? "s" : ""}</span>
              <button className="btn sm" onClick={() => {
                const names = ["app-debug-v0.9.1.apk", "split-config.arm64_v8a.apk", "module-pro.apkm"];
                const pick = names[Math.floor(Math.random() * names.length)];
                setFiles(f => [...f, { name: pick, size: +(Math.random() * 80 + 15).toFixed(1), type: pick.split('.').pop() }]);
              }}>
                <Icon name="plus" size={12} /> Add files
              </button>
            </div>
          </div>
          <div>
            {files.length === 0 ? (
              <div className="dropzone" style={{ margin: 14 }}>
                <Icon name="package" size={28} />
                <div className="big">Drop APK / APKS / XAPK / APKM</div>
                <div style={{ fontSize: 11, marginTop: 4 }}>or click "Add files" above</div>
              </div>
            ) : (
              files.map((f, i) => (
                <div key={i} className="file-row">
                  <div className="ficon">.{f.type}</div>
                  <div>
                    <div className="fname">{f.name}</div>
                    <div className="fmeta">{f.size} MB · {f.type.toUpperCase()} {f.type === "aab" ? "— unsupported" : ""}</div>
                  </div>
                  <button className="btn sm icon-only ghost x" onClick={() => removeFile(i)}>
                    <Icon name="x" size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>Target devices</h3>
            <div className="head-actions">
              <span className="tag">{selectedDevices.size} selected</span>
              <button className="btn sm ghost" onClick={() => {
                if (selectedDevices.size === onlineDevices.length) setSelectedDevices(new Set());
                else setSelectedDevices(new Set(onlineDevices.map(d => d.serial)));
              }}>{selectedDevices.size === onlineDevices.length ? "Clear" : "Select all"}</button>
            </div>
          </div>
          <div>
            {onlineDevices.map(d => (
              <div key={d.serial}
                   className="paired-row"
                   style={{ cursor: "pointer" }}
                   onClick={() => toggleDev(d.serial)}>
                <div className="cb" data-checked={selectedDevices.has(d.serial)} />
                <Icon name={d.connection === "wifi" ? "wifi" : "usb"} size={14} style={{ color: "var(--text-muted)" }} />
                <div>
                  <div className="alias">{d.model}</div>
                  <div className="ip">{d.serial}</div>
                </div>
                <span className="pill online" style={{ marginLeft: "auto" }}>online</span>
              </div>
            ))}
          </div>
        </div>

        <div className="h-stack" style={{ gap: 8 }}>
          <button
            className="btn primary"
            style={{ flex: 1, height: 38, minWidth: 0 }}
            disabled={!files.length || !selectedDevices.size || running}
            onClick={startInstall}>
            <Icon name="download" size={14} />
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {running ? "Installing…" : `Install · ${files.length} file${files.length !== 1 ? "s" : ""} → ${selectedDevices.size} device${selectedDevices.size !== 1 ? "s" : ""}`}
            </span>
          </button>
          <button className="btn" disabled={!running} onClick={() => setRunning(false)}>
            <Icon name="stop" size={12} /> Cancel
          </button>
        </div>
      </div>

      <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
        <div className="card-head">
          <h3>Installation queue</h3>
          <div className="head-actions">
            {queue.length > 0 && (
              <span className="tag">
                {queue.filter(q => q.state === "success").length}/{queue.length} done
              </span>
            )}
            <button className="btn sm ghost" onClick={() => setQueue([])} disabled={running || !queue.length}>
              <Icon name="x" size={11} /> Clear
            </button>
          </div>
        </div>

        {queue.length === 0 ? (
          <div className="empty-state" style={{ flex: 1 }}>
            <div className="es-ico"><Icon name="package" size={22} /></div>
            <h3>Nothing queued</h3>
            <p>Add files and pick at least one online device, then hit Install. Operations run sequentially per device and continue on others if one disconnects.</p>
          </div>
        ) : (
          <div className="scroll-y" style={{ flex: 1 }}>
            {/* progress summary */}
            <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
              <div className="h-stack" style={{ justifyContent: "space-between", marginBottom: 6 }}>
                <span className="text-secondary" style={{ fontSize: 12 }}>Overall progress</span>
                <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {queue.filter(q => q.state === "success" || q.state === "failed").length} / {queue.length}
                </span>
              </div>
              <div className="bar">
                <div className="fill" style={{ width: `${(queue.filter(q => q.state === "success" || q.state === "failed").length / queue.length) * 100}%` }} />
              </div>
            </div>
            {queue.map((q, i) => (
              <div key={i} className={`queue-item ${q.state === "running" ? "running" : ""}`}>
                <div>
                  <div className="qd">{q.device}</div>
                  <div className="qf">{q.file}</div>
                </div>
                <div className="qstate">
                  {q.state === "queued" && <span className="pill">Queued</span>}
                  {q.state === "running" && <span className="pill accent"><span className="pdot" />Installing…</span>}
                  {q.state === "success" && <span className="pill online"><Icon name="check" size={10} /> Installed</span>}
                  {q.state === "failed" && <span className="pill danger"><Icon name="x" size={10} /> Failed</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

window.InstallerModule = InstallerModule;
