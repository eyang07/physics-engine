/**
 * The seam between the viewer and wherever trajectories come from.
 *
 * Today there is one implementation, `StaticSource`, which serves the
 * precomputed JSON that the Python scripts export. The whole point of this
 * interface is Phase 3's promise: a future `GeneratedSource` — backed by a
 * small Python server calling `generate_example(system_id, params)` — can
 * implement the same `get` and drop in without the UI changing. `params` is
 * threaded through now precisely so that swap stays invisible later.
 */
import type { Trajectory } from "./trajectory";

/** The minimum a source needs to locate a system's data. */
export interface SystemRef {
  id: string;
  dataPath: string;
}

export interface TrajectorySource {
  get(system: SystemRef, params?: Record<string, number>): Promise<Trajectory>;
}

/** Serves precomputed trajectories. There is one file per system, so params
 * are ignored — every parameter set returns the default export. */
export class StaticSource implements TrajectorySource {
  private readonly cache = new Map<string, Promise<Trajectory>>();

  get(system: SystemRef): Promise<Trajectory> {
    const cached = this.cache.get(system.id);
    if (cached) {
      return cached;
    }
    const pending = this.fetch(system).catch((error) => {
      this.cache.delete(system.id);
      throw error;
    });
    this.cache.set(system.id, pending);
    return pending;
  }

  private async fetch(system: SystemRef): Promise<Trajectory> {
    const response = await fetch(system.dataPath);
    if (!response.ok) {
      throw new Error(`Unable to load ${system.id}: ${response.status}`);
    }
    return (await response.json()) as Trajectory;
  }
}
