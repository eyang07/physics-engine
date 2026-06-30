/**
 * Per-obligation display status (FE-060).
 *
 * Collapses one obligation's `proofStatuses` / `enclosureStatuses` into a single
 * headline status, its signed worst margin, and the evidence kinds backing it,
 * for the progressive-disclosure obligation list. This is the per-obligation
 * analogue of `deriveClaimStatus` (`claimStatus.ts`), which collapses the same
 * records to one verdict for the whole claim.
 *
 * Honesty, never broken here (mirrors the legacy ledger and `claimStatus.ts`):
 *   - A single violated sample (or violated enclosure) dominates — the honest
 *     headline is the worst case, whatever stronger evidence also exists.
 *   - Measured evidence is never rendered as proved/certified; a sound
 *     certified-numeric enclosure is never rendered as discharged; `pending`
 *     stays `external-required`.
 *   - The badge headlines the strongest *non-violated* standing; the weaker
 *     evidence kinds still surface as evidence chips, so nothing is hidden and
 *     nothing is overstated.
 */
import type { IrObligation, VerificationProblem } from "../data/verification";

export type ObligationStatusKind =
  | "discharged"
  | "certified-numeric"
  | "measured-holds"
  | "measured-violated"
  | "pending";

/** An evidence kind backing an obligation, surfaced as a chip (UI_RECONFIGURATION_PLAN §4). */
export type EvidenceKind = "sampled" | "numeric-certificate" | "external-theorem" | "candidate";

export interface EvidenceChip {
  kind: EvidenceKind;
  label: string;
  gloss: string;
}

export interface ObligationStatus {
  kind: ObligationStatusKind;
  /** The short status-badge label (UI_RECONFIGURATION_PLAN §4). */
  label: string;
  /** The one-sentence honesty note, carried as the badge's tooltip. */
  gloss: string;
  /** Signed worst margin to the obligation boundary (BE-036); null if unsampled. */
  margin: number | null;
  /** Whether the headline is a proved/certified *fill* vs. a measured *outline*
   * vs. a *dashed* pending — drives the redundant (grayscale-safe) shape. */
  fill: "filled" | "hatched" | "outline" | "dashed";
  /** The evidence kinds backing the obligation, strongest first. */
  evidence: EvidenceChip[];
}

const CERTIFIED_HOLDS = "certified-holds";
const RIGOR_CERTIFIED_NUMERIC = "certified-numeric";

const DETAILS: Record<ObligationStatusKind, Omit<ObligationStatus, "margin" | "evidence">> = {
  discharged: {
    kind: "discharged",
    label: "proved",
    gloss: "Deductively proved or certificate-accepted by an external method.",
    fill: "filled",
  },
  "certified-numeric": {
    kind: "certified-numeric",
    label: "certified-numeric",
    gloss:
      "Closed by a sound numeric enclosure over the stated box under recorded assumptions — sound, not a theorem and not externally discharged.",
    fill: "hatched",
  },
  "measured-holds": {
    kind: "measured-holds",
    label: "measured: holds",
    gloss: "Sampled values satisfied the obligation — measured evidence, not a proof.",
    fill: "outline",
  },
  "measured-violated": {
    kind: "measured-violated",
    label: "measured: violated",
    gloss: "At least one sample violated the obligation.",
    fill: "filled",
  },
  pending: {
    kind: "pending",
    label: "pending",
    gloss: "No measured or certified evidence yet — awaiting external discharge.",
    fill: "dashed",
  },
};

// An external method actually discharged this obligation when its sampled status
// moved off `external-required`. The engine never self-emits this, so in current
// data it never fires — but the ladder stays open to a real external discharge.
function isExternallyDischarged(externalStatus: string): boolean {
  return externalStatus !== "" && externalStatus !== "external-required";
}

const SAMPLED_CHIP: EvidenceChip = {
  kind: "sampled",
  label: "sampled evidence",
  gloss: "Sampled along the rollout / region grid — measured evidence, not a proof.",
};
const NUMERIC_CERTIFICATE_CHIP: EvidenceChip = {
  kind: "numeric-certificate",
  label: "numeric certificate",
  gloss: "A sound interval enclosure over the stated box — sound, still external-required.",
};
const EXTERNAL_THEOREM_CHIP: EvidenceChip = {
  kind: "external-theorem",
  label: "external theorem",
  gloss: "Discharged by an external sound method.",
};
const CANDIDATE_CHIP: EvidenceChip = {
  kind: "candidate",
  label: "candidate",
  gloss: "A proposed certificate function for this obligation — not yet accepted.",
};

/**
 * Derive one obligation's display status, signed margin, and backing evidence
 * from the problem's measured/certified records.
 */
export function deriveObligationStatus(
  obligation: IrObligation,
  problem: VerificationProblem,
): ObligationStatus {
  const proofs = problem.proofStatuses.filter((s) => s.obligationId === obligation.id);
  const enclosures = problem.enclosureStatuses.filter((s) => s.obligationId === obligation.id);

  const violated =
    proofs.some((s) => s.status === "measured-violated") ||
    enclosures.some((s) => s.verdict === "certified-violated");
  const discharged = proofs.some((s) => isExternallyDischarged(s.externalStatus));
  const certified = enclosures.some(
    (s) => s.verdict === CERTIFIED_HOLDS && s.rigor === RIGOR_CERTIFIED_NUMERIC,
  );
  const measured = proofs.some((s) => s.status === "measured-holds");

  // The tightest (most negative) signed margin across the obligation's sampled
  // statuses, so the row headlines the closest the evidence came to the boundary.
  let margin: number | null = null;
  for (const s of proofs) {
    if (s.worstMargin !== null && (margin === null || s.worstMargin < margin)) {
      margin = s.worstMargin;
    }
  }

  // Evidence chips: every backing kind, independent of the headline, so nothing
  // is hidden behind the single status badge.
  const evidence: EvidenceChip[] = [];
  if (discharged) {
    evidence.push(EXTERNAL_THEOREM_CHIP);
  }
  if (certified) {
    evidence.push(NUMERIC_CERTIFICATE_CHIP);
  }
  if (proofs.some((s) => s.status === "measured-holds" || s.status === "measured-violated")) {
    evidence.push(SAMPLED_CHIP);
  }
  if (problem.candidates.some((c) => c.obligationIds.includes(obligation.id))) {
    evidence.push(CANDIDATE_CHIP);
  }

  // Headline: a violation dominates; otherwise the strongest non-violated rung.
  let kind: ObligationStatusKind;
  if (violated) {
    kind = "measured-violated";
  } else if (discharged) {
    kind = "discharged";
  } else if (certified) {
    kind = "certified-numeric";
  } else if (measured) {
    kind = "measured-holds";
  } else {
    kind = "pending";
  }

  return { ...DETAILS[kind], margin, evidence };
}
