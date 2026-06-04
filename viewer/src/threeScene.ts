import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { theme } from "./design/theme";
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

  context.font = "600 42px Inter, system-ui, sans-serif";
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

function makePendulumFlowField(): THREE.Group {
  const group = new THREE.Group();
  const material = new THREE.LineBasicMaterial({
    color: new THREE.Color(theme.textMuted),
    transparent: true,
    opacity: 0.5,
  });
  const coneMaterial = new THREE.MeshBasicMaterial({
    color: new THREE.Color(theme.textMuted),
    transparent: true,
    opacity: 0.55,
  });

  for (let theta = -2.6; theta <= 2.61; theta += 0.65) {
    for (let momentum = -2.6; momentum <= 2.61; momentum += 0.65) {
      const dTheta = momentum;
      const dMomentum = -PENDULUM_GRAVITY * Math.sin(theta);
      const magnitude = Math.hypot(dTheta, dMomentum);
      if (magnitude < 0.2) {
        continue;
      }

      const step = 0.055 / magnitude;
      const start = pendulumPoint(theta - dTheta * step, momentum - dMomentum * step, 0.14);
      const end = pendulumPoint(theta + dTheta * step, momentum + dMomentum * step, 0.14);
      group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([start, end]), material));

      const direction = new THREE.Vector3().subVectors(end, start).normalize();
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.03, 0.105, 10), coneMaterial);
      cone.position.copy(end);
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
      group.add(cone);
    }
  }

  return group;
}

function makePendulumHamiltonianGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  group.rotation.y = -0.22;
  group.add(makePendulumSurface(), makePendulumFlowField());
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
  group.add(lineFromPoints(points, new THREE.Color(theme.accent)));

  const fieldMaterial = new THREE.LineBasicMaterial({
    color: new THREE.Color(theme.cool),
    transparent: true,
    opacity: 0.35,
  });
  const coneMaterial = new THREE.MeshBasicMaterial({
    color: new THREE.Color(theme.cool),
    transparent: true,
    opacity: 0.52,
  });
  for (let x = -1.5; x <= 1.51; x += 0.75) {
    for (let z = -1.5; z <= 1.51; z += 0.75) {
      const start = new THREE.Vector3(x, -1.25, z);
      const end = new THREE.Vector3(x, 1.25, z);
      group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([start, end]), fieldMaterial));
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.035, 0.14, 10), coneMaterial);
      cone.position.copy(end);
      group.add(cone);
    }
  }

  const label = makeLabel("B");
  label.position.set(1.78, 1.32, 1.45);
  group.add(label);
  return group;
}

function makeUniformGravityGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => new THREE.Vector3(state[0] - 0.9, state[1] * 0.42 - 0.65, 0));
  group.add(lineFromPoints(points, new THREE.Color(theme.accent)));

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(3.6, 1.2),
    new THREE.MeshBasicMaterial({ color: 0xdbe8f0, transparent: true, opacity: 0.45, side: THREE.DoubleSide }),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0.35, -0.72, 0);
  group.add(ground);

  const arrowMaterial = new THREE.LineBasicMaterial({ color: new THREE.Color(theme.cool), transparent: true, opacity: 0.48 });
  const coneMaterial = new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.cool), transparent: true, opacity: 0.6 });
  for (let x = -1.2; x <= 1.8; x += 0.5) {
    const start = new THREE.Vector3(x, 1.05, -0.72);
    const end = new THREE.Vector3(x, 0.45, -0.72);
    group.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([start, end]), arrowMaterial));
    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.035, 0.12, 10), coneMaterial);
    cone.position.copy(end);
    cone.rotation.x = Math.PI;
    group.add(cone);
  }

  const label = makeLabel("g");
  label.position.set(1.95, 0.9, -0.72);
  group.add(label);
  return group;
}

function makeIdealSpringGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const xValues = data.states.map((state) => state[0]);
  const pointTrace = xValues.map((x, index) => new THREE.Vector3(x, Math.sin(index * 0.035) * 0.06, 0));
  group.add(lineFromPoints(pointTrace, new THREE.Color(theme.accent), 0.55));

  const wall = new THREE.Mesh(
    new THREE.BoxGeometry(0.12, 1.2, 0.12),
    new THREE.MeshStandardMaterial({ color: new THREE.Color(theme.cool), roughness: 0.7 }),
  );
  wall.position.set(-1.35, 0, 0);
  group.add(wall);

  const rail = lineFromPoints(
    [new THREE.Vector3(-1.35, -0.36, 0), new THREE.Vector3(1.35, -0.36, 0)],
    new THREE.Color(theme.textFaint),
    0.4,
  );
  group.add(rail);

  const equilibrium = lineFromPoints([new THREE.Vector3(0, -0.52, 0), new THREE.Vector3(0, 0.52, 0)], new THREE.Color(theme.cool), 0.32);
  group.add(equilibrium);
  return group;
}

function makeKeplerGroup(data: Trajectory): THREE.Group {
  const group = new THREE.Group();
  const points = data.states.map((state) => new THREE.Vector3(state[4], 0, state[5]));
  group.add(lineFromPoints(points, new THREE.Color(theme.accent)));

  const focus = new THREE.Mesh(
    new THREE.SphereGeometry(0.11, 28, 18),
    new THREE.MeshStandardMaterial({ color: 0xf0b44c, emissive: 0x8b4a16, emissiveIntensity: 0.22, roughness: 0.35 }),
  );
  focus.position.set(0, 0, 0);
  group.add(focus);

  const plane = new THREE.Mesh(
    new THREE.CircleGeometry(1.75, 72),
    new THREE.MeshBasicMaterial({ color: 0xdbe8f0, transparent: true, opacity: 0.25, side: THREE.DoubleSide }),
  );
  plane.rotation.x = -Math.PI / 2;
  group.add(plane);

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

    if (mode === "pendulumHamiltonian") {
      this.root.add(makePendulumHamiltonianGroup(data));
      this.camera.position.set(4.3, 2.55, 5.3);
      this.controls.target.set(0, 0.72, 0);
    } else if (mode === "sphereGeodesic") {
      this.root.add(makeSphereGeodesicGroup(data));
      this.camera.position.set(2.5, 1.6, 3.2);
      this.controls.target.set(0, 0, 0);
    } else if (mode === "chargedParticle") {
      this.root.add(makeChargedParticleGroup(data));
      this.camera.position.set(3.4, 2.15, 3.5);
      this.controls.target.set(0, 0, 0);
    } else if (mode === "uniformGravity") {
      this.root.add(makeUniformGravityGroup(data));
      this.camera.position.set(2.7, 1.8, 3.2);
      this.controls.target.set(0.25, 0.1, 0);
    } else if (mode === "idealSpring") {
      this.root.add(makeIdealSpringGroup(data));
      this.dynamicSpring = lineFromPoints([], new THREE.Color(theme.cool), 0.82);
      this.root.add(this.dynamicSpring);
      this.camera.position.set(2.3, 1.25, 2.8);
      this.controls.target.set(0, 0, 0);
    } else {
      this.root.add(makeKeplerGroup(data));
      this.camera.position.set(2.4, 1.7, 2.8);
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
          const sy = Math.sin(alpha * Math.PI * 16) * 0.12;
          points.push(new THREE.Vector3(sx, sy, 0));
        }
        this.dynamicSpring.geometry.dispose();
        this.dynamicSpring.geometry = new THREE.BufferGeometry().setFromPoints(points);
      }
      this.root.rotation.y = Math.sin(elapsed * 0.08) * 0.06;
    } else {
      this.marker.position.set(state[4], 0, state[5]);
      this.root.rotation.y = Math.sin(elapsed * 0.08) * 0.08;
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
