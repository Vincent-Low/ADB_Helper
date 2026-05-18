// Module: Terminal
const TerminalModule = ({ ctx }) => {
  const { activeDevice, toast } = ctx;
  const [lines, setLines] = React.useState(() => buildInitialLines(activeDevice));
  const [cmd, setCmd] = React.useState("");
  const [recording, setRecording] = React.useState(false);
  const [showHistory, setShowHistory] = React.useState(false);
  const [selectedMacro, setSelectedMacro] = React.useState(null);
  const [playing, setPlaying] = React.useState(null); // { name, step, total }
  const [histIdx, setHistIdx] = React.useState(-1);
  const screenRef = React.useRef(null);
  const histRef = React.useRef([...MOCK_HISTORY]);

  React.useEffect(() => {
    if (screenRef.current) screenRef.current.scrollTop = screenRef.current.scrollHeight;
  }, [lines]);

  const exec = (text) => {
    const newLines = [...lines, { kind: "input", text }];
    const resp = simulateCmd(text, activeDevice);
    resp.forEach(r => newLines.push(r));
    setLines(newLines);
    if (!histRef.current.includes(text)) histRef.current.unshift(text);
  };

  const onSubmit = (e) => {
    e.preventDefault();
    if (!cmd.trim()) return;
    exec(cmd.trim());
    setCmd("");
    setHistIdx(-1);
  };

  const onKey = (e) => {
    if (e.key === "ArrowUp") {
      e.preventDefault();
      const next = Math.min(histIdx + 1, histRef.current.length - 1);
      setHistIdx(next);
      setCmd(histRef.current[next] || "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.max(histIdx - 1, -1);
      setHistIdx(next);
      setCmd(next === -1 ? "" : histRef.current[next]);
    } else if (e.ctrlKey && e.key === "l") {
      e.preventDefault();
      setLines([]);
    }
  };

  const playMacro = (m) => {
    setPlaying({ name: m.name, step: 0, total: m.cmds });
    let step = 0;
    const tick = () => {
      step += 1;
      if (step > m.cmds) { setPlaying(null); toast({ kind: "success", title: `Macro complete: ${m.name}` }); return; }
      setPlaying({ name: m.name, step, total: m.cmds });
      setLines(prev => [...prev, { kind: "info", text: `→ macro step ${step}/${m.cmds}` }]);
      setTimeout(tick, 600);
    };
    setTimeout(tick, 400);
  };

  return (
    <div className="term-grid">
      <div className="card term-shell">
        <div className="card-head" style={{ padding: "8px 12px" }}>
          <Icon name="terminal" size={14} style={{ color: "var(--accent)" }} />
          <h3 style={{ textTransform: "none", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: 0 }}>
            adb shell · {activeDevice ? activeDevice.serial : "no device"}
          </h3>
          <div className="head-actions">
            {recording && (
              <span className="rec-indicator"><span className="rdot" /> Recording</span>
            )}
            {playing && (
              <span className="pill accent"><span className="pdot" />Playing {playing.step}/{playing.total}</span>
            )}
            <button className="btn sm ghost" onClick={() => setLines([])} title="Clear (Ctrl+L)">
              <Icon name="x" size={12} /> Clear
            </button>
            <button className="btn sm ghost" onClick={() => setShowHistory(true)}>
              <Icon name="logs" size={12} /> History
            </button>
          </div>
        </div>
        <div ref={screenRef} className="term-screen">
          {lines.map((l, i) => <TermLine key={i} line={l} device={activeDevice} />)}
          {lines.length === 0 && <div style={{ color: "var(--text-muted)" }}>{"// terminal cleared"}</div>}
        </div>
        <form className="term-input-row" onSubmit={onSubmit}>
          <span className="prompt">{activeDevice?.serial?.slice(0, 8) || "device"}:/$</span>
          <input
            autoFocus
            value={cmd}
            onChange={e => setCmd(e.target.value)}
            onKeyDown={onKey}
            placeholder="type a command and press enter — try: getprop ro.build.version.release"
          />
          <span className="kbd">↑</span>
          <span className="kbd">⏎</span>
        </form>
      </div>

      <div className="term-side">
        <div className="card">
          <div className="card-head">
            <h3>Macros</h3>
            <div className="head-actions">
              <button
                className="btn sm"
                style={recording ? { color: "var(--danger)", borderColor: "oklch(0.68 0.2 25 / 0.4)" } : {}}
                onClick={() => {
                  if (recording) {
                    setRecording(false);
                    toast({ kind: "success", title: "Macro saved", msg: "Captured 3 commands" });
                  } else {
                    setRecording(true);
                    toast({ kind: "info", title: "Recording macro…", msg: "Commands typed here will be captured" });
                  }
                }}
              >
                <Icon name={recording ? "stop" : "record"} size={11} /> {recording ? "Stop" : "Record"}
              </button>
            </div>
          </div>
          <div className="scroll-y" style={{ maxHeight: 280 }}>
            {MOCK_MACROS.map((m, i) => (
              <div key={i} className="macro-row" data-selected={selectedMacro === i}
                   onClick={() => setSelectedMacro(i)}
                   onDoubleClick={() => playMacro(m)}>
                <Icon name="play" size={11} className="play-ico" />
                <div>
                  <div className="mname">{m.name}</div>
                  <div className="mmeta">{m.cmds} commands · {m.last}</div>
                </div>
                <button className="btn sm icon-only ghost" onClick={(e) => { e.stopPropagation(); playMacro(m); }}>
                  <Icon name="play" size={11} />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="card flex-1" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div className="card-head">
            <h3>Shortcuts</h3>
          </div>
          <div className="card-body v-stack" style={{ gap: 8 }}>
            <div className="h-stack" style={{ justifyContent: "space-between" }}>
              <span className="text-secondary">Command history</span>
              <span><span className="kbd">↑</span> <span className="kbd">↓</span></span>
            </div>
            <div className="h-stack" style={{ justifyContent: "space-between" }}>
              <span className="text-secondary">Clear terminal</span>
              <span><span className="kbd">Ctrl</span> <span className="kbd">L</span></span>
            </div>
            <div className="h-stack" style={{ justifyContent: "space-between" }}>
              <span className="text-secondary">Stop running cmd</span>
              <span><span className="kbd">Ctrl</span> <span className="kbd">C</span></span>
            </div>
            <div className="h-stack" style={{ justifyContent: "space-between" }}>
              <span className="text-secondary">Autocomplete</span>
              <span><span className="kbd">Tab</span></span>
            </div>
            <div className="divider" />
            <div className="text-muted" style={{ fontSize: 11, lineHeight: 1.5 }}>
              Macros record only the commands you type — interactive stdin during execution is not captured. Playback runs on the current active device.
            </div>
          </div>
        </div>
      </div>

      {showHistory && (
        <div className="modal-overlay" onClick={() => setShowHistory(false)}>
          <div className="modal" style={{ width: 520 }} onClick={e => e.stopPropagation()}>
            <div className="mhead"><h3>Command History · last 50</h3></div>
            <div style={{ maxHeight: 360, overflow: "auto" }}>
              {histRef.current.map((h, i) => (
                <div key={i}
                     style={{
                       padding: "8px 18px",
                       borderBottom: "1px solid var(--border)",
                       fontFamily: "var(--font-mono)", fontSize: 12,
                       cursor: "pointer", color: "var(--text-secondary)",
                     }}
                     onClick={() => { setCmd(h); setShowHistory(false); }}
                     onMouseEnter={e => e.currentTarget.style.background = "var(--surface-2)"}
                     onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  {h}
                </div>
              ))}
            </div>
            <div className="mfoot">
              <button className="btn ghost" onClick={() => setShowHistory(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const TermLine = ({ line, device }) => {
  if (line.kind === "input") {
    return (
      <div className="term-line">
        <span className="user">root</span><span className="at">@</span>
        <span className="path">{device?.codename || "device"}</span>
        <span className="at">:</span><span className="path">/ $</span>{" "}
        <span className="cmd">{line.text}</span>
      </div>
    );
  }
  const cls = "out-" + (line.kind === "err" ? "err" : line.kind === "warn" ? "warn" : line.kind === "ok" ? "ok" : "info");
  return <div className="term-line"><span className={cls}>{line.text}</span></div>;
};

const buildInitialLines = (d) => ([
  { kind: "info", text: "ADB_Helper terminal · adb shell" },
  { kind: "info", text: `Connected to ${d?.model || "device"} (${d?.serial || "—"})` },
  { kind: "ok", text: "✓ shell session ready" },
  { kind: "input", text: "getprop ro.build.version.release" },
  { kind: "info", text: d?.android || "14" },
  { kind: "input", text: "dumpsys battery | grep level" },
  { kind: "info", text: `  level: ${d?.battery ?? 87}` },
  { kind: "input", text: "pm list packages -3 | wc -l" },
  { kind: "info", text: "47" },
]);

const simulateCmd = (cmd, d) => {
  const c = cmd.toLowerCase().trim();
  if (c.startsWith("clear")) return [];
  if (c.includes("getprop ro.build.version.release")) return [{ kind: "info", text: d?.android || "14" }];
  if (c.includes("getprop ro.product.model")) return [{ kind: "info", text: d?.model || "Pixel 7 Pro" }];
  if (c.includes("ro.product.manufacturer")) return [{ kind: "info", text: d?.manufacturer || "Google" }];
  if (c.startsWith("pm list packages")) return [
    { kind: "info", text: "package:com.android.chrome" },
    { kind: "info", text: "package:com.google.android.gm" },
    { kind: "info", text: "package:com.spotify.music" },
    { kind: "info", text: "package:com.Slack" },
    { kind: "info", text: "… 23 more" },
  ];
  if (c.startsWith("dumpsys battery")) return [
    { kind: "info", text: "Current Battery Service state:" },
    { kind: "info", text: `  AC powered: false` },
    { kind: "info", text: `  level: ${d?.battery ?? 87}` },
    { kind: "info", text: `  temperature: ${Math.round((d?.batTemp ?? 31.5) * 10)}` },
    { kind: "info", text: `  technology: ${d?.batTech || "Li-ion"}` },
  ];
  if (c.startsWith("wm density")) return [{ kind: "info", text: `Physical density: ${d?.dpi || 512}` }];
  if (c.startsWith("input keyevent")) return [{ kind: "ok", text: "✓ key event sent" }];
  if (c.startsWith("ls")) return [
    { kind: "info", text: "acct        dev        proc       storage    vendor" },
    { kind: "info", text: "apex        etc        product    sys" },
    { kind: "info", text: "bin         init.rc    sdcard     system" },
  ];
  if (c.startsWith("logcat")) return [
    { kind: "info", text: "--------- beginning of main" },
    { kind: "warn", text: "03-15 14:32:07.441 W ActivityManager: Slow operation: 412ms (so/foreground)" },
    { kind: "err", text: "03-15 14:32:07.522 E SQLiteLog: (14) cannot open file at line 33857 of [b65d23f9]" },
    { kind: "info", text: "(use -d to dump, -c to clear)" },
  ];
  if (c === "exit" || c === "logout") return [{ kind: "info", text: "session retained — close pane to exit" }];
  return [{ kind: "err", text: `sh: ${cmd.split(" ")[0]}: not found` }];
};

window.TerminalModule = TerminalModule;
