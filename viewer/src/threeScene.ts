import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { theme } from "./design/theme";
import { FlowField } from "./flow";
import type { Trajectory } from "./data/trajectory";

export type { Trajectory };

export type ThreeMode =
  | "pendulumHamiltonian"
  | "sphereGeodesic"
  | "chargedParticle"
  | "uniformGravity"
  | "idealSpring"
  | "keplerOrbit";

const PENDULUM_GRAVITY = 9.81;

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

function glowLine(points: THREE.Vector3[], color: THREE.ColorRepresentation): THREE.Group {
  const group = new THREE.Group();
  group.add(lineFromPoints(points, color, 0.95));
  group.add(lineFromPoints(points, color, 0.22));
  (group.children[1] as THREE.Line).scale.setScalar(1.006);
  return group;
}

function trajectoryEvery<T>(items: T[], count: number): T[] {
  if (items.length <= count) {
    return items;
  }
  const step = Math.max(1, Math.floor(items.length / count));
  return items.filter((_item, index) => index % step === 0);
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
    lineFromPoints(
      data.states.map((state) => pendulumPoint(state[0], state[1], 0.08)),
      new THREE.Color(theme.accent),
    ),
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
    lineFromPoints(
      data.states.map((state) => new THREE.Vector3(state[4], state[5], state[6])),
      new THREE.Color(theme.accent),
    ),
  );

  const north = makeLabel("N");
  north.position.set(0, 1.28, 0);
  group.add(north);
  return group;
}

function makeChargedParticleGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => new THREE.Vector3(state[0], state[2] * 0.62, state[1]));
  group.add(glowLine(points, new THREE.Color(theme.accent)));

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
  group.add(glowLine(points, new THREE.Color(theme.accent)));

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
  group.add(glowLine(pointTrace, new THREE.Color(theme.accent)));

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

function makeKeplerGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => new THREE.Vector3(state[4], 0, state[5]));
  group.add(glowLine(points, new THREE.Color(theme.accent)));

  const focus = new THREE.Mesh(
    new THREE.SphereGeometry(0.105, 32, 18),
    new THREE.MeshStandardMaterial({
      color: 0xf0b44c,
      emissive: 0x8b4a16,
      emissiveIntensity: 0.28,
      roughness: 0.35,
    }),
  );
  focus.position.set(0, 0, 0);
  group.add(focus);

  const plane = new THREE.Mesh(
    new THREE.CircleGeometry(1.72, 96),
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(theme.textFaint),
      transparent: true,
      opacity: 0.07,
      side: THREE.DoubleSide,
    }),
  );
  plane.rotation.x = -Math.PI / 2;
  group.add(plane);

  for (let radius = 0.45; radius <= 1.55; radius += 0.32) {
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

  for (let radius = 0.55; radius <= 1.55; radius += 0.42) {
    for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 4) {
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
  label.position.set(0.24, 0.32, 0.16);
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
    this.root.clear();
    this.dynamicSpring = null;
    this.flow?.dispose();
    this.flow = null;
    this.marker.scale.setScalar(1);

    if (mode === "pendulumHamiltonian") {
      this.root.add(makePendulumHamiltonianGroup(data));
      this.flow = makePendulumFlow();
      this.root.add(this.flow.object);
      this.camera.position.set(4.3, 2.55, 5.3);
      this.controls.target.set(0, 0.72, 0);
    } else if (mode === "sphereGeodesic") {
      this.root.add(makeSphereGeodesicGroup(data));
      this.camera.position.set(2.5, 1.6, 3.2);
      this.controls.target.set(0, 0, 0);
    } else if (mode === "chargedParticle") {
      this.root.add(makeChargedParticleGroup(data));
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
      this.dynamicSpring = lineFromPoints([], new THREE.Color(theme.cool), 0.82);
      this.root.add(this.dynamicSpring);
      this.marker.scale.setScalar(1.35);
      this.camera.position.set(2.25, 1.08, 2.75);
      this.controls.target.set(0, 0, 0);
    } else {
      this.root.add(makeKeplerGroup(data));
      this.marker.scale.setScalar(0.88);
      this.flow = new FlowField({
        field: (x, z) => {
          const radiusSquared = x * x + z * z + 0.18;
          const scale = 1 / Math.pow(radiusSquared, 1.25);
          return [-x * scale, -z * scale];
        },
        bounds: { xMin: -1.55, xMax: 1.55, yMin: -1.55, yMax: 1.55 },
        toPosition: (x, z) => new THREE.Vector3(x, 0.12, z),
        count: 260,
        rate: 0.12,
        life: 3.8,
        size: 0.024,
        intensity: 0.42,
      });
      this.root.add(this.flow.object);
      this.camera.position.set(2.35, 1.55, 2.85);
      this.controls.target.set(0, 0, 0);
    }

    this.root.add(this.marker);
    this.controls.update();
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

  render(state: number[], elapsed: number) {
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
    } else {
      this.marker.position.set(state[4], 0, state[5]);
      this.root.rotation.y = Math.sin(elapsed * 0.08) * 0.08;
    }

    this.flow?.update();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
