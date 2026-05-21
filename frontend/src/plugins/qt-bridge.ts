/* QWebChannel bootstrap.
 *
 * IMPORTANT design notes:
 *  - qwebchannel.js is vendored at src/assets/qwebchannel.js so we don't
 *    depend on qrc:// at runtime (which doesn't work under Vite's HTTP
 *    dev server) and so a plain browser can also load the SPA for visual
 *    work.  We import it as ESM and read window.QWebChannel as a fallback.
 *  - Registered Python QObjects appear under `channel.objects`, NOT on
 *    `channel` itself. Resolving `channel` directly would yield
 *    "TypeError: undefined is not a function" on every slot call.
 */
import { QWebChannel as QWebChannelMod } from "@/assets/qwebchannel.js";
import type { QtBridges } from "@/types/qt-bridge";

declare global {
  interface Window {
    qt?: { webChannelTransport: any };
    QWebChannel: any;
  }
}

const QWebChannel: any =
  QWebChannelMod ?? (typeof window !== "undefined" ? window.QWebChannel : undefined);

let _bridges: QtBridges | null = null;
let _ready: Promise<QtBridges> | null = null;

export function initBridge(): Promise<QtBridges> {
  if (_ready) return _ready;
  _ready = new Promise<QtBridges>((resolve) => {
    if (typeof window === "undefined" || !window.qt?.webChannelTransport) {
      console.warn("[qt-bridge] No Qt transport — running in browser-only mock mode.");
      _bridges = mockBridges();
      resolve(_bridges);
      return;
    }
    /* eslint-disable @typescript-eslint/no-explicit-any */
    new QWebChannel(window.qt.webChannelTransport, (ch: any) => {
      _bridges = ch.objects as QtBridges;
      resolve(_bridges);
    });
  });
  return _ready;
}

export function useBridge(): QtBridges {
  if (!_bridges) {
    throw new Error("qt-bridge not ready — await initBridge() before mounting Vue");
  }
  return _bridges;
}

export function isMockBridge(): boolean {
  return _bridges !== null && (_bridges as any).__mock === true;
}

function mockBridges(): QtBridges {
  // Stub so Vue components don't blow up in a plain browser.
  //   - slot calls return Promise<[]>  (NOT undefined) so callers doing
  //       arr.value = await bridge.x.list()
  //     get a valid iterable.
  //   - bridge-level proxies are CACHED so identity is stable:
  //       bridge.terminal === bridge.terminal
  //     This matters because useSignal() captures a reference and later
  //     calls .disconnect() — without caching, disconnect runs against a
  //     different noopSignal than the one connect was called on.
  const slot = (..._args: any[]) => Promise.resolve([] as any);
  const noopSignal = { connect: () => {}, disconnect: () => {} };

  function makeBridgeProxy(): any {
    const signalCache = new Map<string | symbol, any>();
    return new Proxy(slot, {
      get(_t, prop) {
        if (!signalCache.has(prop)) signalCache.set(prop, noopSignal);
        return signalCache.get(prop);
      },
    });
  }

  const bridgeCache = new Map<string | symbol, any>();
  const proxy = new Proxy(
    {},
    {
      get(_t, prop) {
        if (prop === "__mock") return true;
        if (!bridgeCache.has(prop)) bridgeCache.set(prop, makeBridgeProxy());
        return bridgeCache.get(prop);
      },
    },
  );
  return proxy as unknown as QtBridges;
}
