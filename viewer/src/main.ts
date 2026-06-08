import "katex/dist/katex.min.css";
import { ThreeScene, type ThreeMode, type Trajectory } from "./threeScene";
import { theme } from "./design/theme";
import {
  loadManifest,
  type ManifestLens,
  type SystemManifest,
} from "./data/manifest";
import { StaticSource } from "./data/source";
import { drawEffectivePotentialScene } from "./effectivePotentialCanvas";
import { renderHome } from "./home";
import { PlaybackClock, sampleTrajectory, trajectoryDuration } from "./playback";
import {
  computePendulumBounds,
  drawPendulumScene,
  drawStageBackground,
  type Bounds,
} from "./pendulumCanvas";
import { drawPhaseScene, drawPotentialContourScene, drawPotentialScene } from "./phasePotentialCanvas";
import { StructurePanel } from "./structurePanel";
import { drawWavefrontScene } from "./wavefrontCanvas";
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
  "variableSpeedWavefront",
]);

function requireElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing required element: ${selector}`);
  }
  return element;
}

const homeView = requireElement<HTMLElement>("#homeView");
const selectionView = requireElement<HTMLElement>("#selectionView");
const app = requireElement<HTMLElement>("#app");
const homeCanvas = requireElement<HTMLCanvasElement>("#homeCanvas");
const enterSimulations = requireElement<HTMLButtonElement>("#enterSimulations");
const backToSystems = requireElement<HTMLButtonElement>("#backToSystems");
const systemGallery = requireElement<HTMLElement>("#systemGallery");
const canvas = requireElement<HTMLCanvasElement>("#scene");
const threeCanvas = requireElement<HTMLCanvasElement>("#hamiltonianScene");
const systemTitle = requireElement<HTMLElement>("#systemTitle");
const systemSelect = requireElement<HTMLSelectElement>("#systemSelect");
const visualizationModes = requireElement<HTMLElement>("#visualizationModes");
const playButton = requireElement<HTMLButtonElement>("#playButton");
const speedControl = requireElement<HTMLInputElement>("#speedControl");
const principlesPanel = requireElement<HTMLElement>("#principles");
const invariantsPanel = requireElement<HTMLElement>("#invariants");
const parametersPanel = requireElement<HTMLElement>("#parameters");
const loopPhaseArc = requireElement<SVGCircleElement>("#loopPhaseArc");

const context = canvas.getContext("2d");
if (!context) {
  throw new Error("Canvas 2D context is unavailable.");
}
const ctx: CanvasRenderingContext2D = context;
const homeContext = homeCanvas.getContext("2d");
if (!homeContext) {
  throw new Error("Home canvas 2D context is unavailable.");
}
const homeCtx: CanvasRenderingContext2D = homeContext;
const threeScene = new ThreeScene(threeCanvas);

const trajectorySource = new StaticSource();
const structurePanel = new StructurePanel(principlesPanel, invariantsPanel, parametersPanel, loopPhaseArc);
const clock = new PlaybackClock();

let activeView: "home" | "selection" | "simulation" = "home";
let examples: SystemManifest[] = [];
let lensById = new Map<string, ManifestLens>();
let selectedExample: SystemManifest | null = null;
let selectedVisualization: ManifestLens | null = null;
let trajectory: Trajectory | null = null;
let pendulumBounds: Bounds | null = null;

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

enterSimulations.addEventListener("click", () => {
  showSelection();
});

backToSystems.addEventListener("click", () => {
  showSelection();
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

function renderSystemGallery() {
  systemGallery.replaceChildren();
  examples.forEach((example) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "system-card";
    button.innerHTML = `
      <span class="system-card__category">${example.category}</span>
      <strong>${example.title}</strong>
      <span>${example.description}</span>
    `;
    button.addEventListener("click", () => {
      showSimulation();
      void selectExample(example.id);
    });
    systemGallery.append(button);
  });
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

function loadTrajectory(example: SystemManifest): Promise<Trajectory> {
  // Behind the StaticSource seam: a future GeneratedSource (Python server)
  // implements the same interface, so parameter-driven generation can drop in
  // here without changing the call site.
  return trajectorySource.get(example);
}

function setCanvasMode(mode: "2d" | "3d") {
  const is2d = mode === "2d";
  canvas.classList.toggle("stage__canvas--active", is2d);
  threeCanvas.classList.toggle("stage__canvas--active", !is2d);
  threeScene.setActive(!is2d);
}

function setView(view: "home" | "selection" | "simulation") {
  activeView = view;
  homeView.classList.toggle("view-hidden", view !== "home");
  selectionView.classList.toggle("view-hidden", view !== "selection");
  app.classList.toggle("view-hidden", view !== "simulation");
  threeScene.setActive(
    view === "simulation" && selectedVisualization !== null && isThreeMode(selectedVisualization.id),
  );
}

function showSelection() {
  setView("selection");
}

function showSimulation() {
  setView("simulation");
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
  systemTitle.textContent = nextExample.title;
  systemSelect.value = nextExample.id;
  renderVisualizationButtons();
  clock.reset();
  syncPlayButton();
  structurePanel.clear();

  trajectory = await loadTrajectory(nextExample);
  pendulumBounds = nextExample.id === "pendulum" ? computePendulumBounds(trajectory) : null;
  applyVisualization();
  void structurePanel.show(nextExample.id, trajectory);
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
});

function render(now: number) {
  if (activeView === "home") {
    renderHome(homeCanvas, homeCtx, now);
    requestAnimationFrame(render);
    return;
  }

  if (activeView !== "simulation") {
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
  } else {
    threeScene.render(current.state, time, current.index);
  }

  structurePanel.update(current.phase);
  requestAnimationFrame(render);
}

setView("home");

async function initialize() {
  try {
    const manifest = await loadManifest();
    examples = manifest.systems;
    lensById = new Map(manifest.lenses.map((lens) => [lens.id, lens]));
    selectedExample = examples[0] ?? null;
    selectedVisualization = selectedExample ? lensFor(selectedExample.lenses[0]) : null;
    if (selectedExample) {
      systemTitle.textContent = selectedExample.title;
    }
    populateSystemSelect();
    renderSystemGallery();
    renderVisualizationButtons();
  } catch (error) {
    console.warn("Manifest preload failed:", error);
  }
}

void initialize();

requestAnimationFrame(render);
