/* global React, MOCK_BUTTONS, MOCK_DEVICE_INFO */
const { useState: useState3 } = React;

// ============================================================
// Device Buttons
// ============================================================
function DeviceButtonsScreen() {
  return (
    <div className="screen-enter" style={{display:'flex', flexDirection:'column', gap:'var(--gap)'}}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Device Buttons</h1>
          <p className="module-sub">Send hardware key events and one-shot commands to the active device</p>
        </div>
      </div>

      <div className="section-label">Navigation</div>
      <div className="btn-grid">
        {window.MOCK_BUTTONS.slice(0, 3).map(b => {
          const I = window[b.ico];
          return (
            <button key={b.id} className="btn-tile">
              <div className="bt-icon">{I && <I />}</div>
              <div className="bt-label">{b.label}</div>
              <div className="bt-sub">{b.key}</div>
            </button>
          );
        })}
      </div>

      <div className="section-label">Volume &amp; media</div>
      <div className="btn-grid">
        {window.MOCK_BUTTONS.slice(3, 7).map(b => {
          const I = window[b.ico];
          return (
            <button key={b.id} className="btn-tile">
              <div className="bt-icon">{I && <I />}</div>
              <div className="bt-label">{b.label}</div>
              <div className="bt-sub">{b.key}</div>
            </button>
          );
        })}
      </div>

      <div className="section-label">System</div>
      <div className="btn-grid">
        {window.MOCK_BUTTONS.slice(7).map(b => {
          const I = window[b.ico];
          const isPower = b.id === 'power';
          const isReboot = b.id === 'reboot';
          return (
            <button key={b.id} className="btn-tile">
              <div className="bt-icon" style={isPower || isReboot ? {color:'var(--warn)'} : {}}>{I && <I />}</div>
              <div className="bt-label">{b.label}</div>
              <div className="bt-sub">{b.key}</div>
            </button>
          );
        })}
      </div>

      {/* Recent actions log */}
      <div className="card">
        <div className="card-head">
          <div className="card-title">Recent actions</div>
          <div className="card-actions">
            <button className="btn ghost sm">Clear</button>
          </div>
        </div>
        <div className="card-body tight">
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th style={{width:120}}>Time</th>
                  <th style={{width:180}}>Action</th>
                  <th>Command</th>
                  <th style={{width:120, textAlign:'right'}}>Result</th>
                </tr>
              </thead>
              <tbody>
                {[
                  {t:'14:18:02', a:'Home',       c:'adb shell input keyevent KEYCODE_HOME',        r:'ok'},
                  {t:'14:17:48', a:'Volume +',   c:'adb shell input keyevent KEYCODE_VOLUME_UP',   r:'ok'},
                  {t:'14:17:48', a:'Volume +',   c:'adb shell input keyevent KEYCODE_VOLUME_UP',   r:'ok'},
                  {t:'14:17:31', a:'Screenshot', c:'adb shell screencap -p /sdcard/shot.png',     r:'ok'},
                  {t:'14:12:09', a:'Back',       c:'adb shell input keyevent KEYCODE_BACK',        r:'ok'},
                ].map((row, i) => (
                  <tr key={i}>
                    <td className="mono" style={{color:'var(--text-secondary)', fontSize:'var(--text-xs)'}}>{row.t}</td>
                    <td>{row.a}</td>
                    <td className="mono" style={{color:'var(--text-muted)', fontSize:'var(--text-xs)'}}>{row.c}</td>
                    <td style={{textAlign:'right'}}>
                      <span className="pill online"><span className="dot"/>{row.r}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Device Info
// ============================================================
function DeviceInfoScreen() {
  const info = window.MOCK_DEVICE_INFO;
  const sections = [
    { key: 'device', label: 'Device' },
    { key: 'system', label: 'System' },
    { key: 'cpu',    label: 'CPU' },
    { key: 'gpu',    label: 'GPU' },
    { key: 'memory', label: 'Memory' },
  ];

  return (
    <div className="screen-enter" style={{display:'flex', flexDirection:'column', gap:'var(--gap)'}}>
      <div className="module-head">
        <div>
          <h1 className="module-title">Device Info</h1>
          <p className="module-sub">Static snapshot · click Refresh to re-poll the device</p>
        </div>
        <div className="module-actions">
          <button className="btn ghost"><IconClipboard /> Copy</button>
          <button className="btn ghost"><IconDownload /> Export TXT</button>
          <button className="btn"><IconRefresh /> Refresh</button>
        </div>
      </div>

      {sections.map(s => (
        <div className="card" key={s.key}>
          <div className="card-head">
            <div className="card-title">{s.label}</div>
          </div>
          <div className="card-body">
            <div className="kv-list">
              {Object.entries(info[s.key]).map(([k, v]) => (
                <React.Fragment key={k}>
                  <div className="kv-key">{k}</div>
                  <div className="kv-val">{v}</div>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { DeviceButtonsScreen, DeviceInfoScreen });
