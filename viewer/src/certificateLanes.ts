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

import { dossier } from "./design/dossier";
import type { CertificateSeries } from "./data/trajectory";
import { clamp, formatSignedMeasured } from "./util";

/** The tightest sampled record for one obligation (BE-036): its signed worst
 * margin to the boundary and the worst sampled candidate value, the same
 * measured evidence the ledger headlines. */
export type ObligationWorst = { margin: number; value: number | null };

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

const COMPARISON_LATEX: Record<string, string> = {
  "<=": "\\le",
  "<": "<",
  ">=": "\\ge",
  ">": ">",
  "==": "=",
  "=": "=",
};

function renderLatex(element: HTMLElement, latex: string): void {
  katex.render(latex, element, { throwOnError: false, displayMode: false });
}

// A structural constant (the obligation threshold), trimmed — not a measured
// magnitude.
function constantLatex(value: number): string {
  if (Object.is(value, -0) || Math.abs(value) < 1e-12) {
    return "0";
  }
  return Number(value.toFixed(3))
    .toString()
    .replace(/\.?0+$/, "");
}

// A Lyapunov candidate reads as V, a barrier (the default) as B. Derived from
// the exported candidate id — the lane labels the series, it does not classify.
function baseSymbol(record: CertificateSeries): string {
  return (record.candidateId ?? "").toLowerCase().includes("lyapunov") ? "V" : "B";
}

function symbolLatex(record: CertificateSeries): string {
  const base = baseSymbol(record);
  return record.kind === "flow-derivative" ? `\\dot{${base}}` : base;
}

// Show `symbol <comparison> rhs` when one comparison applies (e.g. the
// non-increase obligation `\dot B \le 0`). Region-conditional value obligations
// impose more than one, so there the threshold is ambiguous and we omit it.
function captionLatex(record: CertificateSeries): string | null {
  const comparisons = new Set(record.comparisonBaselines.map((baseline) => baseline.comparison));
  if (comparisons.size !== 1) {
    return null;
  }
  const baseline = record.comparisonBaselines[0];
  const comparison = COMPARISON_LATEX[baseline.comparison] ?? baseline.comparison;
  return `${symbolLatex(record)} ${comparison} ${constantLatex(baseline.rhs)}`;
}

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
    records.forEach((record) => this.buildRow(record, series));
    if (this.lanes.length === 0) {
      // Make the absence legible: a problem can simply carry no measured
      // certificate series. State that rather than leaving an empty panel.
      const empty = document.createElement("p");
      empty.className = "diagnostic-empty";
      empty.textContent = "No measured certificate series for this problem.";
      this.container.append(empty);
    }
  }

  update(phase: number): void {
    this.lanes.forEach((lane) => drawLane(lane, phase));
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

  private buildRow(record: CertificateSeries, series: Record<string, number[]>): void {
    const values = series[record.series];
    if (!values || values.length === 0) {
      return;
    }
    const baseline = record.comparisonBaselines[0]?.rhs ?? 0;
    let amplitude = 0;
    for (const value of values) {
      amplitude = Math.max(amplitude, Math.abs(value - baseline));
    }

    const row = document.createElement("div");
    row.className = "diagnostic";
    row.dataset.obligations = record.obligationIds.join(" ");
    // A lane that bears on obligations is selectable: activating it reveals which
    // obligations the measured signal supports. Lanes with none stay inert.
    if (record.obligationIds.length > 0) {
      row.classList.add("diagnostic--selectable");
      row.setAttribute("role", "button");
      row.setAttribute("aria-pressed", "false");
      row.tabIndex = 0;
      row.addEventListener("click", () => this.toggleSelect(row, record.obligationIds));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this.toggleSelect(row, record.obligationIds);
        }
      });
    }

    const head = document.createElement("div");
    head.className = "diagnostic__head";
    const symbol = document.createElement("span");
    symbol.className = "diagnostic__symbol";
    renderLatex(symbol, symbolLatex(record));
    const caption = document.createElement("span");
    caption.className = "diagnostic__caption";
    const latex = captionLatex(record);
    if (latex) {
      renderLatex(caption, latex);
    } else {
      caption.textContent = record.kind === "flow-derivative" ? "flow derivative" : "candidate value";
    }
    head.append(symbol, caption);

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
        obligationIds: record.obligationIds,
        canvas: lane,
        ctx: laneCtx,
        readout,
        values,
        baseline,
        amplitude,
        selectedWorst: null,
      });
    }
  }
}

// The certificate value v(t) drawn against its obligation threshold (dashed
// baseline). The curve auto-scales to its own excursion so its sign and shape
// relative to the threshold read clearly; the playhead tracks the run.
function drawLane(lane: Lane, phase: number): void {
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
