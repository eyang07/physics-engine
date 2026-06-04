import "katex/dist/katex.min.css";
import { ThreeScene, type ThreeMode, type Trajectory } from "./threeScene";
import { theme } from "./design/theme";
import { loadManifest } from "./data/manifest";
import { StaticSource } from "./data/source";
import { renderHome } from "./home";
import { PlaybackClock, sampleTrajectory } from "./playback";
import {
  computePendulumBounds,
  drawPendulumScene,
  drawStageBackground,
  type Bounds,
} from "./pendulumCanvas";
import { StructurePanel } from "./structurePanel";
import "./styles.css";

type CanvasMode = "pendulumMotionPhase" | ThreeMode;

type Visualization = {
  id: CanvasMode;
  label: string;
};

type ExampleConfig = {
  id: string;
  title: string;
  description: string;
  category: string;
  dataPath: string;
  visualizations: Visualization[];
};

function requireElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing required element: ${selector}`);
  }
  return element;
}

const examples: ExampleConfig[] = [
  {
    id: "pendulum",
    title: "Simple Pendulum",
    description: "A nonlinear oscillator viewed as physical motion, phase portrait, or Hamiltonian flow.",
    category: "Analytical Mechanics",
    dataPath: "/data/pendulum.json",
    visualizations: [
      { id: "pendulumMotionPhase", label: "Motion + Phase" },
      { id: "pendulumHamiltonian", label: "Hamiltonian Flow" },
    ],
  },
  {
    id: "sphere-geodesic",
    title: "Geodesic on a Sphere",
    description: "Free motion on a curved configuration space; the path becomes a great circle.",
    category: "Differential Geometry",
    dataPath: "/data/sphere_geodesic.json",
    visualizations: [{ id: "sphereGeodesic", label: "Great-Circle Flow" }],
  },
  {
    id: "charged-particle",
    title: "Electron in a Magnetic Field",
    description: "Lorentz-force motion from a velocity-dependent electromagnetic Lagrangian.",
    category: "Fields",
    dataPath: "/data/charged_particle.json",
    visualizations: [{ id: "chargedParticle", label: "Lorentz Orbit" }],
  },
  {
    id: "uniform-gravity",
    title: "Uniform Gravitational Field",
    description: "Projectile motion from a constant gravitational potential.",
    category: "Classical Motion",
    dataPath: "/data/uniform_gravity.json",
    visualizations: [{ id: "uniformGravity", label: "Projectile Path" }],
  },
  {
    id: "ideal-spring",
    title: "Ideal Spring",
    description: "A mass-spring oscillator with conserved quadratic energy.",
    category: "Oscillators",
    dataPath: "/data/ideal_spring.json",
    visualizations: [{ id: "idealSpring", label: "Spring Motion" }],
  },
  {
    id: "kepler",
    title: "Kepler Problem",
    description: "Planar inverse-square central-force motion with conserved angular momentum.",
    category: "Orbital Mechanics",
    dataPath: "/data/kepler_problem.json",
    visualizations: [{ id: "keplerOrbit", label: "Orbital Flow" }],
  },
];

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
let selectedExample = examples[0];
let selectedVisualization = selectedExample.visualizations[0];
let trajectory: Trajectory | null = null;
let pendulumBounds: Bounds | null = null;

playButton.addEventListener("click", () => {
  const playing = clock.toggle();
  playButton.textContent = playing ? "Pause" : "Play";
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

function populateSystemSelect() {
  systemSelect.replaceChildren();
  examples.forEach((example) => {
    const option = document.createElement("option");
    option.value = example.id;
    option.textContent = example.title;
    systemSelect.append(option);
  });
  systemSelect.value = selectedExample.id;
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
  selectedExample.visualizations.forEach((visualization) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "mode-switch__button";
    button.textContent = visualization.label;
    button.classList.toggle("mode-switch__button--active", visualization.id === selectedVisualization.id);
    button.addEventListener("click", () => {
      selectedVisualization = visualization;
      applyVisualization();
      renderVisualizationButtons();
    });
    visualizationModes.append(button);
  });
}

function loadTrajectory(example: ExampleConfig): Promise<Trajectory> {
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
  threeScene.setActive(view === "simulation" && selectedVisualization.id !== "pendulumMotionPhase");
}

function showSelection() {
  setView("selection");
}

function showSimulation() {
  setView("simulation");
}

function applyVisualization() {
  if (!trajectory) {
    return;
  }

  if (selectedVisualization.id === "pendulumMotionPhase") {
    setCanvasMode("2d");
  } else {
    setCanvasMode("3d");
    threeScene.setVisualization(selectedVisualization.id, trajectory);
  }
}

async function selectExample(exampleId: string) {
  const nextExample = examples.find((example) => example.id === exampleId) ?? examples[0];
  selectedExample = nextExample;
  selectedVisualization = nextExample.visualizations[0];
  systemTitle.textContent = nextExample.title;
  systemSelect.value = nextExample.id;
  renderVisualizationButtons();
  clock.reset();
  structurePanel.clear();

  trajectory = await loadTrajectory(nextExample);
  pendulumBounds = nextExample.id === "pendulum" ? computePendulumBounds(trajectory) : null;
  applyVisualization();
  void structurePanel.show(nextExample.id, trajectory);
}

function resize2dCanvas() {
  if (selectedVisualization.id !== "pendulumMotionPhase") {
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
  const time = clock.advance(now, Number(speedControl.value));

  if (activeView === "home") {
    renderHome(homeCanvas, homeCtx, now);
    requestAnimationFrame(render);
    return;
  }

  if (activeView !== "simulation") {
    requestAnimationFrame(render);
    return;
  }

  if (!trajectory) {
    resize2dCanvas();
    drawStageBackground(ctx, canvas.clientWidth, canvas.clientHeight);
    ctx.fillStyle = theme.textMuted;
    ctx.font = "16px Inter, system-ui, sans-serif";
    ctx.fillText("Loading example data...", 32, 48);
    requestAnimationFrame(render);
    return;
  }

  const current = sampleTrajectory(trajectory, time);
  if (selectedVisualization.id === "pendulumMotionPhase") {
    resize2dCanvas();
    drawPendulumScene(ctx, trajectory, pendulumBounds, current, canvas.clientWidth, canvas.clientHeight);
  } else {
    threeScene.render(current.state, time);
  }

  structurePanel.update(current.phase);
  requestAnimationFrame(render);
}

populateSystemSelect();
renderSystemGallery();
renderVisualizationButtons();
setView("home");

// Warm the manifest cache for the Structure panel.
void loadManifest().catch((error) => {
  console.warn("Manifest preload failed:", error);
});

requestAnimationFrame(render);
