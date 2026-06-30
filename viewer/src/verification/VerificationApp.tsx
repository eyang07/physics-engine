/**
 * Root component for the Verification-domain React shell.
 *
 * FE-055 stood up the React + Tailwind + Radix toolchain with an empty root.
 * FE-058 renders the first real piece — `TopBarIdentity` (model · claim · one
 * overall verdict token) — driven by the active problem the host hands in via
 * `setVerificationProblem`. The legacy vanilla verification panel still draws the
 * rest of the view alongside this tree; later tasks (FE-059+) migrate the
 * assumptions block, obligation list, plot wrappers, and artifact panel here.
 */
import { TopBarIdentity } from "./TopBarIdentity";
import type { VerificationProblem } from "../data/verification";

export type VerificationAppProps = {
  problem: VerificationProblem | null;
};

export function VerificationApp({ problem }: VerificationAppProps): JSX.Element | null {
  if (!problem) {
    return null;
  }
  return <TopBarIdentity problem={problem} />;
}
