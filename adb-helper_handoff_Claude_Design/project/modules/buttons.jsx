// Module: Device Buttons
const DeviceButtonsModule = ({ ctx }) => {
  const { activeDevice, toast } = ctx;
  const [pressed, setPressed] = React.useState(null);
  const [showReboot, setShowReboot] = React.useState(false);
  const [lastShot, setLastShot] = React.useState(null);

  const press = (label, key) => {
    setPressed(label);
    setTimeout(() => setPressed(null), 250);
    toast({ kind: "info", title: label, msg: `adb shell input keyevent ${key}` });
  };

  const takeScreenshot = () => {
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    setLastShot(`adb_helper_screenshot_${ts}.png`);
    toast({ kind: "success", title: "Screenshot saved", msg: `~/screenshots/adb_helper_screenshot_${ts}.png` });
  };

  const BTNS = [
    { l: "Home", k: "KEYCODE_HOME", i: "home" },
    { l: "Back", k: "KEYCODE_BACK", i: "arrow_left" },
    { l: "Recents", k: "KEYCODE_APP_SWITCH", i: "square" },
    { l: "Power", k: "KEYCODE_POWER", i: "power", danger: true },
    { l: "Vol +", k: "KEYCODE_VOLUME_UP", i: "vol_up" },
    { l: "Vol −", k: "KEYCODE_VOLUME_DOWN", i: "vol_down" },
    { l: "Mute", k: "KEYCODE_VOLUME_MUTE", i: "vol_mute" },
    { l: "Camera", k: "KEYCODE_CAMERA", i: "camera" },
    { l: "Rotate", k: "settings put system accelerometer_rotation", i: "rotate" },
    { l: "Screenshot", k: "screencap", i: "camera", action: takeScreenshot },
    { l: "Reboot", k: "adb reboot", i: "refresh", danger: true, action: () => setShowReboot(true) },
  ];

  return (
    <div className="dbtn-layout">
      <div className="card" style={{ display: "flex", flexDirection: "column" }}>
        <div className="card-head">
          <h3>Hardware & Software Keys</h3>
          <div className="head-actions">
            <span className="tag">
              {activeDevice ? `${activeDevice.model}` : "no device"}
            </span>
          </div>
        </div>
        <div className="dbtn-grid">
          {BTNS.map(b => (
            <button
              key={b.l}
              className={`dbtn ${b.danger ? "danger" : ""}`}
              onClick={() => b.action ? b.action() : press(b.l, b.k)}
              style={pressed === b.l ? { borderColor: "var(--accent)", background: "var(--accent-faint)", color: "var(--accent)" } : {}}
            >
              <Icon name={b.i} size={20} />
              <div className="lbl">{b.l}</div>
            </button>
          ))}
        </div>
        <div style={{ padding: "12px 14px", borderTop: "1px solid var(--border)", color: "var(--text-muted)", fontSize: 11, lineHeight: 1.5 }}>
          Most keys map to <span className="tag">adb shell input keyevent &lt;KEY&gt;</span>. Reboot, screenshot, and rotate run their own commands.
        </div>
      </div>

      <div className="card screenshot-preview" style={{ alignSelf: "start" }}>
        <div className="card-head" style={{ borderBottom: "none", padding: "6px 6px 10px" }}>
          <h3>Last screenshot</h3>
          <div className="head-actions">
            <button className="btn sm icon-only ghost" title="Open folder"><Icon name="folder" size={12} /></button>
            <button className="btn sm" onClick={takeScreenshot}><Icon name="camera" size={12} /> Capture</button>
          </div>
        </div>
        <div className="screenshot-frame">
          <div className="ph-stripes" />
          {lastShot ? (
            <div style={{
              position: "absolute", inset: 0, display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", color: "var(--text-secondary)",
              fontFamily: "var(--font-mono)", fontSize: 10, padding: 16, textAlign: "center", gap: 8,
            }}>
              <Icon name="check" size={20} style={{ color: "var(--success)" }} />
              <span>Captured</span>
              <span style={{ color: "var(--text-muted)", fontSize: 9, wordBreak: "break-all" }}>{lastShot}</span>
            </div>
          ) : (
            <div style={{
              position: "absolute", inset: 0, display: "grid", placeItems: "center",
              color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 11,
            }}>
              no captures yet
            </div>
          )}
        </div>
        <div style={{ padding: "0 4px", fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5 }}>
          Captured via <span className="tag">adb exec-out screencap -p</span>. Saved to your configured screenshots folder.
        </div>
      </div>

      {showReboot && (
        <div className="modal-overlay" onClick={() => setShowReboot(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="mhead"><h3>Reboot device?</h3></div>
            <div className="mbody">
              This will reboot <strong style={{ color: "var(--text-primary)" }}>{activeDevice?.model}</strong>. Any unsaved data on the device may be lost. ADB will need to re-detect the device after boot.
            </div>
            <div className="mfoot">
              <button className="btn ghost" onClick={() => setShowReboot(false)}>Cancel</button>
              <button className="btn primary" onClick={() => {
                setShowReboot(false);
                toast({ kind: "warn", title: "Rebooting…", msg: "adb reboot" });
              }}>Reboot</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

window.DeviceButtonsModule = DeviceButtonsModule;
