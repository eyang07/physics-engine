/**
 * The 2D pendulum lens: physical motion drawn beside its phase portrait.
 *
 * (This is the one inherently-2D view; the rest live in three.js. A general
 * lens registry is future work — for now this stays a focused module.)
 */
import { theme } from "./design/theme";
import type { Trajectory } from "./data/trajectory";
import type { Sample } from "./playback";

export type Bounds = {
  minTheta: number;
  maxTheta: number;
  minOmega: number;
  maxOmega: number;
};

type Point2D = {
  x: number;
  y: number;
};

export function drawStageBackground(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, theme.ink900);
  gradient.addColorStop(0.55, theme.ink800);
  gradient.addColorStop(1, theme.ink850);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = theme.hairline;
  ctx.lineWidth = 1;
  for (let x = 0; x <= width; x += 36) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y <= height; y += 36) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

export function computePendulumBounds(data: Trajectory): Bounds {
  const theta = data.states.map((state) => state[0]);
  const omega = data.states.map((state) => state[1]);
  const thetaPad = Math.max(0.1, 0.08 * (Math.max(...theta) - Math.min(...theta)));
  const omegaPad = Math.max(0.1, 0.08 * (Math.max(...omega) - Math.min(...omega)));
  return {
    minTheta: Math.min(...theta) - thetaPad,
    maxTheta: Math.max(...theta) + thetaPad,
    minOmega: Math.min(...omega) - omegaPad,
    maxOmega: Math.max(...omega) + omegaPad,
  };
}

function drawPendulum(ctx: CanvasRenderingContext2D, theta: number, width: number, height: number): void {
  const centerX = width * 0.33;
  const centerY = height * 0.24;
  const length = Math.min(width, height) * 0.34;
  const bobX = centerX + length * Math.sin(theta);
  const bobY = centerY + length * Math.cos(theta);

  ctx.save();
  ctx.lineCap = "round";

  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(centerX, centerY, length, Math.PI * 0.62, Math.PI * 0.38, true);
  ctx.stroke();

  ctx.strokeStyle = theme.textMuted;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(centerX, centerY);
  ctx.lineTo(bobX, bobY);
  ctx.stroke();

  ctx.fillStyle = theme.textPrimary;
  ctx.beginPath();
  ctx.arc(centerX, centerY, 7, 0, Math.PI * 2);
  ctx.fill();

  const bobGradient = ctx.createRadialGradient(bobX - 8, bobY - 10, 4, bobX, bobY, 24);
  bobGradient.addColorStop(0, "#f8d58b");
  bobGradient.addColorStop(0.55, "#d88d42");
  bobGradient.addColorStop(1, "#904f2d");
  ctx.fillStyle = bobGradient;
  ctx.beginPath();
  ctx.arc(bobX, bobY, 24, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = theme.hairline;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(centerX, centerY);
  ctx.lineTo(centerX, centerY + length + 36);
  ctx.stroke();

  ctx.restore();
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
    ctx.shadowBlur = 10 * alpha * alpha;
    ctx.beginPath();
    ctx.moveTo(points[index - 1].x, points[index - 1].y);
    ctx.lineTo(points[index].x, points[index].y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawPhasePortrait(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  bounds: Bounds,
  currentIndex: number,
  theta: number,
  omega: number,
  area: DOMRect,
): void {
  const pad = 38;
  const left = area.x + pad;
  const right = area.x + area.width - pad;
  const top = area.y + pad;
  const bottom = area.y + area.height - pad;

  const mapX = (value: number) =>
    left + ((value - bounds.minTheta) / (bounds.maxTheta - bounds.minTheta)) * (right - left);
  const mapY = (value: number) =>
    bottom - ((value - bounds.minOmega) / (bounds.maxOmega - bounds.minOmega)) * (bottom - top);

  ctx.save();
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(left, mapY(0));
  ctx.lineTo(right, mapY(0));
  ctx.moveTo(mapX(0), top);
  ctx.lineTo(mapX(0), bottom);
  ctx.stroke();

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 2;
  ctx.beginPath();
  data.states.forEach((state, index) => {
    const x = mapX(state[0]);
    const y = mapY(state[1]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  drawFadingPath(
    ctx,
    data.states.slice(Math.max(0, currentIndex - 179), currentIndex + 1).map((state) => ({
      x: mapX(state[0]),
      y: mapY(state[1]),
    })),
    3,
  );

  ctx.fillStyle = theme.accentStrong;
  ctx.beginPath();
  ctx.arc(mapX(theta), mapY(omega), 6, 0, Math.PI * 2);
  ctx.fill();

  ctx.shadowBlur = 0;
  ctx.fillStyle = theme.textMuted;
  ctx.font = '12px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText("θ", right - 18, mapY(0) - 8);
  ctx.fillText("θ̇", mapX(0) + 10, top + 12);

  ctx.restore();
}

export function drawPendulumScene(
  ctx: CanvasRenderingContext2D,
  data: Trajectory,
  bounds: Bounds | null,
  sample: Sample,
  width: number,
  height: number,
): void {
  drawStageBackground(ctx, width, height);
  drawPendulum(ctx, sample.state[0], width, height);
  if (bounds) {
    drawPhasePortrait(
      ctx,
      data,
      bounds,
      sample.index,
      sample.state[0],
      sample.state[1],
      new DOMRect(width * 0.53, height * 0.17, width * 0.39, height * 0.62),
    );
  }
}
