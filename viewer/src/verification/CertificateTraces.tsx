/**
 * React wrapper for the candidate-certificate lanes (FE-057).
 *
 * Owns a `<canvas>` per lane and drives the framework-free `drawCertificateLane`
 * renderer (FE-056) imperatively, animating while `active` against the shared
 * rollout phase. Lane labels and metrics come from `prepareCertificateLanes`, so
 * neither this wrapper nor the vanilla `CertificateLanes` re-derives them. A
 * `selectedObligationId` surfaces that obligation's worst sampled margin on the
 * lanes that bear on it — measured evidence, never a proof.
 */
import { useCallback, useEffect, useMemo, useRef, type MutableRefObject } from "react";

import type { CertificateSeries } from "../data/trajectory";
import { formatSignedMeasured } from "../util";
import { MathSpan } from "./MathSpan";
import {
  drawCertificateLane,
  prepareCertificateLanes,
  type CertificateLaneDescriptor,
  type ObligationWorst,
} from "./render/certificateLanes";
import { useCanvasFrameLoop } from "./rollout";

export type CertificateTracesProps = {
  /** The controlled rollout's series values, keyed by series name. */
  series: Record<string, number[]>;
  /** The exported certificate-series records to draw as lanes. */
  records: CertificateSeries[];
  /** Per-obligation worst sampled record (BE-036), for the selected obligation. */
  worstByObligation?: Map<string, ObligationWorst>;
  /** The selected obligation, whose worst margin is surfaced on bearing lanes. */
  selectedObligationId?: string | null;
  /** The shared rollout phase in [0, 1], advanced by `useRolloutPhase`. */
  phaseRef: MutableRefObject<number>;
  /** Whether the rollout animation loop should run. */
  active: boolean;
};

// The intersection-safe-set semantics, stated once above the named barrier
// lanes: a state is safe only where every candidate barrier holds. Both barriers
// stay candidates — this names and relates them, it certifies nothing.
function IntersectionNote(): JSX.Element {
  return (
    <div className="diagnostic-intersection">
      <span className="diagnostic-intersection__lead">
        Safe set is the intersection of these candidate barriers:
      </span>
      <MathSpan latex="\{\max_i B_i \le 0\}" className="diagnostic-intersection__math" />
      <span className="diagnostic-intersection__tail">
        — safe only where every barrier holds. Both stay candidates, not certified.
      </span>
    </div>
  );
}

export function CertificateTraces({
  series,
  records,
  worstByObligation,
  selectedObligationId,
  phaseRef,
  active,
}: CertificateTracesProps): JSX.Element {
  const { lanes, isIntersection } = useMemo(
    () => prepareCertificateLanes(series, records),
    [series, records],
  );
  const laneRefs = useRef<(HTMLCanvasElement | null)[]>([]);

  // The selected obligation's worst record, surfaced only on lanes that bear on
  // it. Null when nothing is selected or this lane does not bear on it.
  const worstFor = useCallback(
    (descriptor: CertificateLaneDescriptor): ObligationWorst | null => {
      if (!selectedObligationId || !descriptor.obligationIds.includes(selectedObligationId)) {
        return null;
      }
      return worstByObligation?.get(selectedObligationId) ?? null;
    },
    [selectedObligationId, worstByObligation],
  );

  const draw = useCallback(() => {
    lanes.forEach((descriptor, index) => {
      const canvas = laneRefs.current[index];
      if (!canvas) {
        return;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        return;
      }
      drawCertificateLane(
        {
          canvas,
          ctx,
          values: descriptor.values,
          baseline: descriptor.baseline,
          amplitude: descriptor.amplitude,
          selectedWorst: worstFor(descriptor),
        },
        phaseRef.current,
      );
    });
  }, [lanes, worstFor, phaseRef]);

  useCanvasFrameLoop(active, draw);
  // Redraw once when the lanes or selection change (covers the paused case).
  useEffect(() => {
    draw();
  }, [draw]);

  if (lanes.length === 0) {
    return <p className="diagnostic-empty">No measured certificate series for this problem.</p>;
  }

  return (
    <div className="verif-certificate-traces">
      {isIntersection && <IntersectionNote />}
      {lanes.map((descriptor, index) => {
        const worst = worstFor(descriptor);
        return (
          <div className="diagnostic" key={descriptor.series}>
            <div className="diagnostic__head">
              <MathSpan latex={descriptor.symbolLatex} className="diagnostic__symbol" />
              {descriptor.captionLatex ? (
                <MathSpan latex={descriptor.captionLatex} className="diagnostic__caption" />
              ) : (
                <span className="diagnostic__caption">{descriptor.captionFallback}</span>
              )}
              {descriptor.barrierLabel && (
                <span className="diagnostic__barrier">{descriptor.barrierLabel}</span>
              )}
            </div>
            <canvas
              ref={(el) => {
                laneRefs.current[index] = el;
              }}
              className="diagnostic__residual diagnostic__certificate"
            />
            {worst && (
              <div
                className="diagnostic__margin"
                title="signed worst sampled margin to the obligation boundary (BE-036) — measured evidence, consistent with the ledger, not a proof"
              >
                <span className="diagnostic__margin-label">worst margin</span>
                <span className="diagnostic__margin-value">{formatSignedMeasured(worst.margin)}</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
