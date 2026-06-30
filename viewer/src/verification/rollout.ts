/**
 * Rollout playback hooks for the Verification React shell (FE-057).
 *
 * These reuse the existing `PlaybackClock` and trajectory sampling unchanged;
 * React only orchestrates *when* to advance and draw, never *how* the rollout is
 * computed. `useRolloutPhase` is the single owner of clock advancement so the
 * shared clock is advanced exactly once per frame; the canvas wrappers read the
 * returned phase ref and draw to it, matching the vanilla stage's behaviour.
 */
import { useEffect, useRef, type MutableRefObject } from "react";

import { PlaybackClock, sampleTrajectory, trajectoryDuration } from "../playback";
import type { Trajectory } from "../data/trajectory";

/**
 * Drive a shared `PlaybackClock` and expose the current rollout phase in [0, 1]
 * via a ref. A single RAF advances the clock and wraps elapsed time modulo the
 * trajectory duration (looping playback), exactly as the vanilla stage does.
 * Returning a ref (not state) keeps the per-frame phase out of React's render
 * path, so consumers redraw imperatively without re-rendering every frame.
 */
export function useRolloutPhase(
  clock: PlaybackClock,
  trajectory: Trajectory | null,
  speed: number,
  active: boolean,
): MutableRefObject<number> {
  const phaseRef = useRef(0);
  const trajectoryRef = useRef(trajectory);
  const speedRef = useRef(speed);
  trajectoryRef.current = trajectory;
  speedRef.current = speed;

  useEffect(() => {
    if (!active) {
      return;
    }
    let raf = 0;
    const loop = (now: number): void => {
      const time = clock.advance(now, speedRef.current);
      const data = trajectoryRef.current;
      if (data) {
        const duration = trajectoryDuration(data);
        phaseRef.current = sampleTrajectory(data, duration > 0 ? time % duration : time).phase;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [clock, active]);

  return phaseRef;
}

/**
 * Run `draw` on every animation frame while `active`, and once whenever it stops
 * (so a paused canvas still reflects its latest inputs). The latest `draw` is
 * held in a ref so changing it does not restart the loop.
 */
export function useCanvasFrameLoop(active: boolean, draw: () => void): void {
  const drawRef = useRef(draw);
  drawRef.current = draw;

  useEffect(() => {
    if (!active) {
      drawRef.current();
      return;
    }
    let raf = 0;
    const loop = (): void => {
      drawRef.current();
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [active]);
}

export { PlaybackClock };
