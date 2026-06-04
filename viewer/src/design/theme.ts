/**
 * Chrome palette access for canvas / WebGL code.
 *
 * The single source of truth is design/tokens.css. We read the CSS custom
 * properties lazily (on first use, after the stylesheet is applied) and cache
 * resolved values, so JS-drawn surfaces stay in lockstep with the chrome
 * tokens. Fallbacks mirror the token defaults to guard against very early
 * reads. Data colormaps (fields/flow/fluids) are NOT here — see
 * design/colormaps.ts.
 */
const cache = new Map<string, string>();

function token(name: string, fallback: string): string {
  const cached = cache.get(name);
  if (cached !== undefined) {
    return cached;
  }
  let value = "";
  if (typeof document !== "undefined") {
    value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }
  // Only cache once the stylesheet is actually applied; otherwise fall back
  // and retry on a later access (e.g. inside the render loop).
  if (value) {
    cache.set(name, value);
    return value;
  }
  return fallback;
}

export const theme = {
  get ink900() {
    return token("--ink-900", "#0d1117");
  },
  get ink850() {
    return token("--ink-850", "#10151d");
  },
  get ink800() {
    return token("--ink-800", "#131a24");
  },
  get ink700() {
    return token("--ink-700", "#1a212c");
  },
  get hairline() {
    return token("--hairline", "rgba(255, 255, 255, 0.09)");
  },
  get hairlineStrong() {
    return token("--hairline-strong", "rgba(255, 255, 255, 0.16)");
  },
  get textPrimary() {
    return token("--text-primary", "#e8edf2");
  },
  get textMuted() {
    return token("--text-muted", "#8a94a6");
  },
  get textFaint() {
    return token("--text-faint", "rgba(232, 237, 242, 0.45)");
  },
  get accent() {
    return token("--accent", "#f0b46a");
  },
  get accentStrong() {
    return token("--accent-strong", "#f6cd92");
  },
  get cool() {
    return token("--cool", "#6fb6c9");
  },
};
