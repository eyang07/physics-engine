/**
 * FE-044 — the shared scalar-field lens.
 *
 * Renders a scalar field Python sampled over a 2D coordinate grid (BE-091) as a
 * heatmap with iso-contours. The coloring is the single honest scalar→color
 * mapping (`scalarScale`, FE-038), captioned on stage by the shared scalar
 * legend, so a potential, a curvature scalar, or an intensity field all read the
 * same way. The grid is drawn exactly as exported: this lens computes only the
 * value range and the colors, never the field — it is a renderer, not a solver.
 *
 * The heatmap and the contour lines share one index-based grid mapping, so the
 * iso-lines sit on the colored cells they trace rather than drifting half a cell.
 */
import { type ScalarField } from "./data/trajectory";
import { scalarScale, viridis } from "./design/colormaps";
import { theme } from "./design/theme";

function setupCanvas(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const pixelRatio = window.devicePixelRatio || 1;
  const drawingWidth = Math.max(1, Math.floor(width * pixelRatio));
  const drawingHeight = Math.max(1, Math.floor(height * pixelRatio));
  if (ctx.canvas.width !== drawingWidth || ctx.canvas.height !== drawingHeight) {
    ctx.canvas.width = drawingWidth;
    ctx.canvas.height = drawingHeight;
  }
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
}

function drawBackground(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, theme.ink900);
  gradient.addColorStop(0.52, theme.ink800);
  gradient.addColorStop(1, theme.ink850);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);
}

type PlotArea = {
  left: number;
  top: number;
  width: number;
  height: number;
};

function plotArea(width: number, height: number): PlotArea {
  const marginX = Math.max(48, width * 0.09);
  const marginY = Math.max(40, height * 0.1);
  return {
    left: marginX,
    top: marginY,
    width: Math.max(1, width - 2 * marginX),
    height: Math.max(1, height - 2 * marginY),
  };
}

function valueDomain(values: number[][]): [number, number] {
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  for (const row of values) {
    for (const value of row) {
      if (!Number.isFinite(value)) {
        continue;
      }
      if (value < min) {
        min = value;
      }
      if (value > max) {
        max = value;
      }
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [0, 1];
  }
  return [min, max];
}

/**
 * Blit the grid as a heatmap. The field is rasterized at grid resolution into an
 * offscreen image and stretched into the plot area with bilinear smoothing, so
 * the colored cells map one-to-one onto the exported samples. The image's top row
 * is the largest second-coordinate value, matching the upward stage axis.
 */
function drawHeatmap(
  ctx: CanvasRenderingContext2D,
  field: ScalarField,
  scale: ReturnType<typeof scalarScale>,
  area: PlotArea,
): void {
  const [nx, ny] = field.shape;
  const image = ctx.createImageData(nx, ny);
  for (let py = 0; py < ny; py += 1) {
    const j = ny - 1 - py; // image row 0 is the highest second-coordinate value
    for (let px = 0; px < nx; px += 1) {
      const [r, g, b] = scale.at(field.values[px][j]);
      const offset = (py * nx + px) * 4;
      image.data[offset] = r;
      image.data[offset + 1] = g;
      image.data[offset + 2] = b;
      image.data[offset + 3] = 255;
    }
  }
  const tile = document.createElement("canvas");
  tile.width = nx;
  tile.height = ny;
  const tileCtx = tile.getContext("2d");
  if (!tileCtx) {
    return;
  }
  tileCtx.putImageData(image, 0, 0);
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(tile, area.left, area.top, area.width, area.height);
  ctx.restore();
}

/**
 * Draw a handful of iso-contours with marching squares. The lines use the same
 * index→screen mapping as the heatmap (grid sample `i` sits at the center of its
 * cell), so a contour rides the band of color it separates. This only connects
 * exported values at the levels they cross — no field is evaluated here.
 */
function drawContours(
  ctx: CanvasRenderingContext2D,
  field: ScalarField,
  domain: [number, number],
  area: PlotArea,
): void {
  const [nx, ny] = field.shape;
  const [min, max] = domain;
  const span = max - min;
  if (!(span > 0)) {
    return;
  }
  const gridX = (i: number): number => area.left + ((i + 0.5) / nx) * area.width;
  const gridY = (j: number): number => area.top + ((ny - 1 - j + 0.5) / ny) * area.height;

  const levelCount = 7;
  ctx.save();
  ctx.lineWidth = 1.1;
  ctx.lineCap = "round";
  for (let l = 1; l <= levelCount; l += 1) {
    const level = min + (span * l) / (levelCount + 1);
    // Brighten the higher iso-levels so the contours read as a gradient too.
    ctx.strokeStyle = `rgba(13, 18, 28, ${0.22 + 0.3 * (l / levelCount)})`;
    ctx.beginPath();
    for (let i = 0; i < nx - 1; i += 1) {
      for (let j = 0; j < ny - 1; j += 1) {
        const corners = [
          { vi: i, vj: j, v: field.values[i][j] },
          { vi: i + 1, vj: j, v: field.values[i + 1][j] },
          { vi: i + 1, vj: j + 1, v: field.values[i + 1][j + 1] },
          { vi: i, vj: j + 1, v: field.values[i][j + 1] },
        ];
        const crossings: { x: number; y: number }[] = [];
        for (let e = 0; e < 4; e += 1) {
          const a = corners[e];
          const b = corners[(e + 1) % 4];
          if (a.v < level === b.v < level) {
            continue;
          }
          const t = (level - a.v) / (b.v - a.v);
          const fi = a.vi + (b.vi - a.vi) * t;
          const fj = a.vj + (b.vj - a.vj) * t;
          crossings.push({ x: gridX(fi), y: gridY(fj) });
        }
        // The common case is two crossings (one segment); a saddle cell has four,
        // drawn as two segments in edge order — close enough for an overlay.
        for (let c = 0; c + 1 < crossings.length; c += 2) {
          ctx.moveTo(crossings[c].x, crossings[c].y);
          ctx.lineTo(crossings[c + 1].x, crossings[c + 1].y);
        }
      }
    }
    ctx.stroke();
  }
  ctx.restore();
}

function drawFrame(ctx: CanvasRenderingContext2D, field: ScalarField, area: PlotArea): void {
  ctx.save();
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.strokeRect(area.left, area.top, area.width, area.height);

  ctx.fillStyle = theme.textMuted;
  ctx.font = '13px "IBM Plex Sans", system-ui, sans-serif';
  ctx.textAlign = "center";
  ctx.fillText(field.coordinates[0], area.left + area.width / 2, area.top + area.height + 26);
  ctx.save();
  ctx.translate(area.left - 30, area.top + area.height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(field.coordinates[1], 0, 0);
  ctx.restore();
  ctx.restore();
}

/** Render the scalar field as a heatmap with iso-contours on the 2D stage. */
export function drawScalarFieldScene(
  ctx: CanvasRenderingContext2D,
  field: ScalarField,
  width: number,
  height: number,
): void {
  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);

  const area = plotArea(width, height);
  const domain = valueDomain(field.values);
  const scale = scalarScale(viridis, domain);

  drawHeatmap(ctx, field, scale, area);
  drawContours(ctx, field, domain, area);
  drawFrame(ctx, field, area);
}
