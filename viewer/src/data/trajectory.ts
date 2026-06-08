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

export type Vector3Tuple = [number, number, number];
export type AxisBounds = Partial<Record<"x" | "y" | "z", [number, number]>>;

export type ReferenceGeometryHint = {
  kind: string;
  radius?: number;
  radii?: number[];
  angles?: number;
  length?: number;
  position?: Vector3Tuple;
  start?: Vector3Tuple;
  end?: Vector3Tuple;
  axis?: Vector3Tuple;
  scale?: Vector3Tuple;
  offset?: Vector3Tuple;
  echoAngles?: number[];
  yValues?: number[];
};

export type RendererHints = {
  bounds?: AxisBounds;
  camera?: {
    position?: Vector3Tuple;
    target?: Vector3Tuple;
  };
  referenceGeometry?: ReferenceGeometryHint[];
  flow?: {
    kind?: string;
    bounds?: AxisBounds;
  };
  transform?: {
    center?: Vector3Tuple;
    scale?: number | Vector3Tuple;
    offset?: Vector3Tuple;
  };
};

/** Map each state-variable name to its column index in `states`. */
export function stateIndex(trajectory: Trajectory): Map<string, number> {
  const index = new Map<string, number>();
  trajectory.state_names.forEach((name, column) => index.set(name, column));
  return index;
}

function isNumberTuple3(value: unknown): value is Vector3Tuple {
  return (
    Array.isArray(value) &&
    value.length === 3 &&
    value.every((item) => typeof item === "number")
  );
}

function isBounds(value: unknown): value is AxisBounds {
  if (!value || typeof value !== "object") {
    return false;
  }
  return Object.values(value).every(
    (range) =>
      Array.isArray(range) &&
      range.length === 2 &&
      range.every((item) => typeof item === "number"),
  );
}

function referenceGeometryHint(value: unknown): ReferenceGeometryHint | null {
  if (!value || typeof value !== "object") {
    return null;
  }
  const candidate = value as Record<string, unknown>;
  if (typeof candidate.kind !== "string") {
    return null;
  }
  return {
    kind: candidate.kind,
    radius: typeof candidate.radius === "number" ? candidate.radius : undefined,
    radii:
      Array.isArray(candidate.radii) && candidate.radii.every((item) => typeof item === "number")
        ? candidate.radii
        : undefined,
    angles: typeof candidate.angles === "number" ? candidate.angles : undefined,
    length: typeof candidate.length === "number" ? candidate.length : undefined,
    position: isNumberTuple3(candidate.position) ? candidate.position : undefined,
    start: isNumberTuple3(candidate.start) ? candidate.start : undefined,
    end: isNumberTuple3(candidate.end) ? candidate.end : undefined,
    axis: isNumberTuple3(candidate.axis) ? candidate.axis : undefined,
    scale: isNumberTuple3(candidate.scale) ? candidate.scale : undefined,
    offset: isNumberTuple3(candidate.offset) ? candidate.offset : undefined,
    echoAngles:
      Array.isArray(candidate.echoAngles) && candidate.echoAngles.every((item) => typeof item === "number")
        ? candidate.echoAngles
        : undefined,
    yValues:
      Array.isArray(candidate.yValues) && candidate.yValues.every((item) => typeof item === "number")
        ? candidate.yValues
        : undefined,
  };
}

/** Renderer-only scene hints exported by Python alongside the trajectory. */
export function rendererHints(trajectory: Trajectory): RendererHints {
  const raw = trajectory.metadata?.rendererHints;
  if (!raw || typeof raw !== "object") {
    return {};
  }
  const candidate = raw as Record<string, unknown>;
  const camera =
    candidate.camera && typeof candidate.camera === "object"
      ? (candidate.camera as Record<string, unknown>)
      : {};
  const flow =
    candidate.flow && typeof candidate.flow === "object"
      ? (candidate.flow as Record<string, unknown>)
      : {};
  const transform =
    candidate.transform && typeof candidate.transform === "object"
      ? (candidate.transform as Record<string, unknown>)
      : {};
  const transformScale =
    typeof transform.scale === "number" || isNumberTuple3(transform.scale)
      ? transform.scale
      : undefined;
  return {
    bounds: isBounds(candidate.bounds) ? candidate.bounds : undefined,
    camera: {
      position: isNumberTuple3(camera.position) ? camera.position : undefined,
      target: isNumberTuple3(camera.target) ? camera.target : undefined,
    },
    referenceGeometry: Array.isArray(candidate.referenceGeometry)
      ? candidate.referenceGeometry.flatMap((item) => {
          const hint = referenceGeometryHint(item);
          return hint ? [hint] : [];
        })
      : undefined,
    flow: {
      kind: typeof flow.kind === "string" ? flow.kind : undefined,
      bounds: isBounds(flow.bounds) ? flow.bounds : undefined,
    },
    transform: {
      center: isNumberTuple3(transform.center) ? transform.center : undefined,
      scale: transformScale,
      offset: isNumberTuple3(transform.offset) ? transform.offset : undefined,
    },
  };
}
