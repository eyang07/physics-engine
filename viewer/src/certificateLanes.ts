/**
 * Candidate-certificate lanes for the Verification world.
 *
 * Given the controlled trajectory's certificate series (the barrier/Lyapunov
 * value B(x(t)) and its flow derivative), this draws each as a lane against its
 * obligation threshold — measured signal only, qualitative, no decimals. The
 * pass/fail verdict lives in the proof-status surface, not here. Crossings track
 * playback via the shared phase.
 */
import katex from "katex";

import type { CertificateSeries } from "./data/trajectory";
import { formatSignedMeasured } from "./util";
import {
  drawCertificateLane,
  prepareCertificateLanes,
  type CertificateLaneDescriptor,
  type ObligationWorst,
} from "./verification/render/certificateLanes";

// The pure lane drawing and preparation now live in the framework-free render
// module (FE-056/FE-057); re-export `ObligationWorst` so existing importers
// (e.g. the stage) keep their `./certificateLanes` import path.
export type { ObligationWorst };

type Lane = {
  row: HTMLElement;
  obligationIds: string[];
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  readout: HTMLElement;
  values: number[];
  baseline: number;
  amplitude: number;
  // The selected obligation's worst record, drawn as a closest-approach level on
  // this lane while that obligation is selected; null when nothing is selected
  // or this lane does not bear on it.
  selectedWorst: ObligationWorst | null;
};

function renderLatex(element: HTMLElement, latex: string): void {
  katex.render(latex, element, { throwOnError: false, displayMode: false });
}

export class CertificateLanes {
  private lanes: Lane[] = [];
  private selectedRow: HTMLElement | null = null;
  // The per-obligation worst record (BE-036), so a selected obligation's worst
  // sampled margin can be surfaced on the lanes that bear on it.
  private worstByObligation = new Map<string, ObligationWorst>();

  // Notified when a lane is selected (with the obligations it bears on) or
  // cleared (null), so the host can emphasize the matching obligations.
  onSelect: (obligationIds: string[] | null) => void = () => {};

  constructor(private readonly container: HTMLElement) {}

  get count(): number {
    return this.lanes.length;
  }

  clear(): void {
    this.container.replaceChildren();
    this.lanes = [];
    this.selectedRow = null;
    this.worstByObligation = new Map();
  }

  show(
    series: Record<string, number[]>,
    records: CertificateSeries[],
    worstByObligation: Map<string, ObligationWorst> = new Map(),
  ): void {
    this.clear();
    this.worstByObligation = worstByObligation;
    const { lanes, isIntersection } = prepareCertificateLanes(series, records);
    lanes.forEach((descriptor) => this.buildRow(descriptor));
    if (this.lanes.length === 0) {
      // Make the absence legible: a problem can simply carry no measured
      // certificate series. State that rather than leaving an empty panel.
      const empty = document.createElement("p");
      empty.className = "diagnostic-empty";
      empty.textContent = "No measured certificate series for this problem.";
      this.container.append(empty);
    } else if (isIntersection) {
      this.container.prepend(this.intersectionNote());
    }
  }

  // The intersection-safe-set semantics, stated once above the named barrier
  // lanes: a state is safe only where every candidate barrier holds, i.e. the
  // safe set is their intersection {max_i B_i <= 0}. Both barriers stay
  // candidates — this names and relates them, it certifies nothing.
  private intersectionNote(): HTMLElement {
    const note = document.createElement("div");
    note.className = "diagnostic-intersection";
    const lead = document.createElement("span");
    lead.className = "diagnostic-intersection__lead";
    lead.textContent = "Safe set is the intersection of these candidate barriers:";
    const math = document.createElement("span");
    math.className = "diagnostic-intersection__math";
    renderLatex(math, "\\{\\max_i B_i \\le 0\\}");
    const tail = document.createElement("span");
    tail.className = "diagnostic-intersection__tail";
    tail.textContent = "— safe only where every barrier holds. Both stay candidates, not certified.";
    note.append(lead, math, tail);
    return note;
  }

  update(phase: number): void {
    this.lanes.forEach((lane) => drawCertificateLane(lane, phase));
  }

  // Select a lane (by its row) to reveal the obligations it bears on, or clear
  // the selection. Re-selecting the active lane clears it.
  private toggleSelect(row: HTMLElement, obligationIds: string[]): void {
    const clearing = this.selectedRow === row;
    if (this.selectedRow) {
      this.selectedRow.classList.remove("diagnostic--selected");
      this.selectedRow.setAttribute("aria-pressed", "false");
    }
    if (clearing) {
      this.selectedRow = null;
      this.onSelect(null);
      return;
    }
    this.selectedRow = row;
    row.classList.add("diagnostic--selected");
    row.setAttribute("aria-pressed", "true");
    this.onSelect([...obligationIds]);
  }

  // Emphasize the lanes that bear on a selected obligation and dim the rest; a
  // null selection clears all emphasis. Lets the obligation surfaces show which
  // measured signal supports which obligation.
  setEmphasis(obligationId: string | null): void {
    this.lanes.forEach((lane) => {
      lane.row.classList.remove("diagnostic--emphasized", "diagnostic--dimmed");
      const bears = obligationId !== null && lane.obligationIds.includes(obligationId);
      if (obligationId !== null) {
        lane.row.classList.add(bears ? "diagnostic--emphasized" : "diagnostic--dimmed");
      }
      // The selected obligation's worst sampled margin (BE-036), surfaced on the
      // lane(s) that bear on it. The same measured value the ledger headlines —
      // never a proof.
      const worst = bears && obligationId !== null ? this.worstByObligation.get(obligationId) ?? null : null;
      this.setLaneReadout(lane, worst);
    });
  }

  // Show (or hide) a lane's worst-margin readout: the signed BE-036 margin as a
  // chip, with the worst sampled candidate value drawn as a closest-approach
  // level line on the lane (see drawLane). Measured evidence only.
  private setLaneReadout(lane: Lane, worst: ObligationWorst | null): void {
    lane.selectedWorst = worst;
    if (!worst) {
      lane.readout.hidden = true;
      lane.readout.textContent = "";
      return;
    }
    lane.readout.replaceChildren();
    const label = document.createElement("span");
    label.className = "diagnostic__margin-label";
    label.textContent = "worst margin";
    const value = document.createElement("span");
    value.className = "diagnostic__margin-value";
    value.textContent = formatSignedMeasured(worst.margin);
    lane.readout.append(label, value);
    lane.readout.title =
      "signed worst sampled margin to the obligation boundary (BE-036) — measured evidence, consistent with the ledger, not a proof";
    lane.readout.hidden = false;
  }

  private buildRow(descriptor: CertificateLaneDescriptor): void {
    const { obligationIds } = descriptor;
    const row = document.createElement("div");
    row.className = "diagnostic";
    row.dataset.obligations = obligationIds.join(" ");
    // A lane that bears on obligations is selectable: activating it reveals which
    // obligations the measured signal supports. Lanes with none stay inert.
    if (obligationIds.length > 0) {
      row.classList.add("diagnostic--selectable");
      row.setAttribute("role", "button");
      row.setAttribute("aria-pressed", "false");
      row.tabIndex = 0;
      row.addEventListener("click", () => this.toggleSelect(row, obligationIds));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this.toggleSelect(row, obligationIds);
        }
      });
    }

    const head = document.createElement("div");
    head.className = "diagnostic__head";
    const symbol = document.createElement("span");
    symbol.className = "diagnostic__symbol";
    renderLatex(symbol, descriptor.symbolLatex);
    const caption = document.createElement("span");
    caption.className = "diagnostic__caption";
    if (descriptor.captionLatex) {
      renderLatex(caption, descriptor.captionLatex);
    } else {
      caption.textContent = descriptor.captionFallback;
    }
    head.append(symbol, caption);
    // In an intersection package, name which barrier this lane is (box vs
    // keep-out), so a reader can tell the two candidate barriers apart. It stays
    // a candidate label — the lane certifies nothing.
    if (descriptor.barrierLabel) {
      const barrier = document.createElement("span");
      barrier.className = "diagnostic__barrier";
      barrier.textContent = descriptor.barrierLabel;
      head.append(barrier);
    }

    const lane = document.createElement("canvas");
    lane.className = "diagnostic__residual diagnostic__certificate";
    // The worst-margin readout for the selected obligation; hidden until this
    // lane bears on a selected obligation with an exported worst record.
    const readout = document.createElement("div");
    readout.className = "diagnostic__margin";
    readout.hidden = true;
    row.append(head, lane, readout);
    this.container.append(row);

    const laneCtx = lane.getContext("2d");
    if (laneCtx) {
      this.lanes.push({
        row,
        obligationIds,
        canvas: lane,
        ctx: laneCtx,
        readout,
        values: descriptor.values,
        baseline: descriptor.baseline,
        amplitude: descriptor.amplitude,
        selectedWorst: null,
      });
    }
  }
}
