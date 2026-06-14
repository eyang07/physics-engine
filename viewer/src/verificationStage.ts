/**
 * The Verification world's animated stage.
 *
 * It plays the self-contained controlled trajectory the engine exported with a
 * verification problem and draws it on the exported phase-plane region geometry,
 * with the candidate-certificate lanes tracking playback. This is a separate
 * world from the Systems gallery: it renders only verification data and never
 * re-derives physics.
 */
import { drawStageBackground } from "./pendulumCanvas";
import { PlaybackClock, sampleTrajectory, trajectoryDuration } from "./playback";
import { CertificateLanes } from "./certificateLanes";
import { theme } from "./design/theme";
import type { RegionGeometry, VerificationProblem } from "./data/verification";
import type { Trajectory } from "./data/trajectory";
import { clamp } from "./util";

type Bounds = {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
};

const ROLE_RGB: Record<string, string> = {
  domain: "138, 148, 166",
  safe: "240, 180, 106",
  initial: "111, 182, 201",
  unsafe: "201, 92, 78",
};

const ROLE_DRAW_ORDER = ["domain", "safe", "initial", "unsafe"];

// A phase-plane window covering every region grid, so the safe corridor (around
// upright) and the unsafe bottom are both visible behind the trajectory.
function boundsFromRegions(regions: RegionGeometry[]): Bounds | null {
  let minX = Infinity;
  let maxX = -Infinity;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const region of regions) {
    for (const x of region.grid.x) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
    }
    for (const y of region.grid.y) {
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
  }
  if (!Number.isFinite(minX) || !Number.isFinite(minY)) {
    return null;
  }
  return { minX, maxX, minY, maxY };
}

function boundsFromTrajectory(trajectory: Trajectory): Bounds {
  const xValues = trajectory.states.map((state) => state[0] ?? 0);
  const yValues = trajectory.states.map((state) => state[1] ?? 0);
  const xSpan = Math.max(...xValues) - Math.min(...xValues);
  const ySpan = Math.max(...yValues) - Math.min(...yValues);
  const xPad = Math.max(0.1, xSpan * 0.08);
  const yPad = Math.max(0.1, ySpan * 0.08);
  return {
    minX: Math.min(...xValues) - xPad,
    maxX: Math.max(...xValues) + xPad,
    minY: Math.min(...yValues) - yPad,
    maxY: Math.max(...yValues) + yPad,
  };
}

function isInsideRegion(value: number, level: number, convention: string | null): boolean {
  if (!Number.isFinite(value)) {
    return false;
  }
  if (convention && /(^|[^<])>=?/.test(convention)) {
    return value >= level;
  }
  return value <= level;
}

function drawRegionGeometry(
  ctx: CanvasRenderingContext2D,
  regions: RegionGeometry[],
  mapX: (value: number) => number,
  mapY: (value: number) => number,
  clip: { left: number; right: number; top: number; bottom: number },
): void {
  ctx.save();
  ctx.beginPath();
  ctx.rect(clip.left, clip.top, clip.right - clip.left, clip.bottom - clip.top);
  ctx.clip();

  const byRole = (role: string) => regions.filter((region) => region.role === role);
  const ordered = [
    ...ROLE_DRAW_ORDER.flatMap(byRole),
    ...regions.filter((region) => !ROLE_DRAW_ORDER.includes(region.role)),
  ];

  ordered.forEach((region) => {
    const { x, y, values } = region.grid;
    if (x.length < 2 || y.length < 2 || values.length === 0) {
      return;
    }
    const level = region.level ?? 0;
    ctx.fillStyle = `rgba(${ROLE_RGB[region.role] ?? ROLE_RGB.domain}, 0.16)`;
    for (let row = 0; row < y.length - 1 && row < values.length; row += 1) {
      const valueRow = values[row];
      for (let col = 0; col < x.length - 1 && col < valueRow.length; col += 1) {
        if (!isInsideRegion(valueRow[col], level, region.convention)) {
          continue;
        }
        const x0 = mapX(x[col]);
        const x1 = mapX(x[col + 1]);
        const y0 = mapY(y[row]);
        const y1 = mapY(y[row + 1]);
        ctx.fillRect(x0, Math.min(y0, y1), Math.max(1, x1 - x0), Math.max(1, Math.abs(y0 - y1)));
      }
    }
  });

  ctx.lineWidth = 1.4;
  ctx.lineJoin = "round";
  ordered.forEach((region) => {
    ctx.strokeStyle = `rgba(${ROLE_RGB[region.role] ?? ROLE_RGB.domain}, 0.88)`;
    region.boundaryPolylines.forEach((polyline) => {
      ctx.beginPath();
      polyline.forEach(([x, y], index) => {
        const sx = mapX(x);
        const sy = mapY(y);
        if (index === 0) {
          ctx.moveTo(sx, sy);
        } else {
          ctx.lineTo(sx, sy);
        }
      });
      ctx.stroke();
    });
  });
  ctx.restore();
}

function drawVerificationPhaseScene(
  ctx: CanvasRenderingContext2D,
  trajectory: Trajectory,
  regions: RegionGeometry[],
  bounds: Bounds,
  phase: number,
  width: number,
  height: number,
): void {
  drawStageBackground(ctx, width, height);
  const plot = {
    left: Math.max(34, width * 0.08),
    right: width - Math.max(26, width * 0.06),
    top: Math.max(28, height * 0.09),
    bottom: height - Math.max(42, height * 0.12),
  };
  const spanX = Math.max(1e-9, bounds.maxX - bounds.minX);
  const spanY = Math.max(1e-9, bounds.maxY - bounds.minY);
  const mapX = (value: number) => plot.left + ((value - bounds.minX) / spanX) * (plot.right - plot.left);
  const mapY = (value: number) => plot.bottom - ((value - bounds.minY) / spanY) * (plot.bottom - plot.top);

  ctx.save();
  ctx.strokeStyle = theme.hairlineStrong;
  ctx.lineWidth = 1;
  ctx.strokeRect(plot.left, plot.top, plot.right - plot.left, plot.bottom - plot.top);
  ctx.restore();

  drawRegionGeometry(ctx, regions, mapX, mapY, plot);

  const count = trajectory.states.length;
  const activeIndex = clamp(Math.round(phase * (count - 1)), 0, count - 1);
  const step = Math.max(1, Math.floor(count / 420));

  ctx.save();
  ctx.beginPath();
  for (let index = 0; index < count; index += step) {
    const state = trajectory.states[index];
    const x = mapX(state[0] ?? 0);
    const y = mapY(state[1] ?? 0);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.strokeStyle = theme.accent;
  ctx.lineWidth = 2;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 10;
  ctx.stroke();
  ctx.restore();

  const active = trajectory.states[activeIndex] ?? trajectory.states[0];
  ctx.fillStyle = theme.accentStrong;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 14;
  ctx.beginPath();
  ctx.arc(mapX(active[0] ?? 0), mapY(active[1] ?? 0), 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;

  ctx.fillStyle = theme.textMuted;
  ctx.font = '12px "IBM Plex Mono", monospace';
  ctx.fillText(trajectory.state_names[0] ?? "x", plot.right - 18, plot.bottom + 24);
  ctx.fillText(trajectory.state_names[1] ?? "y", plot.left - 24, plot.top + 10);
}

export class VerificationStage {
  private readonly ctx: CanvasRenderingContext2D;
  private readonly clock = new PlaybackClock();
  private readonly certificateLanes: CertificateLanes;
  private trajectory: Trajectory | null = null;
  private bounds: Bounds | null = null;
  private regions: RegionGeometry[] = [];
  private active = false;
  private running = false;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private readonly playButton: HTMLButtonElement,
    private readonly speedControl: HTMLInputElement,
    certificateContainer: HTMLElement,
  ) {
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Verification stage 2D context is unavailable.");
    }
    this.ctx = context;
    this.certificateLanes = new CertificateLanes(certificateContainer);
    this.playButton.addEventListener("click", () => this.togglePlay());
  }

  /** Load a problem's controlled trajectory + region geometry onto the stage. */
  show(problem: VerificationProblem): void {
    const vt = problem.trajectory;
    this.certificateLanes.clear();
    this.clock.reset();
    if (!vt || vt.states.length === 0) {
      this.trajectory = null;
      this.bounds = null;
      this.regions = [];
      this.syncPlayButton();
      return;
    }
    this.trajectory = {
      time: vt.time,
      state_names: vt.stateNames,
      states: vt.states,
      series: vt.series,
      metadata: {},
    };
    this.regions = problem.regionGeometry;
    this.bounds = boundsFromRegions(problem.regionGeometry) ?? boundsFromTrajectory(this.trajectory);
    this.certificateLanes.show(vt.series, vt.certificateSeries);
    this.syncPlayButton();
    this.resize();
  }

  clear(): void {
    this.certificateLanes.clear();
    this.clock.reset();
    this.clock.pause();
    this.trajectory = null;
    this.bounds = null;
    this.regions = [];
    this.syncPlayButton();
    this.resize();
  }

  /** Start or stop the stage's own animation loop (driven by domain switching). */
  setActive(active: boolean): void {
    this.active = active;
    if (!active) {
      this.clock.pause();
      this.syncPlayButton();
      return;
    }
    if (active) {
      this.resize();
      if (!this.running) {
        this.running = true;
        requestAnimationFrame(this.loop);
      }
    }
  }

  resize(): void {
    const pixelRatio = window.devicePixelRatio || 1;
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    this.canvas.width = Math.max(1, Math.floor(width * pixelRatio));
    this.canvas.height = Math.max(1, Math.floor(height * pixelRatio));
    this.ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }

  private togglePlay(): void {
    const duration = this.trajectory ? trajectoryDuration(this.trajectory) : 0;
    if (!this.clock.playing && duration > 0 && this.clock.time >= duration) {
      this.clock.reset();
    } else {
      this.clock.toggle();
    }
    this.syncPlayButton();
  }

  private syncPlayButton(): void {
    const duration = this.trajectory ? trajectoryDuration(this.trajectory) : 0;
    if (!this.clock.playing && duration > 0 && this.clock.time >= duration) {
      this.playButton.textContent = "Replay";
    } else {
      this.playButton.textContent = this.clock.playing ? "Pause" : "Play";
    }
  }

  private readonly loop = (now: number): void => {
    if (!this.active) {
      this.running = false;
      return;
    }
    this.render(now);
    requestAnimationFrame(this.loop);
  };

  private render(now: number): void {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    if (!this.trajectory || !this.bounds) {
      drawStageBackground(this.ctx, width, height);
      this.ctx.fillStyle = theme.textMuted;
      this.ctx.font = '16px "IBM Plex Sans", system-ui, sans-serif';
      this.ctx.fillText("No trajectory for this problem.", 32, 48);
      return;
    }

    const time = this.clock.advance(now, Number(this.speedControl.value));
    const duration = trajectoryDuration(this.trajectory);
    if (duration > 0 && time >= duration && this.clock.playing) {
      this.clock.pause();
      this.syncPlayButton();
    }
    const sample = sampleTrajectory(this.trajectory, time);
    drawVerificationPhaseScene(
      this.ctx,
      this.trajectory,
      this.regions,
      this.bounds,
      sample.phase,
      width,
      height,
    );
    this.certificateLanes.update(sample.phase);
  }
}
