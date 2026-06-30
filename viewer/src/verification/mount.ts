/**
 * Mount/unmount controller for the Verification-domain React root.
 *
 * `main.ts` calls these as the active domain is switched: the root is created
 * when the Verification domain is shown and torn down when leaving it, so React
 * never runs (and never reconciles) while the Systems domain is active. The root
 * lives in its own container inside `#verificationDomain` rather than over the
 * host element directly, so the legacy vanilla verification panel — still a child
 * of `#verificationDomain` — keeps rendering untouched (FE-055). The container is
 * prepended so the FE-058 top bar reads above the legacy dossier.
 *
 * The host feeds the active problem in via `setVerificationProblem`; the latest
 * problem is retained across unmount so re-entering the domain re-renders it.
 */
import { createElement } from "react";
import { createRoot, type Root } from "react-dom/client";

import { VerificationApp } from "./VerificationApp";
import type { PackageManifest, VerificationProblem } from "../data/verification";
import "./verification.css";

/**
 * The downloadable artifacts the host published for the active problem: the
 * backend-agnostic IR file and, when the export bundled one, the self-contained
 * package (its manifest and the path to assemble the bundle from). The React
 * shell renders these as the artifact panel; missing ones simply omit.
 */
export interface VerificationArtifacts {
  irPath: string | null;
  packagePath: string | null;
  packageManifest: PackageManifest | null;
}

const CONTAINER_ID = "verificationReactRoot";

let root: Root | null = null;
let container: HTMLElement | null = null;
let currentProblem: VerificationProblem | null = null;
let currentArtifacts: VerificationArtifacts | null = null;

function renderRoot(): void {
  if (root) {
    root.render(
      createElement(VerificationApp, { problem: currentProblem, artifacts: currentArtifacts }),
    );
  }
}

export function mountVerificationApp(host: HTMLElement): void {
  if (root) {
    return;
  }
  container = document.createElement("div");
  container.id = CONTAINER_ID;
  host.prepend(container);
  root = createRoot(container);
  renderRoot();
}

export function unmountVerificationApp(): void {
  if (root) {
    root.unmount();
    root = null;
  }
  if (container) {
    container.remove();
    container = null;
  }
}

/**
 * Set the active verification problem (and its downloadable artifacts) the React
 * shell renders. Safe to call while the root is unmounted (Systems domain
 * active): the values are retained and drawn on the next mount. Passing no
 * artifacts clears them, so an error/empty state shows no stale export links.
 */
export function setVerificationProblem(
  problem: VerificationProblem | null,
  artifacts: VerificationArtifacts | null = null,
): void {
  currentProblem = problem;
  currentArtifacts = artifacts;
  renderRoot();
}
