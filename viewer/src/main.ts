import katex from "katex";
import "katex/dist/katex.min.css";
import "./styles.css";

type Trajectory = {
  time: number[];
  state_names: string[];
  states: number[][];
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

const canvas = requireElement<HTMLCanvasElement>("#scene");
const playButton = requireElement<HTMLButtonElement>("#playButton");
const speedControl = requireElement<HTMLInputElement>("#speedControl");
const timeValue = requireElement<HTMLElement>("#timeValue");
const thetaValue = requireElement<HTMLElement>("#thetaValue");
const omegaValue = requireElement<HTMLElement>("#omegaValue");

const context = canvas.getContext("2d");
if (!context) {
  throw new Error("Canvas 2D context is unavailable.");
}
const ctx: CanvasRenderingContext2D = context;

let trajectory: Trajectory | null = null;
let bounds: Bounds | null = null;
let playbackTime = 0;
let lastFrameTime = performance.now();
let playing = true;

playButton.addEventListener("click", () => {
  playing = !playing;
  playButton.textContent = playing ? "Pause" : "Play";
});

function renderLatexLabels() {
  document.querySelectorAll<HTMLElement>("[data-latex]").forEach((element) => {
    katex.render(element.dataset.latex ?? "", element, {
      throwOnError: false,
      displayMode: false,
    });
  });
}

function resizeCanvas() {
  const pixelRatio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * pixelRatio));
  canvas.height = Math.max(1, Math.floor(height * pixelRatio));
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
}

window.addEventListener("resize", resizeCanvas);

async function loadTrajectory(): Promise<Trajectory> {
  const response = await fetch("/data/pendulum.json");
  if (!response.ok) {
    throw new Error(`Unable to load pendulum data: ${response.status}`);
  }
  return response.json();
}

function computeBounds(data: Trajectory): Bounds {
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

function sample(data: Trajectory, time: number): { theta: number; omega: number; index: number } {
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
    theta: state0[0] + alpha * (state1[0] - state0[0]),
    omega: state0[1] + alpha * (state1[1] - state0[1]),
    index: low,
  };
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

  const bobGradient = ctx.createRadialGradient(
    bobX - 8,
    bobY - 10,
    4,
    bobX,
    bobY,
    24,
  );
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

function drawPhasePortrait(data: Trajectory, currentIndex: number, sampleTheta: number, sampleOmega: number, area: DOMRect) {
  if (!bounds) {
    return;
  }

  const pad = 38;
  const left = area.x + pad;
  const right = area.x + area.width - pad;
  const top = area.y + pad;
  const bottom = area.y + area.height - pad;

  const mapX = (theta: number) =>
    left + ((theta - bounds!.minTheta) / (bounds!.maxTheta - bounds!.minTheta)) * (right - left);
  const mapY = (omega: number) =>
    bottom - ((omega - bounds!.minOmega) / (bounds!.maxOmega - bounds!.minOmega)) * (bottom - top);

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
  ctx.arc(mapX(sampleTheta), mapY(sampleOmega), 6, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "rgba(23, 37, 45, 0.72)";
  ctx.font = "12px Inter, system-ui, sans-serif";
  ctx.fillText("θ", right - 18, mapY(0) - 8);
  ctx.fillText("θ̇", mapX(0) + 10, top + 12);

  ctx.restore();
}

function render(now: number) {
  resizeCanvas();
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const dt = (now - lastFrameTime) / 1000;
  lastFrameTime = now;

  if (playing) {
    playbackTime += dt * Number(speedControl.value);
  }

  drawBackground(width, height);

  if (!trajectory) {
    ctx.fillStyle = "#17252d";
    ctx.font = "16px Inter, system-ui, sans-serif";
    ctx.fillText("Loading pendulum data...", 32, 48);
    requestAnimationFrame(render);
    return;
  }

  const current = sample(trajectory, playbackTime);
  drawPendulum(current.theta, width, height);

  const phaseArea = new DOMRect(width * 0.53, height * 0.17, width * 0.39, height * 0.62);
  drawPhasePortrait(trajectory, current.index, current.theta, current.omega, phaseArea);

  timeValue.textContent = `${playbackTime.toFixed(2)} s`;
  thetaValue.textContent = `${current.theta.toFixed(3)} rad`;
  omegaValue.textContent = `${current.omega.toFixed(3)} rad/s`;

  requestAnimationFrame(render);
}

loadTrajectory()
  .then((data) => {
    trajectory = data;
    bounds = computeBounds(data);
  })
  .catch((error: unknown) => {
    ctx.fillStyle = "#8b2f2f";
    ctx.font = "16px Inter, system-ui, sans-serif";
    ctx.fillText(error instanceof Error ? error.message : "Unable to load trajectory.", 32, 48);
  });

renderLatexLabels();
resizeCanvas();
requestAnimationFrame(render);
