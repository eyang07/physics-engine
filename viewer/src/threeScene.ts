import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { theme } from "./design/theme";
import { FlowField } from "./flow";
import {
  rendererHints,
  type ReferenceGeometryHint,
  type RendererHints,
  type Trajectory,
  type Vector3Tuple,
} from "./data/trajectory";

export type { Trajectory };

export type ThreeMode =
  | "pendulumHamiltonian"
  | "sphereGeodesic"
  | "chargedParticle"
  | "uniformGravity"
  | "idealSpring"
  | "keplerOrbit"
  | "beadHoop"
  | "lorenzAttractor"
  | "henonHeilesFlow";

const PENDULUM_GRAVITY = 9.81;

type LorenzTransform = {
  center: THREE.Vector3;
  scale: number;
};

type PotentialSurfaceMetadata = {
  xValues: number[];
  yValues: number[];
  values: number[][];
  energy?: number;
};

function vectorFromTuple(value: Vector3Tuple): THREE.Vector3 {
  return new THREE.Vector3(value[0], value[1], value[2]);
}

function referenceHint(hints: RendererHints, kind: string): ReferenceGeometryHint | undefined {
  return hints.referenceGeometry?.find((item) => item.kind === kind);
}

function axisRange(hints: RendererHints, axis: "x" | "y" | "z", fallback: [number, number]): [number, number] {
  return hints.bounds?.[axis] ?? fallback;
}

function flowRange(hints: RendererHints, axis: "x" | "z", fallback: [number, number]): [number, number] {
  return hints.flow?.bounds?.[axis] ?? fallback;
}

function makeLabel(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 96;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Unable to create label canvas.");
  }

  context.font = '700 42px "Space Grotesk", "IBM Plex Sans", system-ui, sans-serif';
  context.fillStyle = theme.textPrimary;
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
    }),
  );
  sprite.scale.set(0.52, 0.2, 1);
  return sprite;
}

function lineFromPoints(
  points: THREE.Vector3[],
  color: THREE.ColorRepresentation,
  opacity = 1,
): THREE.Line {
  return new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({
      color,
      transparent: opacity < 1,
      opacity,
    }),
  );
}

function vectorArrow(
  start: THREE.Vector3,
  vector: THREE.Vector3,
  color: THREE.ColorRepresentation,
  opacity = 0.55,
): THREE.Group {
  const group = new THREE.Group();
  const length = vector.length();
  if (length < 1e-6) {
    return group;
  }

  const end = start.clone().add(vector);
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: opacity < 1,
    opacity,
  });
  group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([start, end]), material));

  const cone = new THREE.Mesh(
    new THREE.ConeGeometry(0.026, 0.095, 14),
    new THREE.MeshBasicMaterial({
      color,
      transparent: opacity < 1,
      opacity,
    }),
  );
  cone.position.copy(end);
  cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), vector.clone().normalize());
  group.add(cone);
  return group;
}

function contextLine(points: THREE.Vector3[], opacity = 0.28): THREE.Line {
  return lineFromPoints(points, new THREE.Color(theme.cool), opacity);
}

function trajectoryEvery<T>(items: T[], count: number): T[] {
  if (items.length <= count) {
    return items;
  }
  const step = Math.max(1, Math.floor(items.length / count));
  return items.filter((_item, index) => index % step === 0);
}

function rawLorenzPoint(state: number[]): THREE.Vector3 {
  return new THREE.Vector3(state[0], state[2], state[1]);
}

function lorenzPoint(state: number[], transform: LorenzTransform): THREE.Vector3 {
  return rawLorenzPoint(state).sub(transform.center).multiplyScalar(transform.scale);
}

function lorenzTransform(data: Trajectory): LorenzTransform {
  const rawPoints = data.states.map(rawLorenzPoint);
  const box = new THREE.Box3().setFromPoints(rawPoints);
  const size = new THREE.Vector3();
  const center = new THREE.Vector3();
  box.getSize(size);
  box.getCenter(center);
  const scale = 3.1 / Math.max(size.x, size.y, size.z, 1);
  return { center, scale };
}

function makeFadingTrail(length: number, color: THREE.ColorRepresentation): THREE.Line {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(length * 3);
  const colors = new Float32Array(length * 3);
  const base = new THREE.Color(color);

  for (let index = 0; index < length; index += 1) {
    const alpha = index / Math.max(1, length - 1);
    const brightness = alpha * alpha;
    colors[index * 3] = base.r * brightness;
    colors[index * 3 + 1] = base.g * brightness;
    colors[index * 3 + 2] = base.b * brightness;
  }

  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return new THREE.Line(
    geometry,
    new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
    }),
  );
}

function pendulumHamiltonian(theta: number, momentum: number): number {
  return 0.5 * momentum * momentum + PENDULUM_GRAVITY * (1 - Math.cos(theta));
}

function pendulumPoint(theta: number, momentum: number, energyOffset = 0): THREE.Vector3 {
  return new THREE.Vector3(
    theta * 0.62,
    (pendulumHamiltonian(theta, momentum) + energyOffset) * 0.1,
    momentum * 0.42,
  );
}

function makePendulumSurface(): THREE.Mesh {
  const thetaMin = -Math.PI;
  const thetaMax = Math.PI;
  const momentumMin = -3.2;
  const momentumMax = 3.2;
  const thetaSegments = 88;
  const momentumSegments = 54;
  const geometry = new THREE.BufferGeometry();
  const positions: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  const color = new THREE.Color();

  for (let i = 0; i <= thetaSegments; i += 1) {
    const theta = thetaMin + (i / thetaSegments) * (thetaMax - thetaMin);
    for (let j = 0; j <= momentumSegments; j += 1) {
      const momentum = momentumMin + (j / momentumSegments) * (momentumMax - momentumMin);
      const point = pendulumPoint(theta, momentum);
      positions.push(point.x, point.y, point.z);
      color.setHSL(0.52 - Math.min(0.38, pendulumHamiltonian(theta, momentum) / 42), 0.42, 0.58);
      colors.push(color.r, color.g, color.b);
    }
  }

  const row = momentumSegments + 1;
  for (let i = 0; i < thetaSegments; i += 1) {
    for (let j = 0; j < momentumSegments; j += 1) {
      const a = i * row + j;
      const b = (i + 1) * row + j;
      const c = (i + 1) * row + j + 1;
      const d = i * row + j + 1;
      indices.push(a, b, d, b, c, d);
    }
  }

  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();

  return new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.72,
      roughness: 0.72,
      metalness: 0.04,
      side: THREE.DoubleSide,
    }),
  );
}

// Advected particles drifting along the Hamiltonian phase-space field, replacing
// the old discrete arrow grid. The same primitive is meant to scale to fluids.
function makePendulumFlow(): FlowField {
  return new FlowField({
    // theta_dot = p,  p_dot = -g sin(theta)
    field: (theta, momentum) => [momentum, -PENDULUM_GRAVITY * Math.sin(theta)],
    bounds: { xMin: -2.9, xMax: 2.9, yMin: -3.05, yMax: 3.05 },
    toPosition: (theta, momentum) => pendulumPoint(theta, momentum, 0.14),
    count: 900,
    rate: 0.16,
    life: 3.0,
    size: 0.05,
  });
}

function makePendulumHamiltonianGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  group.rotation.y = -0.22;
  group.add(makePendulumSurface());
  group.add(
    contextLine(data.states.map((state) => pendulumPoint(state[0], state[1], 0.08)), 0.34),
  );

  const thetaLabel = makeLabel("θ");
  thetaLabel.position.copy(pendulumPoint(Math.PI + 0.4, 0, 0.2));
  group.add(thetaLabel);

  const momentumLabel = makeLabel("pθ");
  momentumLabel.position.copy(pendulumPoint(0, 3.55, 0.2));
  group.add(momentumLabel);

  const energyLabel = makeLabel("H");
  energyLabel.position.set(-2.75, 2.35, -1.95);
  group.add(energyLabel);

  return group;
}

function makeSphereGeodesicGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const sphere = new THREE.Mesh(
    new THREE.SphereGeometry(1, 64, 36),
    new THREE.MeshStandardMaterial({
      color: 0xdbe8f0,
      transparent: true,
      opacity: 0.42,
      roughness: 0.72,
      metalness: 0.02,
    }),
  );
  group.add(sphere);

  const wire = new THREE.Mesh(
    new THREE.SphereGeometry(1.003, 32, 16),
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(theme.textFaint),
      wireframe: true,
      transparent: true,
      opacity: 0.16,
    }),
  );
  group.add(wire);

  group.add(
    contextLine(data.states.map((state) => new THREE.Vector3(state[4], state[5], state[6])), 0.36),
  );

  const north = makeLabel("N");
  north.position.set(0, 1.28, 0);
  group.add(north);
  return group;
}

function makeChargedParticleGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => new THREE.Vector3(state[0], state[2] * 0.62, state[1]));
  group.add(contextLine(points, 0.36));

  const guideMaterial = new THREE.LineBasicMaterial({
    color: new THREE.Color(theme.textFaint),
    transparent: true,
    opacity: 0.18,
  });
  for (const y of [-0.7, 0.05, 0.8]) {
    const ring = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(
        Array.from({ length: 129 }, (_, index) => {
          const angle = (index / 128) * Math.PI * 2;
          return new THREE.Vector3(Math.cos(angle) * 0.86, y, Math.sin(angle) * 0.86);
        }),
      ),
      guideMaterial,
    );
    group.add(ring);
  }

  const fieldMaterial = new THREE.LineBasicMaterial({
    color: new THREE.Color(theme.cool),
    transparent: true,
    opacity: 0.24,
  });
  const coneMaterial = new THREE.MeshBasicMaterial({
    color: new THREE.Color(theme.cool),
    transparent: true,
    opacity: 0.42,
  });
  for (let x = -1.2; x <= 1.21; x += 0.6) {
    for (let z = -1.2; z <= 1.21; z += 0.6) {
      const start = new THREE.Vector3(x, -1.05, z);
      const end = new THREE.Vector3(x, 1.05, z);
      group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([start, end]), fieldMaterial));
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.028, 0.12, 12), coneMaterial);
      cone.position.copy(end);
      group.add(cone);
    }
  }

  for (const point of trajectoryEvery(points, 14)) {
    const tangent = new THREE.Vector3(-point.z, 0, point.x).normalize().multiplyScalar(0.16);
    group.add(vectorArrow(point.clone().setY(point.y + 0.04), tangent, new THREE.Color(theme.textFaint), 0.26));
  }

  const label = makeLabel("B");
  label.position.set(1.48, 1.2, 1.22);
  group.add(label);
  return group;
}

function makeUniformGravityGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => new THREE.Vector3(state[0] - 0.9, state[1] * 0.42 - 0.65, 0));
  group.add(contextLine(points, 0.34));

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(3.8, 1.4, 18, 3),
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(theme.textFaint),
      wireframe: true,
      transparent: true,
      opacity: 0.18,
      side: THREE.DoubleSide,
    }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0.28, -0.74, 0);
  group.add(ground);

  for (let x = -1.3; x <= 1.8; x += 0.45) {
    for (let z = -0.55; z <= 0.56; z += 0.55) {
      group.add(
        vectorArrow(
          new THREE.Vector3(x, 0.98, z),
          new THREE.Vector3(0, -0.42, 0),
          new THREE.Color(theme.cool),
          0.3,
        ),
      );
    }
  }

  for (const state of trajectoryEvery(data.states, 12)) {
    const position = new THREE.Vector3(state[0] - 0.9, state[1] * 0.42 - 0.65, 0.04);
    const velocity = new THREE.Vector3(state[2], state[3] * 0.42, 0).normalize().multiplyScalar(0.17);
    group.add(vectorArrow(position, velocity, new THREE.Color(theme.textFaint), 0.32));
  }

  const label = makeLabel("g");
  label.position.set(1.42, 0.86, -0.55);
  group.add(label);
  return group;
}

function makeIdealSpringGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const xValues = data.states.map((state) => state[0]);
  const span = Math.max(1.1, ...xValues.map(Math.abs));
  const pointTrace = xValues.map((x, index) => new THREE.Vector3(x, -0.04, Math.sin(index * 0.032) * 0.045));
  group.add(contextLine(pointTrace, 0.28));

  const wall = new THREE.Mesh(
    new THREE.BoxGeometry(0.1, 1.05, 0.1),
    new THREE.MeshStandardMaterial({
      color: new THREE.Color(theme.cool),
      transparent: true,
      opacity: 0.82,
      roughness: 0.72,
    }),
  );
  wall.position.set(-1.42, 0, 0);
  group.add(wall);

  const rail = lineFromPoints(
    [new THREE.Vector3(-1.42, -0.34, 0), new THREE.Vector3(1.42, -0.34, 0)],
    new THREE.Color(theme.textFaint),
    0.4,
  );
  group.add(rail);

  const equilibrium = lineFromPoints([new THREE.Vector3(0, -0.48, 0), new THREE.Vector3(0, 0.48, 0)], new THREE.Color(theme.cool), 0.32);
  group.add(equilibrium);

  for (let x = -span; x <= span + 1e-6; x += span / 3) {
    if (Math.abs(x) < 0.08) {
      continue;
    }
    const direction = new THREE.Vector3(-Math.sign(x) * 0.18, 0, 0);
    group.add(vectorArrow(new THREE.Vector3(x, 0.42, 0), direction, new THREE.Color(theme.cool), 0.28));
  }

  const potential = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(
      Array.from({ length: 96 }, (_, index) => {
        const x = -span + (index / 95) * span * 2;
        return new THREE.Vector3(x, 0.015 * x * x - 0.56, 0);
      }),
    ),
    new THREE.LineBasicMaterial({
      color: new THREE.Color(theme.textFaint),
      transparent: true,
      opacity: 0.24,
    }),
  );
  group.add(potential);
  return group;
}

function makeKeplerGroup(data: Trajectory, hints: RendererHints): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => new THREE.Vector3(state[4], 0, state[5]));
  group.add(contextLine(points, 0.36));
  const centralBody = referenceHint(hints, "centralBody");
  const orbitalPlane = referenceHint(hints, "orbitalPlane");
  const radialRings = referenceHint(hints, "radialRings");
  const forceSamples = referenceHint(hints, "centralForceSamples");
  const centralRadius = centralBody?.radius ?? 0.105;
  const centralPosition = centralBody?.position ? vectorFromTuple(centralBody.position) : new THREE.Vector3(0, 0, 0);
  const planeRadius = orbitalPlane?.radius ?? 1.72;

  const focus = new THREE.Mesh(
    new THREE.SphereGeometry(centralRadius, 32, 18),
    new THREE.MeshStandardMaterial({
      color: 0xf0b44c,
      emissive: 0x8b4a16,
      emissiveIntensity: 0.28,
      roughness: 0.35,
    }),
  );
  focus.position.copy(centralPosition);
  group.add(focus);

  const plane = new THREE.Mesh(
    new THREE.CircleGeometry(planeRadius, 96),
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(theme.textFaint),
      transparent: true,
      opacity: 0.07,
      side: THREE.DoubleSide,
    }),
  );
  plane.rotation.x = -Math.PI / 2;
  group.add(plane);

  const ringRadii = radialRings?.radii ?? [0.45, 0.77, 1.09, 1.41];
  for (const radius of ringRadii) {
    const ring = lineFromPoints(
      Array.from({ length: 129 }, (_, index) => {
        const angle = (index / 128) * Math.PI * 2;
        return new THREE.Vector3(Math.cos(angle) * radius, 0.005, Math.sin(angle) * radius);
      }),
      new THREE.Color(theme.textFaint),
      0.16,
    );
    group.add(ring);
  }

  const forceRadii = forceSamples?.radii ?? [0.55, 0.97, 1.39];
  const forceAngles = Math.max(3, Math.floor(forceSamples?.angles ?? 8));
  for (const radius of forceRadii) {
    for (let angleIndex = 0; angleIndex < forceAngles; angleIndex += 1) {
      const angle = (angleIndex / forceAngles) * Math.PI * 2;
      const start = new THREE.Vector3(Math.cos(angle) * radius, 0.08, Math.sin(angle) * radius);
      const inward = start.clone().multiplyScalar(-0.13 / Math.max(0.55, radius));
      inward.y = 0;
      group.add(vectorArrow(start, inward, new THREE.Color(theme.cool), 0.26));
    }
  }

  for (const point of trajectoryEvery(points, 10)) {
    group.add(lineFromPoints([new THREE.Vector3(0, 0.015, 0), point.clone().setY(0.015)], new THREE.Color(theme.textFaint), 0.18));
  }

  const label = makeLabel("μ");
  label.position.copy(
    centralPosition.clone().add(new THREE.Vector3(centralRadius * 2.3, centralRadius * 3, centralRadius * 1.5)),
  );
  group.add(label);
  return group;
}

function beadPoint(state: number[]): THREE.Vector3 {
  return new THREE.Vector3(state[2], state[4], state[3]);
}

function makeHoopLine(radius = 1, opacity = 0.38): THREE.Line {
  return lineFromPoints(
    Array.from({ length: 161 }, (_, index) => {
      const theta = (index / 160) * Math.PI * 2;
      return new THREE.Vector3(radius * Math.sin(theta), -radius * Math.cos(theta), 0);
    }),
    new THREE.Color(theme.cool),
    opacity,
  );
}

function makeBeadHoopGroup(data: Trajectory, hints: RendererHints): { group: THREE.Group; hoop: THREE.Group } {
  const group = new THREE.Group();
  const hoop = new THREE.Group();
  const constraint = referenceHint(hints, "constraintHoop");
  const rotationAxis = referenceHint(hints, "rotationAxis");
  const radius = constraint?.radius ?? (typeof data.metadata?.radius === "number" ? data.metadata.radius : 1);
  const echoAngles = constraint?.echoAngles ?? [
    Math.PI / 5,
    (2 * Math.PI) / 5,
    (3 * Math.PI) / 5,
    (4 * Math.PI) / 5,
  ];

  hoop.add(makeHoopLine(radius, 0.58));
  hoop.add(lineFromPoints([new THREE.Vector3(0, -radius, 0), new THREE.Vector3(0, radius, 0)], new THREE.Color(theme.textFaint), 0.2));
  hoop.add(lineFromPoints([new THREE.Vector3(-radius, 0, 0), new THREE.Vector3(radius, 0, 0)], new THREE.Color(theme.textFaint), 0.16));
  group.add(hoop);

  for (const angle of echoAngles) {
    const echo = makeHoopLine(radius, 0.12);
    echo.rotation.y = angle;
    group.add(echo);
  }

  const trajectory = data.states.map(beadPoint);

  for (const point of trajectoryEvery(trajectory, 12)) {
    const radial = new THREE.Vector3(point.x, 0, point.z);
    if (radial.length() > 1e-4) {
      radial.normalize().multiplyScalar(0.12 * radius);
      group.add(vectorArrow(point.clone().setY(point.y + 0.04), radial, new THREE.Color(theme.textFaint), 0.24));
    }
  }

  const axisStart = rotationAxis?.start ? vectorFromTuple(rotationAxis.start) : new THREE.Vector3(0, -1.18 * radius, 0);
  const axisEnd = rotationAxis?.end ? vectorFromTuple(rotationAxis.end) : new THREE.Vector3(0, 1.18 * radius, 0);
  const axis = lineFromPoints([axisStart, axisEnd], new THREE.Color(theme.textFaint), 0.24);
  group.add(axis);

  const label = makeLabel("Ω");
  label.position.set(0.26 * radius, 1.22 * radius, 0.18 * radius);
  group.add(label);
  return { group, hoop };
}

function fixedPointCoordinates(data: Trajectory): number[][] {
  const fixedPoints = data.metadata?.fixedPoints;
  if (!Array.isArray(fixedPoints)) {
    return [];
  }

  return fixedPoints.flatMap((item) => {
    if (!item || typeof item !== "object" || !("coordinates" in item)) {
      return [];
    }
    const coordinates = (item as { coordinates?: Record<string, unknown> }).coordinates;
    const x = coordinates?.x;
    const y = coordinates?.y;
    const z = coordinates?.z;
    return typeof x === "number" && typeof y === "number" && typeof z === "number" ? [[x, y, z]] : [];
  });
}

function makeLorenzAttractorGroup(data: Trajectory, transform: LorenzTransform): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => lorenzPoint(state, transform));

  group.add(contextLine(points, 0.26));
  group.add(lineFromPoints(points, new THREE.Color(theme.textFaint), 0.1));

  const box = new THREE.Box3().setFromPoints(points);
  const size = new THREE.Vector3();
  box.getSize(size);
  const guideRadius = Math.max(size.x, size.z) * 0.36;
  for (const y of [-0.68, 0, 0.68]) {
    const guide = lineFromPoints(
      Array.from({ length: 129 }, (_item, index) => {
        const angle = (index / 128) * Math.PI * 2;
        return new THREE.Vector3(Math.cos(angle) * guideRadius, y, Math.sin(angle) * guideRadius * 0.7);
      }),
      new THREE.Color(theme.textFaint),
      0.12,
    );
    group.add(guide);
  }

  const step = Math.max(1, Math.floor(points.length / 34));
  for (let index = step; index < points.length - step; index += step) {
    const tangent = points[index + 1].clone().sub(points[index - 1]);
    if (tangent.length() < 1e-5) {
      continue;
    }
    group.add(
      vectorArrow(
        points[index].clone(),
        tangent.normalize().multiplyScalar(0.16),
        new THREE.Color(theme.textFaint),
        0.28,
      ),
    );
  }

  const fixedMaterial = new THREE.MeshStandardMaterial({
    color: new THREE.Color(theme.cool),
    emissive: new THREE.Color(theme.cool),
    emissiveIntensity: 0.16,
    transparent: true,
    opacity: 0.72,
    roughness: 0.45,
  });
  for (const point of fixedPointCoordinates(data)) {
    const marker = new THREE.Mesh(new THREE.SphereGeometry(0.04, 18, 12), fixedMaterial);
    marker.position.copy(lorenzPoint(point, transform));
    group.add(marker);
  }

  return group;
}

function potentialSurfaceMetadata(data: Trajectory): PotentialSurfaceMetadata | null {
  const surface = data.metadata?.potentialSurface;
  if (!surface || typeof surface !== "object") {
    return null;
  }
  const candidate = surface as Partial<PotentialSurfaceMetadata>;
  if (!Array.isArray(candidate.xValues) || !Array.isArray(candidate.yValues) || !Array.isArray(candidate.values)) {
    return null;
  }
  return candidate as PotentialSurfaceMetadata;
}

function henonPotential(x: number, y: number, data: Trajectory): number {
  const metadata = data.metadata as { stiffness?: number; coupling?: number } | undefined;
  const stiffness = metadata?.stiffness ?? 1;
  const coupling = metadata?.coupling ?? 1;
  return 0.5 * stiffness * (x * x + y * y) + coupling * (x * x * y - (y * y * y) / 3);
}

function henonPoint(state: number[], data: Trajectory): THREE.Vector3 {
  const x = state[0];
  const y = state[1];
  return new THREE.Vector3(x * 1.38, henonPotential(x, y, data) * 0.95 - 0.36, y * 1.38);
}

function makeHenonSurface(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const surface = potentialSurfaceMetadata(data);
  if (!surface) {
    return group;
  }

  const geometry = new THREE.BufferGeometry();
  const positions: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  const color = new THREE.Color();
  const flatValues = surface.values.flat().filter(Number.isFinite);
  const minValue = Math.min(...flatValues);
  const maxValue = Math.max(...flatValues);
  const span = Math.max(1e-6, maxValue - minValue);

  surface.yValues.forEach((y, row) => {
    surface.xValues.forEach((x, col) => {
      const value = surface.values[row][col];
      positions.push(x * 1.38, value * 0.95 - 0.36, y * 1.38);
      const normalized = (value - minValue) / span;
      color.setHSL(0.54 - normalized * 0.37, 0.5, 0.46 + normalized * 0.12);
      colors.push(color.r, color.g, color.b);
    });
  });

  const columns = surface.xValues.length;
  for (let row = 0; row < surface.yValues.length - 1; row += 1) {
    for (let col = 0; col < surface.xValues.length - 1; col += 1) {
      const a = row * columns + col;
      const b = row * columns + col + 1;
      const c = (row + 1) * columns + col + 1;
      const d = (row + 1) * columns + col;
      indices.push(a, b, d, b, c, d);
    }
  }

  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();

  group.add(
    new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.5,
        roughness: 0.78,
        metalness: 0.03,
        side: THREE.DoubleSide,
      }),
    ),
  );

  const rowStep = Math.max(1, Math.floor(surface.yValues.length / 10));
  const colStep = Math.max(1, Math.floor(surface.xValues.length / 10));
  for (let row = 0; row < surface.yValues.length; row += rowStep) {
    group.add(
      lineFromPoints(
        surface.xValues.map((x, col) => new THREE.Vector3(x * 1.38, surface.values[row][col] * 0.95 - 0.35, surface.yValues[row] * 1.38)),
        new THREE.Color(theme.textFaint),
        0.12,
      ),
    );
  }
  for (let col = 0; col < surface.xValues.length; col += colStep) {
    group.add(
      lineFromPoints(
        surface.yValues.map((y, row) => new THREE.Vector3(surface.xValues[col] * 1.38, surface.values[row][col] * 0.95 - 0.35, y * 1.38)),
        new THREE.Color(theme.textFaint),
        0.12,
      ),
    );
  }

  return group;
}

function makeHenonHeilesGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  group.rotation.y = -0.24;
  group.add(makeHenonSurface(data));

  const trajectory = data.states.map((state) => henonPoint(state, data));
  group.add(contextLine(trajectory, 0.28));
  group.add(lineFromPoints(trajectory, new THREE.Color(theme.textFaint), 0.1));

  const metadata = data.metadata as { stiffness?: number; coupling?: number } | undefined;
  const stiffness = metadata?.stiffness ?? 1;
  const coupling = metadata?.coupling ?? 1;
  for (let x = -0.85; x <= 0.86; x += 0.34) {
    for (let y = -0.78; y <= 0.79; y += 0.34) {
      const value = henonPotential(x, y, data);
      const forceX = -(stiffness * x + 2 * coupling * x * y);
      const forceY = -(stiffness * y + coupling * (x * x - y * y));
      const force = new THREE.Vector3(forceX, 0, forceY);
      if (force.length() < 1e-5) {
        continue;
      }
      const start = new THREE.Vector3(x * 1.38, value * 0.95 - 0.24, y * 1.38);
      group.add(vectorArrow(start, force.normalize().multiplyScalar(0.12), new THREE.Color(theme.textFaint), 0.22));
    }
  }

  const label = makeLabel("H");
  label.position.set(-1.3, 0.72, -1.25);
  group.add(label);
  return group;
}

export class ThreeScene {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  private readonly controls: OrbitControls;
  private readonly root = new THREE.Group();
  private readonly marker: THREE.Mesh;
  private dynamicSpring: THREE.Line | null = null;
  private beadHoop: THREE.Group | null = null;
  private beadHoopOmega = 0;
  private lorenzTransform: LorenzTransform = { center: new THREE.Vector3(), scale: 1 };
  private henonData: Trajectory | null = null;
  private motionTrail: THREE.Line | null = null;
  private motionTrailPoints: THREE.Vector3[] = [];
  private flow: FlowField | null = null;
  private active = false;
  private mode: ThreeMode | null = null;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
    });
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    this.scene.fog = new THREE.Fog(new THREE.Color(theme.ink800), 8, 18);
    this.camera.position.set(4.3, 2.55, 5.3);
    this.camera.lookAt(0, 0.72, 0);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.enablePan = false;
    this.controls.minDistance = 2.8;
    this.controls.maxDistance = 9.0;
    this.controls.target.set(0, 0.72, 0);

    const ambient = new THREE.HemisphereLight(0xffffff, 0xd7c7aa, 2.1);
    const key = new THREE.DirectionalLight(0xffffff, 1.7);
    key.position.set(3.2, 6.5, 4.4);
    this.scene.add(ambient, key, this.root);

    this.marker = new THREE.Mesh(
      new THREE.SphereGeometry(0.105, 28, 18),
      new THREE.MeshStandardMaterial({
        color: new THREE.Color(theme.accentStrong),
        roughness: 0.3,
        metalness: 0.1,
        emissive: new THREE.Color(theme.accent),
        emissiveIntensity: 0.5,
      }),
    );
  }

  setActive(active: boolean) {
    this.active = active;
    if (active) {
      this.resize();
      this.renderer.render(this.scene, this.camera);
    }
  }

  setVisualization(mode: ThreeMode, data: Trajectory) {
    this.mode = mode;
    const hints = rendererHints(data);
    this.root.clear();
    this.dynamicSpring = null;
    this.beadHoop = null;
    this.beadHoopOmega = 0;
    this.lorenzTransform = { center: new THREE.Vector3(), scale: 1 };
    this.henonData = null;
    this.motionTrail = null;
    this.motionTrailPoints = [];
    this.flow?.dispose();
    this.flow = null;
    this.marker.scale.setScalar(1);
    this.controls.minDistance = 2.8;
    this.controls.maxDistance = 9.0;

    if (mode === "pendulumHamiltonian") {
      this.root.add(makePendulumHamiltonianGroup(data));
      this.setMotionTrail(data.states.map((state) => pendulumPoint(state[0], state[1], 0.22)), 90);
      this.flow = makePendulumFlow();
      this.root.add(this.flow.object);
      this.camera.position.set(4.3, 2.55, 5.3);
      this.controls.target.set(0, 0.72, 0);
    } else if (mode === "sphereGeodesic") {
      this.root.add(makeSphereGeodesicGroup(data));
      this.setMotionTrail(data.states.map((state) => new THREE.Vector3(state[4], state[5], state[6])), 90);
      this.camera.position.set(2.5, 1.6, 3.2);
      this.controls.target.set(0, 0, 0);
    } else if (mode === "chargedParticle") {
      this.root.add(makeChargedParticleGroup(data));
      this.setMotionTrail(data.states.map((state) => new THREE.Vector3(state[0], state[2] * 0.62, state[1])), 110);
      this.marker.scale.setScalar(0.82);
      this.flow = new FlowField({
        field: (x, z) => [-z, x],
        bounds: { xMin: -1.28, xMax: 1.28, yMin: -1.28, yMax: 1.28 },
        toPosition: (x, z) => new THREE.Vector3(x, -0.58, z),
        count: 240,
        rate: 0.24,
        life: 3.2,
        size: 0.026,
        intensity: 0.46,
      });
      this.root.add(this.flow.object);
      this.camera.position.set(3.0, 2.0, 3.4);
      this.controls.target.set(0, 0, 0);
    } else if (mode === "uniformGravity") {
      this.root.add(makeUniformGravityGroup(data));
      this.setMotionTrail(data.states.map((state) => new THREE.Vector3(state[0] - 0.9, state[1] * 0.42 - 0.65, 0)), 90);
      this.marker.scale.setScalar(0.92);
      this.flow = new FlowField({
        field: (_x, _z) => [0, -1],
        bounds: { xMin: -1.45, xMax: 1.95, yMin: -0.56, yMax: 1.1 },
        toPosition: (x, z) => new THREE.Vector3(x, z, -0.58),
        count: 180,
        rate: 0.34,
        life: 2.5,
        size: 0.026,
        intensity: 0.42,
      });
      this.root.add(this.flow.object);
      this.camera.position.set(2.65, 1.65, 3.25);
      this.controls.target.set(0.25, 0.1, 0);
    } else if (mode === "idealSpring") {
      this.root.add(makeIdealSpringGroup(data));
      this.setMotionTrail(data.states.map((state) => new THREE.Vector3(state[0], 0, 0)), 80);
      this.dynamicSpring = lineFromPoints([], new THREE.Color(theme.cool), 0.82);
      this.root.add(this.dynamicSpring);
      this.marker.scale.setScalar(1.35);
      this.camera.position.set(2.25, 1.08, 2.75);
      this.controls.target.set(0, 0, 0);
    } else if (mode === "keplerOrbit") {
      this.root.add(makeKeplerGroup(data, hints));
      this.setMotionTrail(data.states.map((state) => new THREE.Vector3(state[4], 0, state[5])), 100);
      this.marker.scale.setScalar(0.88);
      const [flowXMin, flowXMax] = flowRange(hints, "x", [-1.55, 1.55]);
      const [flowZMin, flowZMax] = flowRange(hints, "z", [-1.55, 1.55]);
      this.flow = new FlowField({
        field: (x, z) => {
          const radiusSquared = x * x + z * z + 0.18;
          const scale = 1 / Math.pow(radiusSquared, 1.25);
          return [-x * scale, -z * scale];
        },
        bounds: { xMin: flowXMin, xMax: flowXMax, yMin: flowZMin, yMax: flowZMax },
        toPosition: (x, z) => new THREE.Vector3(x, 0.12, z),
        count: 260,
        rate: 0.12,
        life: 3.8,
        size: 0.024,
        intensity: 0.42,
      });
      this.root.add(this.flow.object);
      this.applyCameraHints(hints, [2.35, 1.55, 2.85], [0, 0, 0]);
    } else if (mode === "beadHoop") {
      const { group, hoop } = makeBeadHoopGroup(data, hints);
      this.root.add(group);
      this.beadHoop = hoop;
      this.beadHoopOmega = typeof data.metadata?.angular_speed === "number" ? data.metadata.angular_speed : 0;
      this.setMotionTrail(data.states.map(beadPoint), 90);
      this.marker.scale.setScalar(0.9);
      this.applyCameraHints(hints, [2.35, 1.35, 2.65], [0, 0, 0]);
    } else if (mode === "lorenzAttractor") {
      this.lorenzTransform = lorenzTransform(data);
      this.root.add(makeLorenzAttractorGroup(data, this.lorenzTransform));
      this.setMotionTrail(data.states.map((state) => lorenzPoint(state, this.lorenzTransform)), 180);
      this.marker.scale.setScalar(0.72);
      this.camera.position.set(3.0, 2.05, 4.4);
      this.controls.target.set(0, 0.05, 0);
    } else {
      this.henonData = data;
      this.root.add(makeHenonHeilesGroup(data));
      this.setMotionTrail(data.states.map((state) => henonPoint(state, data)), 150);
      this.marker.scale.setScalar(0.78);
      this.camera.position.set(2.7, 1.75, 3.45);
      this.controls.target.set(0, 0.05, 0);
    }

    this.root.add(this.marker);
    this.controls.update();
  }

  private applyCameraHints(
    hints: RendererHints,
    fallbackPosition: Vector3Tuple,
    fallbackTarget: Vector3Tuple,
  ) {
    this.camera.position.copy(vectorFromTuple(hints.camera?.position ?? fallbackPosition));
    this.controls.target.copy(vectorFromTuple(hints.camera?.target ?? fallbackTarget));

    const xRange = axisRange(hints, "x", [-1, 1]);
    const yRange = axisRange(hints, "y", [-1, 1]);
    const zRange = axisRange(hints, "z", [-1, 1]);
    const span = Math.max(
      xRange[1] - xRange[0],
      yRange[1] - yRange[0],
      zRange[1] - zRange[0],
      1,
    );
    this.controls.minDistance = Math.max(1.2, span * 0.9);
    this.controls.maxDistance = Math.max(5.5, span * 4.4);
  }

  resize() {
    const width = this.canvas.clientWidth;
    const height = this.canvas.clientHeight;
    const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    const drawingWidth = Math.max(1, Math.floor(width * pixelRatio));
    const drawingHeight = Math.max(1, Math.floor(height * pixelRatio));

    if (this.canvas.width !== drawingWidth || this.canvas.height !== drawingHeight) {
      this.renderer.setSize(width, height, false);
      this.camera.aspect = width / Math.max(1, height);
      this.camera.updateProjectionMatrix();
    }
  }

  render(state: number[], elapsed: number, sampleIndex: number) {
    if (!this.active || !this.mode) {
      return;
    }

    this.resize();
    if (this.mode === "pendulumHamiltonian") {
      this.marker.position.copy(pendulumPoint(state[0], state[1], 0.22));
      this.root.rotation.y = Math.sin(elapsed * 0.16) * 0.08;
    } else if (this.mode === "sphereGeodesic") {
      this.marker.position.set(state[4], state[5], state[6]);
      this.root.rotation.y = Math.sin(elapsed * 0.12) * 0.12;
    } else if (this.mode === "chargedParticle") {
      this.marker.position.set(state[0], state[2] * 0.62, state[1]);
      this.root.rotation.y = Math.sin(elapsed * 0.1) * 0.08;
    } else if (this.mode === "uniformGravity") {
      this.marker.position.set(state[0] - 0.9, state[1] * 0.42 - 0.65, 0);
      this.root.rotation.y = Math.sin(elapsed * 0.1) * 0.08;
    } else if (this.mode === "idealSpring") {
      const x = state[0];
      this.marker.position.set(x, 0, 0);
      if (this.dynamicSpring) {
        const left = -1.29;
        const points: THREE.Vector3[] = [];
        for (let i = 0; i <= 42; i += 1) {
          const alpha = i / 42;
          const sx = left + (x - left) * alpha;
          const sy = Math.sin(alpha * Math.PI * 16) * 0.105;
          const taper = Math.sin(alpha * Math.PI);
          points.push(new THREE.Vector3(sx, 0.02 + sy * taper, 0.03 * Math.cos(alpha * Math.PI * 16) * taper));
        }
        this.dynamicSpring.geometry.dispose();
        this.dynamicSpring.geometry = new THREE.BufferGeometry().setFromPoints(points);
      }
      this.root.rotation.y = Math.sin(elapsed * 0.08) * 0.06;
    } else if (this.mode === "keplerOrbit") {
      this.marker.position.set(state[4], 0, state[5]);
      this.root.rotation.y = Math.sin(elapsed * 0.08) * 0.08;
    } else if (this.mode === "beadHoop") {
      this.marker.position.copy(beadPoint(state));
      if (this.beadHoop) {
        this.beadHoop.rotation.y = -this.beadHoopOmega * elapsed;
      }
      this.root.rotation.y = Math.sin(elapsed * 0.08) * 0.07;
    } else if (this.mode === "lorenzAttractor") {
      const point = lorenzPoint(state, this.lorenzTransform);
      this.marker.position.copy(point);
      this.root.rotation.y = -0.35 + Math.sin(elapsed * 0.065) * 0.08;
    } else if (this.henonData) {
      const point = henonPoint(state, this.henonData);
      this.marker.position.copy(point);
      this.root.rotation.y = Math.sin(elapsed * 0.07) * 0.07;
    }

    this.updateMotionTrail(sampleIndex);
    this.flow?.update();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  private setMotionTrail(points: THREE.Vector3[], length: number) {
    this.motionTrailPoints = points;
    this.motionTrail = makeFadingTrail(length, new THREE.Color(theme.accentStrong));
    this.root.add(this.motionTrail);
  }

  private updateMotionTrail(currentIndex: number) {
    if (!this.motionTrail || this.motionTrailPoints.length === 0) {
      return;
    }
    const positions = this.motionTrail.geometry.getAttribute("position") as THREE.BufferAttribute;
    const length = positions.count;
    const nearest = Math.min(Math.max(0, currentIndex), this.motionTrailPoints.length - 1);

    for (let index = 0; index < length; index += 1) {
      const sourceIndex = Math.max(0, nearest - (length - 1 - index));
      const point = this.motionTrailPoints[sourceIndex] ?? this.motionTrailPoints[nearest];
      positions.setXYZ(index, point.x, point.y, point.z);
    }
    positions.needsUpdate = true;
  }
}
