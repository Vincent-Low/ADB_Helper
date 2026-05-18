// Module: Logcat
const LogcatModule = ({ ctx }) => {
  const { activeDevice, toast } = ctx;
  const [exports, setExports] = React.useState([
    { name: "logcat_15.03.26_14.32_GMT-7.txt", size: "2.1 MB", when: "2 minutes ago" },
    { name: "logcat_15.03.26_09.17_GMT-7.txt", size: "847 KB", when: "5 hours ago" },
    { name: "logcat_14.03.26_22.04_GMT-7.txt", size: "3.4 MB", when: "Yesterday" },
    { name: "logcat_14.03.26_18.51_GMT-7.txt", size: "1.2 MB", when: "Yesterday" },
  ]);
  const [running, setRunning] = React.useState(false);

  const doExport = () => {
    if (!activeDevice) return;
    setRunning(true);
    setTimeout(() => {
      const now = new Date();
      const dd = String(now.getDate()).padStart(2, "0");
      const mm = String(now.getMonth() + 1).padStart(2, "0");
      const yy = String(now.getFullYear()).slice(-2);
      const hh = String(now.getHours()).padStart(2, "0");
      const mi = String(now.getMinutes()).padStart(2, "0");
      const tz = -now.getTimezoneOffset() / 60;
      const fname = `logcat_${dd}.${mm}.${yy}_${hh}.${mi}_GMT${tz >= 0 ? "+" : ""}${tz}.txt`;
      const size = (Math.random() * 3 + 0.3).toFixed(1) + " MB";
      setExports(e => [{ name: fname, size, when: "just now" }, ...e]);
      setRunning(false);
      toast({ kind: "success", title: "Logcat exported", msg: fname });
    }, 1400);
  };

  if (!activeDevice) return <NoDeviceEmpty label="Logcat" />;

  return (
    <div className="v-stack" style={{ gap: "var(--gap)" }}>
      <div className="card">
        <div className="card-head"><h3>Export Logcat Buffer</h3></div>
        <div className="card-body" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div className="v-stack" style={{ gap: 10 }}>
            <div className="text-secondary" style={{ fontSize: 12, lineHeight: 1.55 }}>
              Dumps the current logcat buffer of <strong style={{ color: "var(--text-primary)" }}>{activeDevice.model}</strong> ({activeDevice.serial}) to a timestamped file in your logcat folder.
            </div>
            <div style={{
              padding: "10px 12px", background: "var(--bg-elev)", borderRadius: 4,
              fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-secondary)",
              border: "1px solid var(--border)",
            }}>
              $ adb -s {activeDevice.serial} logcat -d &gt;<br />
              &nbsp;&nbsp;~/logcat/logcat_DD.MM.YY_HH.mm_GMT±N.txt
            </div>
            <div className="h-stack" style={{ gap: 8 }}>
              <button className="btn primary" onClick={doExport} disabled={running} style={{ flex: 1 }}>
                {running
                  ? <><span className="spinner" />Exporting…</>
                  : <><Icon name="download" size={14} /> Export logcat</>}
              </button>
              <button className="btn icon-only" title="Open folder"><Icon name="folder" size={14} /></button>
            </div>
          </div>

          <div className="v-stack" style={{ gap: 0 }}>
            <div className="text-muted" style={{ fontSize: 11, marginBottom: 6, fontWeight: 500, letterSpacing: 0.04, textTransform: "uppercase" }}>Configuration</div>
            <div className="info-section" style={{ border: "1px solid var(--border)", borderRadius: 4, background: "var(--surface-2)" }}>
              <div className="info-row"><div className="k">Save folder</div><div className="v mono">~/.config/adb_helper/logcat/</div></div>
              <div className="info-row"><div className="k">Filename</div><div className="v mono">logcat_&lt;date&gt;_&lt;time&gt;_GMT±N.txt</div></div>
              <div className="info-row"><div className="k">Mode</div><div className="v mono">Single-shot (-d flag)</div></div>
              <div className="info-row"><div className="k">Timezone</div><div className="v mono">GMT{-new Date().getTimezoneOffset() / 60 >= 0 ? "+" : ""}{-new Date().getTimezoneOffset() / 60}</div></div>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h3>Recent Exports</h3>
          <div className="head-actions">
            <span className="tag">{exports.length} files</span>
            <button className="btn sm ghost"><Icon name="folder" size={12} /> Open folder</button>
          </div>
        </div>
        <table className="table">
          <thead>
            <tr><th>Filename</th><th style={{ width: 100 }}>Size</th><th style={{ width: 140 }}>Exported</th><th style={{ width: 100 }}></th></tr>
          </thead>
          <tbody>
            {exports.map((e, i) => (
              <tr key={i} onClick={() => toast({ kind: "info", title: "Opening", msg: e.name })}>
                <td className="mono" style={{ color: "var(--text-secondary)" }}>{e.name}</td>
                <td className="mono muted">{e.size}</td>
                <td className="muted">{e.when}</td>
                <td style={{ textAlign: "right" }}>
                  <button className="btn sm icon-only ghost" onClick={(ev) => ev.stopPropagation()}><Icon name="copy" size={11} /></button>
                  <button className="btn sm icon-only ghost" onClick={(ev) => ev.stopPropagation()}><Icon name="trash" size={11} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

window.LogcatModule = LogcatModule;
