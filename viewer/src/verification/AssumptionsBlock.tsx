/**
 * AssumptionsBlock (FE-059).
 *
 * Surfaces the active, undischarged assumptions every obligation is conditional
 * on, above the obligation list, so a reader cannot miss the preconditions the
 * claim leans on. "Active" means at least one obligation depends on it
 * (`obligation.assumptionIds`); each is shown with its bound (KaTeX) and tagged
 * `active` / `undischarged`. The disturbance set W is labelled when present.
 *
 * Honesty: assumptions are stated preconditions, never discharged here — the
 * engine proposes them and an external method would have to establish them. The
 * `undischarged` tag says so verbatim.
 */
import type { IrAssumption, IrObligation, VerificationProblem } from "../data/verification";
import { MathSpan } from "./MathSpan";

const COMPARISON_LATEX: Record<string, string> = {
  "<=": "\\le",
  "<": "<",
  ">=": "\\ge",
  ">": ">",
  "==": "=",
  "=": "=",
};

// A structural bound constant (the assumption's right-hand side), trimmed — a
// spec precondition, not a measured magnitude.
function constantLatex(value: number): string {
  if (Object.is(value, -0) || Math.abs(value) < 1e-12) {
    return "0";
  }
  return Number(value.toFixed(6))
    .toString()
    .replace(/\.?0+$/, "");
}

// The assumption's bound as `lhs <cmp> rhs`, or just the expression when there is
// no comparison/right-hand side to show. Null when there is no expression at all.
function boundLatex(assumption: IrAssumption): string | null {
  const lhs = assumption.expression?.latex;
  if (!lhs) {
    return null;
  }
  const comparison = COMPARISON_LATEX[assumption.comparison];
  if (!comparison || assumption.rhs === null) {
    return lhs;
  }
  return `${lhs} ${comparison} ${constantLatex(assumption.rhs)}`;
}

// The disturbance set W: an assumption that bounds a disturbance variable `w_i`.
// Detected from the expression (the mathematical signature `w` + index) or the
// assumption id, so the wind box reads as W rather than a generic bound.
function isDisturbanceSet(assumption: IrAssumption): boolean {
  const display = assumption.expression?.display ?? "";
  return /(^|[^a-z])w\d/i.test(display) || /disturb|wind/i.test(assumption.id);
}

export type AssumptionsBlockProps = {
  problem: VerificationProblem;
};

export function AssumptionsBlock({ problem }: AssumptionsBlockProps): JSX.Element | null {
  // The obligations that depend on each assumption, so "active" is concrete: a
  // precondition is active exactly when some obligation leans on it.
  const dependents = new Map<string, IrObligation[]>();
  for (const obligation of problem.obligations) {
    for (const id of obligation.assumptionIds) {
      const list = dependents.get(id) ?? [];
      list.push(obligation);
      dependents.set(id, list);
    }
  }

  const active = problem.assumptions.filter((assumption) => dependents.has(assumption.id));
  if (active.length === 0) {
    return null;
  }

  return (
    <section className="vf-assumptions" aria-label="Active assumptions">
      <header className="vf-assumptions__head">
        <h2 className="vf-assumptions__title">Active assumptions</h2>
        <p className="vf-assumptions__note">
          Undischarged preconditions — every obligation below is conditional on these.
        </p>
      </header>
      <ul className="vf-assumptions__list">
        {active.map((assumption) => {
          const bound = boundLatex(assumption);
          const deps = dependents.get(assumption.id) ?? [];
          return (
            <li className="vf-assumption" key={assumption.id}>
              <div className="vf-assumption__head">
                <code className="vf-assumption__id">{assumption.id}</code>
                <span className="vf-tag vf-tag--active">active</span>
                <span className="vf-tag vf-tag--undischarged">undischarged</span>
                {isDisturbanceSet(assumption) && (
                  <span className="vf-tag vf-tag--disturbance">disturbance set W</span>
                )}
              </div>
              {bound && <MathSpan latex={bound} className="vf-assumption__bound" />}
              {assumption.description && (
                <p className="vf-assumption__desc">{assumption.description}</p>
              )}
              <div className="vf-assumption__deps">
                <span className="vf-assumption__deps-label">required by</span>
                {deps.map((obligation) => (
                  <span className="vf-assumption__dep" key={obligation.id}>
                    {obligation.name}
                  </span>
                ))}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
