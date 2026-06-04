import { theme } from "./design/theme";
import type { Trajectory } from "./data/trajectory";
import type { Sample } from "./playback";
import { clamp } from "./util";

type Bounds = {
  minR: number;
  maxR: number;
  minRDot: number;
  maxRDot: number;
  minV: number;
  maxV: number;
};

function columnIndex(data: Trajectory, name: string): number {
  const index = data.state_names.indexOf(name);
  if (index < 0) {
    throw new Error(`Effective-potential lens requires state column ${name}`);
  }
  return index;
}

function mean(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / Math.max(1, values.length);
}

function keplerAngularMomentum(data: Trajectory): number {
  const series = data.series?.ell;
  if (series && series.length > 0) {
    return mean(series);
  }

  const rIndex = columnIndex(data, "r");
  const phiDotIndex = columnIndex(data, "phi_dot");
  return mean(data.states.map((state) => state[rIndex] ** 2 * state[phiDotIndex]));
}

function keplerEnergy(data: Trajectory): number {
  const series = data.series?.H;
  if (series && series.length > 0) {
    return mean(series);
  }

  const rIndex = columnIndex(data, "r");
  const rDotIndex = columnIndex(data, "r_dot");
  const phiDotIndex = columnIndex(data, "phi_dot");
  return mean(
    data.states.map((state) => {
      const r = state[rIndex];
      const rDot = state[rDotIndex];
      const phiDot = state[phiDotIndex];
      return 0.5 * (rDot ** 2 + r ** 2 * phiDot ** 2) - 1 / r;
    }),
  );
}

function effectivePotential(r: number, ell: number): number {
  return ell ** 2 / (2 * r ** 2) - 1 / r;
}

function computeBounds(data: Trajectory, ell: number, energy: number): Bounds {
  const rIndex = columnIndex(data, "r");
  const rDotIndex = columnIndex(data, "r_dot");
  const rValues = data.states.map((state) => state[rIndex]);
  const rDotValues = data.states.map((state) => state[rDotIndex]);
  const rMin = Math.max(0.08, Math.min(...rValues) * 0.78);
  const rMax = Math.max(...rValues) * 1.22;
  const samples = Array.from({ length: 180 }, (_, index) => {
    const r = rMin + (index / 179) * (rMax - rMin);
    return effectivePotential(r, ell);
  });
  const minV = Math.min(...samples, energy);
  const maxV = Math.max(...samples, energy);
  const vPad = Math.max(0.08, (maxV - minV) * 0.16);
  const rDotPad = Math.max(0.08, (Math.max(...rDotValues) - Math.min(...rDotValues)) * 0.18);

  return {
    minR: rMin,
    maxR: rMax,
    minRDot: Math.min(...rDotValues) - rDotPad,
    maxRDot: Math.max(...rDotValues) + rDotPad,
    minV: minV - vPad,
    maxV: maxV + vPad,
  };
}

function plotArea(x: number, y: number, width: number, height: number): DOMRect {
  return new DOMRect(x, y, Math.max(1, width), Math.max(1, height));
}

function drawAxes(ctx: CanvasRenderingContext2D, area: DOMRect): void {
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(area.x, area.y + area.height);
  ctx.lineTo(area.x + area.width, area.y + area.height);
  ctx.moveTo(area.x, area.y);
  ctx.lineTo(area.x, area.y + area.height);
  ctx.stroke();
}

function drawLabel(ctx: CanvasRenderingContext2D, text: string, x: number, y: number): void {
  ctx.fillStyle = theme.textMuted;
  ctx.font = '13px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText(text, x, y);
}

export function drawEffectivePotentialScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  sample: Sample,
  width: number,
  height: number,
): void {
  const pixelRatio = window.devicePixelRatio || 1;
  const drawingWidth = Math.max(1, Math.floor(width * pixelRatio));
  const drawingHeight = Math.max(1, Math.floor(height * pixelRatio));
  if (ctx.canvas.width !== drawingWidth || ctx.canvas.height !== drawingHeight) {
    ctx.canvas.width = drawingWidth;
    ctx.canvas.height = drawingHeight;
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }

  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, theme.ink900);
  gradient.addColorStop(0.56, theme.ink800);
  gradient.addColorStop(1, theme.ink850);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  const rIndex = columnIndex(data, "r");
  const rDotIndex = columnIndex(data, "r_dot");
  const ell = keplerAngularMomentum(data);
  const energy = keplerEnergy(data);
  const bounds = computeBounds(data, ell, energy);

  const left = plotArea(width * 0.08, height * 0.16, width * 0.5, height * 0.68);
  const right = plotArea(width * 0.66, height * 0.2, width * 0.25, height * 0.58);
  const mapR = (r: number, area: DOMRect) =>
    area.x + ((r - bounds.minR) / (bounds.maxR - bounds.minR)) * area.width;
  const mapV = (value: number) =>
    left.y + left.height - ((value - bounds.minV) / (bounds.maxV - bounds.minV)) * left.height;
  const mapRDot = (value: number) =>
    right.y + right.height - ((value - bounds.minRDot) / (bounds.maxRDot - bounds.minRDot)) * right.height;

  drawAxes(ctx, left);
  drawAxes(ctx, right);

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let index = 0; index <= 220; index += 1) {
    const r = bounds.minR + (index / 220) * (bounds.maxR - bounds.minR);
    const x = mapR(r, left);
    const y = mapV(effectivePotential(r, ell));
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  const energyY = mapV(energy);
  ctx.strokeStyle = theme.accent;
  ctx.setLineDash([8, 8]);
  ctx.beginPath();
  ctx.moveTo(left.x, energyY);
  ctx.lineTo(left.x + left.width, energyY);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.strokeStyle = theme.textFaint;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  data.states.forEach((state, index) => {
    const x = mapR(state[rIndex], right);
    const y = mapRDot(state[rDotIndex]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  const r = sample.state[rIndex];
  const rDot = sample.state[rDotIndex];
  ctx.fillStyle = theme.accentStrong;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.arc(clamp(mapR(r, left), left.x, left.x + left.width), mapV(effectivePotential(r, ell)), 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(clamp(mapR(r, right), right.x, right.x + right.width), mapRDot(rDot), 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  drawLabel(ctx, "Veff", left.x + 10, left.y + 18);
  drawLabel(ctx, "H", left.x + left.width - 22, energyY - 8);
  drawLabel(ctx, "r", left.x + left.width - 12, left.y + left.height + 22);
  drawLabel(ctx, "r", right.x + right.width - 12, right.y + right.height + 22);
  drawLabel(ctx, "rdot", right.x + 8, right.y + 18);
}
