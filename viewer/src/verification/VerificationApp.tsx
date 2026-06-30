/**
 * Root component for the Verification-domain React shell.
 *
 * FE-055 stood up the React + Tailwind + Radix toolchain with an empty root.
 * FE-058 added `TopBarIdentity` (model · claim · verdict token); FE-059 adds
 * `AssumptionsBlock` (active, undischarged preconditions), both driven by the
 * active problem the host hands in via `setVerificationProblem`. The legacy
 * vanilla verification panel still draws the rest of the view alongside this
 * tree; later tasks (FE-060+) migrate the obligation list, plot wrappers, and
 * artifact panel here.
 */
import { AssumptionsBlock } from "./AssumptionsBlock";
import { TopBarIdentity } from "./TopBarIdentity";
import type { VerificationProblem } from "../data/verification";

export type VerificationAppProps = {
  problem: VerificationProblem | null;
};

export function VerificationApp({ problem }: VerificationAppProps): JSX.Element | null {
  if (!problem) {
    return null;
  }
  return (
    <>
      <TopBarIdentity problem={problem} />
      <AssumptionsBlock problem={problem} />
    </>
  );
}
