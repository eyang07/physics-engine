import { theme } from "./design/theme";
import type { ManifestLens, SystemManifest } from "./data/manifest";
import { stateIndex, type Trajectory } from "./data/trajectory";
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

type Point2D = {
  x: number;
  y: number;
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

type PotentialSurface = {
  xValues: number[];
  yValues: number[];
  values: number[][];
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
  return plainMathLabel(state.latex);
}

function plainMathLabel(label: string): string {
  return mathLabel(label);
}

function drawLabel(ctx: CanvasRenderingContext2D, text: string, x: number, y: number): void {
  ctx.fillStyle = theme.textMuted;
  ctx.font = '13px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText(text, x, y);
}

function recentWindow<T>(items: T[], currentIndex: number, length = 180): T[] {
  return items.slice(Math.max(0, currentIndex - length + 1), currentIndex + 1);
}

function drawFadingPath(ctx: CanvasRenderingContext2D, points: Point2D[], width: number): void {
  if (points.length < 2) {
    return;
  }

  ctx.save();
  ctx.strokeStyle = theme.accent;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.lineWidth = width;
  for (let index = 1; index < points.length; index += 1) {
    const alpha = index / (points.length - 1);
    ctx.globalAlpha = 0.08 + alpha * 0.88;
    ctx.shadowColor = theme.accent;
    ctx.shadowBlur = 12 * alpha * alpha;
    ctx.beginPath();
    ctx.moveTo(points[index - 1].x, points[index - 1].y);
    ctx.lineTo(points[index].x, points[index].y);
    ctx.stroke();
  }
  ctx.restore();
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

  drawFadingPath(
    ctx,
    recentWindow(data.states, sample.index).map((state) => ({
      x: xOf(state[xIndex], xRange, area),
      y: yOf(state[yIndex], yRange, area),
    })),
    3,
  );

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

function getPotentialSurface(data: Trajectory): PotentialSurface | undefined {
  const metadata = data.metadata as { potentialSurface?: PotentialSurface } | undefined;
  return metadata?.potentialSurface;
}

function drawContourSegment(
  ctx: CanvasRenderingContext2D,
  level: number,
  corners: Array<{ x: number; y: number; value: number }>,
): void {
  const intersections: Array<{ x: number; y: number }> = [];
  const edges = [
    [corners[0], corners[1]],
    [corners[1], corners[2]],
    [corners[2], corners[3]],
    [corners[3], corners[0]],
  ];

  edges.forEach(([start, end]) => {
    const span = end.value - start.value;
    if (Math.abs(span) < 1e-12) {
      return;
    }
    const alpha = (level - start.value) / span;
    if (alpha >= 0 && alpha <= 1) {
      intersections.push({
        x: start.x + (end.x - start.x) * alpha,
        y: start.y + (end.y - start.y) * alpha,
      });
    }
  });

  if (intersections.length >= 2) {
    ctx.moveTo(intersections[0].x, intersections[0].y);
    ctx.lineTo(intersections[1].x, intersections[1].y);
  }
  if (intersections.length >= 4) {
    ctx.moveTo(intersections[2].x, intersections[2].y);
    ctx.lineTo(intersections[3].x, intersections[3].y);
  }
}

function drawArrow2d(
  ctx: CanvasRenderingContext2D,
  startX: number,
  startY: number,
  vectorX: number,
  vectorY: number,
  opacity: number,
): void {
  const length = Math.hypot(vectorX, vectorY);
  if (length < 1e-8) {
    return;
  }
  const ux = vectorX / length;
  const uy = vectorY / length;
  const endX = startX + vectorX;
  const endY = startY + vectorY;

  ctx.strokeStyle = `rgba(111, 182, 201, ${opacity})`;
  ctx.fillStyle = `rgba(111, 182, 201, ${opacity})`;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(startX, startY);
  ctx.lineTo(endX, endY);
  ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(endX, endY);
  ctx.lineTo(endX - ux * 7 - uy * 3.5, endY - uy * 7 + ux * 3.5);
  ctx.lineTo(endX - ux * 7 + uy * 3.5, endY - uy * 7 - ux * 3.5);
  ctx.closePath();
  ctx.fill();
}

export function drawPotentialContourScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  sample: Sample,
  width: number,
  height: number,
): void {
  const surface = getPotentialSurface(data);
  if (!surface) {
    drawUnavailable(ctx, width, height, "Potential surface unavailable.");
    return;
  }
  const indices = stateIndex(data);
  const xIndex = indices.get("x");
  const yIndex = indices.get("y");
  if (xIndex === undefined || yIndex === undefined) {
    drawUnavailable(ctx, width, height, "Configuration data unavailable.");
    return;
  }

  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);

  const area = areaFor(width, height);
  const xRange = range(surface.xValues, [sample.state[xIndex]]);
  const yRange = range(surface.yValues, [sample.state[yIndex]]);
  const flatValues = surface.values.flat().filter(Number.isFinite);
  const valueRange = range(flatValues, surface.energy === undefined ? [] : [surface.energy]);

  for (let row = 0; row < surface.yValues.length - 1; row += 1) {
    for (let col = 0; col < surface.xValues.length - 1; col += 1) {
      const value = surface.values[row][col];
      const normalized = clamp((value - valueRange.min) / (valueRange.max - valueRange.min), 0, 1);
      const alpha = 0.025 + normalized * 0.16;
      ctx.fillStyle = normalized > 0.72 ? `rgba(240, 180, 106, ${alpha})` : `rgba(111, 182, 201, ${alpha})`;
      const x0 = xOf(surface.xValues[col], xRange, area);
      const x1 = xOf(surface.xValues[col + 1], xRange, area);
      const y0 = yOf(surface.yValues[row], yRange, area);
      const y1 = yOf(surface.yValues[row + 1], yRange, area);
      ctx.fillRect(x0, y1, Math.max(1, x1 - x0), Math.max(1, y0 - y1));
    }
  }

  drawAxes(ctx, xRange, yRange, area);

  const levels = Array.from({ length: 10 }, (_item, index) => {
    const alpha = (index + 1) / 11;
    return valueRange.min + alpha * (valueRange.max - valueRange.min);
  });
  if (surface.energy !== undefined) {
    levels.push(surface.energy);
  }
  levels.forEach((level) => {
    ctx.strokeStyle = level === surface.energy ? theme.accent : theme.hairlineStrong;
    ctx.lineWidth = level === surface.energy ? 2 : 1;
    ctx.beginPath();
    for (let row = 0; row < surface.yValues.length - 1; row += 1) {
      for (let col = 0; col < surface.xValues.length - 1; col += 1) {
        drawContourSegment(ctx, level, [
          {
            x: xOf(surface.xValues[col], xRange, area),
            y: yOf(surface.yValues[row], yRange, area),
            value: surface.values[row][col],
          },
          {
            x: xOf(surface.xValues[col + 1], xRange, area),
            y: yOf(surface.yValues[row], yRange, area),
            value: surface.values[row][col + 1],
          },
          {
            x: xOf(surface.xValues[col + 1], xRange, area),
            y: yOf(surface.yValues[row + 1], yRange, area),
            value: surface.values[row + 1][col + 1],
          },
          {
            x: xOf(surface.xValues[col], xRange, area),
            y: yOf(surface.yValues[row + 1], yRange, area),
            value: surface.values[row + 1][col],
          },
        ]);
      }
    }
    ctx.stroke();
  });

  const metadata = data.metadata as { stiffness?: number; coupling?: number } | undefined;
  const stiffness = metadata?.stiffness ?? 1;
  const coupling = metadata?.coupling ?? 1;
  for (let gx = xRange.min; gx <= xRange.max; gx += (xRange.max - xRange.min) / 9) {
    for (let gy = yRange.min; gy <= yRange.max; gy += (yRange.max - yRange.min) / 7) {
      const forceX = -(stiffness * gx + 2 * coupling * gx * gy);
      const forceY = -(stiffness * gy + coupling * (gx * gx - gy * gy));
      const scale = 18 / Math.max(1, Math.hypot(forceX, forceY));
      drawArrow2d(
        ctx,
        xOf(gx, xRange, area),
        yOf(gy, yRange, area),
        forceX * scale,
        -forceY * scale,
        0.2,
      );
    }
  }

  const trajectory = data.states.map((state) => ({
    x: xOf(state[xIndex], xRange, area),
    y: yOf(state[yIndex], yRange, area),
  }));
  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  trajectory.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();

  drawFadingPath(ctx, recentWindow(trajectory, sample.index), 2.4);

  ctx.fillStyle = theme.accentStrong;
  ctx.beginPath();
  ctx.arc(
    xOf(sample.state[xIndex], xRange, area),
    yOf(sample.state[yIndex], yRange, area),
    6,
    0,
    Math.PI * 2,
  );
  ctx.fill();
  ctx.shadowBlur = 0;

  drawLabel(ctx, "Potential Contours", area.left, area.top - 18);
  drawLabel(ctx, "x", area.right - 20, area.bottom + 30);
  drawLabel(ctx, "y", area.left + 10, area.top + 18);
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
  drawLabel(ctx, plainMathLabel(plot.coordinateLatex ?? plot.coordinate), area.right - 48, area.bottom + 30);
  drawLabel(ctx, plainMathLabel(plot.potentialLatex ?? "V"), area.left + 10, area.top + 18);
}
