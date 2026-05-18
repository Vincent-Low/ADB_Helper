// Module: Scrcpy
const ScrcpyModule = ({ ctx }) => {
  const { activeDevice, toast } = ctx;
  const [bitrate, setBitrate] = React.useState(8);
  const [maxRes, setMaxRes] = React.useState("No limit");
  const [orient, setOrient] = React.useState("Auto");
  const [stayAwake, setStayAwake] = React.useState(false);
  const [showTouches, setShowTouches] = React.useState(false);
  const [screenOff, setScreenOff] = React.useState(false);

  if (!activeDevice) return <NoDeviceEmpty label="Scrcpy" />;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--gap)" }}>
      <div className="card">
        <div className="card-head">
          <h3>Launch Options</h3>
          <div className="head-actions"><span className="tag">scrcpy 4.0 · bundled</span></div>
        </div>
        <div className="card-body v-stack" style={{ gap: 14 }}>
          <SettingRow label="Video bitrate" desc={`${bitrate} Mbps · higher = better quality, more bandwidth`}>
            <input type="range" min="1" max="32" value={bitrate} onChange={e => setBitrate(+e.target.value)} style={{ width: 200 }} />
          </SettingRow>
          <SettingRow label="Max resolution" desc="Caps the streamed display dimension">
            <select className="select" value={maxRes} onChange={e => setMaxRes(e.target.value)}>
              <option>No limit</option><option>2560</option><option>1920</option><option>1280</option><option>1024</option><option>720</option>
            </select>
          </SettingRow>
          <SettingRow label="Display orientation" desc="Lock the mirrored window orientation">
            <select className="select" value={orient} onChange={e => setOrient(e.target.value)}>
              <option>Auto</option><option>Portrait</option><option>Landscape</option><option>0°</option><option>90°</option><option>180°</option><option>270°</option>
            </select>
          </SettingRow>
          <SettingRow label="Stay awake" desc="Keep the device screen on while mirroring">
            <div className="cb" data-checked={stayAwake} onClick={() => setStayAwake(s => !s)} />
          </SettingRow>
          <SettingRow label="Show touches" desc="Visualise touch points on the device">
            <div className="cb" data-checked={showTouches} onClick={() => setShowTouches(s => !s)} />
          </SettingRow>
          <SettingRow label="Turn screen off" desc="Black out the device while streaming (privacy)">
            <div className="cb" data-checked={screenOff} onClick={() => setScreenOff(s => !s)} />
          </SettingRow>

          <div className="divider" />

          <button className="btn primary" style={{ height: 38 }}
                  onClick={() => toast({ kind: "success", title: "Launching scrcpy", msg: `${activeDevice.model} · ${bitrate} Mbps` })}>
            <Icon name="cast" size={14} /> Launch scrcpy
          </button>

          <div className="text-muted" style={{ fontSize: 11, lineHeight: 1.5 }}>
            scrcpy opens in its own window, not embedded here. Auto-updates checked daily via GitHub.
          </div>
        </div>
      </div>

      <div className="v-stack" style={{ gap: "var(--gap)" }}>
        <div className="card">
          <div className="card-head"><h3>Command Preview</h3></div>
          <div style={{ padding: 14, background: "var(--bg-elev)", borderTop: "1px solid var(--border)" }}>
            <pre style={{
              margin: 0, fontFamily: "var(--font-mono)", fontSize: 12,
              color: "var(--text-secondary)", lineHeight: 1.7, whiteSpace: "pre-wrap"
            }}>
{`scrcpy \\
  --serial ${activeDevice.serial} \\
  --video-bit-rate ${bitrate}M \\${maxRes !== "No limit" ? `\n  --max-size ${maxRes} \\` : ""}${orient !== "Auto" ? `\n  --display-orientation ${orient.replace("°", "")} \\` : ""}${stayAwake ? `\n  --stay-awake \\` : ""}${showTouches ? `\n  --show-touches \\` : ""}${screenOff ? `\n  --turn-screen-off \\` : ""}
  --window-title "${activeDevice.model}"`}
            </pre>
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h3>Binary Status</h3></div>
          <div className="info-section">
            <div className="info-row"><div className="k">Installed</div><div className="v">scrcpy-v4.0-win64</div></div>
            <div className="info-row"><div className="k">Location</div><div className="v mono">~/.config/adb_helper/scrcpy/</div></div>
            <div className="info-row"><div className="k">Last update check</div><div className="v">2 hours ago</div></div>
            <div className="info-row"><div className="k">Status</div><div className="v"><span className="pill online"><span className="pdot" />Up to date</span></div></div>
          </div>
        </div>
      </div>
    </div>
  );
};

const SettingRow = ({ label, desc, children }) => (
  <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 12, alignItems: "center" }}>
    <div>
      <div style={{ fontSize: 12, fontWeight: 500 }}>{label}</div>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{desc}</div>
    </div>
    {children}
  </div>
);

window.ScrcpyModule = ScrcpyModule;
window.SettingRow = SettingRow;
