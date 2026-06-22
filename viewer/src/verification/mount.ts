/**
 * Mount/unmount controller for the Verification-domain React root.
 *
 * `main.ts` calls these as the active domain is switched: the root is created
 * when the Verification domain is shown and torn down when leaving it, so React
 * never runs (and never reconciles) while the Systems domain is active. The root
 * lives in its own container appended inside `#verificationDomain` rather than
 * over the host element directly, so the legacy vanilla verification panel —
 * still a child of `#verificationDomain` — keeps rendering untouched (FE-055).
 */
import { createElement } from "react";
import { createRoot, type Root } from "react-dom/client";

import { VerificationApp } from "./VerificationApp";
import "./verification.css";

const CONTAINER_ID = "verificationReactRoot";

let root: Root | null = null;
let container: HTMLElement | null = null;

export function mountVerificationApp(host: HTMLElement): void {
  if (root) {
    return;
  }
  container = document.createElement("div");
  container.id = CONTAINER_ID;
  host.appendChild(container);
  root = createRoot(container);
  root.render(createElement(VerificationApp));
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
