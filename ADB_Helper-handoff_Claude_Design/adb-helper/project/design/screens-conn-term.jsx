/* global React, MOCK_DEVICES, MOCK_PAIRED */
const { useState } = React;

// ============================================================
// Connections
// ============================================================
function ConnectionsScreen() {
  const [selected, setSelected] = useState(0);
  const [legacyIp, setLegacyIp] = useState('');
  const [legacyPort, setLegacyPort] = useState('5555');
  const [pairIp, setPairIp] = useState('');
  const [pairPort, setPairPort] = useState('');
  const [pairPin, setPairPin] = useState('');
  const [editingPort, setEditingPort] = useState(null);
  const [paired, setPaired] = useState(window.MOCK_PAIRED);
  const [pairedSel, setPairedSel] = useState(0);

  return (
    <div className="screen-enter" style={{display:'flex', flexDirection:'column', gap:'var(--gap)'}}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Connections</h1>
          <p className="module-sub">Connect over USB or Wi-Fi · pair Android 11+ devices</p>
        </div>
      </div>

      {/* CONNECTED DEVICES */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Connected devices</div>
          <div className="card-actions">
            <span className="pill accent"><span className="dot"></span>{MOCK_DEVICES.length} online</span>
          </div>
        </div>
        <div className="card-body tight">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{width: 240}}>Serial</th>
                  <th style={{width: 160}}>IP address</th>
                  <th style={{width: 140}}>Model</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {MOCK_DEVICES.map((d, i) => (
                  <tr key={d.serial} className={i === selected ? 'selected' : ''} onClick={() => setSelected(i)}>
                    <td className="mono">{d.serial}</td>
                    <td className="mono">{d.ip}</td>
                    <td>{d.model}</td>
                    <td>
                      <span className="pill online"><span className="dot"></span>Online</span>
                      <span style={{marginLeft:8, color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>· Wi-Fi · authorized</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div style={{padding:'10px 14px', borderTop:'1px solid var(--border)', display:'flex', justifyContent:'flex-end', gap:8, background:'var(--bg-elev)'}}>
          <button className="btn ghost sm">Copy serial</button>
          <button className="btn danger sm">Disconnect</button>
        </div>
      </div>

      {/* WI-FI LEGACY */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Wi-Fi connection (legacy)</div>
          <div className="card-actions">
            <span className="pill"><kbd>adb connect</kbd></span>
          </div>
        </div>
        <div className="card-body">
          <div style={{display:'grid', gridTemplateColumns:'1fr 140px auto', gap:10, alignItems:'center'}}>
            <div className="field-row">
              <label className="field-label">IP address</label>
              <input className="input mono" placeholder="192.168.1.10" value={legacyIp} onChange={(e)=>setLegacyIp(e.target.value)} />
            </div>
            <div className="field-row">
              <label className="field-label" style={{minWidth:36}}>Port</label>
              <input className="input mono" value={legacyPort} onChange={(e)=>setLegacyPort(e.target.value)} />
            </div>
            <button className="btn primary">Connect</button>
          </div>
        </div>
      </div>

      {/* WI-FI PAIRING */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Wi-Fi pairing (Android 11+)</div>
          <div className="card-actions">
            <span className="pill"><kbd>adb pair</kbd></span>
          </div>
        </div>
        <div className="card-body">
          <div style={{display:'grid', gridTemplateColumns:'1fr 160px 140px auto', gap:10, alignItems:'center'}}>
            <div className="field-row">
              <label className="field-label">IP address</label>
              <input className="input mono" placeholder="192.168.1.10" value={pairIp} onChange={(e)=>setPairIp(e.target.value)} />
            </div>
            <div className="field-row">
              <label className="field-label" style={{minWidth:80}}>Pairing port</label>
              <input className="input mono" placeholder="44331" value={pairPort} onChange={(e)=>setPairPort(e.target.value)} />
            </div>
            <div className="field-row">
              <label className="field-label" style={{minWidth:32}}>PIN</label>
              <input className="input mono" placeholder="6-digit code" value={pairPin} onChange={(e)=>setPairPin(e.target.value)} maxLength={6} />
            </div>
            <button className="btn primary">Pair</button>
          </div>
        </div>
      </div>

      {/* PAIRED DEVICES */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Paired devices</div>
          <div className="card-actions">
            <span style={{color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>{paired.length} saved</span>
          </div>
        </div>
        <div className="card-body tight">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{width: 200}}>Alias</th>
                  <th style={{width: 160}}>IP address</th>
                  <th style={{width: 160}}>Connection port</th>
                  <th>Last connected</th>
                </tr>
              </thead>
              <tbody>
                {paired.map((p, i) => (
                  <tr key={i} className={i === pairedSel ? 'selected' : ''} onClick={()=>setPairedSel(i)}>
                    <td>{p.alias}</td>
                    <td className="mono">{p.ip}</td>
                    <td>
                      {editingPort === i ? (
                        <input
                          className="input mono"
                          autoFocus
                          style={{height:26, padding:'0 8px'}}
                          value={p.port}
                          onChange={(e)=>{
                            const next = [...paired]; next[i] = {...p, port: e.target.value}; setPaired(next);
                          }}
                          onBlur={()=>setEditingPort(null)}
                        />
                      ) : (
                        <span className="mono" onClick={(e)=>{e.stopPropagation(); setEditingPort(i);}} style={{cursor:'text', padding:'2px 6px', borderRadius:4, background: i===pairedSel ? 'var(--accent-faint)' : 'transparent', border:'1px solid transparent'}}>
                          {p.port}
                        </span>
                      )}
                    </td>
                    <td className="mono" style={{color:'var(--text-secondary)', fontSize:'var(--text-xs)'}}>{p.last}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div style={{padding:'10px 14px', borderTop:'1px solid var(--border)', display:'flex', justifyContent:'flex-end', gap:8, background:'var(--bg-elev)'}}>
          <button className="btn danger sm">Forget</button>
          <button className="btn primary sm">Connect</button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Terminal
// ============================================================
function TerminalScreen() {
  const [cmd, setCmd] = useState('');
  const [recording, setRecording] = useState(false);
  const [output] = useState([
    {t:'sys',  text:'Starting adb shell on 192.168.1.200:40787…'},
    {t:'prompt', host:'a34x:/ $', text:'getprop ro.product.model'},
    {t:'out',  text:'SM-A346E'},
    {t:'prompt', host:'a34x:/ $', text:'whoami'},
    {t:'out',  text:'shell'},
    {t:'prompt', host:'a34x:/ $', text:'pwd'},
    {t:'out',  text:'/'},
    {t:'prompt', host:'a34x:/ $', text:'date'},
    {t:'out',  text:'Tue May 19 14:18:02 GMT+05:00 2026'},
  ]);
  const macros = [
    { name: 'list packages', body: 'pm list packages -3' },
    { name: 'wifi info',     body: 'dumpsys wifi | grep "mNetworkInfo"' },
    { name: 'cpu cores',     body: 'cat /proc/cpuinfo | grep -c processor' },
  ];

  return (
    <div className="screen-enter" style={{display:'flex', flexDirection:'column', gap:'var(--gap)', height:'100%', minHeight:0}}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Terminal</h1>
          <p className="module-sub">adb shell on the active device — macros record terminal commands only</p>
        </div>
        <div className="module-actions">
          <button className="btn ghost"><IconClipboard /> Copy session</button>
          <button className="btn ghost"><IconRefresh /> History</button>
          <button className="btn"><IconTrash /> Clear</button>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'minmax(0,1fr) 280px', gap:'var(--gap)', flex:1, minHeight:0}}>
        {/* terminal */}
        <div className="terminal">
          <div className="terminal-head">
            <div className="left">
              <span className="dot online" />
              <span className="mono" style={{fontSize:'var(--text-xs)'}}>192.168.1.200:40787</span>
              <span style={{color:'var(--text-faint)'}}>·</span>
              <span style={{color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>Geist Mono · 13pt</span>
            </div>
            <div className="actions">
              <button className="btn ghost sm">Copy</button>
              <button className="btn ghost sm">Save</button>
            </div>
          </div>
          <div className="terminal-screen">
            {output.map((l, i) => {
              if (l.t === 'sys')    return <div key={i} className="term-muted">{l.text}</div>;
              if (l.t === 'prompt') return <div key={i}><span className="term-prompt">{l.host}</span> {l.text}</div>;
              return <div key={i}>{l.text}</div>;
            })}
            <div style={{display:'inline-block', width:8, height:14, background:'var(--accent)', verticalAlign:'-2px'}} />
          </div>
          <div className="term-input-row">
            <span className="term-prompt-label">a34x:/ $</span>
            <input className="term-input mono" placeholder="type a command…" value={cmd} onChange={(e)=>setCmd(e.target.value)} />
            <button className="btn primary sm">Run</button>
          </div>
        </div>

        {/* macros */}
        <div className="card" style={{display:'flex', flexDirection:'column'}}>
          <div className="card-head">
            <div className="card-title">Macros</div>
            <div className="card-actions">
              <button className={'btn sm ' + (recording ? 'danger' : 'primary')} onClick={()=>setRecording(!recording)}>
                {recording ? <><IconStop /> Stop</> : <><IconRecord /> Record</>}
              </button>
            </div>
          </div>
          <div style={{padding:'10px 12px', display:'flex', flexDirection:'column', gap:6, overflow:'auto'}}>
            {macros.map((m, i) => (
              <div key={i} style={{display:'flex', alignItems:'center', gap:8, padding:'8px 10px', background:'var(--surface-2)', borderRadius:'var(--radius-sm)', border:'1px solid var(--border)'}}>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontSize:'var(--text-sm)', fontWeight:500}}>{m.name}</div>
                  <div className="mono" style={{fontSize:'var(--text-xxs)', color:'var(--text-muted)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{m.body}</div>
                </div>
                <button className="btn ghost icon sm" title="Run"><IconPlay /></button>
              </div>
            ))}
            {recording && (
              <div style={{display:'flex', alignItems:'center', gap:8, padding:'8px 10px', background:'var(--danger-faint)', borderRadius:'var(--radius-sm)', border:'1px solid rgba(217,76,58,0.3)'}}>
                <span className="dot" style={{background:'var(--danger)'}} />
                <span style={{fontSize:'var(--text-xs)', color:'var(--danger)', fontWeight:500}}>Recording…</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ConnectionsScreen, TerminalScreen });
