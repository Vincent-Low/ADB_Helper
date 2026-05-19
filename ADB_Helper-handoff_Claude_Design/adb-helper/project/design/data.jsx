/* global window */
// Mock data for all modules

const MOCK_DEVICES = [
  { serial: '192.168.1.200:40787', ip: '192.168.1.200', model: 'SM-A346E', codename: 'a34x', status: 'online' },
];

const MOCK_PAIRED = [
  { alias: 'Wi-Fi Device', ip: '192.168.1.200', port: '40787', last: '2026-05-19 14:15:41' },
  { alias: 'Pixel 7 (home)', ip: '192.168.1.42', port: '5555', last: '2026-05-17 21:02:08' },
];

const MOCK_APK_QUEUE = [
  { file: '2gis-dgismobile-full-debug-7.23.0.618.13939-20260519-arm64-v8a.apk', size: '250.7 MB', checked: true },
  { file: '2gis-dgismobile-full-debug-7.23.0.618.13929-20260519-arm64-v8a.apk', size: '250.7 MB', checked: true },
];

const MOCK_DEVICE_INFO = {
  device: {
    Manufacturer: 'samsung',
    Model: 'SM-A346E',
    'Device codename': 'a34x',
    Brand: 'samsung',
    'Serial number': '192.168.1.200:40787',
  },
  system: {
    'Android version': '16',
    'API level': '36',
    'Security patch level': '2026-04-05',
    'Build number': 'BP2A.250605.031.A3.A346EXXSEEZC7',
    'Build fingerprint': 'samsung/a34xdxx/a34x:16/BP2A.250605.031.A3/A346EXXSEEZC7:user/release-keys',
    'Build type': 'user',
    'Build date': 'Tue Apr  7 15:56:44 KST 2026',
    'Bootloader version': 'A346EXXSEEZC7',
    'Baseband / Radio': 'A346EXXSEEZC7,A346EXXSEEZC7',
  },
  cpu: {
    'CPU hardware name': 'N/A',
    'CPU model name': 'N/A',
    'CPU architecture': 'arm64-v8a',
    'Number of cores': '8',
    'CPU governor': 'N/A',
    'Min / Max CPU frequency': '500 MHz / 2000 MHz',
  },
  gpu: {
    'GPU vendor': 'ARM',
    'GPU renderer': 'Mali-G68 MC4',
    'OpenGL ES version': 'OpenGL ES 3.2 v1.r49p1-03bet0.3666fcaacb504f548df1f5efc729b42d.l3709bd948b52e72feea0b835da3d6ff20',
  },
  memory: {
    'Total RAM': '5.3 GB',
    'Available RAM': '1.4 GB',
  },
};

const MOCK_BUTTONS = [
  { id: 'home',   label: 'Home',         key: 'KEYCODE_HOME',           ico: 'IconHome' },
  { id: 'back',   label: 'Back',         key: 'KEYCODE_BACK',           ico: 'IconArrowLeft' },
  { id: 'recent', label: 'Recent Apps',  key: 'KEYCODE_APP_SWITCH',     ico: 'IconSquare' },
  { id: 'volup',  label: 'Volume +',     key: 'KEYCODE_VOLUME_UP',      ico: 'IconVolume' },
  { id: 'voldn',  label: 'Volume −',     key: 'KEYCODE_VOLUME_DOWN',    ico: 'IconVolume' },
  { id: 'mute',   label: 'Mute',         key: 'KEYCODE_VOLUME_MUTE',    ico: 'IconVolumeOff' },
  { id: 'camera', label: 'Camera',       key: 'KEYCODE_CAMERA',         ico: 'IconCamera' },
  { id: 'power',  label: 'Power',        key: 'KEYCODE_POWER',          ico: 'IconPower' },
  { id: 'reboot', label: 'Reboot',       key: 'adb reboot',             ico: 'IconRefresh' },
  { id: 'shot',   label: 'Screenshot',   key: 'screencap -p',           ico: 'IconScreenshot' },
  { id: 'rotate', label: 'Screen Rotate',key: 'settings put system…',   ico: 'IconRotate' },
];

const MOCK_APPS = [
  { pkg: 'android',                                                   status: 'Active' },
  { pkg: 'android.auto_generated_rro_product__',                       status: 'Active' },
  { pkg: 'android.autoinstalls.config.samsung',                        status: 'Active' },
  { pkg: 'app.hiddify.com',                                            status: 'Active' },
  { pkg: 'app.revanced.android.gms',                                   status: 'Active' },
  { pkg: 'app.revanced.android.youtube',                               status: 'Active' },
  { pkg: 'com.android.apps.tag',                                       status: 'Active' },
  { pkg: 'com.android.avatarpicker',                                   status: 'Active' },
  { pkg: 'com.android.backupconfirm',                                  status: 'Active' },
  { pkg: 'com.android.bips',                                           status: 'Active' },
  { pkg: 'com.android.bluetooth',                                      status: 'Active' },
  { pkg: 'com.android.bluetoothmidiservice',                           status: 'Active' },
  { pkg: 'com.android.bookmarkprovider',                               status: 'Active' },
  { pkg: 'com.android.calllogbackup',                                  status: 'Active' },
  { pkg: 'com.android.cameraextensions',                               status: 'Active' },
  { pkg: 'com.android.carrierconfig',                                  status: 'Active' },
  { pkg: 'com.android.carrierdefaultapp',                              status: 'Active' },
  { pkg: 'com.android.certinstaller',                                  status: 'Active' },
  { pkg: 'com.android.chrome',                                         status: 'Active' },
  { pkg: 'com.android.companiondevicemanager',                         status: 'Active' },
  { pkg: 'com.android.companiondevicemanager.auto_generated_characteristics_rro', status: 'Active' },
  { pkg: 'com.android.credentialmanager',                              status: 'Active' },
  { pkg: 'com.android.documentsui',                                    status: 'Active' },
  { pkg: 'com.android.dynsystem',                                      status: 'Active' },
  { pkg: 'com.android.egg',                                            status: 'Active' },
  { pkg: 'com.android.emergency',                                      status: 'Active' },
  { pkg: 'com.android.externalstorage',                                status: 'Active' },
  { pkg: 'com.android.htmlviewer',                                     status: 'Active' },
  { pkg: 'com.android.inputdevices',                                   status: 'Active' },
  { pkg: 'com.android.internal.systemui.navbar.gestural',              status: 'Active' },
];

const MOCK_DEPS = [
  { name: 'ADB (platform-tools)', installed: '37.0.0', latest: '37.0.0', status: 'up-to-date' },
  { name: 'scrcpy',               installed: '4.0',    latest: '4.0',    status: 'up-to-date' },
  { name: 'bundletool',           installed: '1.18.3', latest: '1.19.0', status: 'update'     },
];

const MODULES = [
  { id: 'connections',    label: 'Connections',    icon: 'IconLink',     kbd: 'Ctrl+1' },
  { id: 'terminal',       label: 'Terminal',       icon: 'IconTerminal', kbd: 'Ctrl+2' },
  { id: 'installer',      label: 'Installer',      icon: 'IconPackage',  kbd: 'Ctrl+3' },
  { id: 'scrcpy',         label: 'Scrcpy',         icon: 'IconCast',     kbd: 'Ctrl+4' },
  { id: 'device-buttons', label: 'Device Buttons', icon: 'IconGrid',     kbd: 'Ctrl+5' },
  { id: 'device-info',    label: 'Device Info',    icon: 'IconInfo',     kbd: 'Ctrl+6' },
  { id: 'apps',           label: 'Apps',           icon: 'IconApps',     kbd: 'Ctrl+7' },
  { id: 'logcat',         label: 'Logcat',         icon: 'IconLog',      kbd: 'Ctrl+8' },
];

const MODULES_FOOT = [
  { id: 'settings',       label: 'Settings',       icon: 'IconSettings', kbd: 'Ctrl+,' },
];

Object.assign(window, {
  MOCK_DEVICES, MOCK_PAIRED, MOCK_APK_QUEUE,
  MOCK_DEVICE_INFO, MOCK_BUTTONS, MOCK_APPS, MOCK_DEPS,
  MODULES, MODULES_FOOT,
});
