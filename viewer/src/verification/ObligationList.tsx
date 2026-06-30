/**
 * ObligationList (FE-060).
 *
 * The claim chain's spine: each proof obligation as a scannable row —
 * name · status badge · signed margin — that expands (Radix Collapsible) to its
 * formal statement (KaTeX), the evidence chips backing it, the assumptions it
 * depends on, its candidate certificate, and the action that would discharge it.
 *
 * Honesty (see `obligationStatus.ts`): the status badge encodes proved/certified
 * vs. measured vs. pending by shape + fill + color, never color alone, so the
 * standing survives grayscale. Measured evidence never reads as proved; a sound
 * certified-numeric enclosure never reads as discharged; pending obligations stay
 * `external-required`. The "to discharge" line states what is still required.
 */
import * as Collapsible from "@radix-ui/react-collapsible";

import type {
  IrCandidate,
  IrObligation,
  IrRegion,
  VerificationProblem,
} from "../data/verification";
import { formatSignedMeasured } from "../util";
import { MathSpan } from "./MathSpan";
import { deriveObligationStatus, type ObligationStatus } from "./obligationStatus";

const COMPARISON_LATEX: Record<string, string> = {
  "<=": "\\le",
  "<": "<",
  ">=": "\\ge",
  ">": ">",
  "==": "=",
  "=": "=",
};

// The obligation's claim as `lhs <cmp> rhs` LaTeX, or null when it has no
// expression to render. The rhs is a structural bound (a spec constant), shown
// verbatim — not a measured magnitude.
function statementLatex(obligation: IrObligation): string | null {
  const lhs = obligation.expression?.latex;
  if (!lhs) {
    return null;
  }
  const comparison = COMPARISON_LATEX[obligation.comparison] ?? obligation.comparison;
  const rhs = obligation.rhs ?? 0;
  return `${lhs} ${comparison} ${rhs}`;
}

// The action that would move the obligation off its current standing — always
// honest about what external step is still required.
function dischargeAction(status: ObligationStatus): string {
  switch (status.kind) {
    case "discharged":
      return "Discharged by an external method — no further action.";
    case "certified-numeric":
      return "Sound enclosure recorded; external discharge (proof / accepted certificate) still required.";
    case "measured-violated":
      return "A sample violates the obligation — revise the model, region, or candidate.";
    default:
      return "Awaiting external discharge (sound method or proof).";
  }
}

function ObligationRow({
  obligation,
  problem,
  regionName,
  candidates,
}: {
  obligation: IrObligation;
  problem: VerificationProblem;
  regionName: Map<string, string>;
  candidates: IrCandidate[];
}): JSX.Element {
  const status = deriveObligationStatus(obligation, problem);
  const statement = statementLatex(obligation);
  const region = obligation.regionId ? regionName.get(obligation.regionId) ?? obligation.regionId : null;

  return (
    <Collapsible.Root className="vf-ob" data-status={status.kind}>
      <Collapsible.Trigger className="vf-ob__trigger">
        <span className="vf-ob__caret" aria-hidden="true" />
        <code className="vf-ob__name">{obligation.name}</code>
        <span
          className={`vf-ob__status vf-ob__status--${status.fill}`}
          data-status={status.kind}
          title={status.gloss}
        >
          {status.label}
        </span>
        {status.margin !== null && (
          <span
            className="vf-ob__margin"
            title="Signed worst margin to the obligation boundary — measured, not a proof."
          >
            margin {formatSignedMeasured(status.margin)}
          </span>
        )}
      </Collapsible.Trigger>
      <Collapsible.Content className="vf-ob__content">
        {statement && (
          <div className="vf-ob__statement">
            <MathSpan latex={statement} />
            {region && <span className="vf-ob__region">on {region}</span>}
          </div>
        )}

        {status.evidence.length > 0 && (
          <div className="vf-ob__evidence">
            {status.evidence.map((chip) => (
              <span
                key={chip.kind}
                className={`vf-ob__chip vf-ob__chip--${chip.kind}`}
                title={chip.gloss}
              >
                {chip.label}
              </span>
            ))}
          </div>
        )}

        {obligation.assumptionIds.length > 0 && (
          <div className="vf-ob__row">
            <span className="vf-ob__row-label">depends on</span>
            {obligation.assumptionIds.map((id) => (
              <code key={id} className="vf-ob__dep">
                {id}
              </code>
            ))}
          </div>
        )}

        {candidates.length > 0 && (
          <div className="vf-ob__row">
            <span className="vf-ob__row-label">certificate</span>
            {candidates.map((candidate) => (
              <span key={candidate.id} className="vf-ob__candidate">
                {candidate.name}
                <span className="vf-ob__candidate-kind">{candidate.kind}</span>
              </span>
            ))}
          </div>
        )}

        <p className="vf-ob__discharge">
          <span className="vf-ob__row-label">to discharge</span>
          {dischargeAction(status)}
        </p>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}

export type ObligationListProps = {
  problem: VerificationProblem;
};

export function ObligationList({ problem }: ObligationListProps): JSX.Element | null {
  if (problem.obligations.length === 0) {
    return null;
  }
  const regionName = new Map<string, string>(
    problem.regions.map((region: IrRegion) => [region.id, region.name]),
  );
  // The candidate certificate(s) bearing on each obligation, so its row can name
  // the proposed certificate without rescanning the candidate list per render.
  const candidatesByObligation = new Map<string, IrCandidate[]>();
  for (const candidate of problem.candidates) {
    for (const id of candidate.obligationIds) {
      const list = candidatesByObligation.get(id) ?? [];
      list.push(candidate);
      candidatesByObligation.set(id, list);
    }
  }

  return (
    <section className="vf-obligations" aria-label="Proof obligations">
      <header className="vf-obligations__head">
        <h2 className="vf-obligations__title">Proof obligations</h2>
        <p className="vf-obligations__note">
          Name · status · signed margin; expand for the formal statement, evidence, and what
          would discharge it. A clean sample is evidence, not a proof.
        </p>
      </header>
      <div className="vf-obligations__list">
        {problem.obligations.map((obligation) => (
          <ObligationRow
            key={obligation.id}
            obligation={obligation}
            problem={problem}
            regionName={regionName}
            candidates={candidatesByObligation.get(obligation.id) ?? []}
          />
        ))}
      </div>
    </section>
  );
}
