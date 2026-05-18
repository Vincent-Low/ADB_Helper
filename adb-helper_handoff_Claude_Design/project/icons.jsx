// Lucide-style stroke icons, hand-written paths kept minimal.
const Icon = ({ name, size = 16, strokeWidth = 1.75, className = "", ...rest }) => {
  const paths = ICON_PATHS[name];
  if (!paths) return null;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size} height={size} viewBox="0 0 24 24"
      fill="none" stroke="currentColor"
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
      className={className} {...rest}
    >
      {paths}
    </svg>
  );
};

const ICON_PATHS = {
  // Brand / hardware
  smartphone: <>
    <rect x="6" y="2" width="12" height="20" rx="2" />
    <path d="M11 18h2" />
  </>,
  monitor: <>
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <path d="M8 21h8M12 17v4" />
  </>,
  usb: <>
    <circle cx="12" cy="20" r="1.5" />
    <path d="M12 18.5V9" />
    <path d="M9 12l3-3 3 3" />
    <path d="M6 7l1.5 3L9 7" /><circle cx="7.5" cy="5.5" r="1.5" />
    <path d="M14.5 12.5l2-2 2 2" /><rect x="14.5" y="12.5" width="4" height="3" />
  </>,
  wifi: <>
    <path d="M5 12.55a11 11 0 0 1 14 0" />
    <path d="M8 16a6 6 0 0 1 8 0" />
    <path d="M2 8.82a15 15 0 0 1 20 0" />
    <circle cx="12" cy="20" r="0.5" fill="currentColor"/>
  </>,
  link: <>
    <path d="M10 14a5 5 0 0 0 7.07 0l3.54-3.54a5 5 0 0 0-7.07-7.07l-1.06 1.06" />
    <path d="M14 10a5 5 0 0 0-7.07 0L3.39 13.54a5 5 0 1 0 7.07 7.07l1.06-1.06" />
  </>,
  unlink: <>
    <path d="M3 3l18 18" />
    <path d="M14 10l-1 1m-3 3l-2.5 2.5a3.5 3.5 0 0 1-5-5L5 9" />
    <path d="M10 14l1-1m3-3l2.5-2.5a3.5 3.5 0 0 1 5 5L19 15" />
  </>,
  // Modules
  terminal: <>
    <path d="M4 17l6-6-6-6" />
    <path d="M12 19h8" />
  </>,
  package: <>
    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
    <path d="M3.27 6.96 12 12.01l8.73-5.05" />
    <path d="M12 22.08V12" />
  </>,
  cast: <>
    <path d="M2 16.1A5 5 0 0 1 5.9 20" />
    <path d="M2 12.05A9 9 0 0 1 9.95 20" />
    <path d="M2 8V6a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-6" />
    <circle cx="3" cy="20" r="0.8" fill="currentColor" />
  </>,
  buttons: <>
    <rect x="3" y="6" width="7" height="5" rx="1" />
    <rect x="14" y="6" width="7" height="5" rx="1" />
    <rect x="3" y="13" width="7" height="5" rx="1" />
    <rect x="14" y="13" width="7" height="5" rx="1" />
  </>,
  info: <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8v.01" />
  </>,
  grid: <>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </>,
  logs: <>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <path d="M14 2v6h6" />
    <path d="M8 13h8M8 17h5M8 9h2" />
  </>,
  settings: <>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </>,
  // Actions
  search: <><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  trash: <>
    <path d="M3 6h18" />
    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
  </>,
  power: <><path d="M18.36 6.64a9 9 0 1 1-12.73 0" /><path d="M12 2v10" /></>,
  refresh: <>
    <path d="M3 12a9 9 0 0 1 15-6.7l3 2.7" />
    <path d="M21 4v5h-5" />
    <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
    <path d="M3 20v-5h5" />
  </>,
  download: <>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="M7 10l5 5 5-5" />
    <path d="M12 15V3" />
  </>,
  upload: <>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <path d="M17 8l-5-5-5 5" />
    <path d="M12 3v12" />
  </>,
  play: <><path d="M5 3l14 9-14 9V3z" fill="currentColor" stroke="none"/></>,
  stop: <><rect x="6" y="6" width="12" height="12" rx="1" fill="currentColor" stroke="none"/></>,
  record: <><circle cx="12" cy="12" r="5" fill="currentColor" stroke="none"/></>,
  pause: <><rect x="6" y="5" width="4" height="14" fill="currentColor" stroke="none"/><rect x="14" y="5" width="4" height="14" fill="currentColor" stroke="none"/></>,
  camera: <>
    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
    <circle cx="12" cy="13" r="4" />
  </>,
  folder: <><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" /></>,
  check: <><path d="M20 6L9 17l-5-5" /></>,
  x: <><path d="M18 6L6 18M6 6l12 12" /></>,
  chevron_left: <><path d="M15 18l-6-6 6-6" /></>,
  chevron_right: <><path d="M9 18l6-6-6-6" /></>,
  chevron_down: <><path d="M6 9l6 6 6-6" /></>,
  panel_left: <>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M9 3v18" />
  </>,
  more: <><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/><circle cx="5" cy="12" r="1" fill="currentColor"/></>,
  // Device buttons
  home: <><path d="M3 11l9-9 9 9" /><path d="M5 9v12h14V9" /></>,
  arrow_left: <><path d="M19 12H5M12 19l-7-7 7-7" /></>,
  square: <><rect x="4" y="4" width="16" height="16" rx="2" /></>,
  vol_up: <>
    <path d="M11 5L6 9H2v6h4l5 4z" />
    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
  </>,
  vol_down: <>
    <path d="M11 5L6 9H2v6h4l5 4z" />
    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
  </>,
  vol_mute: <>
    <path d="M11 5L6 9H2v6h4l5 4z" />
    <path d="M22 9l-6 6M16 9l6 6" />
  </>,
  rotate: <>
    <path d="M21 12a9 9 0 1 1-6.22-8.56" />
    <path d="M21 3v6h-6" />
  </>,
  warn: <>
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <path d="M12 9v4M12 17h.01" />
  </>,
  filter: <><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" /></>,
  copy: <>
    <rect x="9" y="9" width="13" height="13" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </>,
  shield: <><path d="M12 2 4 6v6c0 5 3.5 9 8 10 4.5-1 8-5 8-10V6l-8-4z" /></>,
  // Sun/moon for theme
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" /></>,
  moon: <><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></>,
};

window.Icon = Icon;
