/* global React, ReactDOM, MODULES, MODULES_FOOT, useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakSelect, TweakColor */
const { useState, useEffect, useRef, useMemo } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "dark",
  "density": "auto",
  "accent": "#2ec5c5"
} /*EDITMODE-END*/;

// Pick a density based on viewport width (auto mode)
function autoDensity(w) {
  if (w < 1180) return 'compact';
  if (w < 1520) return 'comfortable';
  return 'spacious';
}

function App() {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [route, setRoute] = useState('connections');
  const [sbCollapsed, setSbCollapsed] = useState(false);
  const stageRef = useRef(null);
  const [stageW, setStageW] = useState(window.innerWidth);

  // Track stage width for auto-collapse + auto-density
  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0].contentRect.width;
      setStageW(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Auto-collapse sidebar below 1100
  useEffect(() => {
    setSbCollapsed(stageW < 1100);
  }, [stageW]);

  // Compute density
  const density = tweaks.density === 'auto' ? autoDensity(stageW) : tweaks.density;

  // Apply theme/density at body level so root tokens cascade everywhere
  useEffect(() => {
    document.body.setAttribute('data-theme', tweaks.theme);
    document.body.setAttribute('data-density', density);
  }, [tweaks.theme, density]);

  // Apply custom accent
  useEffect(() => {
    const a = tweaks.accent || '#2ec5c5';
    document.documentElement.style.setProperty('--accent', a);
    // basic derivatives (rough alpha overlays)
    document.documentElement.style.setProperty('--accent-soft', hexA(a, 0.18));
    document.documentElement.style.setProperty('--accent-faint', hexA(a, 0.09));
  }, [tweaks.accent]);

  const sbW = sbCollapsed ? 'var(--sidebar-w-collapsed)' : 'var(--sidebar-w)';

  const screen = useMemo(() => {
    switch (route) {
      case 'connections':return <ConnectionsScreen />;
      case 'terminal':return <TerminalScreen />;
      case 'installer':return <InstallerScreen />;
      case 'scrcpy':return <ScrcpyScreen />;
      case 'device-buttons':return <DeviceButtonsScreen />;
      case 'device-info':return <DeviceInfoScreen />;
      case 'apps':return <AppsScreen />;
      case 'logcat':return <LogcatScreen />;
      case 'settings':return <SettingsScreen />;
      default:return <ConnectionsScreen />;
    }
  }, [route]);

  return (
    <div className="app-stage" ref={stageRef}>
      <div className="app" data-sb={sbCollapsed ? 'collapsed' : 'expanded'} style={{ '--sb-w': sbW }}>
        {/* Titlebar (native frame stand-in) */}
        <div className="titlebar">
          <div></div>
          <div className="tb-title">ADB_Helper</div>
          <div className="tb-controls">
            <button className="tb-btn" title="Minimize">
              <svg viewBox="0 0 12 12"><line x1="2" y1="6" x2="10" y2="6" stroke="currentColor" strokeWidth="1.2" /></svg>
            </button>
            <button className="tb-btn" title="Maximize">
              <svg viewBox="0 0 12 12"><rect x="2.5" y="2.5" width="7" height="7" stroke="currentColor" strokeWidth="1.2" fill="none" /></svg>
            </button>
            <button className="tb-btn close" title="Close">
              <svg viewBox="0 0 12 12"><line x1="2.5" y1="2.5" x2="9.5" y2="9.5" stroke="currentColor" strokeWidth="1.2" /><line x1="9.5" y1="2.5" x2="2.5" y2="9.5" stroke="currentColor" strokeWidth="1.2" /></svg>
            </button>
          </div>
        </div>

        {/* Sidebar + content */}
        <div className="body-grid">
          <Sidebar route={route} setRoute={setRoute} collapsed={sbCollapsed} toggle={() => setSbCollapsed(!sbCollapsed)} />
          <div className="content" data-screen-label={route} key={route}>
            <div className="content-inner">{screen}</div>
          </div>
        </div>

        {/* Statusbar */}
        <StatusBar density={density} accent={tweaks.accent} stageW={stageW} />
      </div>

      <TweaksPanel title="Tweaks" defaultOpen={false}>
        <TweakSection label="Appearance">
          <TweakRadio label="Theme" value={tweaks.theme} onChange={(v) => setTweak('theme', v)} options={[{ label: 'Light', value: 'light' }, { label: 'Dark', value: 'dark' }]} />
        </TweakSection>
        <TweakSection label="Density">
          <TweakSelect label="Mode" value={tweaks.density} onChange={(v) => setTweak('density', v)}
          options={[
          { label: 'Auto (scales to window)', value: 'auto' },
          { label: 'Compact', value: 'compact' },
          { label: 'Comfortable', value: 'comfortable' },
          { label: 'Spacious', value: 'spacious' }]
          } />
          <div style={{ fontSize: 11, color: 'var(--tweak-muted, #888)', marginTop: 6 }}>
            Current: <strong>{density}</strong> · window {Math.round(stageW)}px
          </div>
        </TweakSection>
        <TweakSection label="Accent">
          <TweakColor label="Color" value={tweaks.accent} onChange={(v) => setTweak('accent', v)}
          options={['#2ec5c5', '#3b82f6', '#7c5cff', '#22c55e', '#f97316', '#ef4444']} />
        </TweakSection>
      </TweaksPanel>
    </div>);

}

// helper: hex -> rgba with alpha
function hexA(hex, a) {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

// ============================================================
// Sidebar
// ============================================================
function Sidebar({ route, setRoute, collapsed, toggle }) {
  const renderItem = (m) => {
    const I = window[m.icon];
    return (
      <button
        key={m.id}
        className={'sb-item ' + (route === m.id ? 'active' : '')}
        onClick={() => setRoute(m.id)}
        data-tooltip={m.label}>
        
        <span className="sb-icn">{I && <I />}</span>
        <span className="sb-label">{m.label}</span>
        <span className="sb-kbd">{m.kbd}</span>
      </button>);

  };

  return (
    <div className="sidebar">
      <div className="sb-head">
        <div className="sb-logo">A</div>
        <div className="sb-brand">
          <div className="sb-brand-name">ADB_Helper</div>
          <div className="sb-brand-ver">v1.0.0</div>
        </div>
      </div>

      <div className="sb-section">Workspace</div>
      <div className="sb-list">
        {window.MODULES.map(renderItem)}
      </div>

      <div style={{ flex: 1 }} />

      <div className="sb-section">System</div>
      <div className="sb-list">
        {window.MODULES_FOOT.map(renderItem)}
      </div>

      <div className="sb-footer">
        <button className="sb-collapse" onClick={toggle} title={collapsed ? 'Expand' : 'Collapse'}>
          {collapsed ? <IconChevronRight /> : <IconChevronLeft />}
        </button>
        {!collapsed &&
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="dot online" />
            <span>1 device online</span>
          </div>
        }
      </div>
    </div>);

}

// ============================================================
// Status bar
// ============================================================
function StatusBar({ density, stageW }) {
  return (
    <div className="statusbar">
      <div className="sb-status-left">
        <span className="sb-status-item">
          <span className="dot online" />
          <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>SM-A346E</span>
          <span className="mono" style={{ color: 'var(--text-muted)' }}>(192.168.1.200:40787)</span>
        </span>
        <span className="sb-status-divider" />
        <span className="sb-status-item">
          <span style={{ color: 'var(--text-muted)' }}>Wi-Fi</span>
        </span>
      </div>
    </div>);

}

// Mount
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);