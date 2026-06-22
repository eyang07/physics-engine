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
  /** Per-frame body orientation channel, when the system exports one (BE-089). */
  orientation?: Record<string, unknown>;
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

/**
 * The body orientation Python exported alongside a rigid-body trajectory
 * (`trajectory.orientation`, BE-089). The quaternion series is the source of
 * truth for the body's attitude at each sample; `bodyAxes` is the same rotation
 * expressed as the body-frame triad in world coordinates. The viewer renders the
 * exported orientation and never re-integrates Euler's equations.
 */
export type Orientation = {
  /** e.g. "quaternion-wxyz" — the component order of each quaternion entry. */
  convention: string;
  rigor?: string;
  /** Per-frame orientation as [w, x, y, z], one entry per trajectory sample. */
  quaternion: [number, number, number, number][];
  /** The body-frame triad expressed in world coordinates, per frame. */
  bodyAxes?: { e1: Vector3Tuple[]; e2: Vector3Tuple[]; e3: Vector3Tuple[] };
};

/**
 * The Poinsot polhode construction Python exported under
 * `metadata.rigidBodyGeometry` (BE-087). In body-frame angular-momentum space the
 * motion lies on the intersection of the angular-momentum sphere (|L| constant)
 * and the kinetic-energy ellipsoid; `angularMomentumCurve` is that intersection
 * (the L-space polhode), while `polhode` is the matching curve traced by the
 * angular-velocity vector. The viewer draws these as exported; it never solves
 * Euler's equations.
 */
export type RigidBodyGeometry = {
  /** Principal moments of inertia [I1, I2, I3]. */
  principalMoments: Vector3Tuple;
  /** Radius of the body-frame angular-momentum sphere |L|. */
  sphereRadius: number;
  /** Semi-axes of the kinetic-energy ellipsoid in angular-momentum space. */
  ellipsoidSemiAxes: Vector3Tuple;
  /** Polhode in angular-velocity space, one point per trajectory sample. */
  polhode: Vector3Tuple[];
  /** Sphere ∩ ellipsoid curve in angular-momentum space, per sample. */
  angularMomentumCurve: Vector3Tuple[];
  /** Rigor label Python attached (the rollout diagnostics stay `measured`). */
  rigor?: string;
};

/**
 * The N-body orbit configuration Python exported in `metadata.rendererHints`
 * (BE-082). The bodies' positions are the leading `2 * bodyCount` state columns
 * (planar `x_i, y_i`), already shifted to the center-of-mass frame when
 * `centerOfMassFrame` is set. `bodyColors` names a stable per-body palette slot.
 */
export type NBodyConfig = {
  bodyCount: number;
  bodyColors: string[];
  centerOfMassFrame: boolean;
  bounds?: AxisBounds;
};

/**
 * A scalar field sampled over a 2D coordinate grid that Python evaluated and
 * exported under `metadata.fields.<name>` (BE-091). `values[i][j]` is the field
 * at `axes[0][i]` along the first coordinate and `axes[1][j]` along the second;
 * the viewer colors these samples as exported and never evaluates the field
 * itself. The scalar-field lens (FE-044) draws it as a heatmap with iso-contours;
 * potentials, curvature, and intensity all reuse the same primitive.
 */
export type ScalarField = {
  /** The field's source name, e.g. "electricPotential". */
  name: string;
  /** The two coordinate names spanning the grid, e.g. ["x", "y"]. */
  coordinates: [string, string];
  /** Sample positions along each coordinate: [firstAxis, secondAxis]. */
  axes: [number[], number[]];
  /** Grid dimensions [along axes[0], along axes[1]]. */
  shape: [number, number];
  /** Field values, the outer index running over the first coordinate. */
  values: number[][];
  /** How Python produced the samples, e.g. "symbolic-exact". */
  evaluation?: string;
};

/**
 * A vector field sampled over a 2D coordinate grid that Python evaluated and
 * exported under `metadata.fields.<name>` (BE-091). `components[i][j]` is the
 * vector `[u, v]` at `axes[0][i]`, `axes[1][j]`, and `magnitude[i][j]` its length
 * — both shipped by Python. The vector-field lens (FE-045) draws glyphs from
 * these as exported; it never differentiates a potential to get them.
 */
export type VectorField = {
  name: string;
  coordinates: [string, string];
  axes: [number[], number[]];
  shape: [number, number];
  /** Components per grid point: `components[i][j] = [u, v]`. */
  components: number[][][];
  /** Vector length per grid point, as exported. */
  magnitude: number[][];
};

/**
 * Integrated field-line / streamline polylines Python exported under
 * `metadata.fields.<name>` (BE-091). Each entry in `lines` is one polyline as a
 * list of `[x, y]` points in field coordinates; the lens draws them as exported
 * and never integrates the field itself.
 */
export type FieldLines = {
  name: string;
  lines: [number, number][][];
};

/**
 * A 1D scalar field sampled over a coordinate and a sequence of times that Python
 * evaluated and exported under `metadata.fields.<name>` (BE-094 string, BE-096
 * wave packet). `values[t][i]` is the displacement/amplitude at time `times[t]`
 * and position `axis[i]`. The 1D wave lens (FE-046) animates these frames; it
 * plays back the exported series and never re-solves the wave equation.
 */
export type ScalarFieldSeries = {
  name: string;
  /** The single spatial coordinate name, e.g. "x". */
  coordinate: string;
  /** Sample positions along the coordinate. */
  axis: number[];
  /** Sample times, one per frame. */
  times: number[];
  /** `[frameCount, sampleCount]`. */
  shape: [number, number];
  /** Field values per frame: `values[t][i]`. */
  values: number[][];
  /** The solution variant Python tagged, e.g. a standing vs traveling label. */
  variant?: string;
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
  return parseCertificateSeriesList(trajectory.metadata?.certificateSeries);
}

/** Parse a raw `certificateSeries` array (shared by trajectory + verification data). */
export function parseCertificateSeriesList(raw: unknown): CertificateSeries[] {
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

function isQuaternionTuple(value: unknown): value is [number, number, number, number] {
  return Array.isArray(value) && value.length === 4 && value.every((item) => typeof item === "number");
}

function vector3List(value: unknown): Vector3Tuple[] | null {
  if (!Array.isArray(value)) {
    return null;
  }
  const out: Vector3Tuple[] = [];
  for (const item of value) {
    if (!isNumberTuple3(item)) {
      return null;
    }
    out.push(item);
  }
  return out;
}

/**
 * Read the body orientation channel Python exported with the trajectory. Returns
 * null when the system carries no orientation (most systems are point masses) or
 * the channel is malformed, so callers can fall back to point playback.
 */
export function orientationChannel(trajectory: Trajectory): Orientation | null {
  const raw = asRecord(trajectory.orientation);
  if (!raw || typeof raw.convention !== "string" || !Array.isArray(raw.quaternion)) {
    return null;
  }
  const quaternion: [number, number, number, number][] = [];
  for (const item of raw.quaternion) {
    if (!isQuaternionTuple(item)) {
      return null;
    }
    quaternion.push(item);
  }
  if (quaternion.length === 0) {
    return null;
  }
  const axes = asRecord(raw.bodyAxes);
  let bodyAxes: Orientation["bodyAxes"];
  if (axes) {
    const e1 = vector3List(axes.e1);
    const e2 = vector3List(axes.e2);
    const e3 = vector3List(axes.e3);
    if (e1 && e2 && e3) {
      bodyAxes = { e1, e2, e3 };
    }
  }
  return {
    convention: raw.convention,
    rigor: typeof raw.rigor === "string" ? raw.rigor : undefined,
    quaternion,
    bodyAxes,
  };
}

/**
 * Read the rigid-body polhode geometry Python exported with the trajectory.
 * Returns null when the system carries no such geometry or the channel is
 * malformed, so the lens can fall back gracefully.
 */
export function rigidBodyGeometry(trajectory: Trajectory): RigidBodyGeometry | null {
  const raw = asRecord(trajectory.metadata?.rigidBodyGeometry);
  if (!raw) {
    return null;
  }
  const principalMoments = raw.principalMoments;
  const sphere = asRecord(raw.angularMomentumSphere);
  const ellipsoid = asRecord(raw.energyEllipsoid);
  const polhodeRaw = asRecord(raw.polhode);
  const curveRaw = asRecord(raw.angularMomentumCurve);
  if (!sphere || !ellipsoid || !polhodeRaw || !curveRaw) {
    return null;
  }
  if (!isNumberTuple3(principalMoments) || typeof sphere.radius !== "number") {
    return null;
  }
  if (!isNumberTuple3(ellipsoid.semiAxes)) {
    return null;
  }
  const polhode = vector3List(polhodeRaw.points);
  const angularMomentumCurve = vector3List(curveRaw.points);
  if (!polhode || !angularMomentumCurve) {
    return null;
  }
  return {
    principalMoments,
    sphereRadius: sphere.radius,
    ellipsoidSemiAxes: ellipsoid.semiAxes,
    polhode,
    angularMomentumCurve,
    rigor: typeof raw.rigor === "string" ? raw.rigor : undefined,
  };
}

/**
 * Read the N-body orbit configuration Python exported with the trajectory.
 * Returns null when the trajectory is not an N-body orbit payload or the channel
 * is malformed, so callers can fall back gracefully.
 */
export function nBodyConfig(trajectory: Trajectory): NBodyConfig | null {
  const raw = asRecord(trajectory.metadata?.rendererHints);
  if (!raw || raw.kind !== "n-body-orbits") {
    return null;
  }
  const bodyCount = asNumber(raw.bodyCount);
  if (bodyCount === undefined || bodyCount < 1) {
    return null;
  }
  const bodyColors = Array.isArray(raw.bodyColors)
    ? raw.bodyColors.filter((item): item is string => typeof item === "string")
    : [];
  return {
    bodyCount: Math.floor(bodyCount),
    bodyColors,
    centerOfMassFrame: raw.centerOfMassFrame === true,
    bounds: isBounds(raw.bounds) ? raw.bounds : undefined,
  };
}

function isNumberArray(value: unknown): value is number[] {
  return Array.isArray(value) && value.every((item) => typeof item === "number");
}

function parseScalarField(name: string, raw: Record<string, unknown>): ScalarField | null {
  const { axes, values } = raw;
  if (!Array.isArray(axes) || axes.length !== 2 || !isNumberArray(axes[0]) || !isNumberArray(axes[1])) {
    return null;
  }
  if (!Array.isArray(values) || !values.every(isNumberArray)) {
    return null;
  }
  const nx = axes[0].length;
  const ny = axes[1].length;
  // The grid must be consistent with its declared axes; a ragged or transposed
  // payload is rejected rather than drawn as a misleading field.
  if (nx < 2 || ny < 2 || values.length !== nx || !values.every((row) => row.length === ny)) {
    return null;
  }
  const coords = Array.isArray(raw.coordinates)
    ? raw.coordinates.filter((item): item is string => typeof item === "string")
    : [];
  return {
    name,
    coordinates: [coords[0] ?? "x", coords[1] ?? "y"],
    axes: [axes[0], axes[1]],
    shape: [nx, ny],
    values: values as number[][],
    evaluation: typeof raw.evaluation === "string" ? raw.evaluation : undefined,
  };
}

/**
 * Read a scalar-field grid Python exported under `metadata.fields` (BE-091),
 * preferring one named `preferredName` and otherwise taking the first field
 * tagged as a scalar field. Returns null when the trajectory carries no scalar
 * field or the channel is malformed, so the lens can fall back to a placeholder
 * instead of drawing a broken grid.
 */
export function scalarField(trajectory: Trajectory, preferredName?: string): ScalarField | null {
  for (const [name, record] of fieldsByKind(trajectory, "scalar-field", preferredName)) {
    const parsed = parseScalarField(name, record);
    if (parsed) {
      return parsed;
    }
  }
  return null;
}

function fieldsByKind(trajectory: Trajectory, kind: string, preferredName?: string): [string, Record<string, unknown>][] {
  const fields = asRecord(trajectory.metadata?.fields);
  if (!fields) {
    return [];
  }
  const names = Object.keys(fields);
  if (preferredName && names.includes(preferredName)) {
    names.sort((a, b) => (a === preferredName ? -1 : b === preferredName ? 1 : 0));
  }
  const matches: [string, Record<string, unknown>][] = [];
  for (const name of names) {
    const record = asRecord(fields[name]);
    if (record && (record.kind ?? record.rendererHint) === kind) {
      matches.push([name, record]);
    }
  }
  return matches;
}

/**
 * Read a vector-field grid Python exported under `metadata.fields` (BE-091),
 * preferring one named `preferredName`. Returns null when no well-formed vector
 * field is present, so the lens can skip the glyph overlay gracefully.
 */
export function vectorField(trajectory: Trajectory, preferredName?: string): VectorField | null {
  for (const [name, raw] of fieldsByKind(trajectory, "vector-field", preferredName)) {
    const { axes, components, magnitude } = raw;
    if (!Array.isArray(axes) || axes.length !== 2 || !isNumberArray(axes[0]) || !isNumberArray(axes[1])) {
      continue;
    }
    const nx = axes[0].length;
    const ny = axes[1].length;
    const componentsOk =
      Array.isArray(components) &&
      components.length === nx &&
      components.every(
        (row) => Array.isArray(row) && row.length === ny && row.every((cell) => isNumberArray(cell) && cell.length >= 2),
      );
    const magnitudeOk =
      Array.isArray(magnitude) && magnitude.length === nx && magnitude.every((row) => isNumberArray(row) && row.length === ny);
    if (!componentsOk || !magnitudeOk) {
      continue;
    }
    const coords = Array.isArray(raw.coordinates)
      ? raw.coordinates.filter((item): item is string => typeof item === "string")
      : [];
    return {
      name,
      coordinates: [coords[0] ?? "x", coords[1] ?? "y"],
      axes: [axes[0], axes[1]],
      shape: [nx, ny],
      components: components as number[][][],
      magnitude: magnitude as number[][],
    };
  }
  return null;
}

/**
 * Read integrated field-line polylines Python exported under `metadata.fields`
 * (BE-091), preferring one named `preferredName`. Returns null when no well-formed
 * field-line set is present.
 */
export function fieldLines(trajectory: Trajectory, preferredName?: string): FieldLines | null {
  for (const [name, raw] of fieldsByKind(trajectory, "field-lines", preferredName)) {
    const { lines } = raw;
    if (!Array.isArray(lines)) {
      continue;
    }
    const parsed = lines.filter(
      (line): line is [number, number][] =>
        Array.isArray(line) && line.every((point) => isNumberArray(point) && point.length >= 2),
    ) as [number, number][][];
    if (parsed.length === 0) {
      continue;
    }
    return { name, lines: parsed };
  }
  return null;
}

/**
 * Read every 1D scalar-field time series Python exported under `metadata.fields`
 * (kind `scalar-field-series`), in declaration order. A system can carry more
 * than one (a standing and a traveling string solution; a packet amplitude and
 * its envelope intensity), so the wave lens offers a toggle between them. Returns
 * an empty array when none are present or well-formed.
 */
export function scalarFieldSeriesList(trajectory: Trajectory): ScalarFieldSeries[] {
  const out: ScalarFieldSeries[] = [];
  for (const [name, raw] of fieldsByKind(trajectory, "scalar-field-series")) {
    const { axes, time, values } = raw;
    if (!Array.isArray(axes) || axes.length < 1 || !isNumberArray(axes[0])) {
      continue;
    }
    if (!isNumberArray(time) || !Array.isArray(values) || !values.every(isNumberArray)) {
      continue;
    }
    const axis = axes[0];
    const frameCount = time.length;
    const sampleCount = axis.length;
    if (
      frameCount < 1 ||
      sampleCount < 2 ||
      values.length !== frameCount ||
      !values.every((row) => row.length === sampleCount)
    ) {
      continue;
    }
    const coords = Array.isArray(raw.coordinates)
      ? raw.coordinates.filter((item): item is string => typeof item === "string")
      : [];
    out.push({
      name,
      coordinate: coords[0] ?? "x",
      axis,
      times: time,
      shape: [frameCount, sampleCount],
      values: values as number[][],
      variant: typeof raw.variant === "string" ? raw.variant : undefined,
    });
  }
  return out;
}

/**
 * A 2D scalar field sampled over a coordinate grid and a sequence of times that
 * Python exported under `metadata.fields.<name>` (kind `scalar-field-series` with
 * two coordinate axes; BE-095 membrane). `frames[t][i][j]` is the displacement at
 * time `times[t]`, at `axes[0][i]` along the first coordinate and `axes[1][j]`
 * along the second. The membrane lens (FE-047) lifts these frames into an animated
 * displacement surface; it plays back the exported series and never re-solves the
 * wave equation.
 */
export type SurfaceFieldSeries = {
  name: string;
  /** The two coordinate names spanning the grid, e.g. ["x", "y"]. */
  coordinates: [string, string];
  /** Sample positions along each coordinate: [firstAxis, secondAxis]. */
  axes: [number[], number[]];
  /** Sample times, one per frame. */
  times: number[];
  /** `[frameCount, alongAxes0, alongAxes1]`. */
  shape: [number, number, number];
  /** Displacement per frame: `frames[t][i][j]`, `i` over `axes[0]`. */
  frames: number[][][];
  /** The solution variant Python tagged, e.g. a modal-superposition label. */
  variant?: string;
};

function isNumberGrid(value: unknown): value is number[][] {
  return Array.isArray(value) && value.length > 0 && value.every(isNumberArray);
}

/**
 * Read every 2D scalar-field time series Python exported under `metadata.fields`
 * (kind `scalar-field-series` with two coordinate axes), in declaration order. A
 * membrane carries one per shape family (a rectangular and a circular modal
 * superposition), so the membrane lens offers a selector between them. The 1D
 * wave series (one coordinate axis) are read separately by `scalarFieldSeriesList`;
 * the two readers partition the `scalar-field-series` channels by axis count.
 */
export function surfaceFieldSeriesList(trajectory: Trajectory): SurfaceFieldSeries[] {
  const out: SurfaceFieldSeries[] = [];
  for (const [name, raw] of fieldsByKind(trajectory, "scalar-field-series")) {
    const { axes, time, values } = raw;
    // A surface series spans two coordinate axes (a 1D wave series spans one).
    if (!Array.isArray(axes) || axes.length !== 2 || !isNumberArray(axes[0]) || !isNumberArray(axes[1])) {
      continue;
    }
    if (!isNumberArray(time) || !Array.isArray(values) || !values.every(isNumberGrid)) {
      continue;
    }
    const n0 = axes[0].length;
    const n1 = axes[1].length;
    const frameCount = time.length;
    if (
      n0 < 2 ||
      n1 < 2 ||
      frameCount < 1 ||
      values.length !== frameCount ||
      !values.every((frame) => frame.length === n0 && frame.every((row) => row.length === n1))
    ) {
      continue;
    }
    const coords = Array.isArray(raw.coordinates)
      ? raw.coordinates.filter((item): item is string => typeof item === "string")
      : [];
    out.push({
      name,
      coordinates: [coords[0] ?? "x", coords[1] ?? "y"],
      axes: [axes[0], axes[1]],
      times: time,
      shape: [frameCount, n0, n1],
      frames: values as number[][][],
      variant: typeof raw.variant === "string" ? raw.variant : undefined,
    });
  }
  return out;
}

/**
 * A surface-of-revolution embedding mesh and the geodesic drawn on it, exported
 * under `metadata.surfaceGeometry` (BE-100/BE-101). `mesh.points` is the surface
 * sampled on a `(u, phi)` grid and flattened row-major (u outer, phi inner), in
 * embedding `[x, y, z]` coordinates; `mesh.triangles` indexes those points.
 * `geodesic` is the integrated geodesic as an embedded polyline. The surface-
 * geodesic lens (FE-049) draws both as exported; it never re-derives the surface
 * or re-integrates the geodesic.
 */
export type SurfaceMesh = {
  /** Surface family name, e.g. "torus", "sphere". */
  family: string;
  /** Grid dimensions [along u, along phi]. */
  shape: [number, number];
  /** Vertex positions in embedding coordinates, flattened row-major (u over phi). */
  points: Vector3Tuple[];
  /** Triangle vertex-index triples into `points`. */
  triangles: [number, number, number][];
};

/**
 * The curvature scalar field sampled on the same `(u, phi)` grid as the mesh
 * (BE-105), flattened per-vertex to align with `SurfaceMesh.points`. The
 * surface-geodesic lens (FE-050) colors the mesh by this field; the values are
 * Python's symbolic-exact Gaussian curvature, never recomputed in the viewer.
 */
export type SurfaceCurvature = {
  /** Field source name, e.g. "gaussianCurvature". */
  name: string;
  /** Human-readable quantity, e.g. "Gaussian curvature". */
  quantity?: string;
  /** Per-vertex values, flattened row-major (u over phi), aligned with mesh.points. */
  values: number[];
  /** `[min, max]` over the finite values, for the color scale's domain. */
  range: [number, number];
};

export type SurfaceGeodesicGeometry = {
  family: string;
  mesh: SurfaceMesh;
  /** Geodesic polyline drawn on the surface, in embedding coordinates. */
  geodesic: Vector3Tuple[];
  /** Curvature scalar field over the mesh, when exported (BE-105). */
  curvature?: SurfaceCurvature;
};

// Flatten a `values[u][phi]` grid (validated against the mesh shape) into a
// per-vertex array in the same row-major order as the mesh points, returning
// null when the grid is ragged or mis-shaped.
function flattenSurfaceField(
  raw: Record<string, unknown>,
  uCount: number,
  phiCount: number,
): number[] | null {
  const values = raw.values;
  if (!Array.isArray(values) || values.length !== uCount) {
    return null;
  }
  const flat: number[] = [];
  for (const row of values) {
    if (!isNumberArray(row) || row.length !== phiCount) {
      return null;
    }
    flat.push(...row);
  }
  return flat;
}

/**
 * Read the surface-embedding mesh + geodesic Python exported under
 * `metadata.surfaceGeometry`. Returns null when the trajectory carries no such
 * geometry or any channel is malformed, so the lens can fall back gracefully
 * instead of drawing a broken mesh.
 */
export function surfaceGeodesicGeometry(trajectory: Trajectory): SurfaceGeodesicGeometry | null {
  const raw = asRecord(trajectory.metadata?.surfaceGeometry);
  if (!raw) {
    return null;
  }
  const meshRaw = asRecord(raw.surfaceMesh);
  const geodesicRaw = asRecord(raw.geodesic);
  if (!meshRaw || !geodesicRaw) {
    return null;
  }
  const shape = meshRaw.shape;
  if (
    !Array.isArray(shape) ||
    shape.length !== 2 ||
    !shape.every((item) => typeof item === "number")
  ) {
    return null;
  }
  const [uCount, phiCount] = shape as [number, number];
  if (uCount < 2 || phiCount < 2) {
    return null;
  }
  // points: number[][][] sampled on the (u, phi) grid -> flat Vector3Tuple[] in
  // row-major (u outer, phi inner) order, matching the triangle indexing.
  const pointsRaw = meshRaw.points;
  if (!Array.isArray(pointsRaw) || pointsRaw.length !== uCount) {
    return null;
  }
  const points: Vector3Tuple[] = [];
  for (const row of pointsRaw) {
    if (!Array.isArray(row) || row.length !== phiCount) {
      return null;
    }
    for (const point of row) {
      if (!isNumberTuple3(point)) {
        return null;
      }
      points.push(point);
    }
  }
  const trianglesRaw = meshRaw.triangles;
  if (!Array.isArray(trianglesRaw)) {
    return null;
  }
  const triangles: [number, number, number][] = [];
  for (const triangle of trianglesRaw) {
    if (!isNumberArray(triangle) || triangle.length !== 3) {
      return null;
    }
    if (triangle.some((index) => index < 0 || index >= points.length)) {
      return null;
    }
    triangles.push([triangle[0], triangle[1], triangle[2]]);
  }
  if (triangles.length === 0) {
    return null;
  }
  const geodesic = vector3List(geodesicRaw.points);
  if (!geodesic || geodesic.length < 2) {
    return null;
  }
  const family = typeof raw.family === "string" ? raw.family : "surface";
  const geometry: SurfaceGeodesicGeometry = {
    family,
    mesh: { family, shape: [uCount, phiCount], points, triangles },
    geodesic,
  };

  // Curvature is optional: an absent or mis-shaped field just leaves the mesh
  // uncolored rather than failing the whole lens.
  const curvatureRaw = asRecord(raw.curvature);
  if (curvatureRaw) {
    const flat = flattenSurfaceField(curvatureRaw, uCount, phiCount);
    if (flat) {
      let min = Infinity;
      let max = -Infinity;
      for (const value of flat) {
        if (!Number.isFinite(value)) {
          continue;
        }
        if (value < min) min = value;
        if (value > max) max = value;
      }
      if (Number.isFinite(min) && Number.isFinite(max)) {
        geometry.curvature = {
          name: typeof curvatureRaw.name === "string" ? curvatureRaw.name : "curvature",
          quantity: typeof curvatureRaw.quantity === "string" ? curvatureRaw.quantity : undefined,
          values: flat,
          range: [min, max],
        };
      }
    }
  }

  return geometry;
}

/**
 * One sampled wavefront from the variable-speed ray bundle (BE-097): the ray
 * positions along the front at a snapshot time, with the measured intensity proxy
 * for each segment between adjacent rays. Where neighbouring rays converge toward a
 * caustic the segment intensity rises, so the lens colors the front by it.
 */
export type WavefrontSnapshot = {
  time: number;
  /** Ray positions along the front, `[x, y]`. */
  points: [number, number][];
  /** Per-segment intensity, length `points.length - 1`. */
  intensity: number[];
};

/**
 * The exported wavefront surface + measured intensity field (BE-097), zipped per
 * snapshot. `intensityMax` is a robust high-percentile value used as the color
 * scale's upper bound so a single near-singular caustic cell does not wash out the
 * band. The intensity is `measured` (finite-difference ray spreading), never a
 * proof of focusing — the lens renders the exported diagnostic.
 */
export type WavefrontField = {
  snapshots: WavefrontSnapshot[];
  intensityMax: number;
};

function asPoint2(value: unknown): [number, number] | null {
  return isNumberArray(value) && value.length >= 2 ? [value[0], value[1]] : null;
}

/**
 * Read the exported wavefront surface (`metadata.fields.wavefrontSurface`) and the
 * measured intensity field (`metadata.fields.wavefrontIntensity`), aligned per
 * snapshot. Returns null when either channel is absent or malformed, so the
 * wavefront lens falls back to drawing rays without the intensity band.
 */
export function wavefrontField(trajectory: Trajectory): WavefrontField | null {
  const fields = asRecord(trajectory.metadata?.fields);
  if (!fields) {
    return null;
  }
  const surface = asRecord(fields.wavefrontSurface);
  const intensity = asRecord(fields.wavefrontIntensity);
  if (!surface || !intensity) {
    return null;
  }
  const points = surface.points;
  const times = surface.time;
  const values = intensity.values;
  if (!Array.isArray(points) || !isNumberArray(times) || !Array.isArray(values)) {
    return null;
  }
  const snapshots: WavefrontSnapshot[] = [];
  const count = Math.min(points.length, times.length, values.length);
  for (let s = 0; s < count; s += 1) {
    const rawPoints = points[s];
    const segments = values[s];
    if (!Array.isArray(rawPoints) || !isNumberArray(segments)) {
      continue;
    }
    const parsed = rawPoints.flatMap((point) => {
      const tuple = asPoint2(point);
      return tuple ? [tuple] : [];
    });
    if (parsed.length < 2) {
      continue;
    }
    snapshots.push({ time: times[s], points: parsed, intensity: segments });
  }
  if (snapshots.length === 0) {
    return null;
  }
  // Robust upper bound (95th percentile), mirroring the vector field's
  // `robustMagnitudeMax`: a single caustic spike should not flatten the band.
  const sorted = snapshots
    .flatMap((snapshot) => snapshot.intensity)
    .filter((value) => Number.isFinite(value))
    .sort((a, b) => a - b);
  const cutoff = sorted.length > 0 ? sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))] : 1;
  return { snapshots, intensityMax: Math.max(cutoff, 1e-6) };
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
