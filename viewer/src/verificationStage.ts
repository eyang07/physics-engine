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
import type { RegionGeometry, VerificationProblem } from "./data/verification";
import { formatMeasured, formatSignedMeasured } from "./util";
import {
  prepareStateSpaceScene,
  renderStateSpace,
  renderStateSpaceEmpty,
  roleStyle,
  worstByObligation,
  ROLE_DRAW_ORDER,
  TRAJECTORY_COLOR,
  type HoldsMarker,
  type StateSpaceScene,
  type ViolationMarker,
} from "./verification/render/stateSpace";

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

export class VerificationStage {
  private readonly ctx: CanvasRenderingContext2D;
  private readonly clock = new PlaybackClock();
  private readonly certificateLanes: CertificateLanes;
  private readonly legend: HTMLElement;
  private readonly holdsLegend: HTMLElement;
  private readonly rolesLegend: HTMLElement;
  private readonly disturbanceLegend: HTMLElement;
  // The renderable phase-plane scene for the current problem (FE-056): derived
  // once in show(), drawn each frame in render(). Null when no trajectory.
  private scene: StateSpaceScene | null = null;
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
    const scene = prepareStateSpaceScene(problem);
    this.scene = scene;
    if (!scene || !vt) {
      this.renderRolesLegend([]);
      this.renderDisturbanceAnnotation(null);
      this.setViolations([]);
      this.setHolds([]);
      this.syncPlayButton();
      return;
    }
    this.renderRolesLegend(problem.regionGeometry);
    this.renderDisturbanceAnnotation(disturbanceBoundLatex(problem));
    this.setViolations(scene.violations);
    this.setHolds(scene.holds);
    this.certificateLanes.show(
      vt.series,
      vt.certificateSeries,
      worstByObligation(problem.proofStatuses),
    );
    this.syncPlayButton();
    this.resize();
  }

  // Keep a test-visible count of drawn violation markers on the canvas so visual
  // coverage can assert the marker / no-marker paths without pixel diffing, and
  // mirror the markers into the legend. Any prior focus is dropped: the marker
  // set has changed, so the previously named marker may no longer exist.
  private setViolations(markers: ViolationMarker[]): void {
    this.canvas.dataset.violationMarkers = String(markers.length);
    this.setFocusedViolation(null);
    this.renderLegend(markers);
  }

  // Mirror the closest-approach markers onto the canvas dataset (so visual
  // coverage can assert the marker / no-marker paths without pixel diffing) and
  // into the legend.
  private setHolds(markers: HoldsMarker[]): void {
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
      // The signed negative margin (BE-036): how far the run crossed the
      // obligation boundary into the unsafe set. This is the headline of the
      // violation — measured evidence, never a disproof of safety.
      if (marker.margin !== null) {
        const margin = document.createElement("span");
        margin.className = "verif-violation-legend__margin";
        margin.textContent = formatSignedMeasured(marker.margin);
        margin.title = "signed worst margin (negative = entered the unsafe set) — measured, not a proof";
        entry.append(margin);
      } else if (marker.worstValue !== null) {
        // Fall back to the worst value when no signed margin was exported.
        const value = document.createElement("span");
        value.className = "verif-violation-legend__value";
        value.textContent = formatMeasured(marker.worstValue);
        value.title = "worst measured value";
        entry.append(value);
      }
      // When in the rollout the run crossed into the unsafe set (BE-056). A
      // read-only time annotation from the exported worst.time; omitted for a
      // worst record that carries no time (e.g. a region-grid sample).
      if (marker.time !== null && Number.isFinite(marker.time)) {
        const time = document.createElement("span");
        time.className = "verif-violation-legend__time";
        time.textContent = `entered at t = ${formatMeasured(marker.time)}`;
        time.title = "the rollout time the simulated run crossed into the unsafe set — measured, not a proof";
        entry.append(time);
      }
      entry.addEventListener("click", () => {
        this.setFocusedViolation(this.focusedViolation === index ? null : index);
      });
      this.legend.append(entry);
    });
    // The honest framing: a measured run reached the unsafe set on these
    // samples. That is evidence the controller can be driven out — never a
    // disproof of safety, and it leaves every obligation external-required.
    const note = document.createElement("p");
    note.className = "verif-violation-legend__note";
    note.textContent =
      "This simulated run entered the unsafe set — measured evidence, not a disproof of safety.";
    this.legend.append(note);
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
    this.scene = null;
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
    if (!this.scene) {
      renderStateSpaceEmpty(this.ctx, width, height);
      return;
    }

    const time = this.clock.advance(now, Number(this.speedControl.value));
    const duration = trajectoryDuration(this.scene.trajectory);
    // Loop continuously: wrap the elapsed time so the run restarts at the end.
    const sample = sampleTrajectory(this.scene.trajectory, duration > 0 ? time % duration : time);
    renderStateSpace(
      this.ctx,
      this.scene,
      { focusedViolation: this.focusedViolation },
      sample.phase,
      width,
      height,
    );
    this.certificateLanes.update(sample.phase);
  }
}
