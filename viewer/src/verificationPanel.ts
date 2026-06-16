/**
 * The Verification inspector: a read-only rendering of the verification-problem
 * IR the backend exports. It shows the model the obligations were derived along,
 * the safe/unsafe/initial/domain regions, the candidate certificates, and the
 * proof obligations an external sound method must discharge — each labeled
 * honestly by rigor. It renders only what the IR exports and records no proof
 * results: candidates stay "candidate", obligations stay "external-required".
 */
import katex from "katex";

import type {
  IrObligation,
  IrRegion,
  ProofStatus,
  RegionRole,
  VerificationProblem,
} from "./data/verification";
import { formatMeasured, formatSignedMeasured } from "./util";

const COMPARISON_LATEX: Record<string, string> = {
  "<=": "\\le",
  ">=": "\\ge",
  "<": "<",
  ">": ">",
  "==": "=",
  "=": "=",
};

const ROLE_LABEL: Record<string, string> = {
  safe: "safe",
  unsafe: "unsafe",
  initial: "initial",
  domain: "domain",
};

// The four-level rigor ladder (VISION §7), in order. The engine operates at
// level 1 (measured evidence); levels 2-4 are reached only by routing exported
// artifacts to external backends, never by the engine itself. The copy must
// never imply this engine proves or certifies anything.
const RIGOR_LADDER: ReadonlyArray<{ level: number; title: string; note: string }> = [
  {
    level: 1,
    title: "Measured / simulation-supported",
    note: "Behavior observed in numerical runs — exploratory evidence only, not a proof.",
  },
  {
    level: 2,
    title: "Certified numerical bounds",
    note: "Rigorous enclosures from validated numerics, under stated assumptions.",
  },
  {
    level: 3,
    title: "Reachability / SOS / barrier / Lyapunov-certified",
    note: "A certificate accepted by a sound method, under stated assumptions.",
  },
  {
    level: 4,
    title: "Deductively proved",
    note: "A theorem established in a prover or proof calculus.",
  },
];

// The rigor ladder, rendered honestly. The engine never emits "proved" or
// "certified"; these are the only labels it can produce, and we surface them
// verbatim with a plain-language gloss.
const RIGOR_GLOSS: Record<string, string> = {
  "external-required": "awaiting external discharge",
  measured: "sampled evidence — not a certificate",
  symbolic: "symbolic identity",
  candidate: "candidate — not certified",
};

// Measured proof-status outcomes, surfaced honestly: a clean sample is
// evidence, never a discharge. The obligation always still awaits external
// proof regardless of what the samples showed.
const PROOF_STATUS_LABEL: Record<string, string> = {
  "measured-holds": "holds on samples",
  "measured-violated": "violated on samples",
  "external-required": "not sampled",
};

const PROOF_STATUS_GLOSS: Record<string, string> = {
  "measured-holds": "sampled values satisfied the obligation — measured evidence, not a proof",
  "measured-violated": "at least one sample violated the obligation",
  "external-required": "no measured samples; awaiting external discharge",
};

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function mathSpan(latex: string, displayMode = false): HTMLElement {
  const span = el("span", "verif-math");
  katex.render(latex, span, { throwOnError: false, displayMode });
  return span;
}

function formatNumber(value: number): string {
  return String(value);
}

// A stable DOM id for an obligation card so other surfaces (candidate links,
// and later the status ledger) can scroll to it. Obligation ids are already
// hyphen/alphanumeric, but sanitize defensively.
function obligationCardId(obligationId: string): string {
  return `verif-obligation-${obligationId.replace(/[^a-z0-9-]/gi, "-")}`;
}

// A stable DOM id for an assumption card so an obligation's assumption links can
// scroll to it.
function assumptionCardId(assumptionId: string): string {
  return `verif-assumption-${assumptionId.replace(/[^a-z0-9-]/gi, "-")}`;
}

function section(title: string, id?: string): HTMLElement {
  const node = el("section", "verif-section");
  if (id) {
    node.id = id;
  }
  node.append(el("h2", "verif-section__title", title));
  return node;
}

function rigorBadge(rigor: string): HTMLElement {
  const badge = el("span", `verif-badge verif-badge--${rigor.replace(/[^a-z-]/gi, "-")}`, rigor);
  badge.title = RIGOR_GLOSS[rigor] ?? rigor;
  return badge;
}

function comparisonLatex(comparison: string): string {
  return COMPARISON_LATEX[comparison] ?? comparison;
}

export class VerificationPanel {
  // Card registries (id -> rendered card), rebuilt per problem so cross-references
  // can scroll to and emphasize their target: obligation cards (candidate and
  // measured-status links) and assumption cards (obligation assumption links).
  private readonly obligationCards = new Map<string, HTMLElement>();
  private readonly assumptionCards = new Map<string, HTMLElement>();

  // The obligation whose measured evidence (certificate lanes) is currently
  // emphasized, and a hook the host wires to the certificate lanes. Selection is
  // per-problem and resets on every render.
  private selectedEvidenceObligation: string | null = null;
  onEvidenceSelect: (obligationId: string | null) => void = () => {};

  constructor(
    private readonly summaryEl: HTMLElement,
    private readonly detailsEl: HTMLElement,
  ) {}

  clear(): void {
    this.obligationCards.clear();
    this.assumptionCards.clear();
    this.summaryEl.replaceChildren();
    this.detailsEl.replaceChildren();
  }

  renderEmpty(message: string): void {
    this.obligationCards.clear();
    this.assumptionCards.clear();
    this.detailsEl.replaceChildren();
    const empty = el("div", "verif-empty");
    empty.append(el("p", "verif-empty__title", "No verification problems"));
    empty.append(el("p", "verif-empty__copy", message));
    this.summaryEl.replaceChildren(empty);
  }

  // Verdict-first: a concise summary (what's being proved + measured outcome +
  // rigor) is always visible; the full IR math lives in a collapsed details band.
  render(problem: VerificationProblem, irPath: string | null = null): void {
    this.obligationCards.clear();
    this.assumptionCards.clear();
    this.selectedEvidenceObligation = null;

    // Summary rail.
    const summary = el("div", "verif-summary");
    summary.append(this.renderSummaryHeader(problem, irPath));
    if (problem.obligations.length > 0) {
      summary.append(this.renderObligationLedger(problem));
    }
    this.summaryEl.replaceChildren(summary);

    // Collapsible IR detail.
    const details = el("details", "verif-details");
    details.append(el("summary", "verif-details__summary", "Problem details (IR)"));
    const body = el("div", "verif-details__body");
    if (problem.dynamics) {
      body.append(this.renderDynamics(problem));
    }
    if (problem.regions.length > 0) {
      body.append(this.renderRegions(problem.regions));
    }
    if (problem.candidates.length > 0) {
      body.append(this.renderCandidates(problem));
    }
    if (problem.obligations.length > 0) {
      body.append(this.renderObligations(problem));
      body.append(this.renderProofStatuses(problem));
    }
    if (problem.assumptions.length > 0) {
      body.append(this.renderAssumptions(problem));
    }
    body.append(this.renderRigorLadder(problem));
    details.append(body);
    this.detailsEl.replaceChildren(details);
  }

  private renderSummaryHeader(
    problem: VerificationProblem,
    irPath: string | null,
  ): HTMLElement {
    const header = el("header", "verif-summary__header");
    header.append(el("p", "eyebrow", "Verification problem"));
    header.append(el("h1", "verif-summary__title", problem.name));
    header.append(this.renderRigorChip(problem));

    // The honesty banner: nothing here is proved; external discharge is required.
    const note =
      typeof problem.metadata.note === "string"
        ? problem.metadata.note
        : "Measured evidence only — every obligation awaits external sound discharge; nothing here is certified.";
    header.append(el("p", "verif-note", note));

    // The backend-agnostic IR artifact, offered for routing to an external
    // backend. Absent when the export published no IR (older data); the link
    // downloads the IR JSON, not the viewer-shaped payload.
    if (irPath) {
      const download = el("a", "verif-download-ir", "Download problem (IR)");
      download.href = irPath;
      download.download = `${problem.id}.verification-problem.json`;
      header.append(download);
    }
    return header;
  }

  // A compact, always-visible rigor indicator; the full four-level ladder lives
  // in the details. Keeps "measured" from being mistaken for "proved".
  private renderRigorChip(problem: VerificationProblem): HTMLElement {
    const level = this.currentRigorLevel(problem);
    const step = RIGOR_LADDER.find((entry) => entry.level === level) ?? RIGOR_LADDER[0];
    const chip = el(
      "span",
      "verif-rigor-chip",
      `Rigor: level ${step.level} — ${step.title.toLowerCase()}`,
    );
    chip.title = step.note;
    chip.dataset.level = String(step.level);
    return chip;
  }

  // The rigor level this problem currently sits at. The engine emits only
  // measured evidence, so unless a status reports an external discharge the
  // problem is at level 1. Levels 2-4 are reached only through external
  // backends, never inferred from the engine's own output.
  private currentRigorLevel(problem: VerificationProblem): number {
    const discharged = problem.proofStatuses.some(
      (status) => status.externalStatus !== "" && status.externalStatus !== "external-required",
    );
    return discharged ? 0 : 1;
  }

  // The four-level rigor ladder with the problem's current level marked, so a
  // measured outcome can never be read as a proof or certificate (VISION §7).
  private renderRigorLadder(problem: VerificationProblem): HTMLElement {
    const node = section("Rigor level", "verifRigorLadder");
    node.append(
      el(
        "p",
        "verif-meta",
        "The engine generates candidates and obligations; external sound methods discharge them. This problem sits at the measured level — evidence, not proof.",
      ),
    );

    const current = this.currentRigorLevel(problem);
    const list = el("ol", "verif-ladder");
    RIGOR_LADDER.forEach((step) => {
      const item = el("li", "verif-ladder__step");
      item.dataset.level = String(step.level);
      const isCurrent = step.level === current;
      if (isCurrent) {
        item.classList.add("verif-ladder__step--current");
        item.setAttribute("aria-current", "step");
      }
      const head = el("div", "verif-ladder__head");
      head.append(el("span", "verif-ladder__rank", String(step.level)));
      head.append(el("span", "verif-ladder__title", step.title));
      if (isCurrent) {
        head.append(el("span", "verif-ladder__here", "current"));
      }
      item.append(head);
      item.append(el("p", "verif-ladder__note", step.note));
      list.append(item);
    });
    node.append(list);
    return node;
  }

  // An at-a-glance, honestly labeled safety picture: one row per obligation with
  // its worst measured outcome and a reminder that it still awaits external
  // discharge. Each row jumps to the obligation's full card. The measured
  // outcome is evidence only — never a proof.
  private renderObligationLedger(problem: VerificationProblem): HTMLElement {
    const node = section("Safety properties (measured)", "verifLedger");
    node.append(
      el(
        "p",
        "verif-meta",
        "What we're checking and how it measured — a clean sample is evidence, not a proof; every obligation still awaits external discharge.",
      ),
    );

    // Worst measured outcome per obligation: a violation dominates a hold, and an
    // obligation with no sampled status reads as not sampled.
    const rank = (status: string): number =>
      status === "measured-violated" ? 2 : status === "measured-holds" ? 1 : 0;
    const outcomeByObligation = new Map<string, string>();
    // The signed worst margin (BE-036) per obligation: the tightest (most
    // negative) margin across its sampled statuses, so the ledger headlines the
    // closest the measured evidence came to the obligation boundary.
    const marginByObligation = new Map<string, number>();
    for (const status of problem.proofStatuses) {
      const prev = outcomeByObligation.get(status.obligationId);
      if (prev === undefined || rank(status.status) > rank(prev)) {
        outcomeByObligation.set(status.obligationId, status.status);
      }
      if (status.worstMargin !== null) {
        const prevMargin = marginByObligation.get(status.obligationId);
        if (prevMargin === undefined || status.worstMargin < prevMargin) {
          marginByObligation.set(status.obligationId, status.worstMargin);
        }
      }
    }

    const assumptionIds = new Set(problem.assumptions.map((assumption) => assumption.id));
    const list = el("ul", "verif-ledger");
    problem.obligations.forEach((obligation) => {
      const row = el("li", "verif-ledger__row");
      row.dataset.obligation = obligation.id;
      const head = el("div", "verif-ledger__head");
      const name = el("button", "verif-ledger__name", obligation.name);
      name.type = "button";
      name.addEventListener("click", () => this.jumpToObligation(obligation.id));
      const outcome = outcomeByObligation.get(obligation.id) ?? "external-required";
      head.append(name, this.proofStatusBadge(outcome), rigorBadge(obligation.rigor));
      row.append(head);

      // The measured detail line: the signed safety margin and the assumption
      // region the evidence was restricted to. Either may be absent (an
      // unsampled obligation, or one with no domain assumptions), so the line is
      // built only from what is present rather than showing empty affordances.
      const meta = el("p", "verif-ledger__meta");
      const margin = marginByObligation.get(obligation.id);
      if (margin !== undefined) {
        const chip = el("span", "verif-ledger__margin");
        chip.textContent = `margin ${formatSignedMeasured(margin)}`;
        chip.title = "signed worst margin to the obligation boundary — measured, not a proof";
        meta.append(chip);
      }
      if (obligation.assumptionIds.length > 0) {
        const within = el("span", "verif-ledger__within");
        within.append(el("span", "verif-ledger__within-label", "within"));
        obligation.assumptionIds.forEach((id) => {
          within.append(this.assumptionLink(id, assumptionIds));
        });
        meta.append(within);
      }
      if (meta.childElementCount > 0) {
        row.append(meta);
      }
      list.append(row);
    });
    node.append(list);
    return node;
  }

  private renderDynamics(problem: VerificationProblem): HTMLElement {
    const node = section("Dynamics");
    const dynamics = problem.dynamics!;
    const kind = el("p", "verif-meta");
    kind.textContent = `${dynamics.kind}${
      dynamics.timeVariable ? ` · time variable ${dynamics.timeVariable}` : ""
    }${dynamics.inputs.length === 0 ? " · closed loop (no inputs)" : ""}`;
    node.append(kind);

    // State names arrive as identifiers (`theta`); use the variable LaTeX so the
    // derivative LHS renders with the same symbols as the RHS.
    const variableLatex = new Map(problem.variables.map((variable) => [variable.name, variable.latex]));
    const list = el("div", "verif-eqs");
    dynamics.rhs.forEach((expression, index) => {
      const stateName = dynamics.state[index] ?? `x_{${index}}`;
      const symbol = variableLatex.get(stateName) ?? stateName;
      const row = el("div", "verif-eq");
      const lhs = dynamics.kind === "discrete" ? `${symbol}^{+}` : `\\dot{${symbol}}`;
      row.append(mathSpan(`${lhs} = ${expression.latex}`));
      list.append(row);
    });
    node.append(list);

    if (dynamics.inputs.length > 0) {
      const inputs = el("p", "verif-meta");
      inputs.textContent = `inputs: ${dynamics.inputs
        .map((input) => `${input.name}${input.role ? ` (${input.role})` : ""}`)
        .join(", ")}`;
      node.append(inputs);
    }
    return node;
  }

  private renderRegions(regions: IrRegion[]): HTMLElement {
    const node = section("Regions", "verifRegions");
    const list = el("div", "verif-cards");
    regions.forEach((region) => {
      const card = el("div", "verif-card");
      const head = el("div", "verif-card__head");
      head.append(el("strong", "verif-card__name", region.name));
      head.append(this.roleBadge(region.role));
      card.append(head);
      if (region.expression) {
        card.append(this.setRow(region));
      }
      card.append(el("p", "verif-card__id", region.id));
      list.append(card);
    });
    node.append(list);
    return node;
  }

  private setRow(region: IrRegion): HTMLElement {
    const row = el("div", "verif-card__set");
    const level = region.level ?? 0;
    row.append(mathSpan(`${region.expression!.latex} \\le ${formatNumber(level)}`));
    return row;
  }

  private roleBadge(role: RegionRole): HTMLElement {
    const label = ROLE_LABEL[role] ?? role;
    return el("span", `verif-role verif-role--${String(role).replace(/[^a-z-]/gi, "-")}`, label);
  }

  private renderCandidates(problem: VerificationProblem): HTMLElement {
    const node = section("Candidate certificates", "verifCandidates");
    const obligationIds = new Set(problem.obligations.map((obligation) => obligation.id));
    const list = el("div", "verif-cards");
    problem.candidates.forEach((candidate) => {
      const card = el("div", "verif-card");
      const head = el("div", "verif-card__head");
      head.append(el("strong", "verif-card__name", candidate.name));
      head.append(el("span", "verif-role verif-role--candidate", candidate.kind));
      head.append(rigorBadge("candidate"));
      card.append(head);
      if (candidate.expression) {
        const expr = el("div", "verif-card__set");
        expr.append(mathSpan(candidate.expression.latex));
        card.append(expr);
      }
      if (candidate.obligationIds.length > 0) {
        const obligations = el("p", "verif-card__links");
        obligations.append(el("span", "verif-card__links-label", "obligations:"));
        candidate.obligationIds.forEach((id) => {
          obligations.append(this.obligationLink(id, obligationIds));
        });
        card.append(obligations);
      }
      list.append(card);
    });
    node.append(list);
    return node;
  }

  private renderObligations(problem: VerificationProblem): HTMLElement {
    const node = section("Proof obligations", "verifObligations");
    const regionName = new Map(problem.regions.map((region) => [region.id, region.name]));
    const assumptionIds = new Set(problem.assumptions.map((assumption) => assumption.id));
    // Obligations a certificate lane bears on: only these expose the evidence
    // affordance, so an obligation with no referencing lane stays inert.
    const laneObligationIds = new Set<string>();
    for (const series of problem.trajectory?.certificateSeries ?? []) {
      series.obligationIds.forEach((id) => laneObligationIds.add(id));
    }
    const list = el("div", "verif-cards");
    problem.obligations.forEach((obligation) => {
      list.append(this.obligationCard(obligation, regionName, assumptionIds, laneObligationIds));
    });
    node.append(list);
    return node;
  }

  // A reference from an obligation to an assumption it depends on. A known
  // assumption scrolls to its card; an unknown id stays an inert code label.
  private assumptionLink(assumptionId: string, assumptionIds: Set<string>): HTMLElement {
    if (!assumptionIds.has(assumptionId)) {
      return el("code", "verif-link", assumptionId);
    }
    const link = el("button", "verif-link verif-link--jump", assumptionId);
    link.type = "button";
    link.addEventListener("click", () => this.jumpToAssumption(assumptionId));
    return link;
  }

  // A reference to an obligation from another card. When the obligation is part
  // of this problem the link scrolls to and emphasizes its card; an id with no
  // obligation (e.g. stale metadata) stays an inert code label.
  private obligationLink(obligationId: string, obligationIds: Set<string>): HTMLElement {
    if (!obligationIds.has(obligationId)) {
      return el("code", "verif-link", obligationId);
    }
    const link = el("button", "verif-link verif-link--jump", obligationId);
    link.type = "button";
    link.addEventListener("click", () => this.jumpToObligation(obligationId));
    return link;
  }

  private jumpToObligation(obligationId: string): void {
    this.emphasizeCard(this.obligationCards.get(obligationId));
  }

  // Emphasize the obligations a selected certificate lane bears on (null clears),
  // completing the evidence -> obligation direction. Marks both the obligation
  // cards and their ledger rows.
  emphasizeObligations(obligationIds: string[] | null): void {
    const targeted = obligationIds === null ? null : new Set(obligationIds);
    this.obligationCards.forEach((card, id) => {
      card.classList.toggle("verif-card--referenced", targeted !== null && targeted.has(id));
    });
    this.summaryEl
      .querySelectorAll<HTMLElement>(".verif-ledger__row")
      .forEach((row) => {
        const id = row.dataset.obligation;
        row.classList.toggle(
          "verif-ledger__row--referenced",
          targeted !== null && id !== undefined && targeted.has(id),
        );
      });
  }

  private jumpToAssumption(assumptionId: string): void {
    this.emphasizeCard(this.assumptionCards.get(assumptionId));
  }

  // Scroll a referenced card into view and re-trigger a brief pulse so the
  // navigated-to card is locatable. A missing card is a no-op. Cards live inside
  // the collapsible details, so open any closed <details> ancestor first.
  private emphasizeCard(card: HTMLElement | undefined): void {
    if (!card) {
      return;
    }
    for (let node: HTMLElement | null = card; node; node = node.parentElement) {
      if (node instanceof HTMLDetailsElement) {
        node.open = true;
      }
    }
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.remove("verif-card--targeted");
    void card.offsetWidth; // restart the pulse animation if re-triggered
    card.classList.add("verif-card--targeted");
    card.addEventListener(
      "animationend",
      () => card.classList.remove("verif-card--targeted"),
      { once: true },
    );
  }

  private obligationCard(
    obligation: IrObligation,
    regionName: Map<string, string>,
    assumptionIds: Set<string>,
    laneObligationIds: Set<string>,
  ): HTMLElement {
    const card = el("div", "verif-card");
    card.id = obligationCardId(obligation.id);
    this.obligationCards.set(obligation.id, card);
    const head = el("div", "verif-card__head");
    head.append(el("strong", "verif-card__name", obligation.name));
    head.append(rigorBadge(obligation.rigor));
    card.append(head);

    if (obligation.expression) {
      const claim = el("div", "verif-card__set");
      const rhs = obligation.rhs ?? 0;
      claim.append(
        mathSpan(
          `${obligation.expression.latex} ${comparisonLatex(obligation.comparison)} ${formatNumber(rhs)}`,
        ),
      );
      card.append(claim);
    }

    const meta = el("p", "verif-card__meta");
    if (obligation.regionId) {
      const name = regionName.get(obligation.regionId) ?? obligation.regionId;
      meta.textContent = `on ${name}`;
    }
    card.append(meta);

    // The assumptions this obligation depends on: "valid only under stated
    // assumptions". Linked to their cards when present; absent when there are
    // none, so no empty affordance is shown.
    if (obligation.assumptionIds.length > 0) {
      const assumptions = el("p", "verif-card__links");
      assumptions.append(el("span", "verif-card__links-label", "assumes:"));
      obligation.assumptionIds.forEach((id) => {
        assumptions.append(this.assumptionLink(id, assumptionIds));
      });
      card.append(assumptions);
    }

    if (obligation.description) {
      card.append(el("p", "verif-card__desc", obligation.description));
    }

    // Only obligations a certificate lane bears on can highlight their measured
    // evidence; the rest expose no affordance.
    if (laneObligationIds.has(obligation.id)) {
      const toggle = el("button", "verif-evidence-toggle", "highlight measured evidence");
      toggle.type = "button";
      toggle.dataset.obligation = obligation.id;
      toggle.setAttribute("aria-pressed", "false");
      toggle.addEventListener("click", () => this.toggleEvidence(obligation.id));
      card.append(toggle);
    }
    return card;
  }

  // Toggle which obligation's measured evidence is emphasized in the certificate
  // lanes, syncing the pressed state of every evidence toggle and notifying the
  // host. Re-selecting the active obligation clears the emphasis.
  private toggleEvidence(obligationId: string): void {
    this.selectedEvidenceObligation =
      this.selectedEvidenceObligation === obligationId ? null : obligationId;
    this.detailsEl
      .querySelectorAll<HTMLButtonElement>(".verif-evidence-toggle")
      .forEach((toggle) => {
        toggle.setAttribute(
          "aria-pressed",
          String(toggle.dataset.obligation === this.selectedEvidenceObligation),
        );
      });
    this.onEvidenceSelect(this.selectedEvidenceObligation);
  }

  // Measured proof-status surface: where the backend sampled each obligation
  // and whether those samples satisfied it. Honest by construction — every row
  // reiterates that external discharge is still required, so a clean sample is
  // never mistaken for a proof.
  private renderProofStatuses(problem: VerificationProblem): HTMLElement {
    const node = section("Measured status");
    if (problem.proofStatuses.length === 0) {
      // Obligations exist but none was sampled: say so rather than omit the
      // surface, so "no measured evidence" is not mistaken for a rendering gap.
      node.append(
        el(
          "p",
          "verif-empty-note",
          "No measured status sampled for this problem; every obligation still awaits external discharge.",
        ),
      );
      return node;
    }
    const intro = el(
      "p",
      "verif-meta",
      "Sampled evidence only — a clean sample is not a proof. Every obligation still awaits external discharge.",
    );
    node.append(intro);

    const obligationName = new Map(problem.obligations.map((obligation) => [obligation.id, obligation.name]));
    const regionName = new Map(problem.regions.map((region) => [region.id, region.name]));
    const list = el("div", "verif-cards");
    problem.proofStatuses.forEach((status) => {
      list.append(this.proofStatusCard(status, obligationName, regionName));
    });
    node.append(list);
    return node;
  }

  // The obligation a measured status sampled. When that obligation is part of
  // this problem the name jumps to its card so the measured evidence is
  // navigable back to the obligation it bears on; an unknown obligation id stays
  // an inert heading.
  private statusObligationName(
    status: ProofStatus,
    obligationName: Map<string, string>,
  ): HTMLElement {
    const label = obligationName.get(status.obligationId) ?? status.obligationId;
    if (!obligationName.has(status.obligationId)) {
      return el("strong", "verif-card__name", label);
    }
    const link = el("button", "verif-card__name verif-card__name--jump", label);
    link.type = "button";
    link.addEventListener("click", () => this.jumpToObligation(status.obligationId));
    return link;
  }

  private proofStatusCard(
    status: ProofStatus,
    obligationName: Map<string, string>,
    regionName: Map<string, string>,
  ): HTMLElement {
    const card = el("div", "verif-card");
    const head = el("div", "verif-card__head");
    head.append(this.statusObligationName(status, obligationName));
    head.append(this.proofStatusBadge(status.status));
    card.append(head);

    const where: string[] = [];
    if (status.regionId) {
      where.push(`on ${regionName.get(status.regionId) ?? status.regionId}`);
    }
    if (status.evaluationKind) {
      where.push(status.evaluationKind);
    }
    if (status.sampleCount > 0) {
      where.push(`${status.sampleCount} samples`);
    }
    if (where.length > 0) {
      card.append(el("p", "verif-card__meta", where.join(" · ")));
    }

    // The signed worst margin to the obligation boundary (BE-036): the headline
    // measured quantity. Nonnegative is slack inside the boundary; negative is a
    // violation. The raw worst sample rides along for context.
    if (status.worstMargin !== null) {
      const margin = el("p", "verif-card__meta");
      margin.textContent = `margin: ${formatSignedMeasured(status.worstMargin)}`;
      if (status.worstValue !== null) {
        const sense = status.status === "measured-violated" ? "worst (violating) sample" : "worst sample";
        margin.textContent += ` · ${sense}: ${formatMeasured(status.worstValue)}`;
      }
      card.append(margin);
    } else if (status.worstValue !== null) {
      const worst = el("p", "verif-card__meta");
      const sense = status.status === "measured-violated" ? "worst (violating) sample" : "worst sample";
      worst.textContent = `${sense}: ${formatMeasured(status.worstValue)}`;
      card.append(worst);
    }

    // The sampling note states the assumption region the evidence was restricted
    // to (BE-042/BE-043) and reiterates that a clean sample is not a proof. Show
    // it verbatim when present so the measured scope is never hidden.
    if (status.note) {
      card.append(el("p", "verif-card__desc", status.note));
    }

    // The standing obligation: measured outcome never changes this.
    card.append(el("p", "verif-card__desc", `Still ${status.externalStatus}.`));
    return card;
  }

  private proofStatusBadge(status: string): HTMLElement {
    const label = PROOF_STATUS_LABEL[status] ?? status;
    const badge = el("span", `verif-status verif-status--${status.replace(/[^a-z-]/gi, "-")}`, label);
    badge.title = PROOF_STATUS_GLOSS[status] ?? status;
    return badge;
  }

  private renderAssumptions(problem: VerificationProblem): HTMLElement {
    const node = section("Assumptions");
    const list = el("div", "verif-cards");
    problem.assumptions.forEach((assumption) => {
      const card = el("div", "verif-card");
      card.id = assumptionCardId(assumption.id);
      this.assumptionCards.set(assumption.id, card);
      card.append(el("strong", "verif-card__name", assumption.id));
      if (assumption.expression) {
        const expr = el("div", "verif-card__set");
        expr.append(mathSpan(assumption.expression.latex));
        card.append(expr);
      }
      if (assumption.description) {
        card.append(el("p", "verif-card__desc", assumption.description));
      }
      list.append(card);
    });
    node.append(list);
    return node;
  }
}
