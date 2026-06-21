import "katex/dist/katex.min.css";
import { ThreeScene, type ThreeMode, type Trajectory } from "./threeScene";
import { theme } from "./design/theme";
import {
  loadManifest,
  type ManifestLens,
  type ManifestNormalModes,
  type ManifestParameterVariant,
  type SystemManifest,
} from "./data/manifest";
import { StaticSource } from "./data/source";
import { drawEffectivePotentialScene } from "./effectivePotentialCanvas";
import { PlaybackClock, sampleTrajectory, trajectoryDuration } from "./playback";
import {
  computePendulumBounds,
  drawPendulumScene,
  drawStageBackground,
  type Bounds,
} from "./pendulumCanvas";
import { drawPhaseScene, drawPotentialContourScene, drawPotentialScene } from "./phasePotentialCanvas";
import { StructurePanel } from "./structurePanel";
import { DiagnosticsPanel } from "./diagnosticsPanel";
import { drawWavefrontScene } from "./wavefrontCanvas";
import { drawPoincareSectionScene } from "./poincareSectionCanvas";
import { drawNormalModeScene } from "./normalModeCanvas";
import { drawScalarFieldScene, fieldPlotArea } from "./scalarFieldCanvas";
import { drawVectorFieldOverlay, robustMagnitudeMax } from "./vectorFieldCanvas";
import { VerificationPanel } from "./verificationPanel";
import { VerificationStage } from "./verificationStage";
import { resolveRendererSurface } from "./rendererRegistry";
import { createScalarLegend } from "./scalarLegend";
import { createBodyLegend } from "./bodyLegend";
import { bodyColor, magma, scalarScale, viridis } from "./design/colormaps";
import { fieldLines, nBodyConfig, scalarField, vectorField } from "./data/trajectory";
import {
  loadVerificationAdapterStubs,
  loadVerificationIndex,
  loadVerificationPackageIndex,
  loadVerificationPackageManifest,
  loadVerificationProblem,
  type PackageIndexEntry,
  type PackageRegime,
  type VerificationProblem,
  type VerificationProblemSummary,
} from "./data/verification";
import "./styles.css";

type CanvasMode =
  | "pendulumMotionPhase"
  | "effectivePotential"
  | "pendulumPotential"
  | "uniformGravityVerticalPhase"
  | "uniformGravityPotential"
  | "idealSpringPhase"
  | "idealSpringPotential"
  | "keplerRadialPhase"
  | "beadHoopPhase"
  | "beadHoopPotential"
  | "henonHeilesPhase"
  | "henonHeilesPotential"
  | "henonHeilesPoincare"
  | "variableSpeedWavefront"
  | "electromagneticField";

function requireElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing required element: ${selector}`);
  }
  return element;
}

const systemsDomain = requireElement<HTMLElement>("#systemsDomain");
const verificationDomain = requireElement<HTMLElement>("#verificationDomain");
const domainSystemsButton = requireElement<HTMLButtonElement>("#domainSystems");
const domainVerificationButton = requireElement<HTMLButtonElement>("#domainVerification");
const aboutButton = requireElement<HTMLButtonElement>("#aboutButton");
const aboutDialog = requireElement<HTMLDialogElement>("#aboutDialog");
const aboutClose = requireElement<HTMLButtonElement>("#aboutClose");
const systemCatalog = requireElement<HTMLElement>("#systemCatalog");
const verificationCatalog = requireElement<HTMLElement>("#verificationCatalog");
const verificationMasthead = requireElement<HTMLElement>("#verificationMasthead");
const verificationSummary = requireElement<HTMLElement>("#verificationSummary");
const verificationDetails = requireElement<HTMLElement>("#verificationDetails");
const verificationFigureCaption = requireElement<HTMLElement>("#verificationFigureCaption");
const verificationCanvas = requireElement<HTMLCanvasElement>("#verificationCanvas");
const verificationPlayButton = requireElement<HTMLButtonElement>("#verificationPlayButton");
const verificationSpeedControl = requireElement<HTMLInputElement>("#verificationSpeedControl");
const verificationCertificateLanes = requireElement<HTMLElement>("#verificationCertificateLanes");
const stage = requireElement<HTMLElement>("#systemsDomain .stage");
const canvas = requireElement<HTMLCanvasElement>("#scene");
const threeCanvas = requireElement<HTMLCanvasElement>("#hamiltonianScene");
const systemTitle = requireElement<HTMLElement>("#systemTitle");
const systemSelect = requireElement<HTMLSelectElement>("#systemSelect");
const visualizationModes = requireElement<HTMLElement>("#visualizationModes");
const variantSection = requireElement<HTMLElement>("#variantSection");
const variantModes = requireElement<HTMLElement>("#variantModes");
const modeControlsSection = requireElement<HTMLElement>("#modeControlsSection");
const modeSelector = requireElement<HTMLElement>("#modeSelector");
const modeBlend = requireElement<HTMLInputElement>("#modeBlend");
const modeBlendLabel = requireElement<HTMLElement>("#modeBlendLabel");
const playButton = requireElement<HTMLButtonElement>("#playButton");
const fitToSystem = requireElement<HTMLButtonElement>("#fitToSystem");
const speedControl = requireElement<HTMLInputElement>("#speedControl");
const principlesPanel = requireElement<HTMLElement>("#principles");
const invariantsPanel = requireElement<HTMLElement>("#invariants");
const parametersPanel = requireElement<HTMLElement>("#parameters");
const loopPhaseArc = requireElement<SVGCircleElement>("#loopPhaseArc");
const diagnosticsSection = requireElement<HTMLElement>("#diagnosticsSection");
const diagnosticsPanel_ = requireElement<HTMLElement>("#diagnostics");

const context = canvas.getContext("2d");
if (!context) {
  throw new Error("Canvas 2D context is unavailable.");
}
const ctx: CanvasRenderingContext2D = context;
const threeScene = new ThreeScene(threeCanvas);

// One shared scalar legend overlay on the mechanics stage (FE-038). Scalar
// lenses (potential field today; field magnitude / curvature / intensity later)
// reveal it with their own caption; every other lens keeps it hidden.
const scalarLegend = createScalarLegend({ title: "potential", low: "low", high: "high" });
stage.appendChild(scalarLegend.element);

// A second scalar legend for the vector-field lens (FE-045): the glyph quiver is
// colored by field magnitude through its own colormap, so it carries its own key
// in the opposite corner from the scalar (potential) legend.
const magnitudeLegend = createScalarLegend({
  title: "field magnitude",
  colormap: magma,
  low: "weak",
  high: "strong",
  corner: "bottom-right",
});
stage.appendChild(magnitudeLegend.element);

// One shared categorical body legend overlay (FE-042) keyed to the per-body
// orbit-trail palette; the N-body orbit lens reveals it, others keep it hidden.
const bodyLegend = createBodyLegend({ title: "bodies", corner: "top-left" });
stage.appendChild(bodyLegend.element);

const trajectorySource = new StaticSource();
const structurePanel = new StructurePanel(principlesPanel, invariantsPanel, parametersPanel, loopPhaseArc);
const diagnosticsPanel = new DiagnosticsPanel(diagnosticsSection, diagnosticsPanel_);
const verificationPanel = new VerificationPanel(
  verificationMasthead,
  verificationSummary,
  verificationDetails,
);
const verificationStage = new VerificationStage(
  verificationCanvas,
  verificationPlayButton,
  verificationSpeedControl,
  verificationCertificateLanes,
);
// Selecting an obligation's evidence in the document emphasizes the certificate
// lanes that bear on it (both live in the Verification domain).
verificationPanel.onEvidenceSelect = (obligationId) =>
  verificationStage.emphasizeCertificates(obligationId);
// The reverse direction: selecting a certificate lane emphasizes the obligations
// it bears on in the document.
verificationStage.setOnCertificateSelect((obligationIds) =>
  verificationPanel.emphasizeObligations(obligationIds),
);
const clock = new PlaybackClock();

type Domain = "systems" | "verification";
let activeDomain: Domain = "systems";
let examples: SystemManifest[] = [];
let lensById = new Map<string, ManifestLens>();
let selectedExample: SystemManifest | null = null;
let selectedVisualization: ManifestLens | null = null;
let selectedVariant: ManifestParameterVariant | null = null;
// The selected normal mode for the normal-mode lens (0-based, ascending freq).
let selectedModeIndex = 0;
let trajectory: Trajectory | null = null;
let pendulumBounds: Bounds | null = null;
// Monotonic guard so a slow trajectory load can't overwrite a newer selection.
let loadToken = 0;
let verificationProblems: VerificationProblemSummary[] = [];
// The package discovery index per problem id (BE-047): the published listing the
// catalog is grounded in (model, status, counts, regime). Empty when the index
// is absent, in which case the catalog degrades to the per-example viewer index.
let verificationPackageIndex = new Map<string, PackageIndexEntry>();
let selectedProblemId: string | null = null;

function syncPlayButton() {
  // Playback loops continuously, so the control is only ever Play/Pause.
  playButton.textContent = clock.playing ? "Pause" : "Play";
}

playButton.addEventListener("click", () => {
  clock.toggle();
  syncPlayButton();
});

fitToSystem.addEventListener("click", () => {
  threeScene.resetCamera();
});

// Update the superposition caption as the blend scrub moves (the frame loop
// reads the slider value directly for the animation).
modeBlend.addEventListener("input", () => {
  const modes = activeNormalModes();
  if (modes) {
    updateModeBlendLabel(modes);
  }
});

domainSystemsButton.addEventListener("click", () => {
  setDomain("systems");
});

domainVerificationButton.addEventListener("click", () => {
  setDomain("verification");
});

aboutButton.addEventListener("click", () => {
  aboutDialog.showModal();
});

aboutClose.addEventListener("click", () => {
  aboutDialog.close();
});

systemSelect.addEventListener("change", () => {
  void selectExample(systemSelect.value);
});

function isCanvasMode(id: string): id is CanvasMode {
  return resolveRendererSurface(id) === "2d";
}

function isThreeMode(id: string): id is ThreeMode {
  return resolveRendererSurface(id) === "3d";
}

// A lens whose primitive does not exist yet (a new backend hint the viewer can't
// draw): routed to a graceful placeholder on the 2D stage, never a blank scene.
function isFallbackMode(id: string): boolean {
  return resolveRendererSurface(id) === "fallback";
}

// Turn an exported scalar-field name ("electricPotential") into a qualitative
// legend caption ("electric potential"). The legend stays decimal-free; this
// only humanizes the channel name the field was exported under.
function humanizeFieldName(name: string): string {
  return name
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_-]+/g, " ")
    .trim()
    .toLowerCase();
}

function lensFor(id: string): ManifestLens {
  const lens = lensById.get(id);
  if (!lens) {
    throw new Error(`System references unknown lens: ${id}`);
  }
  return lens;
}

function populateSystemSelect() {
  systemSelect.replaceChildren();
  examples.forEach((example) => {
    const option = document.createElement("option");
    option.value = example.id;
    option.textContent = example.title;
    systemSelect.append(option);
  });
  if (selectedExample) {
    systemSelect.value = selectedExample.id;
  }
}

function renderSystemCatalog() {
  systemCatalog.replaceChildren();
  examples.forEach((example) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "catalog-item";
    button.dataset.systemId = example.id;
    button.classList.toggle("catalog-item--active", example.id === selectedExample?.id);
    button.innerHTML = `
      <span class="catalog-item__category">${example.category}</span>
      <strong>${example.title}</strong>
    `;
    // The catalog rail swaps the stage directly — no separate gallery page.
    button.addEventListener("click", () => {
      void selectExample(example.id);
    });
    systemCatalog.append(button);
  });
}

function updateCatalogActive() {
  systemCatalog.querySelectorAll<HTMLButtonElement>(".catalog-item").forEach((item) => {
    item.classList.toggle("catalog-item--active", item.dataset.systemId === selectedExample?.id);
  });
}

function renderVerificationCatalog() {
  verificationCatalog.replaceChildren();
  verificationProblems.forEach((problem) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "catalog-item";
    button.dataset.problemId = problem.id;
    button.classList.toggle("catalog-item--active", problem.id === selectedProblemId);

    // Ground each entry's model/status/counts in the published discovery index
    // when available, degrading to the per-example viewer summary otherwise.
    const entry = verificationPackageIndex.get(problem.id);
    const model = entry?.model ?? problem.model;
    const status = entry?.status ?? problem.status;
    const itemCounts = entry?.counts ?? problem.counts;

    const category = document.createElement("span");
    category.className = "catalog-item__category";
    category.textContent = model ?? status;

    const title = document.createElement("strong");
    title.textContent = problem.name;

    // The full region/obligation/candidate counts let the workbench be scanned
    // without opening each problem; a status chip names the listed rigor.
    const counts = document.createElement("span");
    counts.className = "catalog-item__counts";
    counts.append(
      countBadge("regions", itemCounts.regions),
      countBadge("obligations", itemCounts.obligations),
      countBadge("candidates", itemCounts.candidates),
      statusChip(status),
    );

    button.append(category, title, counts);
    // The Tier/regime badge (BE-054) lets a reader tell a nominal package from a
    // disturbance-robust one without opening it. Only shown when the discovery
    // index carries the descriptor; it claims nothing beyond the listed rigor.
    if (entry?.regime) {
      button.append(regimeBadge(entry.regime));
    }
    button.addEventListener("click", () => {
      void selectVerificationProblem(problem.id);
    });
    verificationCatalog.append(button);
  });
}

// The package status as a small chip (e.g. "candidate"), read from the listing —
// it names the rigor of the listed package, nothing more.
function statusChip(status: string): HTMLSpanElement {
  const chip = document.createElement("span");
  chip.className = "catalog-item__status";
  chip.dataset.status = status;
  chip.textContent = status;
  return chip;
}

function countBadge(label: string, value: number): HTMLSpanElement {
  const badge = document.createElement("span");
  badge.className = "catalog-item__count";
  badge.dataset.count = label;
  badge.textContent = `${value} ${label}`;
  return badge;
}

// The catalog Tier/regime badge: "robust" for a disturbance-robust (Tier-3)
// package, "nominal" otherwise — read straight from the index descriptor, never
// claiming more than the listed package's rigor.
function regimeBadge(regime: PackageRegime): HTMLSpanElement {
  const robust = regime.kind === "disturbance-robust";
  const badge = document.createElement("span");
  badge.className = `catalog-item__regime catalog-item__regime--${
    robust ? "robust" : "nominal"
  }`;
  badge.dataset.regime = regime.kind;
  badge.textContent = robust ? "robust" : "nominal";
  badge.title = robust
    ? "disturbance-robust (Tier-3): obligations quantified over a wind box — still external-required, not discharged"
    : "nominal (Tier-1/2): no disturbance channel";
  return badge;
}

function updateVerificationCatalogActive() {
  verificationCatalog.querySelectorAll<HTMLButtonElement>(".catalog-item").forEach((item) => {
    item.classList.toggle("catalog-item--active", item.dataset.problemId === selectedProblemId);
  });
}

async function selectVerificationProblem(problemId: string) {
  const summary = verificationProblems.find((problem) => problem.id === problemId);
  if (!summary) {
    return;
  }
  selectedProblemId = summary.id;
  updateVerificationCatalogActive();
  try {
    // The package manifest is an optional, self-contained bundle index; a
    // missing one resolves to null so the view simply omits the package export.
    const [problem, manifest] = await Promise.all([
      loadVerificationProblem(summary.dataPath),
      summary.packagePath
        ? loadVerificationPackageManifest(summary.packagePath)
        : Promise.resolve(null),
    ]);
    // The non-discharging adapter stubs are an optional package component; load
    // them only when a manifest indexes them, resolving to null otherwise.
    const pkg =
      manifest && summary.packagePath
        ? { manifest, path: summary.packagePath }
        : null;
    const stubs = pkg ? await loadVerificationAdapterStubs(pkg.path, pkg.manifest) : null;
    // The open problem's Tier/regime from the discovery index, when listed.
    const regime = verificationPackageIndex.get(summary.id)?.regime ?? null;
    // A stale click (the user moved on) should not overwrite the newer problem.
    if (selectedProblemId === summary.id) {
      verificationStage.show(problem);
      verificationPanel.render(problem, summary.irPath, pkg, stubs, regime);
      setFigureCaption(problem);
    }
  } catch (error) {
    console.warn("Verification problem unavailable:", error);
    verificationStage.clear();
    verificationFigureCaption.textContent = "";
    verificationPanel.renderEmpty(
      `Could not load ${summary.name}. Regenerate with "python -m scripts.generate_verification_problems".`,
    );
  }
}

// The figure caption: a typeset plate label naming the state-space axes and the
// safe set the rollout must stay within. Derived from the problem's own axes and
// region roles — the figure renders the same data, this only names it.
function setFigureCaption(problem: VerificationProblem) {
  const axes = problem.trajectory?.stateNames ?? [];
  const plane = axes.length >= 2 ? `(${axes[0]}, ${axes[1]})` : "state";
  const hasSafe = problem.regions.some((region) => region.role === "safe");
  verificationFigureCaption.textContent = hasSafe
    ? `Figure — state space ${plane}; safe set 𝒮 shaded, controlled rollout in ink.`
    : `Figure — state space ${plane}; controlled rollout in ink.`;
}

function renderVisualizationButtons() {
  visualizationModes.replaceChildren();
  if (!selectedExample || !selectedVisualization) {
    return;
  }
  const activeLensId = selectedVisualization.id;
  selectedExample.lenses.map(lensFor).forEach((visualization) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mode-switch__button";
    button.textContent = visualization.title;
    button.classList.toggle("mode-switch__button--active", visualization.id === activeLensId);
    button.addEventListener("click", () => {
      selectedVisualization = visualization;
      applyVisualization();
      renderVisualizationButtons();
    });
    visualizationModes.append(button);
  });
}

// The variant whose data matches the system's default export, or the first one
// — the family member shown when a system is first selected.
function defaultVariant(example: SystemManifest): ManifestParameterVariant | null {
  const variants = example.variants ?? [];
  if (variants.length === 0) {
    return null;
  }
  return variants.find((variant) => variant.dataPath === example.dataPath) ?? variants[0];
}

function renderVariantButtons() {
  variantModes.replaceChildren();
  const variants = selectedExample?.variants ?? [];
  variantSection.hidden = variants.length === 0;
  if (variants.length === 0) {
    return;
  }
  variants.forEach((variant) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mode-switch__button";
    button.textContent = variant.label;
    button.classList.toggle("mode-switch__button--active", variant.id === selectedVariant?.id);
    button.addEventListener("click", () => {
      if (variant.id === selectedVariant?.id) {
        return;
      }
      selectedVariant = variant;
      renderVariantButtons();
      void loadAndRender();
    });
    variantModes.append(button);
  });
}

// The normal-mode lens (FE-043) exposes a mode selector and a superposition
// scrub. The selector picks one exported mode shape; the blend slider scrubs a
// superposition toward the next mode (their two frequencies beat). Frequencies
// stay qualitative — buttons are numbered low→high, never labelled with decimals.
function activeNormalModes(): ManifestNormalModes | null {
  if (!selectedExample?.normalModes || selectedVisualization?.kind !== "normal-modes") {
    return null;
  }
  return selectedExample.normalModes;
}

function updateModeBlendLabel(modes: ManifestNormalModes) {
  const count = modes.coordinates.length;
  const blend = Number(modeBlend.value);
  if (blend > 0.001) {
    const next = ((selectedModeIndex + 1) % count) + 1;
    modeBlendLabel.textContent = `superpose → mode ${next}`;
  } else {
    modeBlendLabel.textContent = "superpose";
  }
}

function renderModeControls() {
  const modes = activeNormalModes();
  modeControlsSection.hidden = modes === null;
  if (!modes) {
    return;
  }
  if (selectedModeIndex >= modes.frequencies.length) {
    selectedModeIndex = 0;
  }
  modeSelector.replaceChildren();
  modes.frequencies.forEach((_frequency, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mode-switch__button";
    button.textContent = `Mode ${index + 1}`;
    button.classList.toggle("mode-switch__button--active", index === selectedModeIndex);
    button.addEventListener("click", () => {
      if (index === selectedModeIndex) {
        return;
      }
      selectedModeIndex = index;
      // Picking a mode shows it pure; the scrub then superposes from there.
      modeBlend.value = "0";
      renderModeControls();
    });
    modeSelector.append(button);
  });
  updateModeBlendLabel(modes);
}

function loadActiveTrajectory(): Promise<Trajectory> {
  // Behind the StaticSource seam: a future GeneratedSource (Python server)
  // implements the same interface, so parameter-driven generation can drop in
  // here without changing the call site. A selected variant loads its own
  // exported data file, cached separately under a per-variant id.
  const example = selectedExample!;
  if (selectedVariant) {
    return trajectorySource.get({
      id: `${example.id}:${selectedVariant.id}`,
      dataPath: selectedVariant.dataPath,
    });
  }
  return trajectorySource.get(example);
}

function setCanvasMode(mode: "2d" | "3d") {
  const is2d = mode === "2d";
  canvas.classList.toggle("stage__canvas--active", is2d);
  threeCanvas.classList.toggle("stage__canvas--active", !is2d);
  threeScene.setActive(!is2d);
  // The fit-to-system control only applies to the orbit-controlled Three.js
  // scenes; the 2D canvas lenses have no camera to reset.
  fitToSystem.hidden = is2d;
}

function setDomain(domain: Domain) {
  activeDomain = domain;
  const systemsActive = domain === "systems";
  systemsDomain.classList.toggle("domain--active", systemsActive);
  systemsDomain.hidden = !systemsActive;
  verificationDomain.classList.toggle("domain--active", !systemsActive);
  verificationDomain.hidden = systemsActive;
  domainSystemsButton.classList.toggle("domain-switch__button--active", systemsActive);
  domainVerificationButton.classList.toggle("domain-switch__button--active", !systemsActive);
  // The Three.js scene only renders inside the Systems domain, and only when the
  // active lens is a Three mode; otherwise it stays inactive to spare the GPU.
  threeScene.setActive(
    systemsActive && selectedVisualization !== null && isThreeMode(selectedVisualization.id),
  );
  verificationStage.setActive(!systemsActive);
  if (systemsActive) {
    resize2dCanvas();
    threeScene.resize();
  } else if (selectedProblemId === null && verificationProblems.length > 0) {
    // Lazily load the first problem the first time the domain is opened.
    void selectVerificationProblem(verificationProblems[0].id);
  }
}

function applyVisualization() {
  if (!trajectory || !selectedVisualization) {
    return;
  }

  if (isThreeMode(selectedVisualization.id)) {
    setCanvasMode("3d");
    threeScene.setVisualization(selectedVisualization.id, trajectory);
  } else {
    // Both the 2D lenses and the fallback placeholder draw on the 2D canvas.
    setCanvasMode("2d");
  }

  // The scalar legend captions every scalar field the viewer paints: the
  // potential contour and the FE-044 scalar-field lens (an exported potential /
  // curvature / intensity grid). It stays hidden for non-scalar lenses rather
  // than leaving a stale key.
  if (selectedVisualization.kind === "potential-contour") {
    scalarLegend.setColormap(viridis, "potential", "low", "high");
    scalarLegend.show();
  } else if (selectedVisualization.kind === "static-fields") {
    const field = scalarField(trajectory);
    if (field) {
      scalarLegend.setColormap(viridis, humanizeFieldName(field.name), "low", "high");
      scalarLegend.show();
    } else {
      scalarLegend.hide();
    }
  } else {
    scalarLegend.hide();
  }

  // The field-magnitude legend keys the FE-045 glyph quiver; show it only when the
  // static-fields lens has an exported vector field to color.
  if (selectedVisualization.kind === "static-fields" && vectorField(trajectory)) {
    magnitudeLegend.show();
  } else {
    magnitudeLegend.hide();
  }

  // The body legend keys the N-body orbit-trail colors; it shows only when the
  // active trajectory carries an N-body orbit configuration.
  const nBody = nBodyConfig(trajectory);
  if (nBody) {
    bodyLegend.setEntries(
      Array.from({ length: nBody.bodyCount }, (_value, index) => ({
        label: `Body ${index + 1}`,
        color: bodyColor(index),
      })),
    );
    bodyLegend.show();
  } else {
    bodyLegend.hide();
  }

  // The normal-mode selector + superposition scrub show only for the mode lens.
  renderModeControls();
}

async function selectExample(exampleId: string) {
  const nextExample = examples.find((example) => example.id === exampleId) ?? examples[0];
  if (!nextExample) {
    return;
  }
  selectedExample = nextExample;
  selectedVisualization = lensFor(nextExample.lenses[0]);
  selectedVariant = defaultVariant(nextExample);
  selectedModeIndex = 0;
  modeBlend.value = "0";
  systemTitle.textContent = nextExample.title;
  systemSelect.value = nextExample.id;
  updateCatalogActive();
  renderVisualizationButtons();
  renderVariantButtons();
  await loadAndRender();
}

// Load the active system/variant trajectory and refresh every panel. Shared by
// system selection and variant switching; the load guard drops a stale result
// when a newer selection has already started loading.
async function loadAndRender() {
  if (!selectedExample) {
    return;
  }
  const example = selectedExample;
  const token = ++loadToken;
  clock.reset();
  syncPlayButton();
  structurePanel.clear();
  diagnosticsPanel.clear();

  const loaded = await loadActiveTrajectory();
  if (token !== loadToken) {
    return;
  }
  trajectory = loaded;
  pendulumBounds = example.id === "pendulum" ? computePendulumBounds(loaded) : null;
  applyVisualization();
  void structurePanel.show(example.id, loaded);
  diagnosticsPanel.show(loaded);
}

function resize2dCanvas() {
  // Size the 2D canvas for both the canvas lenses and the fallback placeholder
  // (anything that is not a Three.js scene).
  if (!selectedVisualization || isThreeMode(selectedVisualization.id)) {
    return;
  }
  const pixelRatio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * pixelRatio));
  canvas.height = Math.max(1, Math.floor(height * pixelRatio));
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
}

window.addEventListener("resize", () => {
  resize2dCanvas();
  threeScene.resize();
  verificationStage.resize();
});

// A graceful placeholder for a lens whose viewer primitive does not exist yet:
// the backend already exports the data, the rendering primitive is on the way.
// Drawn instead of a blank stage so the new physics systems read honestly.
function drawFallbackStage(title: string, width: number, height: number) {
  drawStageBackground(ctx, width, height);
  ctx.save();
  ctx.textAlign = "center";
  ctx.fillStyle = theme.textPrimary;
  ctx.font = '18px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText(title, width / 2, height / 2 - 10);
  ctx.fillStyle = theme.textMuted;
  ctx.font = '14px "IBM Plex Sans", system-ui, sans-serif';
  ctx.fillText("Visualization coming soon", width / 2, height / 2 + 16);
  ctx.restore();
}

function render(now: number) {
  // The stage only renders inside the Systems domain; the Verification domain is
  // static markup, so we keep pumping the frame loop without drawing.
  if (activeDomain !== "systems") {
    requestAnimationFrame(render);
    return;
  }

  if (!trajectory || !selectedVisualization) {
    resize2dCanvas();
    drawStageBackground(ctx, canvas.clientWidth, canvas.clientHeight);
    ctx.fillStyle = theme.textMuted;
    ctx.font = '16px "IBM Plex Sans", system-ui, sans-serif';
    ctx.fillText("Loading example data...", 32, 48);
    requestAnimationFrame(render);
    return;
  }

  const time = clock.advance(now, Number(speedControl.value));
  const duration = trajectoryDuration(trajectory);
  // Loop continuously: wrap the elapsed time so a finished run restarts instead
  // of dead-ending at the final sample.
  const current = sampleTrajectory(trajectory, duration > 0 ? time % duration : time);
  if (isFallbackMode(selectedVisualization.id)) {
    resize2dCanvas();
    drawFallbackStage(selectedVisualization.title, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedVisualization.id === "pendulumMotionPhase") {
    resize2dCanvas();
    drawPendulumScene(ctx, trajectory, pendulumBounds, current, canvas.clientWidth, canvas.clientHeight);
  } else if (isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "effective-potential") {
    drawEffectivePotentialScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedExample && isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "configuration-phase") {
    drawPhaseScene(ctx, trajectory, selectedExample, selectedVisualization, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedExample && isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "potential-contour") {
    drawPotentialContourScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedExample && isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "potential-energy") {
    drawPotentialScene(ctx, trajectory, selectedExample, selectedVisualization, current, canvas.clientWidth, canvas.clientHeight);
  } else if (isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "static-fields") {
    const field = scalarField(trajectory);
    const vfield = vectorField(trajectory);
    if (field || vfield) {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (field) {
        drawScalarFieldScene(ctx, field, width, height);
      }
      // The vector field (glyphs + field lines) overlays the scalar heatmap on
      // the shared plot area, so the electric field rides its own potential.
      if (vfield) {
        const magnitudeScale = scalarScale(magma, [0, robustMagnitudeMax(vfield)]);
        drawVectorFieldOverlay(ctx, {
          field: vfield,
          lines: fieldLines(trajectory),
          magnitudeScale,
          area: fieldPlotArea(width, height),
        });
      }
    } else {
      resize2dCanvas();
      drawFallbackStage(selectedVisualization.title, canvas.clientWidth, canvas.clientHeight);
    }
  } else if (selectedVisualization.id === "variableSpeedWavefront") {
    drawWavefrontScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedVisualization.id === "henonHeilesPoincare") {
    drawPoincareSectionScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedVisualization.kind === "normal-modes" && selectedExample?.normalModes) {
    resize2dCanvas();
    drawNormalModeScene(
      ctx,
      selectedExample.normalModes,
      { modeIndex: selectedModeIndex, blend: Number(modeBlend.value), time },
      canvas.clientWidth,
      canvas.clientHeight,
    );
  } else {
    threeScene.render(current.state, time, current.index);
  }

  structurePanel.update(current.phase);
  diagnosticsPanel.update(current.phase);
  requestAnimationFrame(render);
}

setDomain("systems");

async function initialize() {
  try {
    const manifest = await loadManifest();
    examples = manifest.systems;
    lensById = new Map(manifest.lenses.map((lens) => [lens.id, lens]));
    selectedExample = examples[0] ?? null;
    selectedVisualization = selectedExample ? lensFor(selectedExample.lenses[0]) : null;
    populateSystemSelect();
    renderSystemCatalog();
    // Load the verification index before the first system render so a system's
    // linked-problem cross-link and region geometry resolve on first paint.
    await initializeVerification();
    // Boot straight into the workbench: render the first system's stage
    // immediately instead of waiting behind a splash gate.
    if (selectedExample) {
      await selectExample(selectedExample.id);
    }
  } catch (error) {
    console.warn("Manifest preload failed:", error);
  }
}

async function initializeVerification() {
  // The discovery index grounds the catalog (model, status, counts, regime),
  // joined by problem id; a missing index degrades to the per-example viewer
  // index.
  const [index, packageIndex] = await Promise.all([
    loadVerificationIndex(),
    loadVerificationPackageIndex(),
  ]);
  verificationProblems = index.problems;
  verificationPackageIndex = packageIndex;
  renderVerificationCatalog();
  if (verificationProblems.length === 0) {
    verificationStage.clear();
    verificationPanel.renderEmpty(
      'No verification problems found. Generate them with "python -m scripts.generate_verification_problems".',
    );
  }
}

void initialize();

requestAnimationFrame(render);
