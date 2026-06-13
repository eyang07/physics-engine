/**
 * The Diagnostics panel: exported phase-space structure, still symbols-only.
 *
 * It renders the diagnostics the Python engine attached to a trajectory's
 * metadata — never recomputing physics, only reading exported series and
 * crossings:
 *
 *   - the finite-time Lyapunov estimate λ(t) as a converging curve against a
 *     neutral baseline (settling above the baseline = sensitive dependence;
 *     hugging it = neutral). The shaded gap is the qualitative magnitude; no
 *     decimal is ever shown.
 *   - each Poincaré section as a scatter of crossing markers in its exported
 *     axes (no numeric ticks). Crossings light up as playback reaches them.
 *
 * Like the Structure panel, it is driven entirely by the manifest/export
 * contract and shows no measured numbers.
 */
import katex from "katex";

import { theme } from "./design/theme";
import { magma } from "./design/colormaps";
import {
  certificateSeries,
  invariantResiduals,
  lyapunovDiagnostic,
  poincareSections,
  type CertificateSeries,
  type InvariantResidual,
  type PoincareSection,
  type Trajectory,
} from "./data/trajectory";
import { clamp } from "./util";

type LyapunovLane = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  series: number[];
  domainMin: number;
  domainMax: number;
};

type ResidualLane = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  // The drift r(t) = q(t) - reference, computed once from exported data.
  residual: number[];
  amplitude: number;
};

type SectionPlot = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  points: { x: number; y: number; normTime: number }[];
  bounds: { minX: number; maxX: number; minY: number; maxY: number };
};

type CertificateLane = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  // The candidate series v(t) and the obligation threshold it is read against.
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

// Structural constant for a section definition (e.g. y = 0). Trimmed, not a
// measured magnitude — same category as the constants in a rendered Lagrangian.
function constantLatex(value: number): string {
  if (Object.is(value, -0) || Math.abs(value) < 1e-12) {
    return "0";
  }
  return Number(value.toFixed(3))
    .toString()
    .replace(/\.?0+$/, "");
}

const GREEK_TO_LATEX: Record<string, string> = {
  ell: "\\ell",
  phi: "\\phi",
  theta: "\\theta",
  psi: "\\psi",
  omega: "\\omega",
};

// The conserved-quantity name as LaTeX (the trajectory metadata carries only the
// identifier, not the manifest's LaTeX): split a `base_sub` and translate Greek
// words, so `p_phi` -> p_{\phi} and `ell` -> \ell.
function invariantSymbolLatex(name: string): string {
  const split = name.match(/^([A-Za-z]+)_([A-Za-z0-9]+)$/);
  if (split) {
    const base = GREEK_TO_LATEX[split[1]] ?? split[1];
    const sub = GREEK_TO_LATEX[split[2]] ?? split[2];
    return `${base}_{${sub}}`;
  }
  return GREEK_TO_LATEX[name] ?? name;
}

// The conservation quality as an order of magnitude only — never a precise
// decimal. `Delta H <~ 10^-8` reads as "deviates by at most about that, relative
// to its scale", which is honest measured evidence of integrator quality.
function residualMagnitudeLatex(residual: InvariantResidual, amplitude: number): string {
  const relative =
    residual.maxRelative ??
    (residual.scale && residual.scale !== 0 ? amplitude / Math.abs(residual.scale) : undefined);
  if (relative === undefined || !Number.isFinite(relative) || relative <= 0) {
    return "\\text{conserved}";
  }
  return `\\lesssim 10^{${Math.floor(Math.log10(relative))}}`;
}

// A robust display window for the running estimate: clip the brief initial
// transient with 2nd/98th percentiles, but always keep the neutral baseline
// (λ = 0) in view so "settles above zero" vs "hugs zero" reads honestly.
function robustDomain(series: number[]): { min: number; max: number } {
  if (series.length === 0) {
    return { min: 0, max: 1 };
  }
  const sorted = [...series].sort((a, b) => a - b);
  const quantile = (p: number) =>
    sorted[clamp(Math.round(p * (sorted.length - 1)), 0, sorted.length - 1)];
  let min = Math.min(0, quantile(0.02));
  let max = Math.max(0, quantile(0.98));
  if (max - min < 1e-9) {
    max = min + 1e-9;
  }
  return { min, max };
}

export class DiagnosticsPanel {
  private lyapunovLane: LyapunovLane | null = null;
  private sectionPlots: SectionPlot[] = [];
  private residualLanes: ResidualLane[] = [];
  private certificateLanes: CertificateLane[] = [];

  constructor(
    private readonly section: HTMLElement,
    private readonly content: HTMLElement,
  ) {}

  clear(): void {
    this.content.replaceChildren();
    this.lyapunovLane = null;
    this.sectionPlots = [];
    this.residualLanes = [];
    this.certificateLanes = [];
    this.section.hidden = true;
  }

  show(data: Trajectory): void {
    this.clear();
    this.renderLyapunov(data);
    this.renderResiduals(data);
    this.renderCertificates(data);
    this.renderSections(data);
    this.section.hidden =
      this.lyapunovLane === null &&
      this.sectionPlots.length === 0 &&
      this.residualLanes.length === 0 &&
      this.certificateLanes.length === 0;
  }

  update(phase: number): void {
    if (this.lyapunovLane) {
      drawLyapunovLane(this.lyapunovLane, phase);
    }
    this.residualLanes.forEach((lane) => drawResidualLane(lane, phase));
    this.certificateLanes.forEach((lane) => drawCertificateLane(lane, phase));
    this.sectionPlots.forEach((plot) => drawSectionPlot(plot, phase));
  }

  // The measured conservation drift of each invariant: r(t) = q(t) - reference,
  // drawn against a zero baseline (perfect conservation). The curve is
  // auto-scaled to its own tiny amplitude so its *shape* — flat, oscillating, or
  // drifting — is legible; the caption gives the order of magnitude only.
  private renderResiduals(data: Trajectory): void {
    invariantResiduals(data).forEach((residual) => this.buildResidualRow(residual, data));
  }

  private buildResidualRow(residual: InvariantResidual, data: Trajectory): void {
    const series = residual.series ? data.series?.[residual.series] : undefined;
    if (!series || series.length === 0) {
      return;
    }
    const reference = residual.reference ?? series[0];
    const drift = series.map((value) => value - reference);
    let amplitude = 0;
    for (const value of drift) {
      amplitude = Math.max(amplitude, Math.abs(value));
    }

    const row = document.createElement("div");
    row.className = "diagnostic";

    const head = document.createElement("div");
    head.className = "diagnostic__head";
    const symbol = document.createElement("span");
    symbol.className = "diagnostic__symbol";
    renderLatex(symbol, `\\Delta ${invariantSymbolLatex(residual.name)}`);
    const caption = document.createElement("span");
    caption.className = "diagnostic__caption";
    renderLatex(caption, residualMagnitudeLatex(residual, amplitude));
    head.append(symbol, caption);

    const lane = document.createElement("canvas");
    lane.className = "diagnostic__residual";
    row.append(head, lane);
    this.content.append(row);

    const laneCtx = lane.getContext("2d");
    if (laneCtx) {
      this.residualLanes.push({ canvas: lane, ctx: laneCtx, residual: drift, amplitude });
    }
  }

  // Candidate-certificate values sampled along the trajectory: the barrier (or
  // Lyapunov) value B(x(t)) and its flow derivative, each drawn against the
  // obligation threshold. This is measured signal only — the pass/fail verdict
  // lives in the Verification domain's proof-status surface, never here.
  private renderCertificates(data: Trajectory): void {
    certificateSeries(data).forEach((record) => this.buildCertificateRow(record, data));
  }

  private buildCertificateRow(record: CertificateSeries, data: Trajectory): void {
    const series = data.series?.[record.series];
    if (!series || series.length === 0) {
      return;
    }
    const baseline = record.comparisonBaselines[0]?.rhs ?? 0;
    let amplitude = 0;
    for (const value of series) {
      amplitude = Math.max(amplitude, Math.abs(value - baseline));
    }

    const row = document.createElement("div");
    row.className = "diagnostic";

    const head = document.createElement("div");
    head.className = "diagnostic__head";
    const symbol = document.createElement("span");
    symbol.className = "diagnostic__symbol";
    renderLatex(symbol, certificateSymbolLatex(record));
    const caption = document.createElement("span");
    caption.className = "diagnostic__caption";
    const captionLatex = certificateCaptionLatex(record);
    if (captionLatex) {
      renderLatex(caption, captionLatex);
    } else {
      caption.textContent = record.kind === "flow-derivative" ? "flow derivative" : "candidate value";
    }
    head.append(symbol, caption);

    const lane = document.createElement("canvas");
    lane.className = "diagnostic__residual diagnostic__certificate";
    row.append(head, lane);
    this.content.append(row);

    const laneCtx = lane.getContext("2d");
    if (laneCtx) {
      this.certificateLanes.push({ canvas: lane, ctx: laneCtx, values: series, baseline, amplitude });
    }
  }

  private renderLyapunov(data: Trajectory): void {
    const diagnostic = lyapunovDiagnostic(data);
    const seriesName = diagnostic?.series;
    const series = seriesName ? data.series?.[seriesName] : undefined;
    if (!diagnostic || !series || series.length === 0) {
      return;
    }

    const row = document.createElement("div");
    row.className = "diagnostic";

    const head = document.createElement("div");
    head.className = "diagnostic__head";
    const symbol = document.createElement("span");
    symbol.className = "diagnostic__symbol";
    renderLatex(symbol, "\\lambda");
    const caption = document.createElement("span");
    caption.className = "diagnostic__caption";
    caption.textContent = lyapunovCaption(diagnostic.kind, diagnostic.method);
    head.append(symbol, caption);

    const lane = document.createElement("canvas");
    lane.className = "diagnostic__lyapunov";
    row.append(head, lane);
    this.content.append(row);

    const laneCtx = lane.getContext("2d");
    if (laneCtx) {
      const { min, max } = robustDomain(series);
      this.lyapunovLane = { canvas: lane, ctx: laneCtx, series, domainMin: min, domainMax: max };
    }
  }

  private renderSections(data: Trajectory): void {
    const sections = poincareSections(data);
    if (sections.length === 0) {
      return;
    }
    const time = data.time ?? [];
    const tStart = time.length > 0 ? time[0] : 0;
    const tEnd = time.length > 0 ? time[time.length - 1] : 1;
    const tSpan = tEnd - tStart || 1;

    sections.forEach((section) => {
      const plot = this.buildSectionPlot(section, tStart, tSpan);
      if (plot) {
        this.sectionPlots.push(plot);
      }
    });
  }

  private buildSectionPlot(
    section: PoincareSection,
    tStart: number,
    tSpan: number,
  ): SectionPlot | null {
    if (section.points.length === 0) {
      return null;
    }
    const row = document.createElement("div");
    row.className = "diagnostic";

    const head = document.createElement("div");
    head.className = "diagnostic__head";
    const symbol = document.createElement("span");
    symbol.className = "diagnostic__symbol";
    renderLatex(symbol, sectionConditionLatex(section));
    const caption = document.createElement("span");
    caption.className = "diagnostic__caption";
    renderLatex(caption, `\\left(${axisLatex(section.axes[0])},\\ ${axisLatex(section.axes[1])}\\right)`);
    head.append(symbol, caption);

    const canvas = document.createElement("canvas");
    canvas.className = "diagnostic__section";
    row.append(head, canvas);
    this.content.append(row);

    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return null;
    }

    const points = section.points.map((point) => ({
      x: point.axisValues[0],
      y: point.axisValues[1],
      normTime: typeof point.time === "number" ? clamp((point.time - tStart) / tSpan, 0, 1) : 0,
    }));
    let minX = Infinity;
    let maxX = -Infinity;
    let minY = Infinity;
    let maxY = -Infinity;
    points.forEach(({ x, y }) => {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    });

    return { canvas, ctx, points, bounds: { minX, maxX, minY, maxY } };
  }
}

function lyapunovCaption(kind?: string, method?: string): string {
  // Drive the caption from exported metadata, not from any computed threshold:
  // the panel describes the diagnostic, it does not classify the system.
  const words = (kind ?? "").split("-").filter(Boolean);
  const phrase = words.length > 0 ? words.join(" ") : "lyapunov";
  return method?.includes("variational") ? `${phrase} · variational` : phrase;
}

// The certificate's base symbol: a Lyapunov candidate reads as V, a barrier
// (the default) as B. Derived from the exported candidate id — the panel only
// labels the exported series, it does not classify the certificate.
function certificateBaseSymbol(record: CertificateSeries): string {
  return (record.candidateId ?? "").toLowerCase().includes("lyapunov") ? "V" : "B";
}

function certificateSymbolLatex(record: CertificateSeries): string {
  const base = certificateBaseSymbol(record);
  return record.kind === "flow-derivative" ? `\\dot{${base}}` : base;
}

// Show the obligation threshold as `symbol <comparison> rhs` when the series is
// read against a single comparison (e.g. the non-increase obligation
// `\dot B \le 0`). Region-conditional value obligations impose more than one
// comparison, so there the threshold is ambiguous and we fall back to a word
// caption.
function certificateCaptionLatex(record: CertificateSeries): string | null {
  const comparisons = new Set(record.comparisonBaselines.map((baseline) => baseline.comparison));
  if (comparisons.size !== 1) {
    return null;
  }
  const baseline = record.comparisonBaselines[0];
  const comparison = COMPARISON_LATEX[baseline.comparison] ?? baseline.comparison;
  return `${certificateSymbolLatex(record)} ${comparison} ${constantLatex(baseline.rhs)}`;
}

function axisLatex(axis: string): string {
  // KaTeX renders "p_x" as p subscript x directly; expand "*_dot" to an overdot.
  const dot = axis.match(/^(.*)_dot$/);
  return dot ? `\\dot{${dot[1]}}` : axis;
}

function sectionConditionLatex(section: PoincareSection): string {
  const coordinate = section.coordinate;
  if (!coordinate) {
    return "\\Sigma";
  }
  const level = `${coordinate} = ${constantLatex(section.value ?? 0)}`;
  if (section.direction === "positive") {
    return `${level},\\ \\dot{${coordinate}} > 0`;
  }
  if (section.direction === "negative") {
    return `${level},\\ \\dot{${coordinate}} < 0`;
  }
  return level;
}

// Prepare a canvas's backing store for the current size + DPR, returning the
// CSS pixel dimensions to draw in. Shared by both diagnostic surfaces.
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

// The running finite-time estimate λ(t): a curve converging against a neutral
// baseline. Above the baseline = expansion (the shaded warm gap is the
// qualitative size); the playhead tracks convergence as the trajectory plays.
function drawLyapunovLane(lane: LyapunovLane, phase: number): void {
  const { canvas, ctx, series, domainMin, domainMax } = lane;
  const { width, height } = prepareCanvas(canvas, ctx);

  const count = series.length;
  if (count === 0) {
    return;
  }
  const pad = 5;
  const span = domainMax - domainMin || 1;
  const yOf = (value: number) =>
    clamp(height - pad - ((value - domainMin) / span) * (height - 2 * pad), pad, height - pad);
  const xOf = (index: number) => (count <= 1 ? 0 : (index / (count - 1)) * width);
  const baselineY = yOf(0);

  // Warm fill between the curve and the neutral baseline: the area is the
  // qualitative magnitude of the exponent, never a printed number.
  const step = Math.max(1, Math.floor(count / 320));
  ctx.beginPath();
  ctx.moveTo(0, baselineY);
  for (let index = 0; index < count; index += step) {
    ctx.lineTo(xOf(index), yOf(series[index]));
  }
  ctx.lineTo(xOf(count - 1), baselineY);
  ctx.closePath();
  ctx.fillStyle = magma.css(0.72, 0.16);
  ctx.fill();

  // Neutral baseline (λ = 0), drawn as a faint dashed reference, no label.
  ctx.save();
  ctx.setLineDash([3, 4]);
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, baselineY);
  ctx.lineTo(width, baselineY);
  ctx.stroke();
  ctx.restore();

  // The converging estimate itself.
  ctx.strokeStyle = theme.accent;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let index = 0; index < count; index += step) {
    const x = xOf(index);
    const y = yOf(series[index]);
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
  ctx.arc(clamp(phase, 0, 1) * width, yOf(series[playIndex]), 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
}

// The conservation drift Δq(t) about a zero baseline. The lane auto-scales to
// the drift's own (tiny) amplitude, so a flat line reads "conserved" and any
// oscillation or secular trend is visible without a printed number.
function drawResidualLane(lane: ResidualLane, phase: number): void {
  const { canvas, ctx, residual, amplitude } = lane;
  const { width, height } = prepareCanvas(canvas, ctx);

  const count = residual.length;
  if (count === 0) {
    return;
  }
  const pad = 5;
  const amp = amplitude > 0 ? amplitude : 1;
  const mid = height / 2;
  const yOf = (value: number) =>
    clamp(mid - (value / amp) * (height / 2 - pad), pad, height - pad);
  const xOf = (index: number) => (count <= 1 ? 0 : (index / (count - 1)) * width);
  const step = Math.max(1, Math.floor(count / 320));

  // Zero baseline = perfect conservation, faint and dashed, no label.
  ctx.save();
  ctx.setLineDash([3, 4]);
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(width, mid);
  ctx.stroke();
  ctx.restore();

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let index = 0; index < count; index += step) {
    const x = xOf(index);
    const y = yOf(residual[index]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  const playIndex = clamp(Math.round(phase * (count - 1)), 0, count - 1);
  ctx.fillStyle = theme.cool;
  ctx.shadowColor = theme.cool;
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.arc(clamp(phase, 0, 1) * width, yOf(residual[playIndex]), 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
}

// A candidate certificate v(t) drawn against its obligation threshold. The
// dashed baseline is the threshold; the curve is the measured value along the
// run, auto-scaled to its own excursion so its sign and shape relative to the
// threshold read clearly. No decimal is shown — the magnitude is qualitative,
// and whether the obligation actually holds is the proof-status surface's job.
function drawCertificateLane(lane: CertificateLane, phase: number): void {
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

  // Obligation threshold baseline, faint and dashed, no label.
  ctx.save();
  ctx.setLineDash([3, 4]);
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(width, mid);
  ctx.stroke();
  ctx.restore();

  // Warm fill between the curve and the threshold: the area is the qualitative
  // margin of the certificate, never a printed number.
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

// A Poincaré section as a scatter of crossing markers in its exported axes. No
// numeric ticks: the recurrence structure (a curve vs. a smear) is the content.
// Crossings already reached by playback glow; later ones stay faint.
function drawSectionPlot(plot: SectionPlot, phase: number): void {
  const { canvas, ctx, points, bounds } = plot;
  const { width, height } = prepareCanvas(canvas, ctx);

  const pad = 12;
  const spanX = bounds.maxX - bounds.minX || 1;
  const spanY = bounds.maxY - bounds.minY || 1;
  const xOf = (x: number) => pad + ((x - bounds.minX) / spanX) * (width - 2 * pad);
  const yOf = (y: number) => height - pad - ((y - bounds.minY) / spanY) * (height - 2 * pad);

  // Faint axes through the origin when it falls inside the exported window.
  ctx.strokeStyle = theme.hairline;
  ctx.lineWidth = 1;
  if (bounds.minX <= 0 && bounds.maxX >= 0) {
    const x0 = xOf(0);
    ctx.beginPath();
    ctx.moveTo(x0, pad);
    ctx.lineTo(x0, height - pad);
    ctx.stroke();
  }
  if (bounds.minY <= 0 && bounds.maxY >= 0) {
    const y0 = yOf(0);
    ctx.beginPath();
    ctx.moveTo(pad, y0);
    ctx.lineTo(width - pad, y0);
    ctx.stroke();
  }

  points.forEach((point) => {
    const visited = point.normTime <= clamp(phase, 0, 1);
    const px = xOf(point.x);
    const py = yOf(point.y);
    if (visited) {
      ctx.fillStyle = theme.cool;
      ctx.shadowColor = theme.cool;
      ctx.shadowBlur = 6;
      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    } else {
      ctx.fillStyle = theme.textFaint;
      ctx.beginPath();
      ctx.arc(px, py, 2, 0, Math.PI * 2);
      ctx.fill();
    }
  });
}
