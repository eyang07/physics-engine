/**
 * BottomStrip (FE-065).
 *
 * A single Radix Collapsible strip along the bottom of the verification
 * inspector that holds the rollout playback controls and the full formal detail
 * (dynamics, region definitions, enclosure boxes). It is collapsed by default so
 * the workbench reads as claim → figure → obligations, with the operational
 * controls and the verbose IR record tucked out of the way until asked for.
 *
 * The strip does NOT re-implement playback: to keep behavior byte-for-byte
 * identical, it *relocates* the existing legacy DOM nodes — the vanilla playback
 * controls (`.verif-stage__controls`) and the detail band (`#verificationDetails`)
 * — into its content, so the `PlaybackClock` wiring `main.ts` attached to those
 * exact nodes keeps working untouched. Each node's original home is recorded and
 * restored on unmount (domain switch), so re-entering the domain is idempotent.
 * The content is force-mounted so the relocated nodes persist across open/close;
 * CSS (not React unmounting) hides them while collapsed.
 */
import * as Collapsible from "@radix-ui/react-collapsible";
import { useLayoutEffect, useRef } from "react";

/** The legacy nodes this strip adopts, in display order (playback, then detail). */
const ADOPTED_SELECTORS = [".verif-stage__controls", "#verificationDetails"] as const;

type Relocation = {
  node: HTMLElement;
  parent: HTMLElement | null;
  next: Element | null;
};

export function BottomStrip(): JSX.Element {
  const playbackHostRef = useRef<HTMLDivElement>(null);
  const detailHostRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const hosts = [playbackHostRef.current, detailHostRef.current];
    const relocations: Relocation[] = [];
    ADOPTED_SELECTORS.forEach((selector, index) => {
      const node = document.querySelector<HTMLElement>(selector);
      const host = hosts[index];
      if (!node || !host) {
        return;
      }
      // Record the home before moving so the node can be returned exactly where
      // the static markup put it when the strip unmounts.
      relocations.push({ node, parent: node.parentElement, next: node.nextElementSibling });
      host.appendChild(node);
    });
    return () => {
      for (const { node, parent, next } of relocations) {
        if (parent) {
          parent.insertBefore(node, next);
        }
      }
    };
  }, []);

  return (
    <Collapsible.Root className="verif-bottom-strip">
      <Collapsible.Trigger className="verif-bottom-strip__trigger">
        <span className="verif-bottom-strip__caret" aria-hidden="true" />
        <span className="verif-bottom-strip__label">Rollout playback &amp; full detail</span>
        <span className="verif-bottom-strip__hint">dynamics · regions · enclosures</span>
      </Collapsible.Trigger>
      <Collapsible.Content className="verif-bottom-strip__content" forceMount>
        <div className="verif-bottom-strip__section" ref={playbackHostRef} />
        <div className="verif-bottom-strip__section" ref={detailHostRef} />
      </Collapsible.Content>
    </Collapsible.Root>
  );
}
