/**
 * FE-037 — the single registry that routes a manifest lens to the stage
 * primitive that renders it.
 *
 * Historically the viewer decided "2D canvas vs. Three.js scene" with
 * `isThreeMode = !isCanvasMode`, which silently sent *any* unrecognised lens to
 * the Three.js path and rendered a blank stage. As the backend adds physics
 * (rigid-body polhodes, normal modes, n-body orbits, …) those lenses arrive
 * before their viewer primitive exists. This registry makes the mapping
 * explicit: a lens resolves to the `2d` canvas, a `3d` scene, or a graceful
 * `fallback` placeholder — never a blank stage. FE-040..FE-043 register the real
 * primitives for the new physics and move them off the fallback.
 */

export type RendererSurface = "2d" | "3d" | "fallback";

/** Lens ids drawn by the 2D canvas lenses (`main.ts` render dispatch). */
export const CANVAS_LENS_IDS = new Set<string>([
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
  "symmetricTopNutationPhase",
  "doublePendulumPhase",
  "symmetricTopPotential",
  "schwarzschildEffectivePotential",
  "coupledOscillatorModes",
  "electromagneticField",
  "vibratingString",
  "wavePacket",
]);

/** Lens ids drawn by a Three.js scene (`ThreeScene.setVisualization`). */
export const THREE_LENS_IDS = new Set<string>([
  "pendulumHamiltonian",
  "sphereGeodesic",
  "surfaceGeodesic",
  "chargedParticle",
  "uniformGravity",
  "idealSpring",
  "keplerOrbit",
  "beadHoop",
  "lorenzAttractor",
  "henonHeilesFlow",
  "symmetricTopAxis",
  "freeRigidBodyPolhode",
  "nBodyOrbits",
  "membraneModes",
]);

/** Resolve which stage primitive renders a lens, or `fallback` if none yet. */
export function resolveRendererSurface(lensId: string): RendererSurface {
  if (CANVAS_LENS_IDS.has(lensId)) {
    return "2d";
  }
  if (THREE_LENS_IDS.has(lensId)) {
    return "3d";
  }
  return "fallback";
}

/** True when a primitive exists for this lens (i.e. it is not a fallback). */
export function isRenderableLens(lensId: string): boolean {
  return resolveRendererSurface(lensId) !== "fallback";
}
