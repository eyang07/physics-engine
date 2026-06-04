/**
 * Playback: a looping clock plus trajectory sampling.
 *
 * Time advances independently of rendering; the clock is the single source of
 * the animation's progress, and `sampleTrajectory` interpolates the exported
 * state at any (wrapped) time so the loop is seamless.
 */
import type { Trajectory } from "./data/trajectory";

export type Sample = {
  state: number[];
  index: number;
  wrappedTime: number;
  /** Position within one loop of the trajectory, in [0, 1). */
  phase: number;
};

export function sampleTrajectory(data: Trajectory, time: number): Sample {
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
    phase: duration > 0 ? wrapped / duration : 0,
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
  }

  toggle(): boolean {
    this.playing = !this.playing;
    return this.playing;
  }
}
