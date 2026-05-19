/* global React, MOCK_APK_QUEUE */
const { useState: useState2 } = React;

// ============================================================
// Installer
// ============================================================
function InstallerScreen() {
  const [queue, setQueue] = useState2(window.MOCK_APK_QUEUE);
  const [targets, setTargets] = useState2([true]);
  const [progress] = useState2(0);

  const totalSize = queue.filter(q=>q.checked).length ? '501.4 MB' : '0 MB';

  return (
    <div className="screen-enter" style={{display:'flex', flexDirection:'column', gap:'var(--gap)'}}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Installer</h1>
          <p className="module-sub">Install APKs to one or more devices sequentially · file × device</p>
        </div>
        <div className="module-actions">
          <span style={{color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>
            {queue.filter(q=>q.checked).length} files · {totalSize} · {targets.filter(Boolean).length} target
          </span>
        </div>
      </div>

      {/* FILES */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Files to install</div>
          <div className="card-actions">
            <button className="btn sm"><IconPlus /> Add files</button>
            <button className="btn ghost sm danger">Remove</button>
            <button className="btn ghost sm">Clear</button>
          </div>
        </div>
        <div className="card-body tight">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{width:36}}></th>
                  <th>File</th>
                  <th style={{width:80}}>Type</th>
                  <th style={{width:120}}>Size</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((q, i) => (
                  <tr key={i}>
                    <td>
                      <div className={'cb ' + (q.checked ? 'checked':'')} onClick={()=>{
                        const next=[...queue]; next[i]={...q, checked:!q.checked}; setQueue(next);
                      }}/>
                    </td>
                    <td className="mono" style={{fontSize:'var(--text-xs)'}}>{q.file}</td>
                    <td><span className="pill accent">apk</span></td>
                    <td className="mono">{q.size}</td>
                  </tr>
                ))}
                {queue.length === 0 && (
                  <tr><td colSpan={4} className="tb-empty">Drop .apk files here or click Add files</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* TARGETS */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Target devices</div>
          <div className="card-actions">
            <span style={{color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>{targets.filter(Boolean).length} of {targets.length} selected</span>
          </div>
        </div>
        <div className="card-body" style={{display:'flex', flexDirection:'column', gap:8}}>
          {window.MOCK_DEVICES.map((d, i) => (
            <label key={i} className="cb-row" style={{padding:'6px 4px'}}>
              <div className={'cb ' + (targets[i] ? 'checked':'')} onClick={()=>{
                const next=[...targets]; next[i]=!next[i]; setTargets(next);
              }}/>
              <span style={{color:'var(--text-primary)', fontWeight:500}}>{d.model}</span>
              <span className="mono" style={{color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>({d.serial})</span>
              <span className="pill online" style={{marginLeft:'auto'}}><span className="dot"/>online</span>
            </label>
          ))}
        </div>
      </div>

      {/* INSTALLATION */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Installation</div>
        </div>
        <div className="card-body" style={{display:'flex', flexDirection:'column', gap:14}}>
          <div style={{display:'flex', gap:8}}>
            <button className="btn primary"><IconDownload /> Install</button>
            <button className="btn ghost">Cancel</button>
            <div style={{marginLeft:'auto', display:'flex', alignItems:'center', gap:12, color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>
              <span>Sequential · per-file errors don't abort the batch</span>
            </div>
          </div>
          <div className="bar">
            <div className="fill" style={{width: progress + '%'}} />
            <div className="bar-label">{progress}%</div>
          </div>
        </div>
      </div>

      {/* RESULTS */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Results</div>
          <div className="card-actions">
            <button className="btn ghost sm">Export CSV</button>
          </div>
        </div>
        <div className="card-body tight">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{width:'40%'}}>File</th>
                  <th style={{width:200}}>Serial</th>
                  <th style={{width:140}}>Model</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colSpan={4} className="tb-empty">Run an install to see results</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Scrcpy
// ============================================================
function ScrcpyScreen() {
  const [bitrate, setBitrate] = useState2('8 Mbps');
  const [maxRes, setMaxRes] = useState2('No limit');
  const [orient, setOrient]  = useState2('Auto');
  const [stayAwake, setStayAwake] = useState2(false);
  const [showTouch, setShowTouch] = useState2(false);
  const [turnOff, setTurnOff] = useState2(false);

  return (
    <div className="screen-enter" style={{display:'flex', flexDirection:'column', gap:'var(--gap)'}}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Scrcpy</h1>
          <p className="module-sub">Mirror device screen — launches as a separate top-level window</p>
        </div>
        <div className="module-actions">
          <span className="pill"><span className="dot online"/>v4.0 ready</span>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'minmax(0, 1fr) 340px', gap:'var(--gap)', alignItems:'start'}}>
      <div className="card">
        <div className="card-head">
          <div className="card-title">Launch options</div>
        </div>
        <div className="card-body" style={{display:'flex', flexDirection:'column', gap:14}}>
          <div className="field">
            <label className="field-label">Video bitrate</label>
            <div className="field-row">
              <select className="select" value={bitrate} onChange={(e)=>setBitrate(e.target.value)}>
                {['2 Mbps','4 Mbps','8 Mbps','12 Mbps','16 Mbps','24 Mbps'].map(o=><option key={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label className="field-label">Max resolution</label>
            <div className="field-row">
              <select className="select" value={maxRes} onChange={(e)=>setMaxRes(e.target.value)}>
                {['No limit','480p','720p','1080p','1440p'].map(o=><option key={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <div className="field">
            <label className="field-label">Orientation lock</label>
            <div className="field-row">
              <select className="select" value={orient} onChange={(e)=>setOrient(e.target.value)}>
                {['Auto','Portrait','Landscape','Reverse portrait','Reverse landscape'].map(o=><option key={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <div className="field" style={{alignItems:'flex-start'}}>
            <label className="field-label" style={{paddingTop:4}}>Flags</label>
            <div className="field-row" style={{flexDirection:'column', alignItems:'flex-start', gap:6}}>
              <label className="cb-row"><div className={'cb '+(stayAwake?'checked':'')} onClick={()=>setStayAwake(!stayAwake)}/>Stay awake while mirroring</label>
              <label className="cb-row"><div className={'cb '+(showTouch?'checked':'')} onClick={()=>setShowTouch(!showTouch)}/>Show touches on device</label>
              <label className="cb-row"><div className={'cb '+(turnOff?'checked':'')} onClick={()=>setTurnOff(!turnOff)}/>Turn device screen off</label>
            </div>
          </div>
        </div>
        <div style={{padding:'12px 16px', borderTop:'1px solid var(--border)', display:'flex', justifyContent:'space-between', alignItems:'center', background:'var(--bg-elev)'}}>
          <div className="code-block" style={{flex:1, marginRight:12, padding:'6px 10px', border:'none', background:'transparent', color:'var(--text-muted)'}}>
            <span className="cmd">scrcpy</span> <span className="flag">--bit-rate</span> 8M <span className="flag">--max-size</span> 0
          </div>
          <button className="btn primary"><IconPlay /> Launch</button>
        </div>
      </div>

      {/* Recent launches */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Recent launches</div>
          <div className="card-actions">
            <button className="btn ghost sm">Clear</button>
          </div>
        </div>
        <div className="card-body" style={{display:'flex', flexDirection:'column', gap:10, padding:'12px 14px'}}>
          {[
            {when:'14:12:08', dev:'SM-A346E', flags:'8 Mbps · Auto · stay-awake', dur:'00:12:41'},
            {when:'12:48:33', dev:'SM-A346E', flags:'8 Mbps · Auto',                dur:'00:03:19'},
            {when:'Yesterday · 22:01', dev:'SM-A346E', flags:'12 Mbps · 1080p',     dur:'00:48:02'},
          ].map((r, i) => (
            <div key={i} style={{display:'grid', gridTemplateColumns:'1fr auto', gap:6, padding:'10px 12px', background:'var(--surface-2)', borderRadius:'var(--radius-sm)', border:'1px solid var(--border)'}}>
              <div style={{minWidth:0}}>
                <div className="mono" style={{fontSize:'var(--text-xs)', color:'var(--text-secondary)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{r.dev}</div>
                <div style={{fontSize:'var(--text-xxs)', color:'var(--text-muted)', marginTop:2, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{r.flags}</div>
              </div>
              <div style={{textAlign:'right', display:'flex', flexDirection:'column', justifyContent:'space-between'}}>
                <span className="mono" style={{fontSize:'var(--text-xxs)', color:'var(--text-muted)'}}>{r.when}</span>
                <span className="mono" style={{fontSize:'var(--text-xxs)', color:'var(--text-secondary)'}}>{r.dur}</span>
              </div>
            </div>
          ))}
        </div>
        <div style={{padding:'10px 14px', borderTop:'1px solid var(--border)', display:'flex', alignItems:'center', gap:8, background:'var(--bg-elev)'}}>
          <span className="section-label" style={{margin:0, flex:1}}>Tips</span>
        </div>
        <div className="card-body" style={{paddingTop:0, fontSize:'var(--text-xs)', color:'var(--text-muted)', lineHeight:1.6}}>
          <p style={{margin:'0 0 6px'}}>• Lower bitrate to reduce latency over Wi-Fi.</p>
          <p style={{margin:'0 0 6px'}}>• “Turn screen off” is useful when mirroring full-screen on PC.</p>
          <p style={{margin:0}}>• scrcpy opens as a separate window; closing it doesn’t affect ADB.</p>
        </div>
      </div>
      </div>
    </div>
  );
}

Object.assign(window, { InstallerScreen, ScrcpyScreen });
