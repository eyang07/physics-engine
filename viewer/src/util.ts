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

// Like `formatMeasured`, but always carries an explicit sign so a signed margin
// reads unambiguously (e.g. `+0.01` of slack vs. `-0.01` of violation). Negative
// values already render with a leading "-"; positive ones gain a leading "+".
export function formatSignedMeasured(value: number): string {
  const formatted = formatMeasured(value);
  return Number.isFinite(value) && value > 0 ? `+${formatted}` : formatted;
}
