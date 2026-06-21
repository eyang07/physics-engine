import { theme } from "./design/theme";
import {
  rendererHints,
  wavefrontField,
  type Trajectory,
  type WavefrontSnapshot,
} from "./data/trajectory";
import { magma, scalarScale, type ScalarScale } from "./design/colormaps";
import type { Sample } from "./playback";
import { clamp } from "./util";

type Point = {
  x: number;
  y: number;
};

type Ray = {
  index: number;
  states: number[][];
};

type RayBundle = {
  stateNames: string[];
  initialY: number[];
  rays: Ray[];
};

type WavefrontRecord = {
  time: number;
  points: number[][];
};

type WavefrontMetadata = {
  parameters?: {
    base_speed?: number;
    lens_strength?: number;
    lens_width?: number;
  };
  rayBundle?: RayBundle;
  wavefronts?: WavefrontRecord[];
  hamiltonian?: {
    maxDrift?: number;
  };
};

type Bounds = {
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
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
  gradient.addColorStop(0.52, theme.ink800);
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

function metadata(data: Trajectory): WavefrontMetadata {
  return (data.metadata ?? {}) as WavefrontMetadata;
}

function isRayBundle(value: RayBundle | undefined): value is RayBundle {
  return Boolean(
    value &&
      Array.isArray(value.rays) &&
      value.rays.every((ray) => Array.isArray(ray.states)) &&
      Array.isArray(value.stateNames),
  );
}

function computeBounds(data: Trajectory): Bounds {
  const hints = rendererHints(data);
  const displayBounds = hints.viewportBounds ?? hints.bounds;
  const xRange = displayBounds?.x ?? [-3, 3];
  const yRange = displayBounds?.y ?? [-2, 2];
  const xSpan = Math.max(1e-6, xRange[1] - xRange[0]);
  const ySpan = Math.max(1e-6, yRange[1] - yRange[0]);
  return {
    xMin: xRange[0] - xSpan * 0.08,
    xMax: xRange[1] + xSpan * 0.08,
    yMin: yRange[0] - ySpan * 0.12,
    yMax: yRange[1] + ySpan * 0.12,
  };
}

function plotArea(width: number, height: number) {
  const marginX = Math.max(42, width * 0.08);
  const marginY = Math.max(36, height * 0.1);
  return {
    left: marginX,
    right: width - marginX,
    top: marginY,
    bottom: height - marginY,
    width: Math.max(1, width - 2 * marginX),
    height: Math.max(1, height - 2 * marginY),
  };
}

function project(point: Point, bounds: Bounds, area: ReturnType<typeof plotArea>): Point {
  return {
    x: area.left + ((point.x - bounds.xMin) / (bounds.xMax - bounds.xMin)) * area.width,
    y: area.bottom - ((point.y - bounds.yMin) / (bounds.yMax - bounds.yMin)) * area.height,
  };
}

function drawMedium(ctx: CanvasRenderingContext2D, data: Trajectory, bounds: Bounds, area: ReturnType<typeof plotArea>) {
  const params = metadata(data).parameters ?? {};
  const strength = params.lens_strength ?? 0.42;
  const width = params.lens_width ?? 0.85;
  const center = project({ x: 0, y: 0 }, bounds, area);
  const edge = project({ x: width, y: 0 }, bounds, area);
  const radius = Math.abs(edge.x - center.x);

  const gradient = ctx.createRadialGradient(center.x, center.y, 0, center.x, center.y, radius * 2.7);
  gradient.addColorStop(0, `rgba(246, 181, 95, ${0.18 + strength * 0.16})`);
  gradient.addColorStop(0.45, "rgba(102, 183, 197, 0.08)");
  gradient.addColorStop(1, "rgba(102, 183, 197, 0)");
  ctx.fillStyle = gradient;
  ctx.beginPath();
  ctx.arc(center.x, center.y, radius * 2.7, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "rgba(246, 181, 95, 0.2)";
  ctx.lineWidth = 1;
  for (const scale of [1, 1.7, 2.4]) {
    ctx.beginPath();
    ctx.arc(center.x, center.y, radius * scale, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawRay(ctx: CanvasRenderingContext2D, ray: Ray, currentIndex: number, bounds: Bounds, area: ReturnType<typeof plotArea>) {
  const states = ray.states.slice(0, currentIndex + 1);
  if (states.length < 2) {
    return;
  }
  ctx.beginPath();
  states.forEach((state, index) => {
    const point = project({ x: state[0], y: state[1] }, bounds, area);
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();
}

function drawWavefront(ctx: CanvasRenderingContext2D, points: number[][], bounds: Bounds, area: ReturnType<typeof plotArea>, alpha: number, width: number) {
  if (points.length < 2) {
    return;
  }
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = theme.accentStrong;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 12 * alpha;
  ctx.beginPath();
  points.forEach((state, index) => {
    const point = project({ x: state[0], y: state[1] }, bounds, area);
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();
  ctx.restore();
}

// FE-048 — draw one exported wavefront colored by its measured intensity proxy:
// each segment between adjacent rays is tinted by the segment's spreading-derived
// intensity, so the front brightens where rays bunch toward a caustic. The colors
// are read straight from the exported diagnostic; no focusing is recomputed here.
function drawIntensityWavefront(
  ctx: CanvasRenderingContext2D,
  snapshot: WavefrontSnapshot,
  bounds: Bounds,
  area: ReturnType<typeof plotArea>,
  scale: ScalarScale,
  alpha: number,
  width: number,
): void {
  const points = snapshot.points.map((point) => project({ x: point[0], y: point[1] }, bounds, area));
  if (points.length < 2) {
    return;
  }
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  for (let index = 0; index < points.length - 1; index += 1) {
    const intensity = snapshot.intensity[Math.min(index, snapshot.intensity.length - 1)] ?? 0;
    ctx.strokeStyle = scale.css(intensity);
    ctx.beginPath();
    ctx.moveTo(points[index].x, points[index].y);
    ctx.lineTo(points[index + 1].x, points[index + 1].y);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawWavefrontScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  sample: Sample,
  width: number,
  height: number,
): void {
  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);

  const meta = metadata(data);
  const bundle = meta.rayBundle;
  if (!isRayBundle(bundle)) {
    ctx.fillStyle = theme.textMuted;
    ctx.font = '16px "IBM Plex Sans", system-ui, sans-serif';
    ctx.fillText("Wavefront data unavailable.", 32, 48);
    return;
  }

  const area = plotArea(width, height);
  const bounds = computeBounds(data);
  const currentIndex = clamp(sample.index, 0, data.time.length - 1);

  drawMedium(ctx, data, bounds, area);

  ctx.strokeStyle = "rgba(117, 185, 198, 0.2)";
  ctx.lineWidth = 1.2;
  for (const ray of bundle.rays) {
    drawRay(ctx, ray, currentIndex, bounds, area);
  }

  // The reached wavefronts, colored by the measured intensity proxy (FE-048): the
  // caustic where rays cross reads as a bright band. Falls back to drawing only the
  // rays + live front when the intensity channel is absent.
  const field = wavefrontField(data);
  if (field) {
    const intensityScale = scalarScale(magma, [0, field.intensityMax]);
    const currentTime = data.time[currentIndex] ?? 0;
    for (const snapshot of field.snapshots) {
      if (snapshot.time <= currentTime) {
        drawIntensityWavefront(ctx, snapshot, bounds, area, intensityScale, 0.5, 2.6);
      }
    }
  }

  const activePoints = bundle.rays.map((ray) => ray.states[currentIndex]).filter(Boolean);
  drawWavefront(ctx, activePoints, bounds, area, 0.95, 3);

  const centerRay = bundle.rays[Math.floor(bundle.rays.length / 2)];
  const centerState = centerRay?.states[currentIndex];
  if (centerState) {
    const point = project({ x: centerState[0], y: centerState[1] }, bounds, area);
    ctx.fillStyle = theme.textPrimary;
    ctx.shadowColor = theme.accent;
    ctx.shadowBlur = 16;
    ctx.beginPath();
    ctx.arc(point.x, point.y, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }
}
