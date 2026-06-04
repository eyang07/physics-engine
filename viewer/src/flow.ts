/**
 * A reusable particle-advection flow field.
 *
 * Instead of a static grid of arrows, a cloud of particles drifts along a
 * vector field, fading in and out — you perceive fast vs. slow regions without
 * a single number. Direction is encoded with the cyclic twilight colormap;
 * brightness fades with each particle's life. Because particles are advected
 * (not redrawn from scratch), watching a Hamiltonian field shows Liouville's
 * theorem directly: the cloud shears but preserves its density.
 *
 * This is the one flow primitive meant to scale — the same renderer serves
 * phase-space flow today and fluid velocity fields later.
 */
import * as THREE from "three";

import { twilight } from "./design/colormaps";

/** A planar vector field in the flow's own coordinates. */
export type Field2D = (x: number, y: number) => [number, number];

export interface FlowOptions {
  field: Field2D;
  /** Rectangle in field coordinates over which particles live. */
  bounds: { xMin: number; xMax: number; yMin: number; yMax: number };
  /** Map a field point to its position in the 3D scene. */
  toPosition: (x: number, y: number) => THREE.Vector3;
  count?: number;
  /** Advection rate: field units per second per unit field magnitude. */
  rate?: number;
  /** Seconds a particle lives before respawning. */
  life?: number;
  /** Point size in world units. */
  size?: number;
}

export class FlowField {
  readonly object: THREE.Points;

  private readonly field: Field2D;
  private readonly bounds: FlowOptions["bounds"];
  private readonly toPosition: FlowOptions["toPosition"];
  private readonly rate: number;
  private readonly life: number;
  private readonly count: number;

  private readonly px: Float32Array;
  private readonly py: Float32Array;
  private readonly age: Float32Array;
  private readonly positions: Float32Array;
  private readonly colors: Float32Array;
  private readonly geometry: THREE.BufferGeometry;
  private last = performance.now();

  constructor(options: FlowOptions) {
    this.field = options.field;
    this.bounds = options.bounds;
    this.toPosition = options.toPosition;
    this.rate = options.rate ?? 1;
    this.life = options.life ?? 2.4;
    this.count = options.count ?? 700;

    this.px = new Float32Array(this.count);
    this.py = new Float32Array(this.count);
    this.age = new Float32Array(this.count);
    this.positions = new Float32Array(this.count * 3);
    this.colors = new Float32Array(this.count * 3);

    for (let i = 0; i < this.count; i += 1) {
      this.spawn(i, Math.random() * this.life);
    }

    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute("position", new THREE.BufferAttribute(this.positions, 3));
    this.geometry.setAttribute("color", new THREE.BufferAttribute(this.colors, 3));

    this.object = new THREE.Points(
      this.geometry,
      new THREE.PointsMaterial({
        size: options.size ?? 0.05,
        sizeAttenuation: true,
        vertexColors: true,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    );
  }

  private spawn(i: number, age: number): void {
    this.px[i] = this.bounds.xMin + Math.random() * (this.bounds.xMax - this.bounds.xMin);
    this.py[i] = this.bounds.yMin + Math.random() * (this.bounds.yMax - this.bounds.yMin);
    this.age[i] = age;
    this.write(i);
  }

  private write(i: number): void {
    const point = this.toPosition(this.px[i], this.py[i]);
    this.positions[i * 3] = point.x;
    this.positions[i * 3 + 1] = point.y;
    this.positions[i * 3 + 2] = point.z;

    const [vx, vy] = this.field(this.px[i], this.py[i]);
    // Direction -> cyclic color (0 and 2*pi share a hue).
    const direction = (Math.atan2(vy, vx) / (Math.PI * 2) + 0.5) % 1;
    const [r, g, b] = twilight.atUnit(direction);
    // Brightness rises and falls over the particle's life (fade in / out).
    const brightness = Math.sin(Math.PI * Math.min(1, this.age[i] / this.life));
    this.colors[i * 3] = r * brightness;
    this.colors[i * 3 + 1] = g * brightness;
    this.colors[i * 3 + 2] = b * brightness;
  }

  private outOfBounds(i: number): boolean {
    return (
      this.px[i] < this.bounds.xMin ||
      this.px[i] > this.bounds.xMax ||
      this.py[i] < this.bounds.yMin ||
      this.py[i] > this.bounds.yMax
    );
  }

  update(): void {
    const now = performance.now();
    const dt = Math.min((now - this.last) / 1000, 0.05);
    this.last = now;

    for (let i = 0; i < this.count; i += 1) {
      const [vx, vy] = this.field(this.px[i], this.py[i]);
      this.px[i] += vx * this.rate * dt;
      this.py[i] += vy * this.rate * dt;
      this.age[i] += dt;

      if (this.age[i] >= this.life || this.outOfBounds(i)) {
        this.spawn(i, 0);
      } else {
        this.write(i);
      }
    }

    (this.geometry.getAttribute("position") as THREE.BufferAttribute).needsUpdate = true;
    (this.geometry.getAttribute("color") as THREE.BufferAttribute).needsUpdate = true;
  }

  dispose(): void {
    this.geometry.dispose();
    (this.object.material as THREE.Material).dispose();
  }
}
