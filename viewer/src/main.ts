import katex from "katex";
import "katex/dist/katex.min.css";
import { ThreeScene, type ThreeMode, type Trajectory } from "./threeScene";
import "./styles.css";

type CanvasMode = "pendulumMotionPhase" | ThreeMode;

type Visualization = {
  id: CanvasMode;
  label: string;
};

type Readout = {
  latex: string;
  value: string;
};

type ExampleConfig = {
  id: string;
  title: string;
  description: string;
  category: string;
  dataPath: string;
  visualizations: Visualization[];
  readouts: (state: number[], time: number) => Readout[];
};

type Bounds = {
  minTheta: number;
  maxTheta: number;
  minOmega: number;
  maxOmega: number;
};

function requireElement<T extends Element>(selector: string): T {
  const element = document.querySelector<T>(selector);
  if (!element) {
    throw new Error(`Missing required element: ${selector}`);
  }
  return element;
}

function pendulumEnergy(theta: number, omega: number): number {
  return 0.5 * omega * omega + 9.81 * (1 - Math.cos(theta));
}

function speed3(state: number[], startIndex: number): number {
  return Math.hypot(state[startIndex], state[startIndex + 1], state[startIndex + 2]);
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
    readouts: (state, time) => [
      { latex: "t", value: `${time.toFixed(2)} s` },
      { latex: "\\theta", value: `${state[0].toFixed(3)} rad` },
      { latex: "\\dot{\\theta}", value: `${state[1].toFixed(3)} rad/s` },
      { latex: "H", value: `${pendulumEnergy(state[0], state[1]).toFixed(3)}` },
    ],
  },
  {
    id: "sphere-geodesic",
    title: "Geodesic on a Sphere",
    description: "Free motion on a curved configuration space; the path becomes a great circle.",
    category: "Differential Geometry",
    dataPath: "/data/sphere_geodesic.json",
    visualizations: [{ id: "sphereGeodesic", label: "Great-Circle Flow" }],
    readouts: (state, time) => [
      { latex: "t", value: `${time.toFixed(2)} s` },
      { latex: "\\theta", value: `${state[0].toFixed(3)} rad` },
      { latex: "\\phi", value: `${state[1].toFixed(3)} rad` },
      { latex: "|r|", value: `${Math.hypot(state[4], state[5], state[6]).toFixed(3)}` },
    ],
  },
  {
    id: "charged-particle",
    title: "Electron in a Magnetic Field",
    description: "Lorentz-force motion from a velocity-dependent electromagnetic Lagrangian.",
    category: "Fields",
    dataPath: "/data/charged_particle.json",
    visualizations: [{ id: "chargedParticle", label: "Lorentz Orbit" }],
    readouts: (state, time) => [
      { latex: "t", value: `${time.toFixed(2)} s` },
      { latex: "|v|", value: `${speed3(state, 3).toFixed(3)}` },
      { latex: "z", value: `${state[2].toFixed(3)}` },
      { latex: "B_z", value: "1.000" },
    ],
  },
  {
    id: "uniform-gravity",
    title: "Uniform Gravitational Field",
    description: "Projectile motion from a constant gravitational potential.",
    category: "Classical Motion",
    dataPath: "/data/uniform_gravity.json",
    visualizations: [{ id: "uniformGravity", label: "Projectile Path" }],
    readouts: (state, time) => [
      { latex: "t", value: `${time.toFixed(2)} s` },
      { latex: "x", value: `${state[0].toFixed(3)}` },
      { latex: "z", value: `${state[1].toFixed(3)}` },
      { latex: "\\dot{z}", value: `${state[3].toFixed(3)}` },
    ],
  },
  {
    id: "ideal-spring",
    title: "Ideal Spring",
    description: "A mass-spring oscillator with conserved quadratic energy.",
    category: "Oscillators",
    dataPath: "/data/ideal_spring.json",
    visualizations: [{ id: "idealSpring", label: "Spring Motion" }],
    readouts: (state, time) => [
      { latex: "t", value: `${time.toFixed(2)} s` },
      { latex: "x", value: `${state[0].toFixed(3)}` },
      { latex: "\\dot{x}", value: `${state[1].toFixed(3)}` },
      { latex: "E", value: `${(0.5 * state[1] ** 2 + 0.5 * state[0] ** 2).toFixed(3)}` },
    ],
  },
  {
    id: "kepler",
    title: "Kepler Problem",
    description: "Planar inverse-square central-force motion with conserved angular momentum.",
    category: "Orbital Mechanics",
    dataPath: "/data/kepler_problem.json",
    visualizations: [{ id: "keplerOrbit", label: "Orbital Flow" }],
    readouts: (state, time) => [
      { latex: "t", value: `${time.toFixed(2)} s` },
      { latex: "r", value: `${state[0].toFixed(3)}` },
      { latex: "\\phi", value: `${state[1].toFixed(3)} rad` },
      { latex: "\\ell", value: `${(state[0] ** 2 * state[3]).toFixed(3)}` },
    ],
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
const readoutLabels = [
  requireElement<HTMLElement>("#readoutLabel0"),
  requireElement<HTMLElement>("#readoutLabel1"),
  requireElement<HTMLElement>("#readoutLabel2"),
  requireElement<HTMLElement>("#readoutLabel3"),
];
const readoutValues = [
  requireElement<HTMLElement>("#readoutValue0"),
  requireElement<HTMLElement>("#readoutValue1"),
  requireElement<HTMLElement>("#readoutValue2"),
  requireElement<HTMLElement>("#readoutValue3"),
];

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

const dataCache = new Map<string, Trajectory>();
let activeView: "home" | "selection" | "simulation" = "home";
let selectedExample = examples[0];
let selectedVisualization = selectedExample.visualizations[0];
let trajectory: Trajectory | null = null;
let pendulumBounds: Bounds | null = null;
let playbackTime = 0;
let lastFrameTime = performance.now();
let playing = true;

playButton.addEventListener("click", () => {
  playing = !playing;
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

function renderLatex(element: HTMLElement, latex: string) {
  element.dataset.latex = latex;
  katex.render(latex, element, {
    throwOnError: false,
    displayMode: false,
  });
}

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

async function loadTrajectory(example: ExampleConfig): Promise<Trajectory> {
  const cached = dataCache.get(example.id);
  if (cached) {
    return cached;
  }

  const response = await fetch(example.dataPath);
  if (!response.ok) {
    throw new Error(`Unable to load ${example.title}: ${response.status}`);
  }
  const data = (await response.json()) as Trajectory;
  dataCache.set(example.id, data);
  return data;
}

function computePendulumBounds(data: Trajectory): Bounds {
  const theta = data.states.map((state) => state[0]);
  const omega = data.states.map((state) => state[1]);
  const thetaPad = Math.max(0.1, 0.08 * (Math.max(...theta) - Math.min(...theta)));
  const omegaPad = Math.max(0.1, 0.08 * (Math.max(...omega) - Math.min(...omega)));
  return {
    minTheta: Math.min(...theta) - thetaPad,
    maxTheta: Math.max(...theta) + thetaPad,
    minOmega: Math.min(...omega) - omegaPad,
    maxOmega: Math.max(...omega) + omegaPad,
  };
}

function sample(data: Trajectory, time: number): { state: number[]; index: number; wrappedTime: number } {
  const duration = data.time[data.time.length - 1] ?? 1;
  const wrapped = ((time % duration) + duration) % duration;
  let low = 0;
  let high = data.time.length - 1;

  while (high - low > 1) {
    const mid = Math.floor((low + high) / 2);
    if (data.time[mid] <= wrapped) {
      low = mid;
    } else {
      high = mid;
    }
  }

  const t0 = data.time[low];
  const t1 = data.time[high] ?? t0;
  const alpha = t1 === t0 ? 0 : (wrapped - t0) / (t1 - t0);
  const state0 = data.states[low];
  const state1 = data.states[high] ?? state0;

  return {
    state: state0.map((value, index) => value + alpha * ((state1[index] ?? value) - value)),
    index: low,
    wrappedTime: wrapped,
  };
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
  playbackTime = 0;

  trajectory = await loadTrajectory(nextExample);
  pendulumBounds = nextExample.id === "pendulum" ? computePendulumBounds(trajectory) : null;
  applyVisualization();
}

function resizeHomeCanvas() {
  const pixelRatio = window.devicePixelRatio || 1;
  const width = homeCanvas.clientWidth;
  const height = homeCanvas.clientHeight;
  homeCanvas.width = Math.max(1, Math.floor(width * pixelRatio));
  homeCanvas.height = Math.max(1, Math.floor(height * pixelRatio));
  homeCtx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
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
  resizeHomeCanvas();
  resize2dCanvas();
  threeScene.resize();
});

function drawHomeBackground(now: number) {
  resizeHomeCanvas();
  const width = homeCanvas.clientWidth;
  const height = homeCanvas.clientHeight;
  const t = now * 0.001;

  const gradient = homeCtx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#f8faf7");
  gradient.addColorStop(0.5, "#dfeef1");
  gradient.addColorStop(1, "#f5ebd9");
  homeCtx.fillStyle = gradient;
  homeCtx.fillRect(0, 0, width, height);

  homeCtx.save();
  homeCtx.translate(width * 0.58, height * 0.5);
  homeCtx.strokeStyle = "rgba(58, 124, 125, 0.32)";
  homeCtx.lineWidth = 1.5;
  for (let orbit = 0; orbit < 7; orbit += 1) {
    const radiusX = 80 + orbit * 46;
    const radiusY = 26 + orbit * 17;
    homeCtx.beginPath();
    for (let i = 0; i <= 180; i += 1) {
      const a = (i / 180) * Math.PI * 2 + t * (0.08 + orbit * 0.01);
      const x = Math.cos(a) * radiusX;
      const y = Math.sin(a) * radiusY + Math.sin(a * 2 + t) * 9;
      if (i === 0) {
        homeCtx.moveTo(x, y);
      } else {
        homeCtx.lineTo(x, y);
      }
    }
    homeCtx.stroke();
  }

  homeCtx.fillStyle = "#17252d";
  for (let i = 0; i < 18; i += 1) {
    const a = t * 0.45 + i * 0.9;
    const x = Math.cos(a) * (100 + (i % 5) * 54);
    const y = Math.sin(a * 1.3) * (40 + (i % 4) * 32);
    homeCtx.globalAlpha = 0.14 + (i % 4) * 0.04;
    homeCtx.beginPath();
    homeCtx.arc(x, y, 3 + (i % 3), 0, Math.PI * 2);
    homeCtx.fill();
  }
  homeCtx.restore();
  homeCtx.globalAlpha = 1;
}

function drawBackground(width: number, height: number) {
  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#f8faf7");
  gradient.addColorStop(0.55, "#e9f0f5");
  gradient.addColorStop(1, "#f3eee5");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(22, 35, 48, 0.07)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= width; x += 36) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 0; y <= height; y += 36) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

function drawPendulum(theta: number, width: number, height: number) {
  const centerX = width * 0.33;
  const centerY = height * 0.24;
  const length = Math.min(width, height) * 0.34;
  const bobX = centerX + length * Math.sin(theta);
  const bobY = centerY + length * Math.cos(theta);

  ctx.save();
  ctx.lineCap = "round";

  ctx.strokeStyle = "rgba(23, 37, 45, 0.18)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(centerX, centerY, length, Math.PI * 0.62, Math.PI * 0.38, true);
  ctx.stroke();

  ctx.strokeStyle = "#2d4d5d";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(centerX, centerY);
  ctx.lineTo(bobX, bobY);
  ctx.stroke();

  ctx.fillStyle = "#17252d";
  ctx.beginPath();
  ctx.arc(centerX, centerY, 7, 0, Math.PI * 2);
  ctx.fill();

  const bobGradient = ctx.createRadialGradient(bobX - 8, bobY - 10, 4, bobX, bobY, 24);
  bobGradient.addColorStop(0, "#f8d58b");
  bobGradient.addColorStop(0.55, "#d88d42");
  bobGradient.addColorStop(1, "#904f2d");
  ctx.fillStyle = bobGradient;
  ctx.beginPath();
  ctx.arc(bobX, bobY, 24, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = "rgba(23, 37, 45, 0.16)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(centerX, centerY);
  ctx.lineTo(centerX, centerY + length + 36);
  ctx.stroke();

  ctx.restore();
}

function drawPhasePortrait(data: Trajectory, currentIndex: number, theta: number, omega: number, area: DOMRect) {
  if (!pendulumBounds) {
    return;
  }

  const pad = 38;
  const left = area.x + pad;
  const right = area.x + area.width - pad;
  const top = area.y + pad;
  const bottom = area.y + area.height - pad;

  const mapX = (value: number) =>
    left + ((value - pendulumBounds!.minTheta) / (pendulumBounds!.maxTheta - pendulumBounds!.minTheta)) * (right - left);
  const mapY = (value: number) =>
    bottom - ((value - pendulumBounds!.minOmega) / (pendulumBounds!.maxOmega - pendulumBounds!.minOmega)) * (bottom - top);

  ctx.save();
  ctx.strokeStyle = "rgba(23, 37, 45, 0.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(left, mapY(0));
  ctx.lineTo(right, mapY(0));
  ctx.moveTo(mapX(0), top);
  ctx.lineTo(mapX(0), bottom);
  ctx.stroke();

  ctx.strokeStyle = "#3a7c7d";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  data.states.forEach((state, index) => {
    const x = mapX(state[0]);
    const y = mapY(state[1]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.strokeStyle = "#d88d42";
  ctx.lineWidth = 3;
  ctx.beginPath();
  data.states.slice(0, currentIndex + 1).forEach((state, index) => {
    const x = mapX(state[0]);
    const y = mapY(state[1]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();

  ctx.fillStyle = "#17252d";
  ctx.beginPath();
  ctx.arc(mapX(theta), mapY(omega), 6, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "rgba(23, 37, 45, 0.72)";
  ctx.font = "12px Inter, system-ui, sans-serif";
  ctx.fillText("θ", right - 18, mapY(0) - 8);
  ctx.fillText("θ̇", mapX(0) + 10, top + 12);

  ctx.restore();
}

function updateReadouts(state: number[], time: number) {
  selectedExample.readouts(state, time).forEach((readout, index) => {
    renderLatex(readoutLabels[index], readout.latex);
    readoutValues[index].textContent = readout.value;
  });
}

function render(now: number) {
  const dt = (now - lastFrameTime) / 1000;
  lastFrameTime = now;

  if (playing) {
    playbackTime += dt * Number(speedControl.value);
  }

  if (activeView === "home") {
    drawHomeBackground(now);
    requestAnimationFrame(render);
    return;
  }

  if (activeView !== "simulation") {
    requestAnimationFrame(render);
    return;
  }

  if (!trajectory) {
    resize2dCanvas();
    drawBackground(canvas.clientWidth, canvas.clientHeight);
    ctx.fillStyle = "#17252d";
    ctx.font = "16px Inter, system-ui, sans-serif";
    ctx.fillText("Loading example data...", 32, 48);
    requestAnimationFrame(render);
    return;
  }

  const current = sample(trajectory, playbackTime);
  if (selectedVisualization.id === "pendulumMotionPhase") {
    resize2dCanvas();
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    drawBackground(width, height);
    drawPendulum(current.state[0], width, height);
    drawPhasePortrait(
      trajectory,
      current.index,
      current.state[0],
      current.state[1],
      new DOMRect(width * 0.53, height * 0.17, width * 0.39, height * 0.62),
    );
  } else {
    threeScene.render(current.state, playbackTime);
  }

  updateReadouts(current.state, current.wrappedTime);
  requestAnimationFrame(render);
}

populateSystemSelect();
renderSystemGallery();
renderVisualizationButtons();
setView("home");
requestAnimationFrame(render);
