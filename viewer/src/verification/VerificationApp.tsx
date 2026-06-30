/**
 * Root component for the Verification-domain React shell.
 *
 * FE-055 stood up the React + Tailwind + Radix toolchain with an empty root.
 * FE-058 added `TopBarIdentity` (model · claim · verdict token); FE-059 added
 * `AssumptionsBlock` (active, undischarged preconditions); FE-060 added
 * `ObligationList` (scannable rows with progressive disclosure); FE-061 added
 * `ArtifactPanel` (IR / package export); FE-062 adds `DocketRail` (the problem
 * list that drives selection). The claim chain is driven by the active problem
 * (and its artifacts) the host hands in via `setVerificationProblem`; the docket
 * comes in via `setVerificationDocket` and shows even before a problem loads. The
 * legacy vanilla verification panel still draws the rest of the view alongside
 * this tree; later tasks migrate the plot wrappers here.
 */
import { ArtifactPanel } from "./ArtifactPanel";
import { AssumptionsBlock } from "./AssumptionsBlock";
import { DocketRail } from "./DocketRail";
import { ObligationList } from "./ObligationList";
import { TopBarIdentity } from "./TopBarIdentity";
import type { VerificationArtifacts, VerificationDocket } from "./mount";
import type { VerificationProblem } from "../data/verification";

export type VerificationAppProps = {
  problem: VerificationProblem | null;
  artifacts: VerificationArtifacts | null;
  docket: VerificationDocket | null;
};

export function VerificationApp({
  problem,
  artifacts,
  docket,
}: VerificationAppProps): JSX.Element | null {
  // The docket can render before any problem loads; the claim chain only renders
  // once a problem is active.
  if (!problem && !docket) {
    return null;
  }
  return (
    <>
      <DocketRail docket={docket} />
      {problem && (
        <>
          <TopBarIdentity problem={problem} />
          <AssumptionsBlock problem={problem} />
          <ObligationList problem={problem} />
          <ArtifactPanel problem={problem} artifacts={artifacts} />
        </>
      )}
    </>
  );
}
