/**
 * TopBarIdentity (FE-058).
 *
 * The verification top bar's identity line: the model the obligations were
 * derived along, the named claim, and one overall verdict token derived in
 * TypeScript by `deriveClaimStatus`. The token is the 5-second headline; it never
 * overstates — "Measured only" reads as measured, "Certified (numeric)" as sound
 * (not proved), and `external-required` stays honest (see `claimStatus.ts`).
 */
import type { VerificationProblem } from "../data/verification";
import { deriveClaimStatus } from "./claimStatus";

export type TopBarIdentityProps = {
  problem: VerificationProblem;
};

function modelName(problem: VerificationProblem): string {
  const declared = problem.metadata.verificationModel;
  if (typeof declared === "string" && declared) {
    return declared;
  }
  return problem.system ?? problem.name;
}

export function TopBarIdentity({ problem }: TopBarIdentityProps): JSX.Element {
  const verdict = deriveClaimStatus(problem);
  return (
    <div className="vf-topbar">
      <dl className="vf-topbar__identity">
        <div className="vf-topbar__field">
          <dt className="vf-topbar__label">Model</dt>
          <dd className="vf-topbar__value">{modelName(problem)}</dd>
        </div>
        <div className="vf-topbar__field">
          <dt className="vf-topbar__label">Claim</dt>
          <dd className="vf-topbar__value">{problem.name}</dd>
        </div>
      </dl>
      <div
        className={`vf-verdict vf-verdict--${verdict.kind}`}
        title={verdict.gloss}
        role="status"
      >
        <span className="vf-verdict__dot" aria-hidden="true" />
        <span className="vf-verdict__label">Status</span>
        <span className="vf-verdict__token">{verdict.label}</span>
      </div>
    </div>
  );
}
