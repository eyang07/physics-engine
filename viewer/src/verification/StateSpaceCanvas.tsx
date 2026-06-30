/**
 * React wrapper for the verification state-space figure (FE-057).
 *
 * Owns a `<canvas>` ref and drives the framework-free `renderStateSpace`
 * renderer (FE-056) imperatively: it animates while `active` using the shared
 * rollout phase, and redraws once whenever the scene or selection changes (so a
 * paused figure still reflects the current selection). No physics, integration,
 * or playback logic lives here — it only decides *when* to draw.
 */
import { useCallback, useEffect, useRef, type MutableRefObject } from "react";

import {
  renderStateSpace,
  renderStateSpaceEmpty,
  type StateSpaceScene,
  type StateSpaceSelection,
} from "./render/stateSpace";
import { useCanvasFrameLoop } from "./rollout";

export type StateSpaceCanvasProps = {
  /** The prepared scene (from `prepareStateSpaceScene`), or null for the
   * empty-state plate. */
  scene: StateSpaceScene | null;
  /** Which obligation is selected (drives margin-marker emphasis/dimming). */
  selection: StateSpaceSelection;
  /** The shared rollout phase in [0, 1], advanced by `useRolloutPhase`. */
  phaseRef: MutableRefObject<number>;
  /** Whether the rollout animation loop should run. */
  active: boolean;
  className?: string;
};

// Match the device-pixel-ratio backing store to the CSS size, resetting the
// drawing transform only when the size changes so the per-frame draw keeps
// working in CSS pixels (as the renderer expects). Mirrors the vanilla stage's
// resize().
function sizeCanvas(
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
): void {
  const pixelRatio = window.devicePixelRatio || 1;
  const drawWidth = Math.max(1, Math.floor(width * pixelRatio));
  const drawHeight = Math.max(1, Math.floor(height * pixelRatio));
  if (canvas.width !== drawWidth || canvas.height !== drawHeight) {
    canvas.width = drawWidth;
    canvas.height = drawHeight;
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }
}

export function StateSpaceCanvas({
  scene,
  selection,
  phaseRef,
  active,
  className,
}: StateSpaceCanvasProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef(scene);
  const selectionRef = useRef(selection);
  sceneRef.current = scene;
  selectionRef.current = selection;

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    sizeCanvas(canvas, ctx, width, height);
    const current = sceneRef.current;
    if (!current) {
      renderStateSpaceEmpty(ctx, width, height);
      return;
    }
    renderStateSpace(ctx, current, selectionRef.current, phaseRef.current, width, height);
  }, [phaseRef]);

  useCanvasFrameLoop(active, draw);
  // Redraw once when the scene or selection changes, covering the paused case
  // where the animation loop is not running.
  useEffect(() => {
    draw();
  }, [draw, scene, selection]);

  return <canvas ref={canvasRef} className={className} />;
}
