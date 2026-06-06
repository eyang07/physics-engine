import { theme } from "./design/theme";
import type { ManifestLens, SystemManifest } from "./data/manifest";
import { stateIndex, type Trajectory } from "./data/trajectory";
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

type PotentialPlot = {
  name: string;
  coordinate: string;
  coordinateLatex?: string;
  potentialLatex?: string;
  coordinateValues: number[];
  potentialValues: number[];
  energy?: number;
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

function range(values: number[], extra: number[] = []): Range {
  const all = values.concat(extra).filter(Number.isFinite);
  if (all.length === 0) {
    return { min: -1, max: 1 };
  }
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min;
  const pad = Math.max(0.08, span * 0.12);
  if (span < 1e-9) {
    return { min: min - 1, max: max + 1 };
  }
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

function labelFor(system: SystemManifest, name: string): string {
  const state = system.state.find((item) => item.name === name);
  if (!state) {
    return name;
  }
  return state.latex
    .replace(/\\dot\{\\theta\}/g, "theta_dot")
    .replace(/\\dot\{\\phi\}/g, "phi_dot")
    .replace(/\\theta/g, "theta")
    .replace(/\\phi/g, "phi");
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

export function drawPhaseScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  system: SystemManifest,
  lens: ManifestLens,
  sample: Sample,
  width: number,
  height: number,
): void {
  const projection = system.projections[lens.projections[0] ?? ""];
  if (!projection || projection.length < 2) {
    drawUnavailable(ctx, width, height, "Phase projection unavailable.");
    return;
  }

  const indices = stateIndex(data);
  const xIndex = indices.get(projection[0]);
  const yIndex = indices.get(projection[1]);
  if (xIndex === undefined || yIndex === undefined) {
    drawUnavailable(ctx, width, height, "Phase data unavailable.");
    return;
  }

  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);

  const area = areaFor(width, height);
  const xs = data.states.map((state) => state[xIndex]);
  const ys = data.states.map((state) => state[yIndex]);
  const xRange = range(xs, [sample.state[xIndex]]);
  const yRange = range(ys, [sample.state[yIndex]]);

  drawAxes(ctx, xRange, yRange, area);

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 2;
  ctx.beginPath();
  data.states.forEach((state, index) => {
    const x = xOf(state[xIndex], xRange, area);
    const y = yOf(state[yIndex], yRange, area);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.strokeStyle = theme.accent;
  ctx.lineWidth = 3;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 11;
  ctx.beginPath();
  data.states.slice(0, sample.index + 1).forEach((state, index) => {
    const x = xOf(state[xIndex], xRange, area);
    const y = yOf(state[yIndex], yRange, area);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = theme.accentStrong;
  ctx.beginPath();
  ctx.arc(xOf(sample.state[xIndex], xRange, area), yOf(sample.state[yIndex], yRange, area), 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  drawLabel(ctx, lens.title, area.left, area.top - 18);
  drawLabel(ctx, labelFor(system, projection[0]), area.right - 48, area.bottom + 30);
  drawLabel(ctx, labelFor(system, projection[1]), area.left + 10, area.top + 18);
}

function getPotentialPlots(data: Trajectory): PotentialPlot[] {
  const metadata = data.metadata as { potentialPlots?: PotentialPlot[] } | undefined;
  return metadata?.potentialPlots ?? [];
}

function choosePotentialPlot(data: Trajectory, system: SystemManifest, lens: ManifestLens): PotentialPlot | undefined {
  const plots = getPotentialPlots(data);
  if (plots.length <= 1) {
    return plots[0];
  }
  const projection = system.projections[lens.projections[0] ?? ""];
  const coordinate = projection?.[0];
  return plots.find((plot) => plot.coordinate === coordinate) ?? plots[0];
}

function interpolate(xs: number[], ys: number[], x: number): number {
  if (xs.length === 0 || ys.length === 0) {
    return 0;
  }
  if (x <= xs[0]) {
    return ys[0];
  }
  for (let index = 1; index < xs.length; index += 1) {
    if (x <= xs[index]) {
      const x0 = xs[index - 1];
      const x1 = xs[index];
      const alpha = x1 === x0 ? 0 : (x - x0) / (x1 - x0);
      return ys[index - 1] + alpha * (ys[index] - ys[index - 1]);
    }
  }
  return ys[ys.length - 1];
}

export function drawPotentialScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  system: SystemManifest,
  lens: ManifestLens,
  sample: Sample,
  width: number,
  height: number,
): void {
  const plot = choosePotentialPlot(data, system, lens);
  if (!plot) {
    drawUnavailable(ctx, width, height, "Potential data unavailable.");
    return;
  }

  const indices = stateIndex(data);
  const coordinateIndex = indices.get(plot.coordinate);
  if (coordinateIndex === undefined) {
    drawUnavailable(ctx, width, height, "Potential coordinate unavailable.");
    return;
  }

  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);

  const area = areaFor(width, height);
  const xRange = range(plot.coordinateValues, [sample.state[coordinateIndex]]);
  const energyValues = plot.energy === undefined ? [] : [plot.energy];
  const yRange = range(plot.potentialValues, energyValues);

  drawAxes(ctx, xRange, yRange, area);

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  plot.coordinateValues.forEach((value, index) => {
    const x = xOf(value, xRange, area);
    const y = yOf(plot.potentialValues[index], yRange, area);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  if (plot.energy !== undefined) {
    const energyY = yOf(plot.energy, yRange, area);
    ctx.strokeStyle = theme.accent;
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 8]);
    ctx.beginPath();
    ctx.moveTo(area.left, energyY);
    ctx.lineTo(area.right, energyY);
    ctx.stroke();
    ctx.setLineDash([]);
    drawLabel(ctx, "H", area.right - 18, clamp(energyY - 8, area.top + 12, area.bottom - 6));
  }

  const currentCoordinate = sample.state[coordinateIndex];
  const currentPotential = interpolate(plot.coordinateValues, plot.potentialValues, currentCoordinate);
  ctx.fillStyle = theme.accentStrong;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.arc(
    clamp(xOf(currentCoordinate, xRange, area), area.left, area.right),
    clamp(yOf(currentPotential, yRange, area), area.top, area.bottom),
    6,
    0,
    Math.PI * 2,
  );
  ctx.fill();
  ctx.shadowBlur = 0;

  drawLabel(ctx, lens.title, area.left, area.top - 18);
  drawLabel(ctx, plot.coordinateLatex ?? plot.coordinate, area.right - 48, area.bottom + 30);
  drawLabel(ctx, plot.potentialLatex ?? "V", area.left + 10, area.top + 18);
}
