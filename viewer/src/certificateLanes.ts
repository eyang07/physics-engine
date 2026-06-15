/**
 * Candidate-certificate lanes for the Verification world.
 *
 * Given the controlled trajectory's certificate series (the barrier/Lyapunov
 * value B(x(t)) and its flow derivative), this draws each as a lane against its
 * obligation threshold — measured signal only, qualitative, no decimals. The
 * pass/fail verdict lives in the proof-status surface, not here. Crossings track
 * playback via the shared phase.
 */
import katex from "katex";

import { theme } from "./design/theme";
import { magma } from "./design/colormaps";
import type { CertificateSeries } from "./data/trajectory";
import { clamp } from "./util";

type Lane = {
  row: HTMLElement;
  obligationIds: string[];
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  values: number[];
  baseline: number;
  amplitude: number;
};

const COMPARISON_LATEX: Record<string, string> = {
  "<=": "\\le",
  "<": "<",
  ">=": "\\ge",
  ">": ">",
  "==": "=",
  "=": "=",
};

function renderLatex(element: HTMLElement, latex: string): void {
  katex.render(latex, element, { throwOnError: false, displayMode: false });
}

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

export class CertificateLanes {
  private lanes: Lane[] = [];

  constructor(private readonly container: HTMLElement) {}

  get count(): number {
    return this.lanes.length;
  }

  clear(): void {
    this.container.replaceChildren();
    this.lanes = [];
  }

  show(series: Record<string, number[]>, records: CertificateSeries[]): void {
    this.clear();
    records.forEach((record) => this.buildRow(record, series));
  }

  update(phase: number): void {
    this.lanes.forEach((lane) => drawLane(lane, phase));
  }

  // Emphasize the lanes that bear on a selected obligation and dim the rest; a
  // null selection clears all emphasis. Lets the obligation surfaces show which
  // measured signal supports which obligation.
  setEmphasis(obligationId: string | null): void {
    this.lanes.forEach((lane) => {
      lane.row.classList.remove("diagnostic--emphasized", "diagnostic--dimmed");
      if (obligationId === null) {
        return;
      }
      lane.row.classList.add(
        lane.obligationIds.includes(obligationId) ? "diagnostic--emphasized" : "diagnostic--dimmed",
      );
    });
  }

  private buildRow(record: CertificateSeries, series: Record<string, number[]>): void {
    const values = series[record.series];
    if (!values || values.length === 0) {
      return;
    }
    const baseline = record.comparisonBaselines[0]?.rhs ?? 0;
    let amplitude = 0;
    for (const value of values) {
      amplitude = Math.max(amplitude, Math.abs(value - baseline));
    }

    const row = document.createElement("div");
    row.className = "diagnostic";
    row.dataset.obligations = record.obligationIds.join(" ");

    const head = document.createElement("div");
    head.className = "diagnostic__head";
    const symbol = document.createElement("span");
    symbol.className = "diagnostic__symbol";
    renderLatex(symbol, symbolLatex(record));
    const caption = document.createElement("span");
    caption.className = "diagnostic__caption";
    const latex = captionLatex(record);
    if (latex) {
      renderLatex(caption, latex);
    } else {
      caption.textContent = record.kind === "flow-derivative" ? "flow derivative" : "candidate value";
    }
    head.append(symbol, caption);

    const lane = document.createElement("canvas");
    lane.className = "diagnostic__residual diagnostic__certificate";
    row.append(head, lane);
    this.container.append(row);

    const laneCtx = lane.getContext("2d");
    if (laneCtx) {
      this.lanes.push({
        row,
        obligationIds: record.obligationIds,
        canvas: lane,
        ctx: laneCtx,
        values,
        baseline,
        amplitude,
      });
    }
  }
}

// The certificate value v(t) drawn against its obligation threshold (dashed
// baseline). The curve auto-scales to its own excursion so its sign and shape
// relative to the threshold read clearly; the playhead tracks the run.
function drawLane(lane: Lane, phase: number): void {
  const { canvas, ctx, values, baseline, amplitude } = lane;
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

  ctx.save();
  ctx.setLineDash([3, 4]);
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(width, mid);
  ctx.stroke();
  ctx.restore();

  ctx.beginPath();
  ctx.moveTo(0, mid);
  for (let index = 0; index < count; index += step) {
    ctx.lineTo(xOf(index), yOf(values[index]));
  }
  ctx.lineTo(xOf(count - 1), mid);
  ctx.closePath();
  ctx.fillStyle = magma.css(0.72, 0.14);
  ctx.fill();

  ctx.strokeStyle = theme.accent;
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
  ctx.fillStyle = theme.accentStrong;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.arc(clamp(phase, 0, 1) * width, yOf(values[playIndex]), 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
}
