/* global React, MOCK_APPS, MOCK_DEPS */
const { useState: useState4 } = React;

// ============================================================
// Apps
// ============================================================
function AppsScreen() {
  const [search, setSearch] = useState4('');
  const [showSystem, setShowSystem] = useState4(true);
  const [showDisabled, setShowDisabled] = useState4(true);
  const [selected, setSelected] = useState4(new Set());

  const filtered = window.MOCK_APPS.filter((a) =>
  !search || a.pkg.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (i) => {
    const next = new Set(selected);
    next.has(i) ? next.delete(i) : next.add(i);
    setSelected(next);
  };

  const ramUsed = 3996,ramTotal = 5457;
  const storUsed = 42601,storTotal = 108201;

  return (
    <div className="screen-enter" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap)', height: '100%', minHeight: 0 }}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Apps</h1>
          <p className="module-sub">Installed packages on active device · system apps can only be disabled</p>
        </div>
        <div className="module-actions">
          <button className="btn ghost"><IconRefresh /> Refresh</button>
        </div>
      </div>

      {/* Meters */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--gap)' }}>
        <div className="meter">
          <div className="meter-head">
            <div className="meter-title">RAM</div>
            <div className="meter-val">{ramUsed} MB / {ramTotal} MB</div>
          </div>
          <div className="bar"><div className="fill" style={{ width: (ramUsed / ramTotal * 100).toFixed(1) + '%' }} /></div>
          <div className="meter-sub">{(ramUsed / ramTotal * 100).toFixed(0)}% used · {ramTotal - ramUsed} MB free</div>
        </div>
        <div className="meter">
          <div className="meter-head">
            <div className="meter-title">Storage</div>
            <div className="meter-val">{(storUsed / 1024).toFixed(1)} GB / {(storTotal / 1024).toFixed(1)} GB</div>
          </div>
          <div className="bar"><div className="fill" style={{ width: (storUsed / storTotal * 100).toFixed(1) + '%' }} /></div>
          <div className="meter-sub">{(storUsed / storTotal * 100).toFixed(0)}% used · {((storTotal - storUsed) / 1024).toFixed(1)} GB free</div>
        </div>
      </div>

      {/* Search row */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
        <div className="card-head">
          <div className="card-title">Installed packages</div>
          <div className="card-actions">
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>{filtered.length} of {window.MOCK_APPS.length} apps</span>
          </div>
        </div>
        <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 12, background: 'var(--bg-elev)' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <span style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', display: 'flex' }}><IconSearch /></span>
            <input className="input" placeholder="Search by package…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ paddingLeft: 34 }} />
          </div>
          <label className="cb-row"><div className={'cb ' + (showSystem ? 'checked' : '')} onClick={() => setShowSystem(!showSystem)} />Show system apps</label>
          <label className="cb-row"><div className={'cb ' + (showDisabled ? 'checked' : '')} onClick={() => setShowDisabled(!showDisabled)} />Show disabled apps</label>
        </div>
        <div className="table-wrap" style={{ flex: 1, minHeight: 0 }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 36 }}></th>
                <th>Package name</th>
                <th style={{ width: 120, textAlign: 'right' }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a, i) =>
              <tr key={i} className={selected.has(i) ? 'selected' : ''} onClick={() => toggle(i)}>
                  <td><div className={'cb ' + (selected.has(i) ? 'checked' : '')} /></td>
                  <td className="mono" style={{ fontSize: 'var(--text-xs)' }}>{a.pkg}</td>
                  <td style={{ textAlign: 'right' }}>
                    <span className="pill online"><span className="dot" />{a.status}</span>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-elev)' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn danger sm" disabled={selected.size === 0}><IconTrash /> Delete</button>
            <button className="btn sm" disabled={selected.size === 0}>Disable</button>
            <button className="btn sm" disabled={selected.size === 0}>Enable</button>
            <button className="btn ghost sm">Export to CSV</button>
          </div>
          <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
            {selected.size > 0 ? `${selected.size} selected · ` : ''}503 apps loaded
          </span>
        </div>
      </div>
    </div>);

}

// ============================================================
// Logcat
// ============================================================
function LogcatScreen() {
  return (
    <div className="screen-enter" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap)', height: '100%', minHeight: 0 }}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Logcat</h1>
          <p className="module-sub">One-shot capture (adb logcat -d) saved to the configured folder</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 320px', gap: 'var(--gap)', flex: 1, minHeight: 0 }}>
        <div className="card" style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div className="card-head">
            <div className="card-title">Capture</div>
            <div className="card-actions">
              <span className="pill"><kbd>-d</kbd> single shot</span>
            </div>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className="code-block">
              <span className="cmd">adb -s 192.168.1.200:40787 logcat</span> <span className="flag">-d</span> &gt;{'\n'}
              {'  '}<span className="path">/home/ashadrin/.config/adb_helper/logcat/logcat_DD.MM.YY_HH.mm_GMT±N.txt</span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn primary" style={{ flex: 1, justifyContent: 'center' }}><IconDownload /> Export logcat</button>
              <button className="btn"><IconFolder /> Open folder</button>
            </div>
          </div>

          <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: 14 }}>
            <span className="section-label" style={{ margin: 0 }}>Recent exports</span>
            <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>No exports yet.</span>
          </div>
          <div className="table-wrap" style={{ flex: 1, minHeight: 0 }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 200 }}>Captured</th>
                  <th style={{ width: 200 }}>Device</th>
                  <th>File</th>
                  <th style={{ width: 120 }}>Size</th>
                </tr>
              </thead>
              <tbody>
                <tr><td colSpan={4} className="tb-empty">No captures yet — click Export logcat to start</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Configuration sidebar */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="card-head">
            <div className="card-title">Configuration</div>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <div className="section-label" style={{ margin: '0 0 6px' }}>Save folder</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <div className="input mono" style={{ display: 'flex', alignItems: 'center', whiteSpace: 'nowrap', overflow: 'hidden' }}>/home/ashadrin/.config/adb_helper/logcat</div>
                <button className="btn"><IconFolder /></button>
              </div>
            </div>

            <div className="kv-list" style={{ gridTemplateColumns: 'max-content 1fr', columnGap: 16, rowGap: 0 }}>
              <div className="kv-key">Filename</div>
              <div className="kv-val" style={{ width: "224px" }}>logcat_&lt;date&gt;_&lt;time&gt;_GMT±N.txt</div>
              <div className="kv-key">Mode</div>
              <div className="kv-val">Single-shot (-d flag)</div>
              <div className="kv-key">Timezone</div>
              <div className="kv-val">GMT+5</div>
              <div className="kv-key">Rotate</div>
              <div className="kv-val">Off</div>
            </div>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12, marginTop: 'auto' }}>
              <div className="section-label" style={{ margin: '0 0 6px' }}>About</div>
              <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Streaming logcat is out of scope for v1.0. Use a one-shot capture when you need a snapshot.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>);

}

// ============================================================
// Settings
// ============================================================
function SettingsScreen() {
  const [theme] = useState4('System');
  const [shotsFolder] = useState4('/home/ashadrin/.config/adb_helper/screenshots');
  const [logFolder] = useState4('/home/ashadrin/.config/adb_helper/logcat');
  const [timeout] = useState4('30');
  const [loglevel] = useState4('Debug');

  return (
    <div className="screen-enter" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--gap)' }}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Settings</h1>
          <p className="module-sub">Application preferences and bundled dependencies</p>
        </div>
      </div>

      {/* About */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">About</div>
        </div>
        <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div className="sb-logo" style={{ width: 42, height: 42, borderRadius: 8, fontSize: 16 }}>A</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 'var(--h1)', fontWeight: 600, letterSpacing: '-0.01em' }}>ADB_Helper</div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 2 }}>
              <span className="pill mono">v1.0.0</span>
              <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>Desktop GUI for Android Debug Bridge</span>
            </div>
          </div>
        </div>
      </div>

      {/* Dependencies */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Installed dependencies</div>
          <div className="card-actions">
            <button className="btn sm"><IconRefresh /> Check for updates</button>
          </div>
        </div>
        <div className="card-body tight">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Component</th>
                  <th style={{ width: 140 }}>Installed</th>
                  <th style={{ width: 140 }}>Latest</th>
                  <th style={{ width: 160 }}>Status</th>
                  <th style={{ width: 120, textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {window.MOCK_DEPS.map((d, i) =>
                <tr key={i}>
                    <td style={{ fontWeight: 500 }}>{d.name}</td>
                    <td className="mono">{d.installed}</td>
                    <td className="mono" style={{ color: d.status === 'update' ? 'var(--accent)' : 'var(--text-muted)' }}>{d.latest}</td>
                    <td>
                      {d.status === 'up-to-date' ?
                    <span className="pill online"><span className="dot" />Up-to-date</span> :
                    <span className="pill warn"><span className="dot" />Update available</span>}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {d.status === 'update' ? <button className="btn primary sm"><IconDownload /> Update</button> : <span style={{ color: 'var(--text-faint)' }}>—</span>}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* General */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">General settings</div>
        </div>
        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="field">
            <label className="field-label">Theme</label>
            <div className="field-row">
              <select className="select" defaultValue={theme}>
                <option>System</option><option>Light</option><option>Dark</option>
              </select>
              <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>follows OS by default</span>
            </div>
          </div>
          <div className="field">
            <label className="field-label">Screenshots folder</label>
            <div className="field-row">
              <input className="input mono" defaultValue={shotsFolder} />
              <button className="btn"><IconFolder /> Browse</button>
            </div>
          </div>
          <div className="field">
            <label className="field-label">Logcat folder</label>
            <div className="field-row">
              <input className="input mono" defaultValue={logFolder} />
              <button className="btn"><IconFolder /> Browse</button>
            </div>
          </div>
          <div className="field">
            <label className="field-label">ADB command timeout</label>
            <div className="field-row" style={{ maxWidth: 240 }}>
              <input className="input mono" defaultValue={timeout} style={{ maxWidth: 120 }} />
              <span style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>seconds</span>
            </div>
          </div>
          <div className="field">
            <label className="field-label">Log level</label>
            <div className="field-row" style={{ maxWidth: 240 }}>
              <select className="select" defaultValue={loglevel}>
                <option>Error</option><option>Warning</option><option>Info</option><option>Debug</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>);

}

Object.assign(window, { AppsScreen, LogcatScreen, SettingsScreen });