/**
 * Playback: a one-shot clock plus trajectory sampling.
 *
 * Time advances independently of rendering; the clock is the single source of
 * the animation's progress, and `sampleTrajectory` interpolates the exported
 * state until the final sample. The viewer treats the data span as one complete
 * run of the example instead of wrapping early.
 */
import type { Trajectory } from "./data/trajectory";
import { clamp } from "./util";

export type Sample = {
  state: number[];
  index: number;
  /** Clamped trajectory time for this sample. */
  wrappedTime: number;
  /** Position within one complete run of the trajectory, in [0, 1]. */
  phase: number;
};

export function trajectoryDuration(data: Trajectory): number {
  const start = data.time[0] ?? 0;
  const end = data.time[data.time.length - 1] ?? start;
  return Math.max(0, end - start);
}

export function sampleTrajectory(data: Trajectory, time: number): Sample {
  const start = data.time[0] ?? 0;
  const duration = trajectoryDuration(data);
  const sampledTime = start + clamp(time, 0, duration);

  let low = 0;
  let high = data.time.length - 1;
  while (high - low > 1) {
    const mid = Math.floor((low + high) / 2);
    if (data.time[mid] <= sampledTime) {
      low = mid;
    } else {
      high = mid;
    }
  }

  const t0 = data.time[low];
  const t1 = data.time[high] ?? t0;
  const alpha = t1 === t0 ? 0 : (sampledTime - t0) / (t1 - t0);
  const state0 = data.states[low];
  const state1 = data.states[high] ?? state0;

  return {
    state: state0.map((value, index) => value + alpha * ((state1[index] ?? value) - value)),
    index: low,
    wrappedTime: sampledTime,
    phase: duration > 0 ? (sampledTime - start) / duration : 1,
  };
}

/** A simple play/pause clock that accumulates scaled wall-clock time. */
export class PlaybackClock {
  time = 0;
  playing = true;
  private last = performance.now();

  /** Advance by the real time since the previous call, scaled by `speed`. */
  advance(now: number, speed: number): number {
    const dt = (now - this.last) / 1000;
    this.last = now;
    if (this.playing) {
      this.time += dt * speed;
    }
    return this.time;
  }

  reset(): void {
    this.time = 0;
    this.playing = true;
    this.last = performance.now();
  }

  pause(): void {
    this.playing = false;
  }

  toggle(): boolean {
    this.playing = !this.playing;
    return this.playing;
  }
}
