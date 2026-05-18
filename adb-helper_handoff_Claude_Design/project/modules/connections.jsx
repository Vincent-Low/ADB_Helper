// Module: Connections
const ConnectionsModule = ({ ctx }) => {
  const { devices, activeSerial, setActiveSerial, paired, toast, disconnect } = ctx;
  const [tab, setTab] = React.useState("classic");
  const [ip, setIp] = React.useState("192.168.1.42");
  const [port, setPort] = React.useState("5555");
  const [pairPort, setPairPort] = React.useState("41953");
  const [pin, setPin] = React.useState("");
  const [showUnauth, setShowUnauth] = React.useState(null);

  return (
    <div className="conn-grid">
      <div className="card conn-list-card">
        <div className="conn-toolbar">
          <div className="search">
            <Icon name="search" size={14} className="ico" />
            <input className="input mono" placeholder="Filter by serial, IP, model…" />
          </div>
          <span className="tag">{devices.filter((d) => d.status === "online").length} online · {devices.length} total</span>
          <div style={{ marginLeft: "auto" }} className="h-stack">
            <button className="btn sm ghost"><Icon name="refresh" size={13} /> Refresh</button>
          </div>
        </div>

        <div className="table-wrap">
          <table className="table">
            <colgroup>
              <col style={{ width: 26 }} />
              <col style={{ width: "26%" }} />
              <col style={{ width: "20%" }} />
              <col style={{ width: "24%" }} />
              <col style={{ width: 70 }} />
              <col style={{ width: "20%" }} />
              <col style={{ width: 50 }} />
            </colgroup>
            <thead>
              <tr>
                <th></th>
                <th>Serial</th>
                <th>IP</th>
                <th>Model</th>
                <th>Conn</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}></th>
              </tr>
            </thead>
            <tbody>
              {devices.map((d) =>
              <tr key={d.serial}
              data-selected={activeSerial === d.serial}
              onClick={() => d.status === "online" && setActiveSerial(d.serial)}>
                  <td>
                    <span style={{
                    display: "inline-block", width: 8, height: 8, borderRadius: "50%",
                    background: d.status === "online" ? "var(--success)" : d.status === "unauthorized" ? "var(--warn)" : "var(--text-muted)",
                    boxShadow: d.status === "online" ? "0 0 6px oklch(0.74 0.16 145 / 0.6)" : "none"
                  }} />
                  </td>
                  <td className="mono">{d.serial}</td>
                  <td className="mono muted">{d.ip || "—"}</td>
                  <td><div style={{ fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis" }}>{d.model}</div><div className="muted" style={{ fontSize: 10 }}>{d.manufacturer}</div></td>
                  <td>
                    <span className="h-stack" style={{ gap: 6 }}>
                      <Icon name={d.connection === "wifi" ? "wifi" : "usb"} size={13} />
                      <span style={{ fontSize: 11, textTransform: "uppercase" }}>{d.connection}</span>
                    </span>
                  </td>
                  <td>
                    {d.status === "online" && <span className="pill online"><span className="pdot" />Online</span>}
                    {d.status === "offline" && <span className="pill offline"><span className="pdot" />Offline</span>}
                    {d.status === "unauthorized" &&
                  <span className="pill warn" onClick={(e) => {e.stopPropagation();setShowUnauth(d);}}>
                        <Icon name="warn" size={10} />Unauthorized
                      </span>
                  }
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn sm ghost" onClick={(e) => {e.stopPropagation();disconnect(d.serial);}}>
                      <Icon name="unlink" size={12} />
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="conn-side">
        <div className="card">
          <div className="card-head"><h3>Connect via Wi-Fi</h3></div>
          <div className="tabs">
            <button data-active={tab === "classic"} onClick={() => setTab("classic")}>Classic (Pre-11)</button>
            <button data-active={tab === "pair"} onClick={() => setTab("pair")}>Pair (Android 11+)</button>
          </div>
          <div className="card-body v-stack" style={{ gap: 12 }}>
            {tab === "classic" ?
            <>
                <div className="field-row">
                  <div className="field">
                    <label>IP Address</label>
                    <input className="input mono" value={ip} onChange={(e) => setIp(e.target.value)} />
                  </div>
                  <div className="field">
                    <label>Port</label>
                    <input className="input mono" value={port} onChange={(e) => setPort(e.target.value)} />
                  </div>
                </div>
                <button className="btn primary" style={{ width: "100%", height: 32 }}
              onClick={() => toast({ kind: "success", title: `Connecting to ${ip}:${port}`, msg: "adb connect — handshake started" })}>
                  <Icon name="link" size={14} /> Connect
                </button>
                <div className="text-muted" style={{ fontSize: 11, lineHeight: 1.5 }}>
                  On the device, enable <span className="tag">Wireless debugging</span> in Developer Options, then enter the IP shown there.
                </div>
              </> :

            <>
                <div className="field-row three">
                  <div className="field">
                    <label>IP Address</label>
                    <input className="input mono" value={ip} onChange={(e) => setIp(e.target.value)} />
                  </div>
                  <div className="field">
                    <label>Pair Port</label>
                    <input className="input mono" value={pairPort} onChange={(e) => setPairPort(e.target.value)} />
                  </div>
                  <div className="field">
                    <label>PIN</label>
                    <input className="input mono" type="password" maxLength={6} placeholder="6 digits" value={pin} onChange={(e) => setPin(e.target.value)} />
                  </div>
                </div>
                <button className="btn primary" style={{ width: "100%", height: 32 }}
              disabled={pin.length !== 6}
              onClick={() => toast({ kind: "success", title: "Pairing…", msg: `adb pair ${ip}:${pairPort} *****` })}>
                  <Icon name="shield" size={14} /> Pair Device
                </button>
                <div className="text-muted" style={{ fontSize: 11, lineHeight: 1.5 }}>
                  On Android 11+, tap <span className="tag">Pair device with pairing code</span> in Wireless Debugging. PIN is masked in logs.
                </div>
              </>
            }
          </div>
        </div>

        <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div className="card-head">
            <h3>Paired Devices</h3>
            <div className="head-actions"><span className="tag">{paired.length} saved</span></div>
          </div>
          <div className="scroll-y" style={{ flex: 1 }}>
            {paired.map((p, i) =>
            <div className="paired-row" key={i}>
                <Icon name="wifi" size={14} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="alias">{p.alias}</div>
                  <div className="ip">{p.ip}</div>
                </div>
                <span className="when" style={{ flexShrink: 0 }}>{p.last}</span>
                <div className="h-stack" style={{ gap: 4, flexShrink: 0 }}>
                  <button className="btn sm" onClick={() => toast({ kind: "success", title: `Connecting to ${p.alias}` })}>Connect</button>
                  <button className="btn sm ghost icon-only"><Icon name="trash" size={12} /></button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {showUnauth &&
      <div className="modal-overlay" onClick={() => setShowUnauth(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="mhead"><h3>Authorise USB Debugging</h3></div>
            <div className="mbody">
              Unlock <strong style={{ color: "var(--text-primary)" }}>{showUnauth.model}</strong>, go to{" "}
              <span className="tag">Developer Options</span>, and tap <strong style={{ color: "var(--text-primary)" }}>Allow</strong> on the USB debugging authorisation prompt. Then reconnect the device.
            </div>
            <div className="mfoot">
              <button className="btn" onClick={() => setShowUnauth(null)}>Got it</button>
            </div>
          </div>
        </div>
      }
    </div>);

};

window.ConnectionsModule = ConnectionsModule;