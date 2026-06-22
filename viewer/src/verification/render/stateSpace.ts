/**
 * Framework-free state-space drawing for the Verification stage (FE-056).
 *
 * The pure Canvas 2D drawing and the scene preparation it needs, lifted out of
 * `verificationStage.ts` so the figure can be drawn without the DOM/class that
 * owns the canvas and legends. The split is deliberate:
 *
 *   - `prepareStateSpaceScene(problem)` derives the renderable scene (trajectory,
 *     framing bounds, region geometry, and the violation/closest-approach markers)
 *     once per problem — the work the stage previously did in `show()`.
 *   - `renderStateSpace(ctx, scene, selection, phase, …)` draws that scene for a
 *     given playback phase and obligation selection, recomputing nothing.
 *
 * Together they realise the `(problem, selection, phase)` render contract while
 * keeping per-frame draws free of geometry recomputation, so behaviour and pixels
 * are identical to the previous in-class `drawVerificationPhaseScene`. The DOM
 * legends stay with the owning class (vanilla today, React in FE-057+).
 */
import { dossier, dossierRole } from "../../design/dossier";
import type { ProofStatus, RegionGeometry, VerificationProblem } from "../../data/verification";
import type { Trajectory } from "../../data/trajectory";
import { clamp } from "../../util";
import type { ObligationWorst } from "./certificateLanes";

export type Bounds = {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
};

export type ViolationMarker = {
  x: number;
  y: number;
  label: string;
  worstValue: number | null;
  // The signed worst margin (BE-036), negative for a violation: the depth the
  // measured run entered the unsafe set. Measured evidence, never a disproof.
  margin: number | null;
  // The rollout time the run reached this point (BE-056), when exported: the
  // moment the simulated run crossed into the unsafe set. Null otherwise.
  time: number | null;
};
// A measured-holds closest-approach annotation: the worst (tightest) sampled
// point and its signed margin to the obligation boundary. Measured slack, never
// a discharge.
export type HoldsMarker = { x: number; y: number; label: string; margin: number | null };

/** The renderable form of a verification problem's phase-plane figure. */
export type StateSpaceScene = {
  trajectory: Trajectory;
  regions: RegionGeometry[];
  bounds: Bounds;
  violations: ViolationMarker[];
  holds: HoldsMarker[];
};

/** What the stage selection contributes to the figure: the focused violation
 * marker, emphasised and with the rest dimmed (null = no focus). */
export type StateSpaceSelection = { focusedViolation: number | null };

const VIOLATION_RGBA = dossier.violated;
const HOLDS_RGBA = dossier.measured;

// Region roles are drawn from the dossier semantic palette (see design/dossier).
export const ROLE_DRAW_ORDER = ["domain", "safe", "initial", "unsafe"];

export function roleStyle(role: string): { stroke: string; fill: string } {
  return dossierRole[role] ?? dossierRole.domain;
}

// The controlled rollout is drawn in ink; mirror it in the legend.
export const TRAJECTORY_COLOR = dossier.ink;

// Frame the stage to the action: the trajectory plus the safe/initial sets it is
// meant to stay within. The far unsafe/domain grids are deliberately excluded
// from framing (they otherwise dominate and squash the motion into a corner);
// their boundaries still draw where they fall inside the clipped plot.
const FOCUS_ROLES = new Set(["safe", "initial"]);

// The light dossier figure ground: cool paper with a faint hairline grid, drawn
// in place of the dark chrome stage background so the figure reads as a typeset
// plate rather than an instrument screen.
function drawDossierBackground(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
): void {
  ctx.fillStyle = dossier.paper;
  ctx.fillRect(0, 0, width, height);
  ctx.strokeStyle = dossier.grid;
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

// A worst sampled point only belongs on the stage if it projects onto the two
// axes this stage actually plots (state[0] vs state[1]). Samples taken on a
// different projection, or with no exported point, return null rather than being
// drawn somewhere misleading.
function projectWorstPoint(
  status: ProofStatus,
  axisX: string,
  axisY: string,
): { x: number; y: number } | null {
  const point = status.worstPoint;
  const projection = status.projection;
  if (!point || !projection) {
    return null;
  }
  const byStateAxis = new Map<string, number>();
  projection.variables.forEach((variable, index) => {
    const axis = projection.variableToStateAxis[variable] ?? variable;
    const value = point[index];
    if (typeof value === "number" && Number.isFinite(value)) {
      byStateAxis.set(axis, value);
    }
  });
  const x = byStateAxis.get(axisX);
  const y = byStateAxis.get(axisY);
  if (x === undefined || y === undefined) {
    return null;
  }
  return { x, y };
}

// The worst sampled violation per obligation, mappable onto the plotted axes.
// The obligation name and worst measured value ride along so each marker can be
// named and quantified in the legend.
function violationMarkers(
  statuses: ProofStatus[],
  axisX: string,
  axisY: string,
  obligationName: Map<string, string>,
): ViolationMarker[] {
  if (!axisX || !axisY) {
    return [];
  }
  const markers: ViolationMarker[] = [];
  for (const status of statuses) {
    if (status.status !== "measured-violated") {
      continue;
    }
    const placed = projectWorstPoint(status, axisX, axisY);
    if (!placed) {
      continue;
    }
    const label = obligationName.get(status.obligationId) ?? status.obligationId;
    markers.push({
      x: placed.x,
      y: placed.y,
      label,
      worstValue: status.worstValue,
      margin: status.worstMargin,
      time: status.worstTime,
    });
  }
  return markers;
}

// The tightest sampled record per obligation (BE-036): the most negative signed
// margin across its sampled statuses and the worst sampled candidate value,
// matching the ledger's headline margin. Lets a selected obligation surface its
// worst margin on the certificate lanes that bear on it. Measured evidence only.
export function worstByObligation(statuses: ProofStatus[]): Map<string, ObligationWorst> {
  const worst = new Map<string, ObligationWorst>();
  for (const status of statuses) {
    if (status.worstMargin === null) {
      continue;
    }
    const prev = worst.get(status.obligationId);
    if (prev === undefined || status.worstMargin < prev.margin) {
      worst.set(status.obligationId, { margin: status.worstMargin, value: status.worstValue });
    }
  }
  return worst;
}

// The closest-approach point per holding obligation: its worst (tightest) sample
// and signed margin (BE-036). A measured-holds status whose worst point maps onto
// the plotted axes gets a marker so the ledger's nonnegative margin is also
// legible geometrically. A tight hold is still measured evidence, never a proof.
function holdsMarkers(
  statuses: ProofStatus[],
  axisX: string,
  axisY: string,
  obligationName: Map<string, string>,
): HoldsMarker[] {
  if (!axisX || !axisY) {
    return [];
  }
  const markers: HoldsMarker[] = [];
  for (const status of statuses) {
    if (status.status !== "measured-holds") {
      continue;
    }
    const placed = projectWorstPoint(status, axisX, axisY);
    if (!placed) {
      continue;
    }
    const label = obligationName.get(status.obligationId) ?? status.obligationId;
    markers.push({ x: placed.x, y: placed.y, label, margin: status.worstMargin });
  }
  return markers;
}

// A worst-violation sample, drawn as a haloed red ring with an inner cross so it
// reads as an annotation distinct from the region outlines, the trajectory, and
// the moving playhead. A small index tag ties each marker to its legend entry.
// When one marker is focused from the legend, it gains an emphasis halo and the
// others are dimmed so the named violation stands out on the phase plane.
function drawViolationMarkers(
  ctx: CanvasRenderingContext2D,
  markers: ViolationMarker[],
  mapX: (value: number) => number,
  mapY: (value: number) => number,
  focusedIndex: number | null,
): void {
  markers.forEach((marker, index) => {
    const cx = mapX(marker.x);
    const cy = mapY(marker.y);
    const focused = focusedIndex === index;
    const dimmed = focusedIndex !== null && !focused;
    ctx.save();
    ctx.globalAlpha = dimmed ? 0.35 : 1;
    if (focused) {
      ctx.lineWidth = 2;
      ctx.strokeStyle = VIOLATION_RGBA;
      ctx.shadowColor = VIOLATION_RGBA;
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.arc(cx, cy, 12, 0, Math.PI * 2);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
    ctx.lineWidth = 4;
    ctx.strokeStyle = "rgba(250, 251, 252, 0.9)";
    ctx.beginPath();
    ctx.arc(cx, cy, 7, 0, Math.PI * 2);
    ctx.stroke();
    ctx.lineWidth = 2;
    ctx.strokeStyle = VIOLATION_RGBA;
    ctx.beginPath();
    ctx.arc(cx, cy, 7, 0, Math.PI * 2);
    ctx.stroke();
    const r = 4;
    ctx.beginPath();
    ctx.moveTo(cx - r, cy - r);
    ctx.lineTo(cx + r, cy + r);
    ctx.moveTo(cx - r, cy + r);
    ctx.lineTo(cx + r, cy - r);
    ctx.stroke();
    ctx.fillStyle = VIOLATION_RGBA;
    ctx.font = 'bold 11px "IBM Plex Mono", monospace';
    ctx.fillText(String(index + 1), cx + 9, cy - 8);
    ctx.restore();
  });
}

// A closest-approach sample, drawn as a hollow measured-teal *diamond* with a
// paper halo — deliberately distinct from the red ringed cross of a violation,
// so a holding obligation's tightest sample reads as measured slack rather than
// a breach. A small index tag ties each marker to its legend entry.
function drawHoldsMarkers(
  ctx: CanvasRenderingContext2D,
  markers: HoldsMarker[],
  mapX: (value: number) => number,
  mapY: (value: number) => number,
): void {
  const diamond = (cx: number, cy: number, radius: number): void => {
    ctx.beginPath();
    ctx.moveTo(cx, cy - radius);
    ctx.lineTo(cx + radius, cy);
    ctx.lineTo(cx, cy + radius);
    ctx.lineTo(cx - radius, cy);
    ctx.closePath();
  };
  markers.forEach((marker, index) => {
    const cx = mapX(marker.x);
    const cy = mapY(marker.y);
    ctx.save();
    // Paper halo so the diamond stays legible over the set washes and rollout.
    ctx.lineWidth = 4;
    ctx.strokeStyle = "rgba(250, 251, 252, 0.9)";
    diamond(cx, cy, 7);
    ctx.stroke();
    ctx.lineWidth = 2;
    ctx.strokeStyle = HOLDS_RGBA;
    diamond(cx, cy, 7);
    ctx.stroke();
    ctx.fillStyle = HOLDS_RGBA;
    ctx.font = 'bold 11px "IBM Plex Mono", monospace';
    ctx.fillText(String(index + 1), cx + 9, cy - 8);
    ctx.restore();
  });
}

function boundsForFocus(trajectory: Trajectory, regions: RegionGeometry[]): Bounds {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const state of trajectory.states) {
    minX = Math.min(minX, state[0] ?? 0);
    maxX = Math.max(maxX, state[0] ?? 0);
    minY = Math.min(minY, state[1] ?? 0);
    maxY = Math.max(maxY, state[1] ?? 0);
  }
  for (const region of regions) {
    if (!FOCUS_ROLES.has(region.role)) {
      continue;
    }
    for (const x of region.grid.x) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
    }
    for (const y of region.grid.y) {
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
  }
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) {
    return { minX: -1, maxX: 1, minY: -1, maxY: 1 };
  }
  const xPad = Math.max(0.1, (maxX - minX) * 0.1);
  const yPad = Math.max(0.1, (maxY - minY) * 0.1);
  return { minX: minX - xPad, maxX: maxX + xPad, minY: minY - yPad, maxY: maxY + yPad };
}

function drawRegionGeometry(
  ctx: CanvasRenderingContext2D,
  regions: RegionGeometry[],
  mapX: (value: number) => number,
  mapY: (value: number) => number,
  clip: { left: number; right: number; top: number; bottom: number },
): void {
  ctx.save();
  ctx.beginPath();
  ctx.rect(clip.left, clip.top, clip.right - clip.left, clip.bottom - clip.top);
  ctx.clip();

  const byRole = (role: string) => regions.filter((region) => region.role === role);
  const ordered = [
    ...ROLE_DRAW_ORDER.flatMap(byRole),
    ...regions.filter((region) => !ROLE_DRAW_ORDER.includes(region.role)),
  ];

  // Each region is a filled set under a firmer outline, so the safe/initial
  // corridors read as areas (a journal figure), not bare contours. Color is the
  // role's semantic dossier hue; the legend names what each means.
  ctx.lineJoin = "round";
  ordered.forEach((region) => {
    const style = roleStyle(region.role);
    region.boundaryPolylines.forEach((polyline) => {
      ctx.beginPath();
      polyline.forEach(([x, y], index) => {
        const sx = mapX(x);
        const sy = mapY(y);
        if (index === 0) {
          ctx.moveTo(sx, sy);
        } else {
          ctx.lineTo(sx, sy);
        }
      });
      ctx.closePath();
      ctx.fillStyle = style.fill;
      ctx.fill();
      ctx.strokeStyle = style.stroke;
      ctx.lineWidth = 1.4;
      ctx.stroke();
    });
  });
  ctx.restore();
}

/**
 * Derive the renderable scene for a problem's phase-plane figure, or null when
 * the problem carries no controlled trajectory. This is the geometry work the
 * stage previously did in `show()`; doing it once keeps per-frame draws cheap.
 */
export function prepareStateSpaceScene(problem: VerificationProblem): StateSpaceScene | null {
  const vt = problem.trajectory;
  if (!vt || vt.states.length === 0) {
    return null;
  }
  const trajectory: Trajectory = {
    time: vt.time,
    state_names: vt.stateNames,
    states: vt.states,
    series: vt.series,
    metadata: {},
  };
  const regions = problem.regionGeometry;
  const bounds = boundsForFocus(trajectory, regions);
  const obligationName = new Map(
    problem.obligations.map((obligation) => [obligation.id, obligation.name]),
  );
  const axisX = vt.stateNames[0] ?? "";
  const axisY = vt.stateNames[1] ?? "";
  return {
    trajectory,
    regions,
    bounds,
    violations: violationMarkers(problem.proofStatuses, axisX, axisY, obligationName),
    holds: holdsMarkers(problem.proofStatuses, axisX, axisY, obligationName),
  };
}

/** Draw the empty-state plate when a problem carries no trajectory. */
export function renderStateSpaceEmpty(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
): void {
  drawDossierBackground(ctx, width, height);
  ctx.fillStyle = dossier.graphite;
  ctx.font = '15px "KaTeX_Main", Georgia, serif';
  ctx.fillText("No trajectory for this problem.", 32, 48);
}

/** Draw the prepared scene for a playback phase and obligation selection. */
export function renderStateSpace(
  ctx: CanvasRenderingContext2D,
  scene: StateSpaceScene,
  selection: StateSpaceSelection,
  phase: number,
  width: number,
  height: number,
): void {
  const { trajectory, regions, bounds, violations, holds } = scene;
  drawDossierBackground(ctx, width, height);
  const plot = {
    left: Math.max(38, width * 0.09),
    right: width - Math.max(26, width * 0.06),
    top: Math.max(28, height * 0.09),
    bottom: height - Math.max(42, height * 0.12),
  };
  const spanX = Math.max(1e-9, bounds.maxX - bounds.minX);
  const spanY = Math.max(1e-9, bounds.maxY - bounds.minY);
  const mapX = (value: number) => plot.left + ((value - bounds.minX) / spanX) * (plot.right - plot.left);
  const mapY = (value: number) => plot.bottom - ((value - bounds.minY) / spanY) * (plot.bottom - plot.top);

  ctx.save();
  ctx.strokeStyle = dossier.ink;
  ctx.lineWidth = 1;
  ctx.strokeRect(plot.left, plot.top, plot.right - plot.left, plot.bottom - plot.top);
  ctx.restore();

  drawRegionGeometry(ctx, regions, mapX, mapY, plot);

  const count = trajectory.states.length;
  const activeIndex = clamp(Math.round(phase * (count - 1)), 0, count - 1);
  const step = Math.max(1, Math.floor(count / 420));

  // The controlled rollout — a clean ink line on paper, no glow.
  ctx.save();
  ctx.beginPath();
  for (let index = 0; index < count; index += step) {
    const state = trajectory.states[index];
    const x = mapX(state[0] ?? 0);
    const y = mapY(state[1] ?? 0);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.strokeStyle = dossier.ink;
  ctx.lineWidth = 1.75;
  ctx.stroke();
  ctx.restore();

  // The playhead — a filled measured-teal dot ringed in paper so it stays
  // legible over the rollout and the set washes.
  const active = trajectory.states[activeIndex] ?? trajectory.states[0];
  const hx = mapX(active[0] ?? 0);
  const hy = mapY(active[1] ?? 0);
  ctx.beginPath();
  ctx.arc(hx, hy, 5, 0, Math.PI * 2);
  ctx.fillStyle = dossier.measured;
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = dossier.paper;
  ctx.stroke();

  // Holding closest-approach markers under the violation markers, so a breach
  // (if any) always reads on top of measured slack.
  drawHoldsMarkers(ctx, holds, mapX, mapY);
  drawViolationMarkers(ctx, violations, mapX, mapY, selection.focusedViolation);

  // Axis labels in the figure's own state names, set in mono.
  ctx.fillStyle = dossier.graphite;
  ctx.font = '12px "IBM Plex Mono", monospace';
  ctx.fillText(trajectory.state_names[0] ?? "x", plot.right - 18, plot.bottom + 24);
  ctx.fillText(trajectory.state_names[1] ?? "y", plot.left - 24, plot.top + 10);
}
