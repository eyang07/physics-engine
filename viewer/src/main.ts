import "katex/dist/katex.min.css";
import { ThreeScene, type ThreeMode, type Trajectory } from "./threeScene";
import { theme } from "./design/theme";
import {
  loadManifest,
  type ManifestLens,
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
import { VerificationPanel } from "./verificationPanel";
import { VerificationStage } from "./verificationStage";
import {
  loadVerificationIndex,
  loadVerificationProblem,
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
  | "variableSpeedWavefront";

const CANVAS_MODE_IDS = new Set<string>([
  "pendulumMotionPhase",
  "effectivePotential",
  "pendulumPotential",
  "uniformGravityVerticalPhase",
  "uniformGravityPotential",
  "idealSpringPhase",
  "idealSpringPotential",
  "keplerRadialPhase",
  "beadHoopPhase",
  "beadHoopPotential",
  "henonHeilesPhase",
  "henonHeilesPotential",
  "henonHeilesPoincare",
  "variableSpeedWavefront",
]);

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
const verificationContent = requireElement<HTMLElement>("#verificationContent");
const verificationCanvas = requireElement<HTMLCanvasElement>("#verificationCanvas");
const verificationPlayButton = requireElement<HTMLButtonElement>("#verificationPlayButton");
const verificationSpeedControl = requireElement<HTMLInputElement>("#verificationSpeedControl");
const verificationCertificateLanes = requireElement<HTMLElement>("#verificationCertificateLanes");
const canvas = requireElement<HTMLCanvasElement>("#scene");
const threeCanvas = requireElement<HTMLCanvasElement>("#hamiltonianScene");
const systemTitle = requireElement<HTMLElement>("#systemTitle");
const systemSelect = requireElement<HTMLSelectElement>("#systemSelect");
const visualizationModes = requireElement<HTMLElement>("#visualizationModes");
const variantSection = requireElement<HTMLElement>("#variantSection");
const variantModes = requireElement<HTMLElement>("#variantModes");
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

const trajectorySource = new StaticSource();
const structurePanel = new StructurePanel(principlesPanel, invariantsPanel, parametersPanel, loopPhaseArc);
const diagnosticsPanel = new DiagnosticsPanel(diagnosticsSection, diagnosticsPanel_);
const verificationPanel = new VerificationPanel(verificationContent);
const verificationStage = new VerificationStage(
  verificationCanvas,
  verificationPlayButton,
  verificationSpeedControl,
  verificationCertificateLanes,
);
const clock = new PlaybackClock();

type Domain = "systems" | "verification";
let activeDomain: Domain = "systems";
let examples: SystemManifest[] = [];
let lensById = new Map<string, ManifestLens>();
let selectedExample: SystemManifest | null = null;
let selectedVisualization: ManifestLens | null = null;
let selectedVariant: ManifestParameterVariant | null = null;
let trajectory: Trajectory | null = null;
let pendulumBounds: Bounds | null = null;
// Monotonic guard so a slow trajectory load can't overwrite a newer selection.
let loadToken = 0;
let verificationProblems: VerificationProblemSummary[] = [];
let selectedProblemId: string | null = null;

function syncPlayButton() {
  const duration = trajectory ? trajectoryDuration(trajectory) : 0;
  if (!clock.playing && duration > 0 && clock.time >= duration) {
    playButton.textContent = "Replay";
  } else {
    playButton.textContent = clock.playing ? "Pause" : "Play";
  }
}

playButton.addEventListener("click", () => {
  const duration = trajectory ? trajectoryDuration(trajectory) : 0;
  if (!clock.playing && duration > 0 && clock.time >= duration) {
    clock.reset();
  } else {
    clock.toggle();
  }
  syncPlayButton();
});

fitToSystem.addEventListener("click", () => {
  threeScene.resetCamera();
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
  return CANVAS_MODE_IDS.has(id);
}

function isThreeMode(id: string): id is ThreeMode {
  return !isCanvasMode(id);
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

    const category = document.createElement("span");
    category.className = "catalog-item__category";
    category.textContent = problem.model ?? problem.status;

    const title = document.createElement("strong");
    title.textContent = problem.name;

    // Obligation/candidate counts from the index summary let the workbench be
    // scanned without opening each problem.
    const counts = document.createElement("span");
    counts.className = "catalog-item__counts";
    counts.append(
      countBadge("obligations", problem.counts.obligations),
      countBadge("candidates", problem.counts.candidates),
    );

    button.append(category, title, counts);
    button.addEventListener("click", () => {
      void selectVerificationProblem(problem.id);
    });
    verificationCatalog.append(button);
  });
}

function countBadge(label: string, value: number): HTMLSpanElement {
  const badge = document.createElement("span");
  badge.className = "catalog-item__count";
  badge.dataset.count = label;
  badge.textContent = `${value} ${label}`;
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
    const problem = await loadVerificationProblem(summary.dataPath);
    // A stale click (the user moved on) should not overwrite the newer problem.
    if (selectedProblemId === summary.id) {
      verificationStage.show(problem);
      verificationPanel.render(problem);
    }
  } catch (error) {
    console.warn("Verification problem unavailable:", error);
    verificationStage.clear();
    verificationPanel.renderEmpty(
      `Could not load ${summary.name}. Regenerate with "python -m scripts.generate_verification_problems".`,
    );
  }
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

  if (isCanvasMode(selectedVisualization.id)) {
    setCanvasMode("2d");
  } else if (isThreeMode(selectedVisualization.id)) {
    setCanvasMode("3d");
    threeScene.setVisualization(selectedVisualization.id, trajectory);
  }
}

async function selectExample(exampleId: string) {
  const nextExample = examples.find((example) => example.id === exampleId) ?? examples[0];
  if (!nextExample) {
    return;
  }
  selectedExample = nextExample;
  selectedVisualization = lensFor(nextExample.lenses[0]);
  selectedVariant = defaultVariant(nextExample);
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
  if (!selectedVisualization || !isCanvasMode(selectedVisualization.id)) {
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
  if (duration > 0 && time >= duration && clock.playing) {
    clock.pause();
    syncPlayButton();
  }
  const current = sampleTrajectory(trajectory, time);
  if (selectedVisualization.id === "pendulumMotionPhase") {
    resize2dCanvas();
    drawPendulumScene(ctx, trajectory, pendulumBounds, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedVisualization.id === "effectivePotential") {
    drawEffectivePotentialScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedExample && isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "configuration-phase") {
    drawPhaseScene(ctx, trajectory, selectedExample, selectedVisualization, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedExample && isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "potential-contour") {
    drawPotentialContourScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedExample && isCanvasMode(selectedVisualization.id) && selectedVisualization.kind === "potential-energy") {
    drawPotentialScene(ctx, trajectory, selectedExample, selectedVisualization, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedVisualization.id === "variableSpeedWavefront") {
    drawWavefrontScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
  } else if (selectedVisualization.id === "henonHeilesPoincare") {
    drawPoincareSectionScene(ctx, trajectory, current, canvas.clientWidth, canvas.clientHeight);
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
  const index = await loadVerificationIndex();
  verificationProblems = index.problems;
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
