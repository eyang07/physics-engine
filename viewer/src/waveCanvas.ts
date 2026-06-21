/**
 * FE-046 — the 1D wave displacement lens.
 *
 * Animates an exported 1D scalar-field time series (BE-094 vibrating string,
 * BE-096 dispersive wave packet) as a displacement curve `y = u(x, t)` that plays
 * back through the exported frames and loops. The string's standing and traveling
 * solutions and the packet's amplitude / envelope-intensity are separate exported
 * series; the caller toggles which one is drawn.
 *
 * A 1D field is a line, not a surface, so this draws on the 2D canvas (the FE-039
 * `FieldSurface` primitive needs a 2D grid to triangulate). It only plays back
 * exported frames — nothing about the wave is re-solved here. The vertical scale
 * is fixed to the series' peak amplitude across all frames, so the packet's
 * envelope visibly flattens as it spreads instead of being rescaled away.
 */
import { theme } from "./design/theme";
import { drawStageBackground } from "./pendulumCanvas";
import { type ScalarFieldSeries } from "./data/trajectory";

// Seconds for one full loop through the exported frames; the playback speed
// control scales the elapsed time the caller passes in.
const LOOP_PERIOD = 8;

function peakAmplitude(values: number[][]): number {
  let peak = 0;
  for (const row of values) {
    for (const value of row) {
      const magnitude = Math.abs(value);
      if (Number.isFinite(magnitude) && magnitude > peak) {
        peak = magnitude;
      }
    }
  }
  return peak > 0 ? peak : 1;
}

/** The interpolated frame for a looped elapsed time, as `value(sampleIndex)`. */
function frameSampler(series: ScalarFieldSeries, time: number): (index: number) => number {
  const count = series.shape[0];
  if (count <= 1) {
    const only = series.values[0] ?? [];
    return (index) => only[index] ?? 0;
  }
  const phase = (((time / LOOP_PERIOD) % 1) + 1) % 1;
  const cursor = phase * count;
  const lo = Math.floor(cursor) % count;
  const hi = (lo + 1) % count;
  const f = cursor - Math.floor(cursor);
  const a = series.values[lo];
  const b = series.values[hi];
  return (index) => a[index] + (b[index] - a[index]) * f;
}

export function drawWaveScene(
  ctx: CanvasRenderingContext2D,
  series: ScalarFieldSeries,
  time: number,
  width: number,
  height: number,
): void {
  drawStageBackground(ctx, width, height);

  const samples = series.shape[1];
  if (samples < 2) {
    return;
  }

  const marginX = Math.min(120, width * 0.12);
  const baseY = height * 0.54;
  const amplitudePx = Math.min(height * 0.34, baseY - 24);
  const peak = peakAmplitude(series.values);

  const leftX = marginX;
  const rightX = width - marginX;
  const span = rightX - leftX;
  const axisMin = series.axis[0];
  const axisMax = series.axis[samples - 1];
  const axisSpan = axisMax - axisMin || 1;
  const screenX = (position: number): number => leftX + ((position - axisMin) / axisSpan) * span;
  const screenY = (value: number): number => baseY - (value / peak) * amplitudePx;

  // Rest baseline (zero displacement).
  ctx.strokeStyle = theme.textFaint;
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 6]);
  ctx.beginPath();
  ctx.moveTo(leftX, baseY);
  ctx.lineTo(rightX, baseY);
  ctx.stroke();
  ctx.setLineDash([]);

  const sample = frameSampler(series, time);

  // A subtle fill from the curve down to the baseline gives the wave body.
  ctx.beginPath();
  ctx.moveTo(leftX, baseY);
  for (let i = 0; i < samples; i += 1) {
    ctx.lineTo(screenX(series.axis[i]), screenY(sample(i)));
  }
  ctx.lineTo(rightX, baseY);
  ctx.closePath();
  const fill = ctx.createLinearGradient(0, baseY - amplitudePx, 0, baseY + amplitudePx);
  fill.addColorStop(0, "rgba(117, 185, 198, 0.20)");
  fill.addColorStop(0.5, "rgba(117, 185, 198, 0.04)");
  fill.addColorStop(1, "rgba(117, 185, 198, 0.20)");
  ctx.fillStyle = fill;
  ctx.fill();

  // The displacement curve itself.
  ctx.save();
  ctx.strokeStyle = theme.accentStrong;
  ctx.lineWidth = 2.4;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 12;
  ctx.beginPath();
  for (let i = 0; i < samples; i += 1) {
    const x = screenX(series.axis[i]);
    const y = screenY(sample(i));
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();
  ctx.restore();

  // The spatial axis label, qualitative — no decimals on the stage.
  ctx.fillStyle = theme.textMuted;
  ctx.font = '12px "IBM Plex Sans", system-ui, sans-serif';
  ctx.textAlign = "center";
  ctx.fillText(series.coordinate, (leftX + rightX) / 2, baseY + amplitudePx + 28);
}
