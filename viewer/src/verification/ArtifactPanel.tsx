/**
 * ArtifactPanel (FE-061).
 *
 * The artifact/export block at the foot of the claim chain: the backend-agnostic
 * problem IR on its own, and — distinct from it — the self-contained BE-039
 * package bundle (manifest + components) assembled into one file on demand. These
 * are the same artifacts the legacy panel exported; the links resolve to the
 * exact same files, and the bundle is assembled by the shared
 * `assembleVerificationPackageBundle`.
 *
 * Honesty: an export gathers measured evidence and candidates and discharges
 * nothing — the bundle note says so verbatim, matching the rest of the shell.
 */
import { useState } from "react";

import { assembleVerificationPackageBundle, type VerificationProblem } from "../data/verification";
import type { VerificationArtifacts } from "./mount";

// Assemble the package into one JSON file and trigger a download. Fetching the
// components is async, so the control is disabled while in flight; a failure
// leaves an honest console warning rather than a half-written file. (Mirrors the
// legacy panel's downloadPackageBundle.)
async function downloadPackageBundle(packagePath: string, problemId: string): Promise<void> {
  const bundle = await assembleVerificationPackageBundle(packagePath);
  const blob = new Blob([`${JSON.stringify(bundle, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${problemId}.verification-package.json`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export type ArtifactPanelProps = {
  problem: VerificationProblem;
  artifacts: VerificationArtifacts | null;
};

export function ArtifactPanel({ problem, artifacts }: ArtifactPanelProps): JSX.Element | null {
  const [downloading, setDownloading] = useState(false);

  const irPath = artifacts?.irPath ?? null;
  const manifest = artifacts?.packageManifest ?? null;
  const packagePath = artifacts?.packagePath ?? null;
  const hasPackage = Boolean(manifest && packagePath);

  // Nothing published: omit the panel entirely rather than show empty links.
  if (!irPath && !hasPackage) {
    return null;
  }

  const onDownload = (): void => {
    if (!packagePath || downloading) {
      return;
    }
    setDownloading(true);
    void downloadPackageBundle(packagePath, problem.id)
      .catch((error) => console.warn("Verification package download failed:", error))
      .finally(() => setDownloading(false));
  };

  return (
    <section className="vf-artifacts" aria-label="Artifacts">
      <header className="vf-artifacts__head">
        <h2 className="vf-artifacts__title">Artifacts</h2>
      </header>

      <div className="vf-artifacts__links">
        {irPath && (
          <a
            className="vf-artifacts__ir"
            href={irPath}
            download={`${problem.id}.verification-problem.json`}
          >
            Problem (IR)
          </a>
        )}

        {hasPackage && manifest && (
          <button
            type="button"
            className="vf-artifacts__package"
            onClick={onDownload}
            disabled={downloading}
            title={manifest.components.map((c) => `${c.kind} — ${c.path}`).join("\n")}
          >
            {downloading
              ? "Assembling package…"
              : `Package bundle (${manifest.components.length})`}
          </button>
        )}
      </div>

      <p className="vf-artifacts__note">
        One self-contained bundle (manifest + components) — gathers measured evidence and
        candidates; discharges nothing.
      </p>
    </section>
  );
}
