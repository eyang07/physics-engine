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

// Compact rendering for a measured sample value: a few significant figures,
// trailing zeros trimmed, so a worst-case sample reads cleanly.
function formatMeasured(value: number): string {
  if (!Number.isFinite(value)) {
    return String(value);
  }
  if (value === 0) {
    return "0";
  }
  return Number(value.toPrecision(3)).toString();
}

function section(title: string): HTMLElement {
  const node = el("section", "verif-section");
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
  /** Set by the host to navigate back to a problem's linked Systems example. */
  onOpenSystem: ((systemId: string) => void) | null = null;

  constructor(private readonly container: HTMLElement) {}

  clear(): void {
    this.container.replaceChildren();
  }

  renderEmpty(message: string): void {
    this.container.replaceChildren();
    const empty = el("div", "verif-empty");
    empty.append(el("p", "verif-empty__title", "No verification problems"));
    empty.append(el("p", "verif-empty__copy", message));
    this.container.append(empty);
  }

  render(problem: VerificationProblem): void {
    this.container.replaceChildren();
    const root = el("article", "verif-doc");

    root.append(this.renderHeader(problem));
    if (problem.dynamics) {
      root.append(this.renderDynamics(problem));
    }
    if (problem.regions.length > 0) {
      root.append(this.renderRegions(problem.regions));
    }
    if (problem.candidates.length > 0) {
      root.append(this.renderCandidates(problem));
    }
    if (problem.obligations.length > 0) {
      root.append(this.renderObligations(problem));
    }
    if (problem.proofStatuses.length > 0) {
      root.append(this.renderProofStatuses(problem));
    }
    if (problem.assumptions.length > 0) {
      root.append(this.renderAssumptions(problem));
    }

    this.container.append(root);
    this.container.scrollTop = 0;
  }

  private renderHeader(problem: VerificationProblem): HTMLElement {
    const header = el("header", "verif-header");
    header.append(el("p", "eyebrow", "Verification problem"));
    header.append(el("h1", "verif-header__title", problem.name));

    const chips = el("div", "verif-chips");
    chips.append(this.chip("id", problem.id));
    if (problem.source) {
      chips.append(this.chip("source", problem.source));
    }
    chips.append(this.chip("schema", problem.schemaVersion));
    header.append(chips);

    // The honesty banner: nothing here is proved; external discharge is required.
    const note =
      typeof problem.metadata.note === "string"
        ? problem.metadata.note
        : "Verification-problem IR only: every obligation awaits external sound discharge. This is candidate metadata, not certification.";
    header.append(el("p", "verif-note", note));

    // Jump back to the Systems example this problem is derived along, when linked.
    if (problem.system) {
      const link = el("button", "panel-link", `Open system: ${problem.system} →`);
      link.type = "button";
      link.addEventListener("click", () => this.onOpenSystem?.(problem.system!));
      header.append(link);
    }
    return header;
  }

  private chip(label: string, value: string): HTMLElement {
    const chip = el("span", "verif-chip");
    chip.append(el("span", "verif-chip__label", label));
    chip.append(el("span", "verif-chip__value", value));
    return chip;
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
    const node = section("Regions");
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
    const node = section("Candidate certificates");
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
          obligations.append(el("code", "verif-link", id));
        });
        card.append(obligations);
      }
      list.append(card);
    });
    node.append(list);
    return node;
  }

  private renderObligations(problem: VerificationProblem): HTMLElement {
    const node = section("Proof obligations");
    const regionName = new Map(problem.regions.map((region) => [region.id, region.name]));
    const list = el("div", "verif-cards");
    problem.obligations.forEach((obligation) => {
      list.append(this.obligationCard(obligation, regionName));
    });
    node.append(list);
    return node;
  }

  private obligationCard(
    obligation: IrObligation,
    regionName: Map<string, string>,
  ): HTMLElement {
    const card = el("div", "verif-card");
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

    if (obligation.description) {
      card.append(el("p", "verif-card__desc", obligation.description));
    }
    return card;
  }

  // Measured proof-status surface: where the backend sampled each obligation
  // and whether those samples satisfied it. Honest by construction — every row
  // reiterates that external discharge is still required, so a clean sample is
  // never mistaken for a proof.
  private renderProofStatuses(problem: VerificationProblem): HTMLElement {
    const node = section("Measured status");
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

  private proofStatusCard(
    status: ProofStatus,
    obligationName: Map<string, string>,
    regionName: Map<string, string>,
  ): HTMLElement {
    const card = el("div", "verif-card");
    const head = el("div", "verif-card__head");
    head.append(el("strong", "verif-card__name", obligationName.get(status.obligationId) ?? status.obligationId));
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

    if (status.worstValue !== null) {
      const worst = el("p", "verif-card__meta");
      const sense = status.status === "measured-violated" ? "worst (violating) sample" : "worst sample";
      worst.textContent = `${sense}: ${formatMeasured(status.worstValue)}`;
      card.append(worst);
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
