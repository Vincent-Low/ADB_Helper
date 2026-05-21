/* Typed shapes for every QWebChannel-registered bridge.
 * These mirror the Python @Slot/Signal surface exactly. */

export interface DeviceContext {
  serial: string;
  model: string;
  manufacturer: string;
  sdk_version: string;
  abi: string;
  connection_type: "usb" | "wifi";
  status: "online" | "offline" | "unauthorized";
  human_label?: string;
}

export interface AdbResult {
  id: string;
  stdout: string;
  stderr: string;
  returncode: number;
  status: "succeeded" | "failed" | "timed_out" | "cancelled";
}

export interface PairedDevice {
  ip: string;
  alias: string;
  last_connected: string | null;
  connect_port: number | null;
}

export type QtSignal<T extends any[] = any[]> = {
  connect: (cb: (...args: T) => void) => void;
  disconnect: (cb: (...args: T) => void) => void;
};

/* ---------------------------------------------------------------- */

export interface AppBridge {
  getInitialState(): Promise<{
    theme: string;
    effectiveTheme: "dark" | "light";
    settings: Record<string, any>;
    activeDevice: DeviceContext | null;
    strings: Record<string, string>;
    appVersion: string;
  }>;
  setTheme(mode: "system" | "light" | "dark"): Promise<void>;
  effectiveTheme(): Promise<"dark" | "light">;
  themeChanged: QtSignal<[string]>;
  activeDeviceChanged: QtSignal<[DeviceContext | null]>;
  settingsChanged: QtSignal<[Record<string, any>]>;
}

export interface ConnectionsBridge {
  listDevices(): Promise<DeviceContext[]>;
  activeDevice(): Promise<DeviceContext | null>;
  setActiveDevice(serial: string): Promise<void>;
  clearActiveDevice(): Promise<void>;
  pair(ip: string, port: number, pin: string): Promise<string>;
  connect(ip: string, port: number): Promise<string>;
  disconnect(target: string): Promise<string>;
  listPaired(): Promise<PairedDevice[]>;
  savePaired(ip: string, alias: string, port: number | null): Promise<void>;
  forgetPaired(ip: string): Promise<void>;
  renamePaired(ip: string, alias: string): Promise<void>;
  touchPaired(ip: string): Promise<void>;
  deviceConnected: QtSignal<[DeviceContext]>;
  deviceDisconnected: QtSignal<[string]>;
  deviceStateChanged: QtSignal<[DeviceContext]>;
  activeDeviceChanged: QtSignal<[DeviceContext | null]>;
  commandFinished: QtSignal<[string, AdbResult]>;
  commandFailed: QtSignal<[string, AdbResult]>;
}

export interface TerminalBridge {
  start(serial: string): Promise<boolean>;
  write(data: string): Promise<void>;
  close(): Promise<void>;
  isRunning(): Promise<boolean>;
  supportsPty(): Promise<boolean>;
  history(): Promise<string[]>;
  appendHistory(command: string): Promise<void>;
  listMacros(): Promise<Array<{ id: number; name: string; commands: string[]; created_at: string }>>;
  saveMacro(name: string, commands: string[]): Promise<number>;
  renameMacro(id: number, name: string): Promise<void>;
  deleteMacro(id: number): Promise<void>;
  output: QtSignal<[string]>;
  exited: QtSignal<[number]>;
  started: QtSignal<[string]>;
}

export interface InstallerPlanEntry { file: string; serial: string }
export interface InstallerStartedPayload { cmd_id: string; file: string; serial: string }
export interface InstallerBridge {
  pickFiles(): Promise<string[]>;
  installFiles(files: string[], serials: string[], timeout?: number): Promise<InstallerPlanEntry[]>;
  cancel(cmd_id: string): Promise<void>;
  cancelAll(): Promise<void>;
  filesDropped: QtSignal<[string[]]>;
  installStarted: QtSignal<[InstallerStartedPayload]>;
  installFinished: QtSignal<[string, AdbResult]>;
  installFailed: QtSignal<[string, AdbResult]>;
  queueDrained: QtSignal<[]>;
}

export interface ScrcpyState { ready: boolean; version: string; path: string }
export interface ScrcpyBridge {
  state(): Promise<ScrcpyState>;
  ensureBinary(): Promise<void>;
  launch(options: {
    bitrate?: string;
    maxResolution?: number | string;
    orientation?: number | string;
    stayAwake?: boolean;
    showTouches?: boolean;
    turnScreenOff?: boolean;
  }): Promise<{ ok: boolean; pid: string; message: string; argv?: string[] }>;
  statusChanged: QtSignal<[string]>;
  binaryReady: QtSignal<[{ ok: boolean; path: string; version: string; message: string }]>;
  launchResult: QtSignal<[any]>;
  processStopped: QtSignal<[string, number]>;
}

export interface ButtonsBridge {
  pressKey(key: string): Promise<string>;
  reboot(mode: "normal" | "bootloader" | "recovery"): Promise<string>;
  toggleRotation(): Promise<string>;
  screenshot(): Promise<string>;
  actionFinished: QtSignal<[{ cmd_id: string; action: string; ok: boolean; message: string }]>;
  screenshotSaved: QtSignal<[string]>;
}

export interface InfoSection { title: string; fields: string[] }
export interface InfoBridge {
  sections(): Promise<InfoSection[]>;
  fetch(serial: string): Promise<void>;
  fetchStarted: QtSignal<[]>;
  fetchFinished: QtSignal<[{ serial: string; fields: Record<string, string>; sections: InfoSection[] }]>;
  fetchProgress: QtSignal<[number, number]>;
}

export interface AppEntry {
  package: string;
  name: string;
  apk_path: string;
  type: "user" | "system";
  status: "active" | "disabled";
}
export interface AppsBridge {
  loadAll(serial: string): Promise<void>;
  refreshMeters(serial: string): Promise<void>;
  uninstall(pkg: string): Promise<string>;
  disablePackage(pkg: string): Promise<string>;
  enablePackage(pkg: string): Promise<string>;
  backupApk(pkg: string, dest: string): Promise<string>;
  listLoaded: QtSignal<[{ serial: string; apps: AppEntry[] }]>;
  appUpdated: QtSignal<[AppEntry]>;
  metersUpdated: QtSignal<[{ kind: "ram" | "storage"; used_mb: number; total_mb: number }]>;
  actionFinished: QtSignal<[{ action: string; package: string; ok: boolean; message: string }]>;
}

export interface LogcatBridge {
  state(): Promise<{
    folder: string;
    filename_pattern: string;
    mode: string;
    recent: Array<{ path: string; size: number; saved: string }>;
    in_progress: boolean;
  }>;
  setFolder(folder: string): Promise<void>;
  export(serial: string): Promise<{ ok: boolean; pid?: string; path?: string; message?: string }>;
  exportStarted: QtSignal<[string]>;
  exportFinished: QtSignal<[{ ok: boolean; path: string; size_bytes: number; message: string }]>;
}

export interface SettingsBridge {
  all(): Promise<Record<string, any>>;
  set(key: string, value: any): Promise<void>;
  get(key: string): Promise<any>;
  pickFolder(title: string, current: string): Promise<string>;
  dependencies(): Promise<Array<{
    component: string;
    installed: boolean;
    version: string;
    latest: string;
    status: string;
  }>>;
  settingsChanged: QtSignal<[Record<string, any>]>;
  depsChecked: QtSignal<[any]>;
}

export interface QtBridges {
  app: AppBridge;
  connections: ConnectionsBridge;
  terminal: TerminalBridge;
  installer: InstallerBridge;
  scrcpy: ScrcpyBridge;
  buttons: ButtonsBridge;
  info: InfoBridge;
  apps: AppsBridge;
  logcat: LogcatBridge;
  settings: SettingsBridge;
}
