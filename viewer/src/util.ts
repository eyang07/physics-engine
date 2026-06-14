export function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

// Compact rendering for a measured sample value: a few significant figures,
// trailing zeros trimmed, so a worst-case sample reads cleanly. Deterministic
// for a given input so generated views stay regenerable.
export function formatMeasured(value: number): string {
  if (!Number.isFinite(value)) {
    return String(value);
  }
  if (value === 0) {
    return "0";
  }
  return Number(value.toPrecision(3)).toString();
}
