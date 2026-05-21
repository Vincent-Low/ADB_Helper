// Reusable input filter helpers. Designed for v-on:input / v-on:beforeinput.

const IPV4_PROGRESS_RE = /^(\d{1,3}\.){0,3}\d{0,3}$/;
const IPV4_VALID_RE =
  /^((25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)$/;

export function isValidIPv4(v: string): boolean {
  return IPV4_VALID_RE.test(v);
}

// Sanitize partial IPv4 typing — keeps only digits and dots, max 3 dots, max 3
// digits per octet, max-octet-value 255. Empty input allowed.
export function sanitizeIPv4Partial(raw: string): string {
  let s = raw.replace(/[^0-9.]/g, "");
  const parts = s.split(".");
  const trimmed: string[] = [];
  for (let i = 0; i < parts.length && i < 4; i++) {
    let p = parts[i].slice(0, 3);
    if (p.length === 3 && Number(p) > 255) p = p.slice(0, 2);
    trimmed.push(p);
  }
  s = trimmed.join(".");
  if (!IPV4_PROGRESS_RE.test(s)) {
    // Shouldn't happen with sanitised pieces, but cut to last valid prefix.
    while (s && !IPV4_PROGRESS_RE.test(s)) s = s.slice(0, -1);
  }
  return s;
}

// Sanitize numeric-only input limited to `max` digits.
export function sanitizeDigits(raw: string, max: number): string {
  return raw.replace(/\D+/g, "").slice(0, max);
}

// Sanitize a TCP/UDP port (1–65535). Returns digits-only, max 5 chars,
// never exceeding 65535 numerically.
export function sanitizePort(raw: string): string {
  let digits = raw.replace(/\D+/g, "").slice(0, 5);
  // Strip leading zeros for multi-digit numbers but keep single "0" allowed
  // visually so user can keep typing — final validity check via isValidPort.
  if (digits.length > 1) digits = digits.replace(/^0+/, "");
  if (digits.length === 5 && Number(digits) > 65535) digits = digits.slice(0, 4);
  return digits;
}

export function isValidPort(v: string | number): boolean {
  const n = typeof v === "string" ? parseInt(v, 10) : v;
  return Number.isInteger(n) && n >= 1 && n <= 65535;
}
