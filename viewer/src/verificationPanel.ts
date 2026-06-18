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
  AdapterStub,
  AdapterStubs,
  IrAssumption,
  IrObligation,
  IrRegion,
  PackageManifest,
  PackageRegime,
  ProofStatus,
  RegionRole,
  VerificationProblem,
} from "./data/verification";
import { assembleVerificationPackageBundle } from "./data/verification";
import { formatMeasured, formatSignedMeasured } from "./util";

/** The self-contained package bundle offered for download/inspection, when the
 * backend published one for this problem. */
export interface VerificationPackageRef {
  manifest: PackageManifest;
  path: string;
}

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

// Terse rung labels for the horizontal certification scale (the masthead
// signature); the full titles ride along as tooltips.
const CERTIFICATION_RUNG: Record<number, string> = {
  1: "measured",
  2: "certified numeric",
  3: "certificate-accepted",
  4: "deductively proved",
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
    private readonly mastheadEl: HTMLElement,
    private readonly summaryEl: HTMLElement,
    private readonly detailsEl: HTMLElement,
  ) {}

  clear(): void {
    this.obligationCards.clear();
    this.assumptionCards.clear();
    this.mastheadEl.replaceChildren();
    this.summaryEl.replaceChildren();
    this.detailsEl.replaceChildren();
  }

  renderEmpty(message: string): void {
    this.obligationCards.clear();
    this.assumptionCards.clear();
    this.mastheadEl.replaceChildren();
    this.detailsEl.replaceChildren();
    const empty = el("div", "verif-empty");
    empty.append(el("p", "verif-empty__title", "No verification problems"));
    empty.append(el("p", "verif-empty__copy", message));
    this.summaryEl.replaceChildren(empty);
  }

  // The dossier: a masthead (claim + certification scale) spans the top, the
  // proof-obligation table is the right column, and the full IR is a collapsed
  // appendix below. Nothing here is proved; the masthead says so verbatim.
  render(
    problem: VerificationProblem,
    irPath: string | null = null,
    pkg: VerificationPackageRef | null = null,
    stubs: AdapterStubs | null = null,
    regime: PackageRegime | null = null,
  ): void {
    this.obligationCards.clear();
    this.assumptionCards.clear();
    this.selectedEvidenceObligation = null;

    // Masthead band (full width above the figure + obligations).
    this.mastheadEl.replaceChildren(this.renderMasthead(problem, regime));

    // Obligations column.
    const obligations = el("div", "verif-summary");
    if (problem.obligations.length > 0) {
      obligations.append(this.renderObligationLedger(problem));
    }
    this.summaryEl.replaceChildren(obligations);

    // Collapsed appendix: the full IR, plus the export affordances.
    const details = el("details", "verif-details");
    details.append(el("summary", "verif-details__summary", "Appendix — problem record (IR)"));
    const body = el("div", "verif-details__body");
    body.append(this.renderExports(problem, irPath, pkg));
    if (pkg) {
      body.append(this.renderPackageInventory(pkg));
    }
    if (stubs && stubs.stubs.length > 0) {
      body.append(this.renderAdapterStubs(problem, stubs));
    }
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

  // The dossier masthead: the problem title and model, a one-line claim status,
  // and the certification scale (the page's signature). It carries the honesty
  // thesis up front — measured evidence, not a discharge.
  private renderMasthead(problem: VerificationProblem, regime: PackageRegime | null): HTMLElement {
    const masthead = el("div", "verif-masthead");

    const head = el("div", "verif-masthead__head");
    const heading = el("div", "verif-masthead__heading");
    heading.append(el("p", "eyebrow", "Verification dossier"));
    heading.append(el("h1", "verif-masthead__title", problem.name));
    head.append(heading);
    const model = this.metaString(problem, "verificationModel") ?? problem.system;
    if (model) {
      const tag = el("p", "verif-masthead__model");
      tag.append(el("span", "verif-masthead__model-label", "model"));
      tag.append(el("code", "verif-masthead__model-id", model));
      head.append(tag);
    }
    // The open problem's Tier/regime from the discovery index (FE-033): nominal
    // vs disturbance-robust, with the disturbance parameters and robust
    // obligations a robust package cites. Shown only when the descriptor exists.
    if (regime) {
      head.append(this.renderRegime(regime));
    }
    masthead.append(head);

    // Claim status — a single formal line. The engine emits only measured
    // evidence, so unless a status reports external discharge the claim is
    // measured-but-undischarged.
    const discharged = this.currentRigorLevel(problem) === 0;
    const claim = el("p", "verif-claim");
    claim.append(el("span", "verif-claim__label", "Claim status"));
    claim.append(
      el(
        "span",
        "verif-claim__text",
        discharged
          ? "externally discharged"
          : "measured evidence · not discharged",
      ),
    );
    masthead.append(claim);

    masthead.append(this.renderCertificationScale(problem));
    return masthead;
  }

  // The open problem's Tier/regime, read straight from the discovery index: a
  // disturbance-robust package names the disturbance parameters and the robust
  // obligation ids it cites. A robust package is still external-required, never
  // discharged — the regime says what the claim is quantified over, nothing more.
  private renderRegime(regime: PackageRegime): HTMLElement {
    const robust = regime.kind === "disturbance-robust";
    const node = el(
      "div",
      `verif-masthead__regime verif-masthead__regime--${robust ? "robust" : "nominal"}`,
    );
    node.append(el("span", "verif-masthead__regime-label", "regime"));
    node.append(
      el("span", "verif-masthead__regime-kind", robust ? "disturbance-robust" : "nominal"),
    );
    node.title = robust
      ? "disturbance-robust (Tier-3): obligations quantified over a wind box — still external-required, not discharged"
      : "nominal (Tier-1/2): no disturbance channel";

    if (robust && regime.disturbanceParameters.length > 0) {
      const detail = el("span", "verif-masthead__regime-detail");
      detail.append(el("span", "verif-masthead__regime-detail-label", "disturbance "));
      detail.append(
        el("code", "verif-masthead__regime-detail-ids", regime.disturbanceParameters.join(", ")),
      );
      node.append(detail);
    }
    if (robust && regime.robustObligationIds.length > 0) {
      const detail = el("span", "verif-masthead__regime-detail");
      detail.append(el("span", "verif-masthead__regime-detail-label", "robust obligations "));
      detail.append(
        el("code", "verif-masthead__regime-detail-ids", regime.robustObligationIds.join(", ")),
      );
      node.append(detail);
    }
    return node;
  }

  // The export appendix: the backend-agnostic IR on its own, and — distinct from
  // it — the self-contained BE-039 package bundle. Lives in the record/appendix,
  // not the masthead, so the claim stays the focus.
  private renderExports(
    problem: VerificationProblem,
    irPath: string | null,
    pkg: VerificationPackageRef | null,
  ): HTMLElement {
    const node = section("Export");
    const exports = el("div", "verif-exports");
    if (irPath) {
      const download = el("a", "verif-download-ir", "Download problem (IR)");
      download.href = irPath;
      download.download = `${problem.id}.verification-problem.json`;
      exports.append(download);
    }
    if (pkg) {
      exports.append(this.renderPackageExport(pkg));
    }
    if (exports.childElementCount === 0) {
      node.append(el("p", "verif-meta", "No export artifact published for this problem."));
    } else {
      node.append(exports);
    }
    return node;
  }

  // A metadata string accessor that never trusts the shape of the IR metadata.
  private metaString(problem: VerificationProblem, key: string): string | null {
    const value = problem.metadata[key];
    return typeof value === "string" && value ? value : null;
  }

  // The self-contained package: a one-line inspect of the indexed components plus
  // a download that assembles the whole bundle into a single file. Visibly
  // distinct from the IR download, and honest — the bundle gathers the same
  // measured/candidate parts and discharges nothing.
  private renderPackageExport(pkg: VerificationPackageRef): HTMLElement {
    const node = el("div", "verif-package");
    const kinds = pkg.manifest.components.map((component) => component.kind).join(", ");
    const inspect = el(
      "p",
      "verif-package__inspect",
      `Package bundle (${pkg.manifest.components.length}): ${kinds}`,
    );
    inspect.title = pkg.manifest.components
      .map((component) => `${component.kind} — ${component.path}`)
      .join("\n");
    node.append(inspect);

    const button = el("button", "verif-download-package", "Download package (bundle)");
    button.type = "button";
    button.addEventListener("click", () => void this.downloadPackageBundle(pkg, button));
    node.append(button);

    node.append(
      el(
        "p",
        "verif-package__note",
        "One self-contained bundle (manifest + components) — gathers measured evidence and candidates; discharges nothing.",
      ),
    );
    return node;
  }

  // A read-only inventory of the published BE-039 package: the manifest's model,
  // status, and counts, and every indexed component (kind, filename,
  // description), so the bundle's contents are inspectable without downloading
  // it. Renders only what the manifest exports; the bundle gathers measured
  // evidence and candidates and discharges nothing.
  private renderPackageInventory(pkg: VerificationPackageRef): HTMLElement {
    const node = section("Package", "verifPackage");
    const manifest = pkg.manifest;

    const meta = el("dl", "verif-package-meta");
    const addMeta = (label: string, value: string): void => {
      meta.append(el("dt", "verif-package-meta__term", label));
      meta.append(el("dd", "verif-package-meta__value", value));
    };
    addMeta("model", manifest.model || "—");
    addMeta("status", manifest.status);
    addMeta(
      "counts",
      `${manifest.counts.regions} regions · ${manifest.counts.obligations} obligations · ` +
        `${manifest.counts.candidates} candidates`,
    );
    node.append(meta);

    const list = el("ul", "verif-package-components");
    manifest.components.forEach((component) => {
      const item = el("li", "verif-package-component");
      const head = el("div", "verif-package-component__head");
      head.append(el("span", "verif-package-component__kind", component.kind));
      head.append(el("code", "verif-package-component__file", component.path));
      item.append(head);
      if (component.description) {
        item.append(el("p", "verif-package-component__desc", component.description));
      }
      list.append(item);
    });
    node.append(list);

    node.append(
      el(
        "p",
        "verif-meta",
        "Inventory of the bundle's indexed components — the same measured evidence and candidates as the IR; it discharges nothing.",
      ),
    );
    return node;
  }

  // The non-discharging adapter stubs (BE-044): per obligation, the external
  // backend categories that could consume it and the obligation shape each would
  // have to handle. Every entry is labeled discharges: false — a stub is a
  // descriptor, never a discharge, and every obligation stays external-required.
  // Renders only what the stubs component exports.
  private renderAdapterStubs(problem: VerificationProblem, stubs: AdapterStubs): HTMLElement {
    const node = section("Adapter stubs", "verifAdapterStubs");
    // The backend's own honesty note, verbatim.
    if (stubs.note) {
      node.append(el("p", "verif-meta", stubs.note));
    }

    const obligationName = new Map(problem.obligations.map((o) => [o.id, o.name]));
    // The category summary for each category id, surfaced as a tooltip so the
    // categories component is inspectable without bulk.
    const categorySummary = new Map(stubs.categories.map((c) => [c.category, c.summary]));

    // Group the stubs by obligation, in the problem's obligation order, then any
    // stub whose obligation is not in this problem (defensive).
    const byObligation = new Map<string, AdapterStub[]>();
    for (const stub of stubs.stubs) {
      const list = byObligation.get(stub.obligationId) ?? [];
      list.push(stub);
      byObligation.set(stub.obligationId, list);
    }
    const order = [
      ...problem.obligations.map((o) => o.id).filter((id) => byObligation.has(id)),
      ...[...byObligation.keys()].filter((id) => !obligationName.has(id)),
    ];

    const list = el("div", "verif-cards");
    order.forEach((obligationId) => {
      const card = el("div", "verif-card");
      const head = el("div", "verif-card__head");
      head.append(this.adapterObligationName(obligationId, obligationName));
      card.append(head);

      const entries = el("ul", "verif-adapter-stubs");
      (byObligation.get(obligationId) ?? []).forEach((stub) => {
        const item = el("li", "verif-adapter-stub");
        const top = el("div", "verif-adapter-stub__head");
        const category = el("span", "verif-adapter-stub__category", stub.category);
        const summary = categorySummary.get(stub.category);
        if (summary) {
          category.title = summary;
        }
        top.append(category);
        // The standing honesty marker: a stub never discharges.
        top.append(el("span", "verif-adapter-stub__discharges", "discharges: false"));
        item.append(top);

        // The obligation shape this category would have to handle.
        const shapeParts = [`target ${stub.target}`];
        if (stub.requiredShapeFeatures.length > 0) {
          shapeParts.push(`shape: ${stub.requiredShapeFeatures.join(", ")}`);
        }
        item.append(el("p", "verif-adapter-stub__shape", shapeParts.join(" · ")));
        entries.append(item);
      });
      card.append(entries);
      list.append(card);
    });
    node.append(list);
    return node;
  }

  // An obligation heading for an adapter-stub card: links to the obligation's
  // full card when the obligation is part of this problem, otherwise an inert
  // heading.
  private adapterObligationName(
    obligationId: string,
    obligationName: Map<string, string>,
  ): HTMLElement {
    const label = obligationName.get(obligationId) ?? obligationId;
    if (!obligationName.has(obligationId)) {
      return el("strong", "verif-card__name", label);
    }
    // A distinct jump class (not verif-card__name--jump) so the measured-status
    // jump count stays unaffected; styled identically.
    const link = el("button", "verif-card__name verif-adapter-stub__jump", label);
    link.type = "button";
    link.addEventListener("click", () => this.jumpToObligation(obligationId));
    return link;
  }

  // Assemble and download the package as one JSON file. Fetching the components
  // is async, so the control is disabled while in flight and a failure leaves an
  // honest console warning rather than a half-written file.
  private async downloadPackageBundle(
    pkg: VerificationPackageRef,
    button: HTMLButtonElement,
  ): Promise<void> {
    button.disabled = true;
    try {
      const bundle = await assembleVerificationPackageBundle(pkg.path);
      const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = el("a");
      anchor.href = url;
      anchor.download = `${pkg.manifest.problemId}.verification-package.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.warn("Verification package download failed:", error);
    } finally {
      button.disabled = false;
    }
  }

  // The certification scale — the dossier's signature. The four rigor rungs as a
  // horizontal gauge: rungs up to the established level are filled, the rest are
  // open on a dashed "not yet established" track, so the gap to a real
  // certificate is the most prominent, true-to-subject thing on the page.
  private renderCertificationScale(problem: VerificationProblem): HTMLElement {
    const current = this.currentRigorLevel(problem);
    const node = el("div", "verif-scale");
    const currentStep = RIGOR_LADDER.find((entry) => entry.level === current);
    node.setAttribute("role", "img");
    node.setAttribute(
      "aria-label",
      `Established to rung ${current} of ${RIGOR_LADDER.length}` +
        (currentStep ? ` — ${currentStep.title}` : "") +
        "; higher rungs require external discharge.",
    );

    const track = el("ol", "verif-scale__track");
    RIGOR_LADDER.forEach((step) => {
      const rung = el("li", "verif-scale__rung");
      rung.dataset.level = String(step.level);
      const established = step.level <= current;
      rung.classList.toggle("verif-scale__rung--established", established);
      rung.classList.toggle("verif-scale__rung--current", step.level === current);
      rung.classList.toggle("verif-scale__rung--open", !established);
      rung.append(el("span", "verif-scale__rank", `${step.level}`));
      rung.append(el("span", "verif-scale__dot"));
      rung.append(el("span", "verif-scale__label", CERTIFICATION_RUNG[step.level] ?? step.title));
      rung.title = `${step.title} — ${step.note}`;
      track.append(rung);
    });
    node.append(track);

    const open = RIGOR_LADDER.filter((step) => step.level > current).map((step) => step.level);
    const caption =
      open.length > 0
        ? `Established to rung ${current} (measured evidence). Rungs ${open[0]}–${open[open.length - 1]} require external discharge.`
        : "Externally discharged.";
    node.append(el("p", "verif-scale__caption", caption));
    return node;
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
    const node = section("Proof obligations", "verifLedger");
    node.append(
      el(
        "p",
        "verif-meta",
        "Each obligation with its measured margin and the assumption region it was sampled within. A clean sample is evidence, not a proof — every obligation still awaits external discharge.",
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

    // The assumptions, by id, so a robust obligation can surface the disturbance
    // bound it is quantified over (FE-023).
    const assumptionById = new Map(problem.assumptions.map((assumption) => [assumption.id, assumption]));

    const list = el("ul", "verif-ledger");
    problem.obligations.forEach((obligation) => {
      const row = el("li", "verif-ledger__row");
      row.dataset.obligation = obligation.id;

      // The obligation name wraps freely on its own line; its measured outcome
      // and rigor badges sit on a row beneath it, so a long name never collides
      // with a badge in the narrow summary rail.
      const head = el("div", "verif-ledger__head");
      const name = el("button", "verif-ledger__name", obligation.name);
      name.type = "button";
      name.addEventListener("click", () => this.jumpToObligation(obligation.id));
      const outcome = outcomeByObligation.get(obligation.id) ?? "external-required";
      const badges = el("div", "verif-ledger__badges");
      badges.append(this.proofStatusBadge(outcome), rigorBadge(obligation.rigor));
      // Tier-3: a disturbance-robust obligation is quantified over the wind box
      // W. Mark it honestly — robust, but still external-required, never
      // discharged.
      const disturbance = this.disturbanceBound(obligation, assumptionById);
      if (disturbance) {
        badges.append(this.robustBadge());
      }
      head.append(name, badges);
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
        // The assumption region as a light inline footnote; the full, navigable
        // assumption cards live in the obligation detail below.
        const within = el("span", "verif-ledger__within");
        within.append(el("span", "verif-ledger__within-label", "within "));
        within.append(
          el("span", "verif-ledger__within-ids", obligation.assumptionIds.join(", ")),
        );
        meta.append(within);
      }
      // The cited disturbance box the robust claim is quantified over, rendered
      // verbatim from the assumption's bound (e.g. |w_1| <= 0.5). Read-only — it
      // says what the robustness is against, not that it is discharged.
      if (disturbance) {
        meta.append(this.disturbanceBoundChip(disturbance));
      }
      if (meta.childElementCount > 0) {
        row.append(meta);
      }
      list.append(row);
    });
    node.append(list);
    return node;
  }

  // The disturbance-box assumption a robust (Tier-3) obligation is quantified
  // over, if any. A robust obligation cites a wind/disturbance-box assumption
  // (its id names the disturbance/wind bound); nominal obligations — including
  // the nominal velocity bound — cite none. Read only from the IR.
  private disturbanceBound(
    obligation: IrObligation,
    assumptionById: Map<string, IrAssumption>,
  ): IrAssumption | null {
    for (const id of obligation.assumptionIds) {
      if (!/disturbance|wind/i.test(id)) {
        continue;
      }
      const assumption = assumptionById.get(id);
      if (assumption) {
        return assumption;
      }
    }
    return null;
  }

  // The honest robust marker: the obligation holds for every admissible
  // disturbance in the wind box W — but it is still external-required, never
  // discharged by the engine.
  private robustBadge(): HTMLElement {
    const badge = el("span", "verif-badge verif-badge--robust", "robust ∀ d ∈ W");
    badge.title =
      "disturbance-robust: quantified over every admissible disturbance in the wind box W — still external-required, not discharged";
    return badge;
  }

  // The cited disturbance bound, rendered verbatim from the assumption (e.g.
  // |w_1| <= 0.5), so a reader can see what the robustness is quantified against.
  private disturbanceBoundChip(assumption: IrAssumption): HTMLElement {
    const chip = el("span", "verif-ledger__disturbance");
    chip.append(el("span", "verif-ledger__disturbance-label", "robust within "));
    if (assumption.expression && assumption.rhs !== null) {
      chip.append(
        mathSpan(
          `${assumption.expression.latex} ${comparisonLatex(assumption.comparison)} ${formatNumber(assumption.rhs)}`,
        ),
      );
    } else {
      chip.append(el("span", "verif-ledger__disturbance-id", assumption.id));
    }
    chip.title = "the disturbance box W the robust claim is quantified over — measured/assumed, not a proof";
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
