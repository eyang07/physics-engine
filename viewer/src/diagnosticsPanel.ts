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
  lyapunovDiagnostic,
  poincareSections,
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

type SectionPlot = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  points: { x: number; y: number; normTime: number }[];
  bounds: { minX: number; maxX: number; minY: number; maxY: number };
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

  constructor(
    private readonly section: HTMLElement,
    private readonly content: HTMLElement,
  ) {}

  clear(): void {
    this.content.replaceChildren();
    this.lyapunovLane = null;
    this.sectionPlots = [];
    this.section.hidden = true;
  }

  show(data: Trajectory): void {
    this.clear();
    this.renderLyapunov(data);
    this.renderSections(data);
    this.section.hidden = this.lyapunovLane === null && this.sectionPlots.length === 0;
  }

  update(phase: number): void {
    if (this.lyapunovLane) {
      drawLyapunovLane(this.lyapunovLane, phase);
    }
    this.sectionPlots.forEach((plot) => drawSectionPlot(plot, phase));
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
