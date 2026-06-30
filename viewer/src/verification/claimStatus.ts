/**
 * Overall claim-status derivation (FE-058).
 *
 * Collapses a problem's per-obligation rigor/measured/certified standing into a
 * single honest headline verdict for the top bar. No backend field carries this
 * — it is derived in TypeScript from the same `proofStatuses` / `enclosureStatuses`
 * the panel already shows (UI_RECONFIGURATION_PLAN §"Data-model assumptions").
 *
 * Honesty rules, never broken here:
 *   - A safety claim is the *conjunction* of its obligations, so the overall
 *     verdict is only as strong as its weakest-supported obligation. The best
 *     obligation never lifts the headline (a single certified enclosure does not
 *     make a part-measured claim "certified"). This is deliberately stricter than
 *     the legacy "highest rung reached" masthead line, so the verdict can never
 *     overstate.
 *   - A single violated sample (or violated enclosure) dominates: the honest
 *     worst case is a counterexample, whatever other evidence exists.
 *   - Measured evidence is never rendered as proved/certified; certified-numeric
 *     is never rendered as discharged. `external-required` stays honest.
 */
import type { VerificationProblem } from "../data/verification";

export type ClaimStatusKind =
  | "discharged"
  | "certified-numeric"
  | "measured-only"
  | "counterexample"
  | "pending-external";

export interface ClaimStatus {
  kind: ClaimStatusKind;
  /** The short headline token (UI_RECONFIGURATION_PLAN §4). */
  label: string;
  /** The one-sentence honesty note, carried as the verdict's tooltip. */
  gloss: string;
}

// The obligation rigor ladder, weakest first: a higher number is a stronger
// standing. The overall verdict takes the *minimum* across obligations.
const RUNG_PENDING = 0;
const RUNG_MEASURED = 1;
const RUNG_CERTIFIED = 2;
const RUNG_DISCHARGED = 3;

const DETAILS: Record<ClaimStatusKind, Omit<ClaimStatus, "kind">> = {
  discharged: {
    label: "Discharged",
    gloss: "Every obligation deductively proved or certificate-accepted by an external method.",
  },
  "certified-numeric": {
    label: "Certified (numeric)",
    gloss:
      "Every obligation closed by a sound numeric enclosure under the stated assumptions — sound over the box, still not a theorem and not externally discharged.",
  },
  "measured-only": {
    label: "Measured only",
    gloss:
      "Sampled evidence satisfies every obligation — measured evidence, not a certificate or a proof.",
  },
  counterexample: {
    label: "Counterexample",
    gloss: "At least one obligation was violated on samples.",
  },
  "pending-external": {
    label: "Pending external",
    gloss:
      "Obligations awaiting external discharge, with no measured or certified evidence yet.",
  },
};

function status(kind: ClaimStatusKind): ClaimStatus {
  return { kind, ...DETAILS[kind] };
}

// An external method actually discharged this obligation when its sampled status
// moved off `external-required`. The engine never self-emits this, so in current
// data it never fires — but the ladder stays open to a real external discharge.
function isExternallyDischarged(externalStatus: string): boolean {
  return externalStatus !== "" && externalStatus !== "external-required";
}

function obligationRung(obligationId: string, problem: VerificationProblem): number {
  const proofs = problem.proofStatuses.filter((s) => s.obligationId === obligationId);
  const enclosures = problem.enclosureStatuses.filter((s) => s.obligationId === obligationId);

  if (proofs.some((s) => isExternallyDischarged(s.externalStatus))) {
    return RUNG_DISCHARGED;
  }
  // A sound certified-numeric enclosure that closes the obligation (level 2);
  // only a genuine `certified-holds` / `certified-numeric` tag counts.
  if (
    enclosures.some((s) => s.verdict === "certified-holds" && s.rigor === "certified-numeric")
  ) {
    return RUNG_CERTIFIED;
  }
  // Sampled evidence satisfied it (level 1): measured, not a certificate.
  if (proofs.some((s) => s.status === "measured-holds")) {
    return RUNG_MEASURED;
  }
  // No measured or certified evidence: the obligation only awaits external
  // discharge.
  return RUNG_PENDING;
}

/**
 * Derive the single overall claim verdict for the top bar from the problem's
 * obligations and their measured/certified statuses.
 */
export function deriveClaimStatus(problem: VerificationProblem): ClaimStatus {
  // A single violation is the honest headline regardless of other evidence.
  const violated =
    problem.proofStatuses.some((s) => s.status === "measured-violated") ||
    problem.enclosureStatuses.some((s) => s.verdict === "certified-violated");
  if (violated) {
    return status("counterexample");
  }

  // With no obligations declared, nothing is established and nothing discharged.
  if (problem.obligations.length === 0) {
    return status("pending-external");
  }

  const weakest = problem.obligations.reduce(
    (acc, obligation) => Math.min(acc, obligationRung(obligation.id, problem)),
    RUNG_DISCHARGED,
  );
  switch (weakest) {
    case RUNG_DISCHARGED:
      return status("discharged");
    case RUNG_CERTIFIED:
      return status("certified-numeric");
    case RUNG_MEASURED:
      return status("measured-only");
    default:
      return status("pending-external");
  }
}
