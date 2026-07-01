/**
 * FE-067 — the Minkowski spacetime-diagram lens for `system_kind =
 * "relativistic-worldline"` (consumes BE-119).
 *
 * The backend proper-time worldline arrives as coordinate points `[x0, x1, x2]`
 * with a `minkowski-2-plus-1` renderer hint (time bounds, spatial axes, and a
 * light-cone reference geometry with an apex and signal speed). This lens plots
 * it as a conventional spacetime diagram: coordinate time `x0` runs up the
 * vertical axis and the spatial displacement runs across the horizontal axis,
 * with the exported light cone drawn through its apex. Nothing physical is
 * recomputed here — the worldline, proper time, apex, and speed are all read
 * straight from the export; the only client-side geometry is the 2D→1D spatial
 * projection needed to place a 2+1 worldline on a flat diagram.
 */
import { theme } from "./design/theme";
import type { Trajectory } from "./data/trajectory";
import type { Sample } from "./playback";
import { clamp } from "./util";

type Vec3 = [number, number, number];

type LightConeHint = {
  kind: string;
  apex: Vec3;
  speed: number;
};

type SpacetimeWorldline = {
  /** Coordinate-time bounds `[x0_min, x0_max]` for the vertical axis. */
  timeBounds: [number, number];
  /** Label for the time axis (e.g. "x0"). */
  timeLabel: string;
  /** Labels for the two spatial coordinates (e.g. ["x1", "x2"]). */
  spaceLabels: string[];
  /** Worldline coordinate points `[x0, x1, x2]`, one per trajectory sample. */
  points: Vec3[];
  lightCone: LightConeHint;
};

function isVec3(value: unknown): value is Vec3 {
  return (
    Array.isArray(value) &&
    value.length === 3 &&
    value.every((item) => typeof item === "number")
  );
}

/** Read the exported spacetime-diagram payload, or null when it is absent. */
export function spacetimeWorldline(data: Trajectory): SpacetimeWorldline | null {
  const meta = data.metadata as Record<string, unknown> | undefined;
  const worldline = meta?.worldline as Record<string, unknown> | undefined;
  const hints = meta?.rendererHints as Record<string, unknown> | undefined;
  if (!worldline || !hints) {
    return null;
  }

  const points = Array.isArray(worldline.points)
    ? worldline.points.filter(isVec3)
    : [];
  if (points.length < 2) {
    return null;
  }

  const bounds = hints.bounds as Record<string, unknown> | undefined;
  const timeRange = bounds?.time;
  const timeBounds: [number, number] =
    Array.isArray(timeRange) &&
    timeRange.length === 2 &&
    timeRange.every((item) => typeof item === "number")
      ? [timeRange[0] as number, timeRange[1] as number]
      : [points[0][0], points[points.length - 1][0]];

  const axes = hints.axes as Record<string, unknown> | undefined;
  const timeLabel = typeof axes?.time === "string" ? (axes.time as string) : "x0";
  const spaceLabels =
    Array.isArray(axes?.space) && axes!.space.every((item) => typeof item === "string")
      ? (axes!.space as string[])
      : (worldline.spatialCoordinates as string[]) ?? ["x1", "x2"];

  const cone = Array.isArray(hints.referenceGeometry)
    ? (hints.referenceGeometry as Record<string, unknown>[]).find(
        (item) => item.kind === "lightCone" && isVec3(item.apex),
      )
    : undefined;
  const lightCone: LightConeHint = cone
    ? {
        kind: "lightCone",
        apex: cone.apex as Vec3,
        speed: typeof cone.speed === "number" ? (cone.speed as number) : 1,
      }
    : { kind: "lightCone", apex: points[0], speed: 1 };

  return { timeBounds, timeLabel, spaceLabels, points, lightCone };
}

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
}

function plotArea(width: number, height: number) {
  const marginX = Math.max(48, width * 0.09);
  const marginY = Math.max(40, height * 0.1);
  return {
    left: marginX,
    right: width - marginX,
    top: marginY,
    bottom: height - marginY,
    width: Math.max(1, width - 2 * marginX),
    height: Math.max(1, height - 2 * marginY),
  };
}

type Frame = {
  apexTime: number;
  spaceOrigin: [number, number];
  spaceDirection: [number, number];
  speed: number;
  halfWidth: number;
  timeBounds: [number, number];
  area: ReturnType<typeof plotArea>;
};

/**
 * Build the diagram frame: the vertical axis is coordinate time; the horizontal
 * axis is the signed spatial displacement along the worldline's net direction of
 * motion (a straight timelike line stays straight). The horizontal half-width is
 * sized so the exported light cone reaches the diagram corners.
 */
function buildFrame(model: SpacetimeWorldline, area: ReturnType<typeof plotArea>): Frame {
  const apex = model.lightCone.apex;
  const spaceOrigin: [number, number] = [apex[1], apex[2]];

  const first = model.points[0];
  const last = model.points[model.points.length - 1];
  let dx = last[1] - first[1];
  let dy = last[2] - first[2];
  const norm = Math.hypot(dx, dy);
  if (norm < 1e-9) {
    dx = 1;
    dy = 0;
  } else {
    dx /= norm;
    dy /= norm;
  }
  const spaceDirection: [number, number] = [dx, dy];

  const [t0, t1] = model.timeBounds;
  const speed = model.lightCone.speed;
  // The cone reaches |h| = speed * |t - apexTime| at the time-window edges.
  const coneReach = Math.max(
    speed * Math.abs(t1 - apex[0]),
    speed * Math.abs(t0 - apex[0]),
  );
  let worldlineReach = 0;
  for (const point of model.points) {
    const h = (point[1] - spaceOrigin[0]) * dx + (point[2] - spaceOrigin[1]) * dy;
    worldlineReach = Math.max(worldlineReach, Math.abs(h));
  }
  const halfWidth = Math.max(coneReach, worldlineReach, 1e-6) * 1.08;

  return {
    apexTime: apex[0],
    spaceOrigin,
    spaceDirection,
    speed,
    halfWidth,
    timeBounds: model.timeBounds,
    area,
  };
}

/** Signed spatial displacement of a worldline point along the motion axis. */
function horizontal(frame: Frame, point: Vec3): number {
  return (
    (point[1] - frame.spaceOrigin[0]) * frame.spaceDirection[0] +
    (point[2] - frame.spaceOrigin[1]) * frame.spaceDirection[1]
  );
}

/** Map diagram coordinates (h = signed space, t = coordinate time) to pixels. */
function project(frame: Frame, h: number, t: number): { x: number; y: number } {
  const { area, halfWidth, timeBounds } = frame;
  const [t0, t1] = timeBounds;
  const tSpan = Math.max(1e-9, t1 - t0);
  return {
    x: area.left + ((h + halfWidth) / (2 * halfWidth)) * area.width,
    y: area.bottom - ((t - t0) / tSpan) * area.height,
  };
}

function drawAxes(ctx: CanvasRenderingContext2D, frame: Frame): void {
  const { area } = frame;
  const originX = project(frame, 0, frame.timeBounds[0]).x;
  const apexY = project(frame, 0, frame.apexTime).y;

  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  // Vertical time axis (h = 0).
  ctx.beginPath();
  ctx.moveTo(originX, area.top);
  ctx.lineTo(originX, area.bottom);
  ctx.stroke();
  // Horizontal space axis through the light-cone apex.
  ctx.beginPath();
  ctx.moveTo(area.left, apexY);
  ctx.lineTo(area.right, apexY);
  ctx.stroke();

  ctx.fillStyle = theme.textMuted;
  ctx.font = '13px "IBM Plex Sans", system-ui, sans-serif';
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  // Time axis label at the top of the vertical axis.
  ctx.fillText("time ↑", originX + 8, area.top + 8);
  ctx.fillText("x⁰", originX + 8, area.top + 26);
  // Space axis label at the right of the horizontal axis.
  ctx.textAlign = "right";
  ctx.fillText("space →", area.right, apexY - 12);
}

function drawLightCone(ctx: CanvasRenderingContext2D, frame: Frame): void {
  const { area, halfWidth, speed, apexTime } = frame;
  const apex = project(frame, 0, apexTime);

  // Future/past cone edges: h = ± speed * (t - apexTime). Trace each of the four
  // rays out to the horizontal half-width so they meet the diagram corners.
  const dt = halfWidth / Math.max(1e-9, speed);
  const rays: Array<[number, number]> = [
    [halfWidth, apexTime + dt],
    [-halfWidth, apexTime + dt],
    [halfWidth, apexTime - dt],
    [-halfWidth, apexTime - dt],
  ];

  // Shade the causal future (the timelike interior above the apex) faintly.
  const futureRight = project(frame, halfWidth, apexTime + dt);
  const futureLeft = project(frame, -halfWidth, apexTime + dt);
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(apex.x, apex.y);
  ctx.lineTo(futureRight.x, futureRight.y);
  ctx.lineTo(futureLeft.x, futureLeft.y);
  ctx.closePath();
  ctx.clip();
  const glow = ctx.createLinearGradient(0, apex.y, 0, area.top);
  glow.addColorStop(0, "rgba(111, 182, 201, 0.16)");
  glow.addColorStop(1, "rgba(111, 182, 201, 0)");
  ctx.fillStyle = glow;
  ctx.fillRect(area.left, area.top, area.width, apex.y - area.top);
  ctx.restore();

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 1.4;
  ctx.setLineDash([6, 5]);
  for (const [h, t] of rays) {
    const end = project(frame, h, t);
    ctx.beginPath();
    ctx.moveTo(apex.x, apex.y);
    ctx.lineTo(end.x, end.y);
    ctx.stroke();
  }
  ctx.setLineDash([]);
}

function drawWorldline(
  ctx: CanvasRenderingContext2D,
  frame: Frame,
  model: SpacetimeWorldline,
  currentIndex: number,
): void {
  const points = model.points.map((point) => project(frame, horizontal(frame, point), point[0]));
  if (points.length < 2) {
    return;
  }

  // The full worldline as a faint geometric object.
  ctx.strokeStyle = theme.textFaint;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  });
  ctx.stroke();

  // The proper-time-traversed portion up to the current sample, drawn bright.
  ctx.save();
  ctx.strokeStyle = theme.accentStrong;
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 10;
  ctx.beginPath();
  for (let index = 0; index <= currentIndex && index < points.length; index += 1) {
    const point = points[index];
    if (index === 0) {
      ctx.moveTo(point.x, point.y);
    } else {
      ctx.lineTo(point.x, point.y);
    }
  }
  ctx.stroke();
  ctx.restore();

  // The current event on the worldline.
  const marker = points[Math.min(currentIndex, points.length - 1)];
  ctx.fillStyle = theme.textPrimary;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 14;
  ctx.beginPath();
  ctx.arc(marker.x, marker.y, 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
}

function drawLegend(ctx: CanvasRenderingContext2D, frame: Frame): void {
  const x = frame.area.left + 14;
  let y = frame.area.top + 14;
  ctx.font = '12px "IBM Plex Sans", system-ui, sans-serif';
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";

  const row = (color: string, dashed: boolean, label: string) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = dashed ? 1.4 : 3;
    ctx.setLineDash(dashed ? [6, 5] : []);
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 22, y);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = theme.textMuted;
    ctx.fillText(label, x + 30, y);
    y += 20;
  };

  row(theme.accentStrong, false, "worldline");
  row(theme.cool, true, "light cone");
}

export function drawSpacetimeScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  sample: Sample,
  width: number,
  height: number,
): void {
  setupCanvas(ctx, width, height);
  drawBackground(ctx, width, height);

  const model = spacetimeWorldline(data);
  if (!model) {
    ctx.fillStyle = theme.textMuted;
    ctx.font = '16px "IBM Plex Sans", system-ui, sans-serif';
    ctx.textAlign = "left";
    ctx.textBaseline = "alphabetic";
    ctx.fillText("Spacetime worldline data unavailable.", 32, 48);
    return;
  }

  const area = plotArea(width, height);
  const frame = buildFrame(model, area);
  const currentIndex = clamp(sample.index, 0, model.points.length - 1);

  drawLightCone(ctx, frame);
  drawAxes(ctx, frame);
  drawWorldline(ctx, frame, model, currentIndex);
  drawLegend(ctx, frame);
}
