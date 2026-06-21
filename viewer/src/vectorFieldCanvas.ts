/**
 * FE-045 — the shared vector-field overlay.
 *
 * Draws an exported vector field (BE-091) as a quiver of glyphs colored by
 * magnitude through the shared FE-038 scalar scale, plus the exported field-line
 * / streamline polylines. It composes over the scalar-field heatmap (FE-044) on
 * the same plot area and projector, so the glyphs and field lines register on the
 * colored cells they describe. Every number is read from the export: this draws
 * the field Python sampled and integrated, it never differentiates a potential or
 * integrates a streamline in the browser.
 */
import { type FieldLines, type VectorField } from "./data/trajectory";
import { type ScalarScale } from "./design/colormaps";
import { fieldProjector, type PlotArea } from "./scalarFieldCanvas";

/**
 * A robust upper end for the magnitude color/length scale: the 95th percentile
 * of the exported magnitudes, so a near-singular cell at a point charge does not
 * wash every other glyph out. The scale clamps above this, saturating honestly
 * rather than implying detail past it.
 */
export function robustMagnitudeMax(field: VectorField): number {
  const values: number[] = [];
  for (const row of field.magnitude) {
    for (const value of row) {
      if (Number.isFinite(value)) {
        values.push(value);
      }
    }
  }
  if (values.length === 0) {
    return 1;
  }
  values.sort((a, b) => a - b);
  const index = Math.min(values.length - 1, Math.floor(values.length * 0.95));
  const max = values[index];
  return max > 0 ? max : values[values.length - 1] || 1;
}

function drawFieldLines(
  ctx: CanvasRenderingContext2D,
  lines: FieldLines,
  project: (x: number, y: number) => { x: number; y: number },
): void {
  ctx.save();
  ctx.strokeStyle = "rgba(232, 238, 247, 0.32)";
  ctx.lineWidth = 1.2;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (const line of lines.lines) {
    if (line.length < 2) {
      continue;
    }
    ctx.beginPath();
    line.forEach(([x, y], index) => {
      const point = project(x, y);
      if (index === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    ctx.stroke();
  }
  ctx.restore();
}

function drawGlyph(
  ctx: CanvasRenderingContext2D,
  baseX: number,
  baseY: number,
  ux: number,
  uy: number,
  length: number,
  color: string,
): void {
  // `uy` is negated: field +y is up, but screen +y is down.
  const tipX = baseX + ux * length;
  const tipY = baseY - uy * length;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(baseX, baseY);
  ctx.lineTo(tipX, tipY);
  ctx.stroke();

  const head = Math.min(6, Math.max(3, length * 0.4));
  const angle = Math.atan2(-uy, ux);
  ctx.beginPath();
  ctx.moveTo(tipX, tipY);
  ctx.lineTo(
    tipX - head * Math.cos(angle - Math.PI / 6),
    tipY - head * Math.sin(angle - Math.PI / 6),
  );
  ctx.lineTo(
    tipX - head * Math.cos(angle + Math.PI / 6),
    tipY - head * Math.sin(angle + Math.PI / 6),
  );
  ctx.closePath();
  ctx.fill();
}

export interface VectorOverlayOptions {
  field: VectorField;
  lines?: FieldLines | null;
  /** Scale mapping magnitude to glyph color; its domain caps glyph length too. */
  magnitudeScale: ScalarScale;
  area: PlotArea;
}

/** Draw the field lines and the magnitude-colored glyph quiver onto the stage. */
export function drawVectorFieldOverlay(
  ctx: CanvasRenderingContext2D,
  options: VectorOverlayOptions,
): void {
  const { field, lines, magnitudeScale, area } = options;
  const [nx, ny] = field.shape;
  const project = fieldProjector(field.axes, area);

  if (lines) {
    drawFieldLines(ctx, lines, project);
  }

  // Subsample to ~14×12 glyphs so the quiver reads without crowding, whatever the
  // export resolution.
  const stepX = Math.max(1, Math.round(nx / 14));
  const stepY = Math.max(1, Math.round(ny / 12));
  const cellScreen = (area.width / nx) * stepX;
  const maxLength = cellScreen * 0.9;
  const minLength = cellScreen * 0.22;
  const scaleMax = magnitudeScale.domain[1];

  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (let i = 0; i < nx; i += stepX) {
    for (let j = 0; j < ny; j += stepY) {
      const [u, v] = field.components[i][j];
      const magnitude = field.magnitude[i][j];
      const norm = Math.hypot(u, v);
      if (!(norm > 0) || !Number.isFinite(magnitude)) {
        continue;
      }
      const base = project(field.axes[0][i], field.axes[1][j]);
      const ratio = scaleMax > 0 ? Math.min(1, magnitude / scaleMax) : 0;
      const length = minLength + ratio * (maxLength - minLength);
      drawGlyph(ctx, base.x, base.y, u / norm, v / norm, length, magnitudeScale.css(magnitude));
    }
  }
  ctx.restore();
}
