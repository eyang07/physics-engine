/**
 * The Poincaré-section lens: a focused full-stage view of the exported section
 * crossings for a Hamiltonian flow (Hénon-Heiles `(x, p_x)` on `y = 0`,
 * `\dot y > 0`).
 *
 * It renders only what Python measured — the `metadata.poincareSections`
 * crossings, located by the backend on the section surface — and never
 * recomputes the flow. Crossings already reached by playback glow; later ones
 * stay faint, so the recurrence structure (a smooth invariant curve vs. a
 * scattered chaotic smear) fills in as the trajectory plays. No numeric ticks:
 * the shape of the set is the content.
 */
import { theme } from "./design/theme";
import { poincareSections, type PoincareSection, type Trajectory } from "./data/trajectory";
import { mathLabel } from "./mathLabel";
import type { Sample } from "./playback";
import { clamp } from "./util";

type Range = {
  min: number;
  max: number;
};

type PlotArea = {
  left: number;
  top: number;
  right: number;
  bottom: number;
  width: number;
  height: number;
};

function setupCanvas(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const pixelRatio = window.devicePixelRatio || 1;
  const drawingWidth = Math.max(1, Math.floor(width * pixelRatio));
  const drawingHeight = Math.max(1, Math.floor(height * pixelRatio));
  if (ctx.canvas.width !== drawingWidth || ctx.canvas.height !== drawingHeight) {
    ctx.canvas.width = drawingWidth;
    ctx.canvas.height = drawingHeight;
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }
}

function drawBackground(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, theme.ink900);
  gradient.addColorStop(0.56, theme.ink800);
  gradient.addColorStop(1, theme.ink850);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = theme.hairline;
  ctx.lineWidth = 1;
  for (let x = 0; x <= width; x += 44) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y <= height; y += 44) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

function areaFor(width: number, height: number): PlotArea {
  const left = Math.max(54, width * 0.09);
  const right = width - Math.max(38, width * 0.08);
  const top = Math.max(42, height * 0.12);
  const bottom = height - Math.max(52, height * 0.12);
  return {
    left,
    right,
    top,
    bottom,
    width: Math.max(1, right - left),
    height: Math.max(1, bottom - top),
  };
}

function range(values: number[]): Range {
  const all = values.filter(Number.isFinite);
  if (all.length === 0) {
    return { min: -1, max: 1 };
  }
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min;
  if (span < 1e-9) {
    return { min: min - 1, max: max + 1 };
  }
  const pad = Math.max(0.08, span * 0.12);
  return { min: min - pad, max: max + pad };
}

function xOf(value: number, bounds: Range, area: PlotArea): number {
  return area.left + ((value - bounds.min) / (bounds.max - bounds.min)) * area.width;
}

function yOf(value: number, bounds: Range, area: PlotArea): number {
  return area.bottom - ((value - bounds.min) / (bounds.max - bounds.min)) * area.height;
}

function drawAxes(ctx: CanvasRenderingContext2D, xRange: Range, yRange: Range, area: PlotArea): void {
  const xAxis = yRange.min <= 0 && yRange.max >= 0 ? yOf(0, yRange, area) : area.bottom;
  const yAxis = xRange.min <= 0 && xRange.max >= 0 ? xOf(0, xRange, area) : area.left;

  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(area.left, xAxis);
  ctx.lineTo(area.right, xAxis);
  ctx.moveTo(yAxis, area.top);
  ctx.lineTo(yAxis, area.bottom);
  ctx.stroke();
}

function drawLabel(ctx: CanvasRenderingContext2D, text: string, x: number, y: number): void {
  ctx.fillStyle = theme.textMuted;
  ctx.font = '13px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText(text, x, y);
}

function drawUnavailable(ctx: CanvasRenderingContext2D, width: number, height: number, message: string): void {
  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);
  ctx.fillStyle = theme.textMuted;
  ctx.font = '16px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText(message, 32, 48);
}

// The section condition (e.g. "y = 0, ẏ > 0") as a plain-text caption, built
// from the exported section definition — a structural constant, not a measured
// magnitude.
function sectionConditionLabel(section: PoincareSection): string {
  const coordinate = section.coordinate;
  if (!coordinate) {
    return "Poincaré section";
  }
  const value = section.value ?? 0;
  const level = `${mathLabel(coordinate)} = ${Math.abs(value) < 1e-12 ? "0" : String(value)}`;
  const velocity = mathLabel(`\\dot{${coordinate}}`);
  if (section.direction === "positive") {
    return `${level}, ${velocity} > 0`;
  }
  if (section.direction === "negative") {
    return `${level}, ${velocity} < 0`;
  }
  return level;
}

export function drawPoincareSectionScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  sample: Sample,
  width: number,
  height: number,
): void {
  const section = poincareSections(data)[0];
  if (!section || section.points.length === 0 || section.axes.length < 2) {
    drawUnavailable(ctx, width, height, "Poincaré section unavailable.");
    return;
  }

  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);

  const area = areaFor(width, height);
  const xs = section.points.map((point) => point.axisValues[0]);
  const ys = section.points.map((point) => point.axisValues[1]);
  const xRange = range(xs);
  const yRange = range(ys);

  drawAxes(ctx, xRange, yRange, area);

  // The crossings, in chronological order. A point counts as "visited" once
  // playback has passed the time the backend located the crossing at; visited
  // points glow, later ones stay faint, so the set accretes as the run plays.
  const reached = sample.wrappedTime;
  section.points.forEach((point) => {
    const px = clamp(xOf(point.axisValues[0], xRange, area), area.left, area.right);
    const py = clamp(yOf(point.axisValues[1], yRange, area), area.top, area.bottom);
    const visited = typeof point.time === "number" ? point.time <= reached : true;
    if (visited) {
      ctx.fillStyle = theme.accentStrong;
      ctx.shadowColor = theme.accent;
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.arc(px, py, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    } else {
      ctx.fillStyle = theme.textFaint;
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  });

  drawLabel(ctx, sectionConditionLabel(section), area.left, area.top - 18);
  drawLabel(ctx, mathLabel(section.axes[0]), area.right - 24, area.bottom + 30);
  drawLabel(ctx, mathLabel(section.axes[1]), area.left + 10, area.top + 18);
}
