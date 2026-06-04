import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export type PhasePoint = {
  theta: number;
  momentum: number;
};

const THETA_MIN = -Math.PI;
const THETA_MAX = Math.PI;
const MOMENTUM_MIN = -3.2;
const MOMENTUM_MAX = 3.2;
const THETA_SCALE = 0.62;
const MOMENTUM_SCALE = 0.42;
const ENERGY_SCALE = 0.1;
const GRAVITY = 9.81;

function hamiltonian(theta: number, momentum: number): number {
  return 0.5 * momentum * momentum + GRAVITY * (1 - Math.cos(theta));
}

function mapPoint(theta: number, momentum: number, energyOffset = 0): THREE.Vector3 {
  return new THREE.Vector3(
    theta * THETA_SCALE,
    (hamiltonian(theta, momentum) + energyOffset) * ENERGY_SCALE,
    momentum * MOMENTUM_SCALE,
  );
}

function makeTextSprite(text: string): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 96;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Unable to create label canvas.");
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "600 42px Inter, system-ui, sans-serif";
  ctx.fillStyle = "rgba(23, 37, 45, 0.82)";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(0.52, 0.2, 1);
  return sprite;
}

function makeEnergySurface(): THREE.Mesh {
  const thetaSegments = 88;
  const momentumSegments = 54;
  const geometry = new THREE.BufferGeometry();
  const positions: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  const color = new THREE.Color();

  for (let i = 0; i <= thetaSegments; i += 1) {
    const theta = THETA_MIN + (i / thetaSegments) * (THETA_MAX - THETA_MIN);
    for (let j = 0; j <= momentumSegments; j += 1) {
      const momentum = MOMENTUM_MIN + (j / momentumSegments) * (MOMENTUM_MAX - MOMENTUM_MIN);
      const point = mapPoint(theta, momentum);
      positions.push(point.x, point.y, point.z);

      const energy = hamiltonian(theta, momentum);
      color.setHSL(0.52 - Math.min(0.38, energy / 42), 0.42, 0.58);
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

function makeTrajectory(points: PhasePoint[]): THREE.Line {
  const geometry = new THREE.BufferGeometry().setFromPoints(
    points.map((point) => mapPoint(point.theta, point.momentum, 0.08)),
  );
  return new THREE.Line(
    geometry,
    new THREE.LineBasicMaterial({
      color: 0xd88d42,
      linewidth: 3,
    }),
  );
}

function makeFlowField(): THREE.Group {
  const group = new THREE.Group();
  const material = new THREE.LineBasicMaterial({
    color: 0x17252d,
    transparent: true,
    opacity: 0.42,
  });
  const coneMaterial = new THREE.MeshBasicMaterial({
    color: 0x17252d,
    transparent: true,
    opacity: 0.48,
  });

  for (let theta = -2.6; theta <= 2.61; theta += 0.65) {
    for (let momentum = -2.6; momentum <= 2.61; momentum += 0.65) {
      const dTheta = momentum;
      const dMomentum = -GRAVITY * Math.sin(theta);
      const magnitude = Math.hypot(dTheta, dMomentum);
      if (magnitude < 0.2) {
        continue;
      }

      const step = 0.055 / magnitude;
      const start = mapPoint(theta - dTheta * step, momentum - dMomentum * step, 0.14);
      const end = mapPoint(theta + dTheta * step, momentum + dMomentum * step, 0.14);
      const lineGeometry = new THREE.BufferGeometry().setFromPoints([start, end]);
      group.add(new THREE.Line(lineGeometry, material));

      const direction = new THREE.Vector3().subVectors(end, start).normalize();
      const cone = new THREE.Mesh(new THREE.ConeGeometry(0.035, 0.12, 10), coneMaterial);
      cone.position.copy(end);
      cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
      group.add(cone);
    }
  }

  return group;
}

function makeAxes(): THREE.Group {
  const group = new THREE.Group();
  const axisMaterial = new THREE.LineBasicMaterial({ color: 0x17252d, transparent: true, opacity: 0.35 });
  const thetaAxis = new THREE.BufferGeometry().setFromPoints([
    mapPoint(THETA_MIN, 0, 0.04),
    mapPoint(THETA_MAX, 0, 0.04),
  ]);
  const momentumAxis = new THREE.BufferGeometry().setFromPoints([
    mapPoint(0, MOMENTUM_MIN, 0.04),
    mapPoint(0, MOMENTUM_MAX, 0.04),
  ]);
  group.add(new THREE.Line(thetaAxis, axisMaterial));
  group.add(new THREE.Line(momentumAxis, axisMaterial));

  const thetaLabel = makeTextSprite("θ");
  thetaLabel.position.copy(mapPoint(THETA_MAX + 0.28, 0, 0.2));
  group.add(thetaLabel);

  const momentumLabel = makeTextSprite("pθ");
  momentumLabel.position.copy(mapPoint(0, MOMENTUM_MAX + 0.38, 0.2));
  group.add(momentumLabel);

  const energyLabel = makeTextSprite("H");
  energyLabel.position.set(-2.75, 2.35, -1.95);
  group.add(energyLabel);

  return group;
}

export class HamiltonianScene {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  private readonly controls: OrbitControls;
  private readonly currentMarker: THREE.Mesh;
  private readonly orbit = new THREE.Group();
  private active = false;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    trajectory: PhasePoint[],
  ) {
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
    });
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    this.scene.fog = new THREE.Fog(0xf8faf7, 8, 18);
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
    this.scene.add(ambient, key);

    this.orbit.rotation.y = -0.22;
    this.orbit.add(makeEnergySurface(), makeFlowField(), makeAxes(), makeTrajectory(trajectory));
    this.scene.add(this.orbit);

    this.currentMarker = new THREE.Mesh(
      new THREE.SphereGeometry(0.105, 28, 18),
      new THREE.MeshStandardMaterial({
        color: 0x17252d,
        roughness: 0.28,
        metalness: 0.18,
        emissive: 0x17252d,
        emissiveIntensity: 0.08,
      }),
    );
    this.orbit.add(this.currentMarker);
  }

  setActive(active: boolean) {
    this.active = active;
    if (active) {
      this.resize();
      this.renderer.render(this.scene, this.camera);
    }
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

  render(point: PhasePoint, elapsed: number) {
    if (!this.active) {
      return;
    }

    this.resize();
    this.currentMarker.position.copy(mapPoint(point.theta, point.momentum, 0.22));
    this.orbit.rotation.y = -0.22 + Math.sin(elapsed * 0.16) * 0.08;
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
