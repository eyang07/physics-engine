/**
 * DocketRail (FE-062).
 *
 * The verification docket: a narrow, collapsible list of the problems the
 * workbench can open, grounded in the discovery index (model · status · counts ·
 * Tier/regime) so the catalog is scannable without loading each one. Selecting an
 * entry drives the host's loader (`onSelect`), which loads the problem and feeds
 * it back through `setVerificationProblem` / `setVerificationDocket`.
 *
 * The whole rail collapses (Radix Collapsible) so it can be tucked aside on a
 * narrow layout; the list itself scrolls, so a multi-package catalog never breaks
 * the layout. Honesty: the status chip and regime badge name only the listed
 * package's rigor — a robust package is still external-required, never discharged.
 */
import * as Collapsible from "@radix-ui/react-collapsible";

import type { DocketEntry, VerificationDocket } from "./mount";

function RegimeBadge({ regime }: { regime: NonNullable<DocketEntry["regime"]> }): JSX.Element {
  const robust = regime.kind === "disturbance-robust";
  return (
    <span
      className={`vf-docket__regime vf-docket__regime--${robust ? "robust" : "nominal"}`}
      title={
        robust
          ? "disturbance-robust (Tier-3): obligations quantified over a wind box — still external-required, not discharged"
          : "nominal (Tier-1/2): no disturbance channel"
      }
    >
      {robust ? "robust" : "nominal"}
    </span>
  );
}

function DocketItem({
  entry,
  selected,
  onSelect,
}: {
  entry: DocketEntry;
  selected: boolean;
  onSelect: (id: string) => void;
}): JSX.Element {
  return (
    <button
      type="button"
      className="vf-docket__item"
      data-selected={selected}
      aria-current={selected ? "true" : undefined}
      onClick={() => onSelect(entry.id)}
    >
      <span className="vf-docket__model">{entry.model ?? entry.status}</span>
      <strong className="vf-docket__name">{entry.name}</strong>
      <span className="vf-docket__counts">
        <span className="vf-docket__count">{entry.counts.regions} regions</span>
        <span className="vf-docket__count">{entry.counts.obligations} obligations</span>
        <span className="vf-docket__status" data-status={entry.status}>
          {entry.status}
        </span>
        {entry.regime && <RegimeBadge regime={entry.regime} />}
      </span>
    </button>
  );
}

export type DocketRailProps = {
  docket: VerificationDocket | null;
};

export function DocketRail({ docket }: DocketRailProps): JSX.Element | null {
  if (!docket || docket.entries.length === 0) {
    return null;
  }
  return (
    <Collapsible.Root className="vf-docket" defaultOpen>
      <div className="vf-docket__head">
        <h2 className="vf-docket__title">Docket</h2>
        <span className="vf-docket__total">{docket.entries.length}</span>
        <Collapsible.Trigger className="vf-docket__toggle" aria-label="Toggle docket">
          <span className="vf-docket__caret" aria-hidden="true" />
        </Collapsible.Trigger>
      </div>
      <Collapsible.Content className="vf-docket__content">
        <div className="vf-docket__list">
          {docket.entries.map((entry) => (
            <DocketItem
              key={entry.id}
              entry={entry}
              selected={entry.id === docket.selectedId}
              onSelect={docket.onSelect}
            />
          ))}
        </div>
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
