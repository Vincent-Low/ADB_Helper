// Module: Device Info
const InfoModule = ({ ctx }) => {
  const { activeDevice: d, toast } = ctx;
  if (!d) return <NoDeviceEmpty label="Device Info" />;

  const SECTIONS = [
    { title: "Device", rows: [
      ["Manufacturer", d.manufacturer],
      ["Model", d.model],
      ["Device codename", d.codename || "—"],
      ["Brand", d.brand || "—"],
      ["Serial number", d.serial],
    ]},
    { title: "System", rows: [
      ["Android version", d.android || "—"],
      ["API level", d.api || "—"],
      ["Security patch", d.securityPatch || "—"],
      ["Build ID", d.buildId || "—"],
      ["Build fingerprint", d.fingerprint || "—"],
      ["Build type", d.buildType || "—"],
      ["Build date", d.buildDate || "—"],
      ["Bootloader", d.bootloader || "—"],
      ["Baseband / Radio", d.baseband || "—"],
    ]},
    { title: "CPU", rows: [
      ["CPU", d.cpuName || "—"],
      ["Architecture", d.cpuArch || "—"],
      ["Cores", d.cores ? `${d.cores} (octa-core)` : "—"],
      ["Governor", d.governor || "—"],
      ["Min freq", d.cpuMin ? `${d.cpuMin} MHz` : "—"],
      ["Max freq", d.cpuMax ? `${d.cpuMax} MHz` : "—"],
    ]},
    { title: "GPU", rows: [
      ["Vendor", d.gpuVendor || "—"],
      ["Renderer", d.gpuRenderer || "—"],
      ["OpenGL ES", d.gles || "—"],
    ]},
    { title: "Memory", rows: [
      ["Total RAM", d.ramTotal ? `${(d.ramTotal / 1024).toFixed(1)} GB (${d.ramTotal} MB)` : "—"],
      ["Available RAM", d.ramAvail ? `${(d.ramAvail / 1024).toFixed(1)} GB (${d.ramAvail} MB)` : "—"],
      ["Swap", d.swap ? `${(d.swap / 1024).toFixed(1)} GB` : "—"],
    ]},
    { title: "Storage", rows: [
      ["Total internal", d.storageTotal ? `${(d.storageTotal / 1024).toFixed(1)} GB` : "—"],
      ["Available", d.storageAvail ? `${(d.storageAvail / 1024).toFixed(1)} GB` : "—"],
    ]},
    { title: "Display", rows: [
      ["Resolution", d.resolution || "—"],
      ["Density", d.dpi ? `${d.dpi} dpi` : "—"],
      ["Refresh rate", d.refresh || "—"],
    ]},
    { title: "Battery", rows: [
      ["Level", d.battery ? `${d.battery}%` : "—"],
      ["Status", d.batStatus || "—"],
      ["Health", d.batHealth || "—"],
      ["Temperature", d.batTemp ? `${d.batTemp} °C` : "—"],
      ["Technology", d.batTech || "—"],
      ["Voltage", d.batVoltage ? `${d.batVoltage} mV` : "—"],
    ]},
    { title: "Network", rows: [
      ["Wi-Fi IP", d.wifiIp || "—"],
      ["Wi-Fi MAC", d.wifiMac || "—"],
      ["Bluetooth MAC", d.btMac || "—"],
      ["IMEI", d.imei || "N/A"],
    ]},
    { title: "Locale & Time", rows: [
      ["Locale", d.locale || "—"],
      ["Timezone", d.timezone || "—"],
    ]},
  ];

  return (
    <div className="info-grid">
      {SECTIONS.map((s, i) => (
        <div key={i} className="card info-section">
          <div className="card-head"><h3>{s.title}</h3></div>
          {s.rows.map(([k, v], j) => (
            <div key={j} className="info-row">
              <div className="k">{k}</div>
              <div className={`v ${v === "N/A" || v === "—" ? "na" : ""}`} title={v}
                   onClick={() => navigator.clipboard?.writeText(String(v)).then(() => toast({ kind: "success", title: "Copied", msg: String(v).slice(0, 60) }))}>
                {v}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

const NoDeviceEmpty = ({ label }) => (
  <div className="empty-state" style={{ minHeight: 320 }}>
    <div className="es-ico"><Icon name="smartphone" size={22} /></div>
    <h3>No active device</h3>
    <p>{label} needs a connected, online device. Head to Connections to plug one in over USB, or pair via Wi-Fi.</p>
  </div>
);

window.InfoModule = InfoModule;
window.NoDeviceEmpty = NoDeviceEmpty;
