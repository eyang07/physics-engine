/**
 * The Verification world's animated stage.
 *
 * It plays the self-contained controlled trajectory the engine exported with a
 * verification problem and draws it on the exported phase-plane region geometry,
 * with the candidate-certificate lanes tracking playback. This is a separate
 * world from the Systems gallery: it renders only verification data and never
 * re-derives physics.
 */
import katex from "katex";

import { PlaybackClock, sampleTrajectory, trajectoryDuration } from "./playback";
import { CertificateLanes } from "./certificateLanes";
import { dossier, dossierRole } from "./design/dossier";
import type { ProofStatus, RegionGeometry, VerificationProblem } from "./data/verification";
import type { Trajectory } from "./data/trajectory";
import { clamp, formatMeasured, formatSignedMeasured } from "./util";

const COMPARISON_LATEX: Record<string, string> = {
  "<=": "\\le",
  ">=": "\\ge",
  "<": "<",
  ">": ">",
  "==": "=",
  "=": "=",
};

// The disturbance (wind) box a Tier-3 robust package is quantified over, read
// verbatim from the assumption that bounds the disturbance channel (its id names
// the disturbance/wind bound). Nominal packages carry no such assumption and get
// no annotation. The returned LaTeX is the bound itself (e.g. |w_1| \le 0.5), so
// the stage states what the robustness is *against* — assumed, never discharged.
function disturbanceBoundLatex(problem: VerificationProblem): string | null {
  for (const assumption of problem.assumptions) {
    if (!/disturbance|wind/i.test(assumption.id)) {
      continue;
    }
    if (!assumption.expression || assumption.rhs === null) {
      continue;
    }
    const cmp = COMPARISON_LATEX[assumption.comparison] ?? assumption.comparison;
    return `${assumption.expression.latex} ${cmp} ${formatMeasured(assumption.rhs)}`;
  }
  return null;
}

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

type Bounds = {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
};

type ViolationMarker = { x: number; y: number; label: string; worstValue: number | null };
// A measured-holds closest-approach annotation: the worst (tightest) sampled
// point and its signed margin to the obligation boundary. Measured slack, never
// a discharge.
type HoldsMarker = { x: number; y: number; label: string; margin: number | null };

const VIOLATION_RGBA = dossier.violated;
const HOLDS_RGBA = dossier.measured;

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
    markers.push({ x: placed.x, y: placed.y, label, worstValue: status.worstValue });
  }
  return markers;
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

// Region roles are drawn from the dossier semantic palette (see design/dossier).
const ROLE_DRAW_ORDER = ["domain", "safe", "initial", "unsafe"];

function roleStyle(role: string): { stroke: string; fill: string } {
  return dossierRole[role] ?? dossierRole.domain;
}

// The controlled rollout is drawn in ink; mirror it in the legend.
const TRAJECTORY_COLOR = dossier.ink;

// Frame the stage to the action: the trajectory plus the safe/initial sets it is
// meant to stay within. The far unsafe/domain grids are deliberately excluded
// from framing (they otherwise dominate and squash the motion into a corner);
// their boundaries still draw where they fall inside the clipped plot.
const FOCUS_ROLES = new Set(["safe", "initial"]);

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

function drawVerificationPhaseScene(
  ctx: CanvasRenderingContext2D,
  trajectory: Trajectory,
  regions: RegionGeometry[],
  bounds: Bounds,
  phase: number,
  width: number,
  height: number,
  markers: ViolationMarker[],
  holds: HoldsMarker[],
  focusedIndex: number | null,
): void {
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
  drawViolationMarkers(ctx, markers, mapX, mapY, focusedIndex);

  // Axis labels in the figure's own state names, set in mono.
  ctx.fillStyle = dossier.graphite;
  ctx.font = '12px "IBM Plex Mono", monospace';
  ctx.fillText(trajectory.state_names[0] ?? "x", plot.right - 18, plot.bottom + 24);
  ctx.fillText(trajectory.state_names[1] ?? "y", plot.left - 24, plot.top + 10);
}

export class VerificationStage {
  private readonly ctx: CanvasRenderingContext2D;
  private readonly clock = new PlaybackClock();
  private readonly certificateLanes: CertificateLanes;
  private readonly legend: HTMLElement;
  private readonly holdsLegend: HTMLElement;
  private readonly rolesLegend: HTMLElement;
  private readonly disturbanceLegend: HTMLElement;
  private trajectory: Trajectory | null = null;
  private bounds: Bounds | null = null;
  private regions: RegionGeometry[] = [];
  private violations: ViolationMarker[] = [];
  private holds: HoldsMarker[] = [];
  private focusedViolation: number | null = null;
  private active = false;
  private running = false;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly playButton: HTMLButtonElement,
    private readonly speedControl: HTMLInputElement,
    certificateContainer: HTMLElement,
  ) {
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Verification stage 2D context is unavailable.");
    }
    this.ctx = context;
    this.certificateLanes = new CertificateLanes(certificateContainer);
    // The violation legend overlays the stage workspace (the canvas's parent),
    // hidden until a measured violation is actually drawn.
    this.legend = document.createElement("div");
    this.legend.className = "verif-violation-legend";
    this.legend.hidden = true;
    canvas.parentElement?.append(this.legend);
    // The closest-approach legend names each holding obligation's tightest sample
    // and its signed margin; hidden until at least one holds marker is drawn.
    this.holdsLegend = document.createElement("div");
    this.holdsLegend.className = "verif-holds-legend";
    this.holdsLegend.hidden = true;
    canvas.parentElement?.append(this.holdsLegend);
    // A small key for the phase-plane colors (region roles + trajectory), shown
    // whenever a problem is on the stage.
    this.rolesLegend = document.createElement("div");
    this.rolesLegend.className = "verif-roles-legend";
    this.rolesLegend.hidden = true;
    canvas.parentElement?.append(this.rolesLegend);
    // The Tier-3 disturbance-set annotation: the wind box the robust claim is
    // quantified over, shown only for packages that carry a disturbance spec.
    this.disturbanceLegend = document.createElement("div");
    this.disturbanceLegend.className = "verif-disturbance-annotation";
    this.disturbanceLegend.hidden = true;
    canvas.parentElement?.append(this.disturbanceLegend);
    this.playButton.addEventListener("click", () => this.togglePlay());
  }

  /** Load a problem's controlled trajectory + region geometry onto the stage. */
  show(problem: VerificationProblem): void {
    const vt = problem.trajectory;
    this.certificateLanes.clear();
    this.clock.reset();
    if (!vt || vt.states.length === 0) {
      this.trajectory = null;
      this.bounds = null;
      this.regions = [];
      this.renderRolesLegend([]);
      this.renderDisturbanceAnnotation(null);
      this.setViolations([]);
      this.setHolds([]);
      this.syncPlayButton();
      return;
    }
    this.trajectory = {
      time: vt.time,
      state_names: vt.stateNames,
      states: vt.states,
      series: vt.series,
      metadata: {},
    };
    this.regions = problem.regionGeometry;
    this.bounds = boundsForFocus(this.trajectory, problem.regionGeometry);
    this.renderRolesLegend(problem.regionGeometry);
    this.renderDisturbanceAnnotation(disturbanceBoundLatex(problem));
    const obligationName = new Map(
      problem.obligations.map((obligation) => [obligation.id, obligation.name]),
    );
    const axisX = vt.stateNames[0] ?? "";
    const axisY = vt.stateNames[1] ?? "";
    this.setViolations(
      violationMarkers(problem.proofStatuses, axisX, axisY, obligationName),
    );
    this.setHolds(holdsMarkers(problem.proofStatuses, axisX, axisY, obligationName));
    this.certificateLanes.show(vt.series, vt.certificateSeries);
    this.syncPlayButton();
    this.resize();
  }

  // Keep a test-visible count of drawn violation markers on the canvas so visual
  // coverage can assert the marker / no-marker paths without pixel diffing, and
  // mirror the markers into the legend. Any prior focus is dropped: the marker
  // set has changed, so the previously named marker may no longer exist.
  private setViolations(markers: ViolationMarker[]): void {
    this.violations = markers;
    this.canvas.dataset.violationMarkers = String(markers.length);
    this.setFocusedViolation(null);
    this.renderLegend(markers);
  }

  // Mirror the closest-approach markers onto the canvas dataset (so visual
  // coverage can assert the marker / no-marker paths without pixel diffing) and
  // into the legend.
  private setHolds(markers: HoldsMarker[]): void {
    this.holds = markers;
    this.canvas.dataset.holdsMarkers = String(markers.length);
    this.renderHoldsLegend(markers);
  }

  // Focus (or clear focus on) a single drawn violation so the stage emphasizes
  // its marker and the legend marks the matching entry. The focused index rides
  // on the canvas dataset so visual coverage can assert focus/clear without
  // pixel diffing, and the legend is restyled to reflect the selection.
  private setFocusedViolation(index: number | null): void {
    this.focusedViolation = index;
    this.canvas.dataset.focusedViolation = index === null ? "" : String(index + 1);
    this.legend
      .querySelectorAll<HTMLButtonElement>(".verif-violation-legend__entry")
      .forEach((entry, entryIndex) => {
        const focused = entryIndex === index;
        entry.classList.toggle("verif-violation-legend__entry--focused", focused);
        entry.setAttribute("aria-pressed", String(focused));
      });
  }

  // The legend names each drawn violation by its obligation, keyed to the marker
  // index. It exists only while at least one marker is on the stage, and each
  // entry is a toggle that focuses its matching stage marker.
  private renderLegend(markers: ViolationMarker[]): void {
    this.legend.replaceChildren();
    if (markers.length === 0) {
      this.legend.hidden = true;
      return;
    }
    const title = document.createElement("p");
    title.className = "verif-violation-legend__title";
    title.textContent = "measured violations";
    this.legend.append(title);
    markers.forEach((marker, index) => {
      const entry = document.createElement("button");
      entry.type = "button";
      entry.className = "verif-violation-legend__entry";
      entry.setAttribute("aria-pressed", "false");
      const tag = document.createElement("span");
      tag.className = "verif-violation-legend__tag";
      tag.textContent = String(index + 1);
      const name = document.createElement("span");
      name.className = "verif-violation-legend__name";
      name.textContent = marker.label;
      entry.append(tag, name);
      // Show how far the sample broke the obligation, when the backend exported
      // a worst value. A missing value simply omits the chip — no broken chrome.
      if (marker.worstValue !== null) {
        const value = document.createElement("span");
        value.className = "verif-violation-legend__value";
        value.textContent = formatMeasured(marker.worstValue);
        value.title = "worst measured value";
        entry.append(value);
      }
      entry.addEventListener("click", () => {
        this.setFocusedViolation(this.focusedViolation === index ? null : index);
      });
      this.legend.append(entry);
    });
    this.legend.hidden = false;
  }

  // The closest-approach legend names each holding obligation by its tightest
  // sample and shows the signed measured margin (BE-036) — read-only, since a
  // holding sample is measured slack, not a breach to focus on. Hidden when no
  // holds marker is on the stage.
  private renderHoldsLegend(markers: HoldsMarker[]): void {
    this.holdsLegend.replaceChildren();
    if (markers.length === 0) {
      this.holdsLegend.hidden = true;
      return;
    }
    const title = document.createElement("p");
    title.className = "verif-holds-legend__title";
    title.textContent = "measured closest approach";
    this.holdsLegend.append(title);
    markers.forEach((marker, index) => {
      const entry = document.createElement("div");
      entry.className = "verif-holds-legend__entry";
      const tag = document.createElement("span");
      tag.className = "verif-holds-legend__tag";
      tag.textContent = String(index + 1);
      const name = document.createElement("span");
      name.className = "verif-holds-legend__name";
      name.textContent = marker.label;
      entry.append(tag, name);
      // Show the signed margin (the closest the evidence came to the boundary)
      // when the backend exported one. A missing margin simply omits the chip.
      if (marker.margin !== null) {
        const value = document.createElement("span");
        value.className = "verif-holds-legend__value";
        value.textContent = formatSignedMeasured(marker.margin);
        value.title = "worst measured margin (signed slack to the boundary)";
        entry.append(value);
      }
      this.holdsLegend.append(entry);
    });
    this.holdsLegend.hidden = false;
  }

  // A small key for the phase-plane colors: each region role present plus the
  // trajectory, so a reader can tell the safe corridor from the unsafe set.
  private renderRolesLegend(regions: RegionGeometry[]): void {
    this.rolesLegend.replaceChildren();
    const roles = ROLE_DRAW_ORDER.filter((role) => regions.some((region) => region.role === role));
    if (roles.length === 0) {
      this.rolesLegend.hidden = true;
      return;
    }
    const entry = (color: string, label: string): HTMLElement => {
      const row = document.createElement("div");
      row.className = "verif-roles-legend__entry";
      const swatch = document.createElement("span");
      swatch.className = "verif-roles-legend__swatch";
      swatch.style.background = color;
      const name = document.createElement("span");
      name.className = "verif-roles-legend__name";
      name.textContent = label;
      row.append(swatch, name);
      return row;
    };
    roles.forEach((role) => this.rolesLegend.append(entry(roleStyle(role).stroke, role)));
    this.rolesLegend.append(entry(TRAJECTORY_COLOR, "rollout"));
    this.rolesLegend.hidden = false;
  }

  // The Tier-3 disturbance-set annotation: the wind box `W` the robust claim is
  // quantified over, rendered verbatim from the disturbance assumption. Hidden
  // for nominal packages (no disturbance spec). Read-only and honest — it states
  // what the robustness is against, never that anything is discharged.
  private renderDisturbanceAnnotation(boundLatex: string | null): void {
    this.disturbanceLegend.replaceChildren();
    if (!boundLatex) {
      this.disturbanceLegend.hidden = true;
      return;
    }
    const title = document.createElement("p");
    title.className = "verif-disturbance-annotation__title";
    title.textContent = "disturbance set W";
    this.disturbanceLegend.append(title);
    const bound = document.createElement("div");
    bound.className = "verif-disturbance-annotation__bound";
    katex.render(boundLatex, bound, { throwOnError: false });
    this.disturbanceLegend.append(bound);
    const note = document.createElement("p");
    note.className = "verif-disturbance-annotation__note";
    note.textContent = "the wind box the robust claim is quantified over — assumed, not discharged";
    this.disturbanceLegend.append(note);
    this.disturbanceLegend.hidden = false;
  }

  /** Emphasize the certificate lanes bearing on an obligation (null clears). */
  emphasizeCertificates(obligationId: string | null): void {
    this.certificateLanes.setEmphasis(obligationId);
  }

  /** Notify when a certificate lane is selected, with the obligations it bears
   * on (null clears), so the host can emphasize them. */
  setOnCertificateSelect(handler: (obligationIds: string[] | null) => void): void {
    this.certificateLanes.onSelect = handler;
  }

  clear(): void {
    this.certificateLanes.clear();
    this.clock.reset();
    this.clock.pause();
    this.trajectory = null;
    this.bounds = null;
    this.regions = [];
    this.renderRolesLegend([]);
    this.renderDisturbanceAnnotation(null);
    this.setViolations([]);
    this.setHolds([]);
    this.syncPlayButton();
    this.resize();
  }

  /** Start or stop the stage's own animation loop (driven by domain switching). */
  setActive(active: boolean): void {
    this.active = active;
    if (!active) {
      this.clock.pause();
      this.syncPlayButton();
      return;
    }
    if (active) {
      this.resize();
      if (!this.running) {
        this.running = true;
        requestAnimationFrame(this.loop);
      }
    }
  }

  resize(): void {
    const pixelRatio = window.devicePixelRatio || 1;
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    this.canvas.width = Math.max(1, Math.floor(width * pixelRatio));
    this.canvas.height = Math.max(1, Math.floor(height * pixelRatio));
    this.ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }

  private togglePlay(): void {
    this.clock.toggle();
    this.syncPlayButton();
  }

  private syncPlayButton(): void {
    // Playback loops continuously, so the control is only ever Play/Pause.
    this.playButton.textContent = this.clock.playing ? "Pause" : "Play";
  }

  private readonly loop = (now: number): void => {
    if (!this.active) {
      this.running = false;
      return;
    }
    this.render(now);
    requestAnimationFrame(this.loop);
  };

  private render(now: number): void {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    if (!this.trajectory || !this.bounds) {
      drawDossierBackground(this.ctx, width, height);
      this.ctx.fillStyle = dossier.graphite;
      this.ctx.font = '15px "KaTeX_Main", Georgia, serif';
      this.ctx.fillText("No trajectory for this problem.", 32, 48);
      return;
    }

    const time = this.clock.advance(now, Number(this.speedControl.value));
    const duration = trajectoryDuration(this.trajectory);
    // Loop continuously: wrap the elapsed time so the run restarts at the end.
    const sample = sampleTrajectory(this.trajectory, duration > 0 ? time % duration : time);
    drawVerificationPhaseScene(
      this.ctx,
      this.trajectory,
      this.regions,
      this.bounds,
      sample.phase,
      width,
      height,
      this.violations,
      this.holds,
      this.focusedViolation,
    );
    this.certificateLanes.update(sample.phase);
  }
}
