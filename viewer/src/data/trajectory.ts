/**
 * The trajectory exported by the Python engine.
 *
 * `state_names` is authoritative: code should look up components by name (via
 * `stateIndex`) rather than by magic numeric index. `series` carries the
 * derived invariants (energy, conserved quantities) the engine sampled, so the
 * viewer never recomputes physics.
 */
export type Trajectory = {
  time: number[];
  state_names: string[];
  states: number[][];
  metadata?: Record<string, unknown>;
  series?: Record<string, number[]>;
};

/** Map each state-variable name to its column index in `states`. */
export function stateIndex(trajectory: Trajectory): Map<string, number> {
  const index = new Map<string, number>();
  trajectory.state_names.forEach((name, column) => index.set(name, column));
  return index;
}
