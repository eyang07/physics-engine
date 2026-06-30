/**
 * Root component for the Verification-domain React shell.
 *
 * FE-055 stood up the React + Tailwind + Radix toolchain with an empty root.
 * FE-058 added `TopBarIdentity` (model · claim · verdict token); FE-059 added
 * `AssumptionsBlock` (active, undischarged preconditions); FE-060 added
 * `ObligationList` (scannable rows with progressive disclosure); FE-061 adds
 * `ArtifactPanel` (IR / package export), all driven by the active problem (and
 * its artifacts) the host hands in via `setVerificationProblem`. The legacy
 * vanilla verification panel still draws the rest of the view alongside this
 * tree; later tasks (FE-062+) migrate the docket and plot wrappers here.
 */
import { ArtifactPanel } from "./ArtifactPanel";
import { AssumptionsBlock } from "./AssumptionsBlock";
import { ObligationList } from "./ObligationList";
import { TopBarIdentity } from "./TopBarIdentity";
import type { VerificationArtifacts } from "./mount";
import type { VerificationProblem } from "../data/verification";

export type VerificationAppProps = {
  problem: VerificationProblem | null;
  artifacts: VerificationArtifacts | null;
};

export function VerificationApp({ problem, artifacts }: VerificationAppProps): JSX.Element | null {
  if (!problem) {
    return null;
  }
  return (
    <>
      <TopBarIdentity problem={problem} />
      <AssumptionsBlock problem={problem} />
      <ObligationList problem={problem} />
      <ArtifactPanel problem={problem} artifacts={artifacts} />
    </>
  );
}
