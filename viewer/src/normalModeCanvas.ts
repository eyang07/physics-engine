import { theme } from "./design/theme";
import { drawStageBackground } from "./pendulumCanvas";
import type { ManifestNormalModes } from "./data/manifest";
import { bodyColor } from "./design/colormaps";

/**
 * FE-043 — the normal-mode lens for the fixed-end oscillator chain.
 *
 * Python solved the small-oscillation eigenproblem and exported the mode shapes
 * and frequencies (BE-083, `manifest.normalModes`). This lens animates an
 * exported shape — or a scrubbed superposition of two adjacent modes — as the
 * transverse displacement of the mass chain: each mass `k` is offset by
 * `q_k(t) = sum_i a_i phi_i[k] cos(omega_i t)`. The eigenvectors and frequencies
 * are the physics Python computed; the harmonic time dependence is the
 * *definition* of a normal mode, so the viewer is displaying the exported
 * structure, not re-deriving it. Frequencies are conveyed by the animation and
 * a qualitative low→high ordering — never as raw decimals on the stage.
 */
export interface NormalModeView {
  /** The selected mode index (0-based, ascending frequency). */
  readonly modeIndex: number;
  /** Superposition blend in [0, 1] toward the next mode. 0 = pure selected. */
  readonly blend: number;
  /** Elapsed playback time in seconds (looped by the caller). */
  readonly time: number;
}

// A visual rate so the lowest mode oscillates at a lively, legible pace; it
// scales the exported angular frequencies uniformly, preserving their ratios.
const VISUAL_RATE = 1.6;

function modeDisplacements(modes: ManifestNormalModes, view: NormalModeView): number[] {
  const count = modes.coordinates.length;
  const modeI = ((view.modeIndex % count) + count) % count;
  const modeJ = (modeI + 1) % count;
  const blend = Math.min(Math.max(view.blend, 0), 1);
  const weightI = 1 - blend;
  const weightJ = blend;
  const phaseI = Math.cos(modes.frequencies[modeI] * view.time * VISUAL_RATE);
  const phaseJ = Math.cos(modes.frequencies[modeJ] * view.time * VISUAL_RATE);
  const shapeI = modes.modeShapes[modeI];
  const shapeJ = modes.modeShapes[modeJ];
  const out: number[] = [];
  for (let k = 0; k < count; k += 1) {
    out.push(weightI * shapeI[k] * phaseI + weightJ * shapeJ[k] * phaseJ);
  }
  return out;
}

export function drawNormalModeScene(
  ctx: CanvasRenderingContext2D,
  modes: ManifestNormalModes,
  view: NormalModeView,
  width: number,
  height: number,
): void {
  drawStageBackground(ctx, width, height);

  const count = modes.coordinates.length;
  if (count === 0) {
    return;
  }

  const marginX = Math.min(120, width * 0.16);
  const baseY = height * 0.54;
  // Largest |component| across all modes, so the amplitude scale is stable as the
  // selection changes and the chain never clips at the stage edges.
  const maxComponent = Math.max(
    1e-6,
    ...modes.modeShapes.flat().map((value) => Math.abs(value)),
  );
  const amplitude = Math.min(height * 0.28, baseY - 24);
  const displacements = modeDisplacements(modes, view);

  // Fixed ends: the chain is anchored to a wall at each side.
  const leftWall = marginX;
  const rightWall = width - marginX;
  const span = rightWall - leftWall;
  const restX = (index: number): number => leftWall + (span * (index + 1)) / (count + 1);
  const massY = (index: number): number =>
    baseY - (displacements[index] / maxComponent) * amplitude;

  // Rest baseline.
  ctx.strokeStyle = theme.textFaint;
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 6]);
  ctx.beginPath();
  ctx.moveTo(leftWall, baseY);
  ctx.lineTo(rightWall, baseY);
  ctx.stroke();
  ctx.setLineDash([]);

  // The walls.
  ctx.fillStyle = theme.textMuted;
  for (const wallX of [leftWall, rightWall]) {
    ctx.fillRect(wallX - 3, baseY - 26, 6, 52);
  }

  // The displaced chain: wall → masses → wall.
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(leftWall, baseY);
  for (let k = 0; k < count; k += 1) {
    ctx.lineTo(restX(k), massY(k));
  }
  ctx.lineTo(rightWall, baseY);
  ctx.stroke();

  // The masses, each in its body-palette color so a superposition reads clearly.
  for (let k = 0; k < count; k += 1) {
    const x = restX(k);
    const y = massY(k);
    // A faint guide from the rest position to the live mass.
    ctx.strokeStyle = theme.hairline;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, baseY);
    ctx.lineTo(x, y);
    ctx.stroke();

    ctx.beginPath();
    ctx.fillStyle = bodyColor(k);
    ctx.arc(x, y, 9, 0, Math.PI * 2);
    ctx.fill();
  }

  // Qualitative caption: which mode(s), and the low→high frequency ordering.
  const modeI = ((view.modeIndex % count) + count) % count;
  const modeJ = (modeI + 1) % count;
  const blended = view.blend > 0.001;
  ctx.fillStyle = theme.textPrimary;
  ctx.font = '600 14px "IBM Plex Sans", system-ui, sans-serif';
  ctx.textAlign = "left";
  ctx.fillText(
    blended ? `Mode ${modeI + 1} + Mode ${modeJ + 1}` : `Mode ${modeI + 1}`,
    leftWall,
    height * 0.16,
  );
  ctx.fillStyle = theme.textMuted;
  ctx.font = '12px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText(
    blended ? "superposition — beats between two modes" : "lower modes oscillate slower",
    leftWall,
    height * 0.16 + 20,
  );
}
