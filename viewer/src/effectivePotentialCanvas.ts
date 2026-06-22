import { theme } from "./design/theme";
import type { Trajectory } from "./data/trajectory";
import { mathLabel } from "./mathLabel";
import type { Sample } from "./playback";
import { clamp } from "./util";

/**
 * One exported effective-potential plot (BE-102): the reduced-coordinate
 * potential curve, the system energy, and — for orbit problems — the turning
 * points and a qualitative orbit classification. The viewer draws exactly what
 * Python computed; it never re-derives the potential in the browser.
 */
type PotentialPlot = {
  coordinate: string;
  coordinateLatex?: string;
  potentialLatex?: string;
  coordinateValues: number[];
  potentialValues: number[];
  energy: number;
  turningPoints?: number[];
  classification?: string;
};

type Bounds = {
  minC: number;
  maxC: number;
  minV: number;
  maxV: number;
  minCDot: number;
  maxCDot: number;
};

function asNumberArray(value: unknown): number[] | null {
  return Array.isArray(value) && value.every((item) => typeof item === "number")
    ? (value as number[])
    : null;
}

/** Read the first exported effective-potential plot, or null if none/malformed. */
function potentialPlot(data: Trajectory): PotentialPlot | null {
  const plots = (data.metadata as { potentialPlots?: unknown } | undefined)?.potentialPlots;
  if (!Array.isArray(plots) || plots.length === 0) {
    return null;
  }
  const raw = plots[0] as Record<string, unknown>;
  const coordinateValues = asNumberArray(raw.coordinateValues);
  const potentialValues = asNumberArray(raw.potentialValues);
  if (
    typeof raw.coordinate !== "string" ||
    !coordinateValues ||
    !potentialValues ||
    coordinateValues.length < 2 ||
    coordinateValues.length !== potentialValues.length ||
    typeof raw.energy !== "number"
  ) {
    return null;
  }
  return {
    coordinate: raw.coordinate,
    coordinateLatex: typeof raw.coordinateLatex === "string" ? raw.coordinateLatex : undefined,
    potentialLatex: typeof raw.potentialLatex === "string" ? raw.potentialLatex : undefined,
    coordinateValues,
    potentialValues,
    energy: raw.energy,
    turningPoints: asNumberArray(raw.turningPoints) ?? undefined,
    classification: typeof raw.classification === "string" ? raw.classification : undefined,
  };
}

// Linear interpolation of the exported potential at a coordinate value. This is
// rendering (reading the exported curve), not a physics re-derivation.
function potentialAt(plot: PotentialPlot, coordinate: number): number {
  const xs = plot.coordinateValues;
  const ys = plot.potentialValues;
  if (coordinate <= xs[0]) {
    return ys[0];
  }
  if (coordinate >= xs[xs.length - 1]) {
    return ys[ys.length - 1];
  }
  for (let index = 1; index < xs.length; index += 1) {
    if (coordinate <= xs[index]) {
      const span = xs[index] - xs[index - 1];
      const alpha = span === 0 ? 0 : (coordinate - xs[index - 1]) / span;
      return ys[index - 1] + alpha * (ys[index] - ys[index - 1]);
    }
  }
  return ys[ys.length - 1];
}

function extent(values: number[]): [number, number] {
  return [Math.min(...values), Math.max(...values)];
}

function computeBounds(plot: PotentialPlot, coordDot: number[] | null): Bounds {
  const [minC, maxC] = extent(plot.coordinateValues);
  const [potMin, potMax] = extent(plot.potentialValues);
  const minV = Math.min(potMin, plot.energy);
  const maxV = Math.max(potMax, plot.energy);
  const vPad = Math.max(1e-3, (maxV - minV) * 0.16);
  const [dotMin, dotMax] = coordDot && coordDot.length > 0 ? extent(coordDot) : [-1, 1];
  const dotPad = Math.max(1e-3, (dotMax - dotMin) * 0.18);
  return {
    minC,
    maxC,
    minV: minV - vPad,
    maxV: maxV + vPad,
    minCDot: dotMin - dotPad,
    maxCDot: dotMax + dotPad,
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

function columnIndex(data: Trajectory, name: string): number {
  return data.state_names.indexOf(name);
}

/**
 * True when Python exported a measured perihelion-precession diagnostic with a
 * non-negligible per-orbit advance — the qualitative signal that a bound orbit
 * precesses (a GR rosette) rather than closing on itself (a Kepler ellipse). The
 * number stays in the diagnostic; here we only read whether it is present and
 * non-zero so the lens can label the orbit "precessing" without a raw decimal.
 */
function orbitPrecesses(data: Trajectory): boolean {
  const diagnostics = data.metadata?.diagnostics as
    | { perihelionPrecession?: { precessionPerOrbit?: unknown } }
    | undefined;
  const perOrbit = diagnostics?.perihelionPrecession?.precessionPerOrbit;
  return typeof perOrbit === "number" && Math.abs(perOrbit) > 1e-3;
}

// Draw the exported orbit (the planar x-y trajectory) in its own panel, with the
// central body at the origin and the current position marked. This is rendering
// the exported state columns, not re-deriving the orbit: a Kepler ellipse closes
// on itself while a Schwarzschild orbit traces a precessing rosette.
function drawOrbitPanel(
  ctx: CanvasRenderingContext2D,
  area: DOMRect,
  orbit: [number, number][],
  current: [number, number],
): void {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const [x, y] of orbit) {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  // Keep the central body (origin) in frame so the focus reads correctly.
  minX = Math.min(minX, 0);
  maxX = Math.max(maxX, 0);
  minY = Math.min(minY, 0);
  maxY = Math.max(maxY, 0);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  // Preserve aspect ratio so the orbit's shape (and its precession) is honest.
  const scale = Math.min(area.width / spanX, area.height / spanY) * 0.86;
  const cx = area.x + area.width / 2 - ((minX + maxX) / 2) * scale;
  const cy = area.y + area.height / 2 + ((minY + maxY) / 2) * scale;
  const mapX = (x: number) => cx + x * scale;
  const mapY = (y: number) => cy - y * scale;

  // The central body the orbit is bound to.
  ctx.fillStyle = theme.textFaint;
  ctx.beginPath();
  ctx.arc(mapX(0), mapY(0), 4, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  orbit.forEach(([x, y], index) => {
    const px = mapX(x);
    const py = mapY(y);
    if (index === 0) {
      ctx.moveTo(px, py);
    } else {
      ctx.lineTo(px, py);
    }
  });
  ctx.stroke();

  ctx.fillStyle = theme.accentStrong;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.arc(mapX(current[0]), mapY(current[1]), 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
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

  const plot = potentialPlot(data);
  if (!plot) {
    ctx.fillStyle = theme.textMuted;
    ctx.font = '15px "IBM Plex Sans", system-ui, sans-serif';
    ctx.fillText("Effective potential unavailable — regenerate example data.", 28, 44);
    return;
  }

  const coordIndex = columnIndex(data, plot.coordinate);
  const coordDotIndex = columnIndex(data, `${plot.coordinate}_dot`);
  const coordDotValues =
    coordDotIndex >= 0 ? data.states.map((state) => state[coordDotIndex]) : null;
  const bounds = computeBounds(plot, coordDotValues);

  // Central-force / GR orbits export a classification and a planar (x, y) trace:
  // for those we draw the orbit itself alongside the potential, so the orbit's
  // shape — a closed Kepler ellipse vs a precessing Schwarzschild rosette — is
  // visible next to its energy level. Other effective-potential systems (the
  // symmetric top) keep the reduced-coordinate phase portrait.
  const xIndex = columnIndex(data, "x");
  const yIndex = columnIndex(data, "y");
  const hasOrbit = Boolean(plot.classification) && xIndex >= 0 && yIndex >= 0;
  const orbit = hasOrbit
    ? data.states.map((state) => [state[xIndex], state[yIndex]] as [number, number])
    : null;

  const hasPhase = !hasOrbit && coordDotValues !== null && coordIndex >= 0;
  const useRight = hasOrbit || hasPhase;
  const left = plotArea(width * 0.08, height * 0.16, width * (useRight ? 0.5 : 0.84), height * 0.68);
  const right = plotArea(width * 0.62, height * 0.18, width * 0.3, height * 0.64);

  const mapC = (coordinate: number, area: DOMRect) =>
    area.x + ((coordinate - bounds.minC) / (bounds.maxC - bounds.minC || 1)) * area.width;
  const mapV = (value: number) =>
    left.y + left.height - ((value - bounds.minV) / (bounds.maxV - bounds.minV || 1)) * left.height;
  const mapCDot = (value: number) =>
    right.y + right.height - ((value - bounds.minCDot) / (bounds.maxCDot - bounds.minCDot || 1)) * right.height;

  drawAxes(ctx, left);
  if (hasPhase) {
    drawAxes(ctx, right);
  }

  // The exported potential curve.
  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 2;
  ctx.beginPath();
  plot.coordinateValues.forEach((coordinate, index) => {
    const x = mapC(coordinate, left);
    const y = mapV(plot.potentialValues[index]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  // The exported energy level.
  const energyY = mapV(plot.energy);
  ctx.strokeStyle = theme.accent;
  ctx.setLineDash([8, 8]);
  ctx.beginPath();
  ctx.moveTo(left.x, energyY);
  ctx.lineTo(left.x + left.width, energyY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Exported turning points: where the energy meets the potential (the orbit's
  // reach in the reduced coordinate).
  for (const turningPoint of plot.turningPoints ?? []) {
    if (turningPoint < bounds.minC || turningPoint > bounds.maxC) {
      continue;
    }
    const x = mapC(turningPoint, left);
    ctx.strokeStyle = theme.textFaint;
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 5]);
    ctx.beginPath();
    ctx.moveTo(x, left.y);
    ctx.lineTo(x, left.y + left.height);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = theme.textPrimary;
    ctx.beginPath();
    ctx.arc(x, energyY, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  // The exported orbit itself (x, y), when this is a central-force / GR orbit.
  if (hasOrbit && orbit) {
    drawOrbitPanel(ctx, right, orbit, [sample.state[xIndex], sample.state[yIndex]]);
  }

  // The reduced-coordinate phase trajectory (coordinate vs its rate).
  if (hasPhase && coordDotValues) {
    ctx.strokeStyle = theme.textFaint;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    data.states.forEach((state, index) => {
      const x = mapC(state[coordIndex], right);
      const y = mapCDot(coordDotValues[index]);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
  }

  // The current position on both panels.
  const coordinate = coordIndex >= 0 ? sample.state[coordIndex] : plot.coordinateValues[0];
  ctx.fillStyle = theme.accentStrong;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 12;
  ctx.beginPath();
  ctx.arc(clamp(mapC(coordinate, left), left.x, left.x + left.width), mapV(potentialAt(plot, coordinate)), 6, 0, Math.PI * 2);
  ctx.fill();
  if (hasPhase && coordDotIndex >= 0) {
    ctx.beginPath();
    ctx.arc(
      clamp(mapC(coordinate, right), right.x, right.x + right.width),
      mapCDot(sample.state[coordDotIndex]),
      6,
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }
  ctx.shadowBlur = 0;

  const coordinateLabel = plot.coordinateLatex ? mathLabel(plot.coordinateLatex) : plot.coordinate;
  const potentialLabel = mathLabel(`${plot.potentialLatex ?? "V"}_{\\mathrm{eff}}`);
  drawLabel(ctx, potentialLabel, left.x + 10, left.y + 18);
  drawLabel(ctx, "E", left.x + left.width - 18, energyY - 8);
  drawLabel(ctx, coordinateLabel, left.x + left.width - 12, left.y + left.height + 22);
  if (hasPhase) {
    drawLabel(ctx, coordinateLabel, right.x + right.width - 12, right.y + right.height + 22);
    drawLabel(ctx, mathLabel(`\\dot{${plot.coordinateLatex ?? plot.coordinate}}`), right.x + 8, right.y + 18);
  }
  if (hasOrbit) {
    drawLabel(ctx, "orbit", right.x + 8, right.y + 16);
  }

  // The exported orbit classification, kept qualitative (no raw decimals). When a
  // measured precession diagnostic is present (the GR rosette), tag it alongside
  // the bound/unbound class so the precessing case reads distinctly from Kepler.
  if (plot.classification) {
    const precessing = hasOrbit && orbitPrecesses(data);
    const label = precessing
      ? `${plot.classification.replace(/[-_]/g, " ")} · precessing`
      : plot.classification.replace(/[-_]/g, " ");
    ctx.fillStyle = theme.textPrimary;
    ctx.font = '600 13px "IBM Plex Sans", system-ui, sans-serif';
    ctx.fillText(label, left.x, left.y - 6);
  }
}
