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
  viewportBounds?: AxisBounds;
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

/**
 * A finite-time Lyapunov diagnostic, as exported in
 * `metadata.diagnostics.lyapunov`. The numbers Python measured (the running
 * estimate, the local growth) live in `trajectory.series`; this metadata only
 * names which series to read and records how they were produced. The viewer
 * never recomputes the exponent — it renders the exported series.
 */
export type LyapunovDiagnostic = {
  kind?: string;
  method?: string;
  /** Name of the running finite-time estimate series in `trajectory.series`. */
  series?: string;
  /** Name of the local growth-rate series in `trajectory.series`. */
  localGrowthSeries?: string;
  timeWindow?: [number, number];
  sampleCount?: number;
};

/** A single section crossing: only the exported axis values (+ crossing time). */
export type PoincarePoint = {
  /** Values for the section's `axes`, in axis order. */
  axisValues: number[];
  time?: number;
};

/**
 * A Poincaré section exported in `metadata.poincareSections`. The crossings are
 * found by Python; the viewer plots the exported axis values as markers and
 * never integrates or root-finds them itself.
 */
export type PoincareSection = {
  name: string;
  coordinate?: string;
  value?: number;
  direction?: "positive" | "negative" | string;
  axes: string[];
  points: PoincarePoint[];
};

/**
 * The measured conservation quality of one invariant, exported in
 * `metadata.invariantResiduals`. Python compares the conserved-quantity series
 * against a reference value and reports the deviation; `series` names the column
 * in `trajectory.series` so the viewer can draw the drift shape without
 * recomputing anything. The numbers are measured evidence of integrator quality,
 * not a proof of conservation.
 */
export type InvariantResidual = {
  name: string;
  /** Series key in `trajectory.series` for the conserved quantity q(t). */
  series?: string;
  /** The reference value the residual is measured against (e.g. q(t0)). */
  reference?: number;
  referenceKind?: string;
  maxAbs?: number;
  rms?: number;
  maxRelative?: number;
  /** Characteristic magnitude used to normalize the relative residual. */
  scale?: number;
};

/**
 * One obligation threshold a candidate series is read against, exported in each
 * `metadata.certificateSeries[].comparisonBaselines` entry. The comparison and
 * rhs come straight from the verification obligation; the viewer draws the
 * threshold but renders no pass/fail verdict here (that is the proof-status
 * surface's measured job).
 */
export type CertificateComparisonBaseline = {
  obligationId: string;
  comparison: string;
  rhs: number;
  regionId?: string;
};

/**
 * A candidate certificate sampled along the trajectory, exported in
 * `metadata.certificateSeries`. `series` names the column in `trajectory.series`
 * (the value `B(x(t))` or its flow derivative). The numbers are measured
 * evidence along one run — never a proof; the engine keeps obligations
 * `external-required`.
 */
export type CertificateSeries = {
  problemId?: string;
  candidateId?: string;
  /** "candidate-value" | "flow-derivative". */
  kind: string;
  label?: string;
  /** Series key in `trajectory.series`. */
  series: string;
  obligationIds: string[];
  comparisonBaselines: CertificateComparisonBaseline[];
};

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : undefined;
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" ? value : undefined;
}

/** Read the Lyapunov diagnostic Python attached to the trajectory metadata. */
export function lyapunovDiagnostic(trajectory: Trajectory): LyapunovDiagnostic | null {
  const diagnostics = asRecord(trajectory.metadata?.diagnostics);
  const raw = asRecord(diagnostics?.lyapunov);
  if (!raw) {
    return null;
  }
  const timeWindow =
    Array.isArray(raw.timeWindow) &&
    raw.timeWindow.length === 2 &&
    raw.timeWindow.every((item) => typeof item === "number")
      ? (raw.timeWindow as [number, number])
      : undefined;
  return {
    kind: typeof raw.kind === "string" ? raw.kind : undefined,
    method: typeof raw.method === "string" ? raw.method : undefined,
    series: typeof raw.series === "string" ? raw.series : undefined,
    localGrowthSeries: typeof raw.localGrowthSeries === "string" ? raw.localGrowthSeries : undefined,
    timeWindow,
    sampleCount: typeof raw.sampleCount === "number" ? raw.sampleCount : undefined,
  };
}

/** Read the invariant-residual diagnostics Python attached to the trajectory. */
export function invariantResiduals(trajectory: Trajectory): InvariantResidual[] {
  const raw = trajectory.metadata?.invariantResiduals;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.flatMap((item) => {
    const record = asRecord(item);
    if (!record || typeof record.name !== "string") {
      return [];
    }
    return [
      {
        name: record.name,
        series: typeof record.series === "string" ? record.series : undefined,
        reference: asNumber(record.reference),
        referenceKind: typeof record.referenceKind === "string" ? record.referenceKind : undefined,
        maxAbs: asNumber(record.maxAbs),
        rms: asNumber(record.rms),
        maxRelative: asNumber(record.maxRelative),
        scale: asNumber(record.scale),
      },
    ];
  });
}

/** Read the candidate-certificate series Python attached to the trajectory. */
export function certificateSeries(trajectory: Trajectory): CertificateSeries[] {
  const raw = trajectory.metadata?.certificateSeries;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.flatMap((item) => {
    const record = asRecord(item);
    if (!record || typeof record.series !== "string") {
      return [];
    }
    const baselines = Array.isArray(record.comparisonBaselines)
      ? record.comparisonBaselines.flatMap((entry) => {
          const baseline = asRecord(entry);
          if (
            !baseline ||
            typeof baseline.obligationId !== "string" ||
            typeof baseline.comparison !== "string" ||
            typeof baseline.rhs !== "number"
          ) {
            return [];
          }
          return [
            {
              obligationId: baseline.obligationId,
              comparison: baseline.comparison,
              rhs: baseline.rhs,
              regionId: typeof baseline.regionId === "string" ? baseline.regionId : undefined,
            },
          ];
        })
      : [];
    return [
      {
        problemId: typeof record.problemId === "string" ? record.problemId : undefined,
        candidateId: typeof record.candidateId === "string" ? record.candidateId : undefined,
        kind: typeof record.kind === "string" ? record.kind : "candidate-value",
        label: typeof record.label === "string" ? record.label : undefined,
        series: record.series,
        obligationIds: Array.isArray(record.obligationIds)
          ? record.obligationIds.filter((id): id is string => typeof id === "string")
          : [],
        comparisonBaselines: baselines,
      },
    ];
  });
}

// Resolve one section axis (e.g. "x", "p_x") to its exported value for a single
// crossing, preferring the named coordinate/extra maps and falling back to the
// state vector by name. No physics: it only looks the value up.
function resolveAxisValue(
  axis: string,
  coordinates: Record<string, unknown> | undefined,
  extra: Record<string, unknown> | undefined,
  state: unknown[] | undefined,
  stateNames: string[],
): number | null {
  if (coordinates && typeof coordinates[axis] === "number") {
    return coordinates[axis] as number;
  }
  if (extra && typeof extra[axis] === "number") {
    return extra[axis] as number;
  }
  const column = stateNames.indexOf(axis);
  if (column >= 0 && state && typeof state[column] === "number") {
    return state[column] as number;
  }
  return null;
}

/** Read the Poincaré sections Python attached to the trajectory metadata. */
export function poincareSections(trajectory: Trajectory): PoincareSection[] {
  const raw = trajectory.metadata?.poincareSections;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.flatMap((item) => {
    const section = asRecord(item);
    if (!section) {
      return [];
    }
    const axes =
      Array.isArray(section.axes) && section.axes.every((axis) => typeof axis === "string")
        ? (section.axes as string[])
        : [];
    if (axes.length < 2) {
      return [];
    }
    const stateNames =
      Array.isArray(section.stateNames) && section.stateNames.every((name) => typeof name === "string")
        ? (section.stateNames as string[])
        : [];
    const rawPoints = Array.isArray(section.points) ? section.points : [];
    const points = rawPoints.flatMap((entry) => {
      const point = asRecord(entry);
      if (!point) {
        return [];
      }
      const coordinates = asRecord(point.coordinates);
      const extra = asRecord(point.extra);
      const state = Array.isArray(point.state) ? point.state : undefined;
      const axisValues: number[] = [];
      for (const axis of axes) {
        const value = resolveAxisValue(axis, coordinates, extra, state, stateNames);
        if (value === null) {
          return [];
        }
        axisValues.push(value);
      }
      const poincarePoint: PoincarePoint = { axisValues };
      if (typeof point.time === "number") {
        poincarePoint.time = point.time;
      }
      return [poincarePoint];
    });
    const value = typeof section.value === "number" ? section.value : undefined;
    return [
      {
        name: typeof section.name === "string" ? section.name : "section",
        coordinate: typeof section.coordinate === "string" ? section.coordinate : undefined,
        value,
        direction: typeof section.direction === "string" ? section.direction : undefined,
        axes,
        points,
      },
    ];
  });
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
    viewportBounds: isBounds(candidate.viewportBounds) ? candidate.viewportBounds : undefined,
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
