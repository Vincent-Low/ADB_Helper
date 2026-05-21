/* Auto-disconnecting QWebChannel signal subscriber.
 *
 * Usage inside <script setup>:
 *   const on = useSignal();
 *   onMounted(() => on(bridge.terminal.output, (b64) => term.write(...)));
 *
 * Connections registered through `on` are automatically `.disconnect()`d
 * in `onBeforeUnmount`.  Prevents the duplicate-handler bug when a
 * `<KeepAlive :max=N>` view is evicted and later re-mounted.
 */
import { getCurrentInstance, onBeforeUnmount } from "vue";
import type { QtSignal } from "@/types/qt-bridge";

export function useSignal() {
  const handlers: Array<() => void> = [];

  // Tie cleanup to the component instance if we have one (we will, inside
  // a setup() call).  When called outside setup we just leak — caller error.
  if (getCurrentInstance()) {
    onBeforeUnmount(() => {
      while (handlers.length) {
        try {
          handlers.pop()!();
        } catch {
          /* ignore — bridge may already be torn down */
        }
      }
    });
  }

  return function on<T extends any[]>(
    signal: QtSignal<T>,
    cb: (...args: T) => void,
  ): void {
    signal.connect(cb);
    handlers.push(() => signal.disconnect(cb));
  };
}
