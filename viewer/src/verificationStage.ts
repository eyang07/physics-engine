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
import type { VerificationProblem } from "./data/verification";
import { formatMeasured } from "./util";
import { dossier } from "./design/dossier";
import {
  prepareStateSpaceScene,
  renderStateSpace,
  renderStateSpaceEmpty,
  roleStyle,
  worstByObligation,
  ROLE_DRAW_ORDER,
  TRAJECTORY_COLOR,
  type StateSpaceScene,
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
  // One compact legend overlaying the figure (FE-064), replacing the four
  // free-floating overlays. It keys only the marks actually present in the
  // current problem and collapses on demand.
  private readonly legend: HTMLElement;
  private legendCollapsed = false;
  // The renderable phase-plane scene for the current problem (FE-056): derived
  // once in show(), drawn each frame in render(). Null when no trajectory.
  private scene: StateSpaceScene | null = null;
  // The obligation selected in the panel, whose margin marker the figure
  // emphasises and the rest dims (null = none). Linked from the obligation list
  // via focusObligation, so selection lives in the panel, not on the legend.
  private focusedObligationId: string | null = null;
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
    // One compact legend overlays the figure (the canvas's parent), hidden until
    // a problem with marks to key is on the stage. It replaces the four
    // free-floating overlays the stage used to stack on the plot.
    this.legend = document.createElement("div");
    this.legend.className = "verif-legend";
    this.legend.hidden = true;
    canvas.parentElement?.append(this.legend);
    this.playButton.addEventListener("click", () => this.togglePlay());
  }

  /** Load a problem's controlled trajectory + region geometry onto the stage. */
  show(problem: VerificationProblem): void {
    const vt = problem.trajectory;
    this.certificateLanes.clear();
    this.clock.reset();
    const scene = prepareStateSpaceScene(problem);
    this.scene = scene;
    // A new problem replaces the marker set, so any prior obligation selection no
    // longer refers to a drawn marker.
    this.focusObligation(null);
    if (!scene || !vt) {
      this.setMarkerCounts(0, 0);
      this.buildLegend(null, null);
      this.syncPlayButton();
      return;
    }
    this.setMarkerCounts(scene.violations.length, scene.holds.length);
    this.buildLegend(problem, scene);
    this.certificateLanes.show(
      vt.series,
      vt.certificateSeries,
      worstByObligation(problem.proofStatuses),
    );
    this.syncPlayButton();
    this.resize();
  }

  // Mirror the drawn marker counts onto the canvas dataset so visual coverage can
  // assert the marker / no-marker paths without pixel diffing. The legend no
  // longer enumerates markers — it only keys the kinds present — so the counts
  // live solely on the dataset.
  private setMarkerCounts(violations: number, holds: number): void {
    this.canvas.dataset.violationMarkers = String(violations);
    this.canvas.dataset.holdsMarkers = String(holds);
  }

  /**
   * Select (or clear) the obligation whose margin marker the figure emphasises.
   * Linked from the obligation list (FE-064): the figure dims every other marker
   * so the selected obligation's geometry stands out. The selected id rides on
   * the canvas dataset so visual coverage can assert selection without pixel
   * diffing; the per-frame render reads `focusedObligationId` directly.
   */
  focusObligation(obligationId: string | null): void {
    this.focusedObligationId = obligationId;
    this.canvas.dataset.focusedObligation = obligationId ?? "";
  }

  // Collapse/expand the single legend. Collapsed hides the body and keeps just
  // the toggle, so the figure can be read with no overlay at all.
  private toggleLegend(): void {
    this.legendCollapsed = !this.legendCollapsed;
    this.legend.dataset.collapsed = String(this.legendCollapsed);
    this.legend
      .querySelector(".verif-legend__toggle")
      ?.setAttribute("aria-expanded", String(!this.legendCollapsed));
  }

  // Build the one compact legend for the current scene: a collapsible key of
  // only the marks actually present — the region roles, the rollout, the
  // violation / closest-approach margin markers, and (for a robust package) the
  // disturbance box the claim is quantified over. Replaces the four stacked
  // overlays the stage used to draw.
  private buildLegend(problem: VerificationProblem | null, scene: StateSpaceScene | null): void {
    this.legend.replaceChildren();
    if (!scene) {
      this.legend.hidden = true;
      return;
    }
    const roles = ROLE_DRAW_ORDER.filter((role) =>
      scene.regions.some((region) => region.role === role),
    );
    const hasViolations = scene.violations.length > 0;
    const hasHolds = scene.holds.length > 0;
    const disturbance = problem ? disturbanceBoundLatex(problem) : null;
    if (roles.length === 0 && !hasViolations && !hasHolds && !disturbance) {
      this.legend.hidden = true;
      return;
    }

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "verif-legend__toggle";
    toggle.textContent = "Legend";
    toggle.setAttribute("aria-expanded", String(!this.legendCollapsed));
    toggle.addEventListener("click", () => this.toggleLegend());
    this.legend.append(toggle);

    const body = document.createElement("div");
    body.className = "verif-legend__body";

    // One keyed row: a swatch (its shape carries the mark's meaning) and a label.
    const row = (swatchClass: string, color: string, label: string): void => {
      const entry = document.createElement("div");
      entry.className = "verif-legend__entry";
      const swatch = document.createElement("span");
      swatch.className = `verif-legend__swatch ${swatchClass}`;
      // The marker glyphs are drawn as outlines, so they take the role color on
      // their border; the filled region/rollout swatches take it as background.
      if (swatchClass.includes("--ring") || swatchClass.includes("--diamond")) {
        swatch.style.borderColor = color;
      } else {
        swatch.style.background = color;
      }
      const name = document.createElement("span");
      name.className = "verif-legend__name";
      name.textContent = label;
      entry.append(swatch, name);
      body.append(entry);
    };

    roles.forEach((role) => row("verif-legend__swatch--box", roleStyle(role).stroke, role));
    row("verif-legend__swatch--line", TRAJECTORY_COLOR, "rollout");
    if (hasHolds) {
      row("verif-legend__swatch--diamond", dossier.measured, "closest approach");
    }
    if (hasViolations) {
      row("verif-legend__swatch--ring", dossier.violated, "measured violation");
    }

    // The Tier-3 disturbance box, folded into the same legend rather than a
    // separate overlay. Read-only and honest — what the robustness is quantified
    // over, never that anything is discharged.
    if (disturbance) {
      const note = document.createElement("div");
      note.className = "verif-legend__disturbance";
      const label = document.createElement("span");
      label.className = "verif-legend__disturbance-label";
      label.textContent = "disturbance set W";
      const bound = document.createElement("span");
      bound.className = "verif-legend__disturbance-bound";
      katex.render(disturbance, bound, { throwOnError: false });
      note.append(label, bound);
      body.append(note);
    }

    this.legend.append(body);
    this.legend.dataset.collapsed = String(this.legendCollapsed);
    this.legend.hidden = false;
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
    this.focusObligation(null);
    this.setMarkerCounts(0, 0);
    this.buildLegend(null, null);
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
      { focusedObligationId: this.focusedObligationId },
      sample.phase,
      width,
      height,
    );
    this.certificateLanes.update(sample.phase);
  }
}
