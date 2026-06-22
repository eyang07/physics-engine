/**
 * Framework-free certificate-lane drawing (FE-056).
 *
 * The pure Canvas 2D drawing for one certificate lane, lifted out of
 * `certificateLanes.ts` so the rendering is independent of the DOM/class that
 * owns the lane rows. `CertificateLanes` (vanilla) and the FE-057 React wrapper
 * both call `drawCertificateLane` with a lane's draw state; behaviour and pixels
 * are identical to the previous in-class `drawLane`.
 */
import { dossier } from "../../design/dossier";
import { clamp } from "../../util";

/** The tightest sampled record for one obligation (BE-036): its signed worst
 * margin to the boundary and the worst sampled candidate value, the same
 * measured evidence the ledger headlines. */
export type ObligationWorst = { margin: number; value: number | null };

/** The draw state one certificate lane needs — the canvas-only subset of the
 * lane the owning class holds. The full `Lane` (with its DOM row/readout) is a
 * structural superset, so it satisfies this without conversion. */
export type CertificateLaneRender = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  values: number[];
  baseline: number;
  amplitude: number;
  // The selected obligation's worst record, drawn as a closest-approach level on
  // this lane while that obligation is selected; null when nothing is selected
  // or this lane does not bear on it.
  selectedWorst: ObligationWorst | null;
};

function prepareCanvas(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D): {
  width: number;
  height: number;
} {
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const drawWidth = Math.max(1, Math.floor(width * pixelRatio));
  const drawHeight = Math.max(1, Math.floor(height * pixelRatio));
  if (canvas.width !== drawWidth || canvas.height !== drawHeight) {
    canvas.width = drawWidth;
    canvas.height = drawHeight;
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }
  ctx.clearRect(0, 0, width, height);
  return { width, height };
}

// The certificate value v(t) drawn against its obligation threshold (dashed
// baseline). The curve auto-scales to its own excursion so its sign and shape
// relative to the threshold read clearly; the playhead tracks the run.
export function drawCertificateLane(lane: CertificateLaneRender, phase: number): void {
  const { canvas, ctx, values, baseline, amplitude, selectedWorst } = lane;
  const { width, height } = prepareCanvas(canvas, ctx);

  const count = values.length;
  if (count === 0) {
    return;
  }
  const pad = 5;
  const amp = amplitude > 0 ? amplitude : 1;
  const mid = height / 2;
  const yOf = (value: number) =>
    clamp(mid - ((value - baseline) / amp) * (height / 2 - pad), pad, height - pad);
  const xOf = (index: number) => (count <= 1 ? 0 : (index / (count - 1)) * width);
  const step = Math.max(1, Math.floor(count / 320));

  // The obligation threshold (the `≤ 0` baseline), a dashed ink-graphite rule.
  ctx.save();
  ctx.setLineDash([3, 4]);
  ctx.strokeStyle = dossier.hairline;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, mid);
  ctx.lineTo(width, mid);
  ctx.stroke();
  ctx.restore();

  // The selected obligation's worst sampled candidate value (BE-036), as a
  // closest-approach level on this lane: the gap from the threshold baseline to
  // this level is the signed worst margin the readout names. Measured evidence
  // drawn against the rollout, never a proof.
  if (selectedWorst && selectedWorst.value !== null && Number.isFinite(selectedWorst.value)) {
    const wy = yOf(selectedWorst.value);
    ctx.save();
    ctx.setLineDash([2, 3]);
    ctx.strokeStyle = dossier.graphite;
    ctx.lineWidth = 1.25;
    ctx.beginPath();
    ctx.moveTo(0, wy);
    ctx.lineTo(width, wy);
    ctx.stroke();
    ctx.restore();
  }

  // The measured signal: a soft teal area under a teal trace — no glow.
  ctx.beginPath();
  ctx.moveTo(0, mid);
  for (let index = 0; index < count; index += step) {
    ctx.lineTo(xOf(index), yOf(values[index]));
  }
  ctx.lineTo(xOf(count - 1), mid);
  ctx.closePath();
  ctx.fillStyle = "rgba(21, 112, 107, 0.12)";
  ctx.fill();

  ctx.strokeStyle = dossier.measured;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (let index = 0; index < count; index += step) {
    const x = xOf(index);
    const y = yOf(values[index]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  const playIndex = clamp(Math.round(phase * (count - 1)), 0, count - 1);
  ctx.fillStyle = dossier.ink;
  ctx.beginPath();
  ctx.arc(clamp(phase, 0, 1) * width, yOf(values[playIndex]), 3, 0, Math.PI * 2);
  ctx.fill();
}
