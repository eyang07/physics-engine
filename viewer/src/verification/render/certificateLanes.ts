/**
 * Framework-free certificate-lane drawing (FE-056).
 *
 * The pure Canvas 2D drawing for one certificate lane, lifted out of
 * `certificateLanes.ts` so the rendering is independent of the DOM/class that
 * owns the lane rows. `CertificateLanes` (vanilla) and the FE-057 React wrapper
 * both call `drawCertificateLane` with a lane's draw state; behaviour and pixels
 * are identical to the previous in-class `drawLane`.
 */
import { dossier } from "../../design/dossier";
import type { CertificateSeries } from "../../data/trajectory";
import { clamp } from "../../util";

/** The tightest sampled record for one obligation (BE-036): its signed worst
 * margin to the boundary and the worst sampled candidate value, the same
 * measured evidence the ledger headlines. */
export type ObligationWorst = { margin: number; value: number | null };

/** The draw state one certificate lane needs — the canvas-only subset of the
 * lane the owning class holds. The full `Lane` (with its DOM row/readout) is a
 * structural superset, so it satisfies this without conversion. */
export type CertificateLaneRender = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  values: number[];
  baseline: number;
  amplitude: number;
  // The selected obligation's worst record, drawn as a closest-approach level on
  // this lane while that obligation is selected; null when nothing is selected
  // or this lane does not bear on it.
  selectedWorst: ObligationWorst | null;
};

function prepareCanvas(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D): {
  width: number;
  height: number;
} {
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const drawWidth = Math.max(1, Math.floor(width * pixelRatio));
  const drawHeight = Math.max(1, Math.floor(height * pixelRatio));
  if (canvas.width !== drawWidth || canvas.height !== drawHeight) {
    canvas.width = drawWidth;
    canvas.height = drawHeight;
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }
  ctx.clearRect(0, 0, width, height);
  return { width, height };
}

// The certificate value v(t) drawn against its obligation threshold (dashed
// baseline). The curve auto-scales to its own excursion so its sign and shape
// relative to the threshold read clearly; the playhead tracks the run.
export function drawCertificateLane(lane: CertificateLaneRender, phase: number): void {
  const { canvas, ctx, values, baseline, amplitude, selectedWorst } = lane;
  const { width, height } = prepareCanvas(canvas, ctx);

  const count = values.length;
  if (count === 0) {
    return;
  }
  const pad = 5;
  const amp = amplitude > 0 ? amplitude : 1;
  const mid = height / 2;
  const yOf = (value: number) =>
    clamp(mid - ((value - baseline) / amp) * (height / 2 - pad), pad, height - pad);
  const xOf = (index: number) => (count <= 1 ? 0 : (index / (count - 1)) * width);
  const step = Math.max(1, Math.floor(count / 320));

  // The obligation threshold (the `≤ 0` baseline), a dashed ink-graphite rule.
  ctx.save();
  ctx.setLineDash([3, 4]);
  ctx.strokeStyle = dossier.hairline;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(width, mid);
  ctx.stroke();
  ctx.restore();

  // The selected obligation's worst sampled candidate value (BE-036), as a
  // closest-approach level on this lane: the gap from the threshold baseline to
  // this level is the signed worst margin the readout names. Measured evidence
  // drawn against the rollout, never a proof.
  if (selectedWorst && selectedWorst.value !== null && Number.isFinite(selectedWorst.value)) {
    const wy = yOf(selectedWorst.value);
    ctx.save();
    ctx.setLineDash([2, 3]);
    ctx.strokeStyle = dossier.graphite;
    ctx.lineWidth = 1.25;
    ctx.beginPath();
    ctx.moveTo(0, wy);
    ctx.lineTo(width, wy);
    ctx.stroke();
    ctx.restore();
  }

  // The measured signal: a soft teal area under a teal trace — no glow.
  ctx.beginPath();
  ctx.moveTo(0, mid);
  for (let index = 0; index < count; index += step) {
    ctx.lineTo(xOf(index), yOf(values[index]));
  }
  ctx.lineTo(xOf(count - 1), mid);
  ctx.closePath();
  ctx.fillStyle = "rgba(21, 112, 107, 0.12)";
  ctx.fill();

  ctx.strokeStyle = dossier.measured;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let index = 0; index < count; index += step) {
    const x = xOf(index);
    const y = yOf(values[index]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  const playIndex = clamp(Math.round(phase * (count - 1)), 0, count - 1);
  ctx.fillStyle = dossier.ink;
  ctx.beginPath();
  ctx.arc(clamp(phase, 0, 1) * width, yOf(values[playIndex]), 3, 0, Math.PI * 2);
  ctx.fill();
}

// ---------------------------------------------------------------------------
// Lane preparation (FE-057)
//
// The pure classification/labelling and metric logic that turns an exported
// `CertificateSeries` into a renderable lane descriptor, shared by the vanilla
// `CertificateLanes` (DOM rows) and the React `CertificateTraces` wrapper so
// neither re-derives the labels. These name the series; they classify nothing.
// ---------------------------------------------------------------------------

const COMPARISON_LATEX: Record<string, string> = {
  "<=": "\\le",
  "<": "<",
  ">=": "\\ge",
  ">": ">",
  "==": "=",
  "=": "=",
};

// A structural constant (the obligation threshold), trimmed — not a measured
// magnitude.
function constantLatex(value: number): string {
  if (Object.is(value, -0) || Math.abs(value) < 1e-12) {
    return "0";
  }
  return Number(value.toFixed(3))
    .toString()
    .replace(/\.?0+$/, "");
}

// A Lyapunov candidate reads as V, a barrier (the default) as B. Derived from
// the exported candidate id — the lane labels the series, it does not classify.
function baseSymbol(record: CertificateSeries): string {
  return (record.candidateId ?? "").toLowerCase().includes("lyapunov") ? "V" : "B";
}

// A safe-set barrier lane: a candidate-value series for a barrier that bears on
// at least one obligation. When a package carries two or more of these together,
// its safe set is their intersection (FE-027).
function isSafeSetBarrierLane(record: CertificateSeries): boolean {
  return (
    record.kind === "candidate-value" &&
    record.obligationIds.length > 0 &&
    baseSymbol(record) === "B"
  );
}

// A readable name for a barrier lane, humanized from the exported candidate id
// (e.g. `geofence-box-barrier` -> `geofence box`). Labels the series; it does
// not reclassify it.
function barrierLabel(record: CertificateSeries): string {
  const id = record.candidateId ?? "";
  const trimmed = id.replace(/-?barrier$/i, "").replace(/[-_]+/g, " ").trim();
  return trimmed || id || "barrier";
}

function symbolLatex(record: CertificateSeries): string {
  const base = baseSymbol(record);
  return record.kind === "flow-derivative" ? `\\dot{${base}}` : base;
}

// Show `symbol <comparison> rhs` when one comparison applies (e.g. the
// non-increase obligation `\dot B \le 0`). Region-conditional value obligations
// impose more than one, so there the threshold is ambiguous and we omit it.
function captionLatex(record: CertificateSeries): string | null {
  const comparisons = new Set(record.comparisonBaselines.map((baseline) => baseline.comparison));
  if (comparisons.size !== 1) {
    return null;
  }
  const baseline = record.comparisonBaselines[0];
  const comparison = COMPARISON_LATEX[baseline.comparison] ?? baseline.comparison;
  return `${symbolLatex(record)} ${comparison} ${constantLatex(baseline.rhs)}`;
}

// The lane's vertical excursion from its threshold baseline, used to auto-scale
// the trace so its sign and shape relative to the threshold read clearly.
function laneAmplitude(values: number[], baseline: number): number {
  let amplitude = 0;
  for (const value of values) {
    amplitude = Math.max(amplitude, Math.abs(value - baseline));
  }
  return amplitude;
}

/** A renderable certificate lane: the measured series plus its labels and the
 * auto-scaling metrics, derived once from an exported `CertificateSeries`. */
export type CertificateLaneDescriptor = {
  /** The trajectory series key this lane plots. */
  series: string;
  obligationIds: string[];
  values: number[];
  baseline: number;
  amplitude: number;
  symbolLatex: string;
  /** The `symbol <cmp> rhs` caption, or null when the threshold is ambiguous. */
  captionLatex: string | null;
  /** The plain caption shown when `captionLatex` is null. */
  captionFallback: string;
  /** The humanized barrier name, set only for intersection-named barrier lanes. */
  barrierLabel: string | null;
};

export type PreparedCertificateLanes = {
  lanes: CertificateLaneDescriptor[];
  /** True when the package carries two or more safe-set barrier lanes, whose
   * safe set is their intersection (FE-027). */
  isIntersection: boolean;
};

/** Turn a problem's certificate series + records into renderable lane
 * descriptors. Records whose series carry no values are dropped, mirroring the
 * vanilla lane builder. */
export function prepareCertificateLanes(
  series: Record<string, number[]>,
  records: CertificateSeries[],
): PreparedCertificateLanes {
  // An intersection safe set carries two or more safe-set barrier lanes
  // together; only then do the lanes name each barrier and state the
  // intersection semantics, leaving single-barrier packages unchanged.
  const isIntersection = records.filter(isSafeSetBarrierLane).length >= 2;
  const lanes: CertificateLaneDescriptor[] = [];
  for (const record of records) {
    const values = series[record.series];
    if (!values || values.length === 0) {
      continue;
    }
    const baseline = record.comparisonBaselines[0]?.rhs ?? 0;
    lanes.push({
      series: record.series,
      obligationIds: record.obligationIds,
      values,
      baseline,
      amplitude: laneAmplitude(values, baseline),
      symbolLatex: symbolLatex(record),
      captionLatex: captionLatex(record),
      captionFallback: record.kind === "flow-derivative" ? "flow derivative" : "candidate value",
      barrierLabel: isIntersection && isSafeSetBarrierLane(record) ? barrierLabel(record) : null,
    });
  }
  return { lanes, isIntersection };
}
