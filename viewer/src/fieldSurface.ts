/**
 * FE-039 — the shared animated field-surface / mesh primitive.
 *
 * One three.js surface that the wave, membrane, wavefront, and curved-surface
 * lenses all draw through, instead of each family rebuilding a grid mesh by
 * hand. It does two things:
 *
 *   1. Colors a static height field — a scalar grid lifted into a surface and
 *      tinted through the shared scalar scale (FE-038), so a potential surface,
 *      a curvature field, or a wavefront intensity all read on the same color
 *      vocabulary. This is what the Hénon–Heiles potential surface uses today.
 *
 *   2. Animates a time-varying displacement field — given a series of frames
 *      (a sampled displacement grid over time), `update(elapsed)` lerps the
 *      surface between frames and loops, so a vibrating string, a membrane mode,
 *      or a spreading wave packet animates from exported data without per-family
 *      animation code. The wave/membrane lenses (FE-046/FE-047) bind their
 *      exported grids here.
 *
 * Like every viewer primitive it only *renders* data: heights and frames come
 * from the backend export; nothing about the physics is recomputed here.
 */
import * as THREE from "three";

import { type Colormap, scalarScale, type ScalarScale, viridis } from "./design/colormaps";
import { theme } from "./design/theme";

/** A scalar field sampled on a rectilinear grid. `values[row][col]` indexes
 *  `yValues[row]` and `xValues[col]`. */
export interface SurfaceGrid {
  readonly xValues: readonly number[];
  readonly yValues: readonly number[];
  readonly values: ReadonlyArray<readonly number[]>;
}

/** Maps grid `(x, height, y)` to scene coordinates: `position = grid * scale + offset`. */
export interface SurfaceTransform {
  readonly scale: readonly [number, number, number];
  readonly offset: readonly [number, number, number];
}

const IDENTITY_TRANSFORM: SurfaceTransform = { scale: [1, 1, 1], offset: [0, 0, 0] };

export interface FieldSurfaceOptions {
  /** Static heights, or the first frame when `frames` is supplied. */
  grid: SurfaceGrid;
  /** Grid → scene transform. Defaults to identity. */
  transform?: SurfaceTransform;
  /** Colormap for the height → color ramp. Defaults to viridis (FE-038). */
  colormap?: Colormap;
  /** Override the color domain; defaults to the grid's height range. Pass a
   *  symmetric range (e.g. `[-A, A]`) for oscillating displacement fields. */
  colorDomain?: readonly [number, number];
  /** Draw faint reference grid lines over the mesh. */
  gridLines?: boolean;
  /** Surface opacity. Defaults to 0.5. */
  opacity?: number;
  /** Time-varying displacement frames; `frames[k]` is a height grid at frame k.
   *  When present, `update(elapsed)` animates and loops the surface. */
  frames?: ReadonlyArray<ReadonlyArray<readonly number[]>>;
  /** Seconds for one full loop through `frames`. Defaults to 4. */
  period?: number;
}

export class FieldSurface {
  /** Add this to a scene / group. */
  readonly object = new THREE.Group();

  private readonly geometry = new THREE.BufferGeometry();
  private readonly position: THREE.Float32BufferAttribute;
  private readonly color: THREE.Float32BufferAttribute;
  private readonly transform: SurfaceTransform;
  private readonly scale: ScalarScale;
  private readonly xValues: readonly number[];
  private readonly yValues: readonly number[];
  private readonly rows: number;
  private readonly cols: number;
  private readonly frames?: ReadonlyArray<ReadonlyArray<readonly number[]>>;
  private readonly period: number;

  constructor(options: FieldSurfaceOptions) {
    this.transform = options.transform ?? IDENTITY_TRANSFORM;
    this.xValues = options.grid.xValues;
    this.yValues = options.grid.yValues;
    this.rows = this.yValues.length;
    this.cols = this.xValues.length;
    this.frames = options.frames;
    this.period = options.period ?? 4;

    const domain = options.colorDomain ?? heightRange(options.frames ?? [options.grid.values]);
    this.scale = scalarScale(options.colormap ?? viridis, domain);

    const vertexCount = this.rows * this.cols;
    this.position = new THREE.Float32BufferAttribute(new Float32Array(vertexCount * 3), 3);
    this.color = new THREE.Float32BufferAttribute(new Float32Array(vertexCount * 3), 3);
    this.geometry.setAttribute("position", this.position);
    this.geometry.setAttribute("color", this.color);
    this.geometry.setIndex(triangleIndices(this.rows, this.cols));

    this.writeHeights(options.grid.values);

    const mesh = new THREE.Mesh(
      this.geometry,
      new THREE.MeshStandardMaterial({
        vertexColors: true,
        transparent: true,
        opacity: options.opacity ?? 0.5,
        roughness: 0.78,
        metalness: 0.03,
        side: THREE.DoubleSide,
      }),
    );
    this.object.add(mesh);

    if (options.gridLines) {
      this.object.add(this.makeGridLines(options.grid.values));
    }
  }

  /** Replace the height field and recolor; recomputes lighting normals. */
  setHeights(values: ReadonlyArray<readonly number[]>): void {
    this.writeHeights(values);
  }

  /** Animate to the displacement frame at `elapsed` seconds, looping over the
   *  configured period. A no-op when the surface was built without `frames`. */
  update(elapsed: number): void {
    if (!this.frames || this.frames.length === 0) {
      return;
    }
    const count = this.frames.length;
    if (count === 1) {
      return;
    }
    const phase = ((elapsed / this.period) % 1 + 1) % 1;
    const cursor = phase * count;
    const lo = Math.floor(cursor) % count;
    const hi = (lo + 1) % count;
    const f = cursor - Math.floor(cursor);
    this.writeInterpolatedHeights(this.frames[lo], this.frames[hi], f);
  }

  dispose(): void {
    this.geometry.dispose();
    this.object.traverse((node) => {
      if (node instanceof THREE.Mesh || node instanceof THREE.LineSegments) {
        (node.material as THREE.Material).dispose();
      }
    });
  }

  private writeHeights(values: ReadonlyArray<readonly number[]>): void {
    const [sx, sy, sz] = this.transform.scale;
    const [ox, oy, oz] = this.transform.offset;
    let v = 0;
    for (let row = 0; row < this.rows; row += 1) {
      for (let col = 0; col < this.cols; col += 1) {
        const height = values[row][col];
        this.position.setXYZ(
          v,
          this.xValues[col] * sx + ox,
          height * sy + oy,
          this.yValues[row] * sz + oz,
        );
        const [r, g, b] = this.scale.atUnit(height);
        this.color.setXYZ(v, r, g, b);
        v += 1;
      }
    }
    this.commit();
  }

  private writeInterpolatedHeights(
    a: ReadonlyArray<readonly number[]>,
    b: ReadonlyArray<readonly number[]>,
    f: number,
  ): void {
    const [sx, sy, sz] = this.transform.scale;
    const [ox, oy, oz] = this.transform.offset;
    let v = 0;
    for (let row = 0; row < this.rows; row += 1) {
      for (let col = 0; col < this.cols; col += 1) {
        const height = a[row][col] + (b[row][col] - a[row][col]) * f;
        this.position.setXYZ(
          v,
          this.xValues[col] * sx + ox,
          height * sy + oy,
          this.yValues[row] * sz + oz,
        );
        const [r, g, b2] = this.scale.atUnit(height);
        this.color.setXYZ(v, r, g, b2);
        v += 1;
      }
    }
    this.commit();
  }

  private commit(): void {
    this.position.needsUpdate = true;
    this.color.needsUpdate = true;
    this.geometry.computeVertexNormals();
  }

  private makeGridLines(values: ReadonlyArray<readonly number[]>): THREE.LineSegments {
    const [sx, sy, sz] = this.transform.scale;
    const [ox, oy, oz] = this.transform.offset;
    // Lift the reference lines a hair above the surface so they read cleanly.
    const lift = oy + 0.01;
    const at = (row: number, col: number): THREE.Vector3 =>
      new THREE.Vector3(
        this.xValues[col] * sx + ox,
        values[row][col] * sy + lift,
        this.yValues[row] * sz + oz,
      );
    const points: THREE.Vector3[] = [];
    const rowStep = Math.max(1, Math.floor(this.rows / 10));
    const colStep = Math.max(1, Math.floor(this.cols / 10));
    for (let row = 0; row < this.rows; row += rowStep) {
      for (let col = 0; col < this.cols - 1; col += 1) {
        points.push(at(row, col), at(row, col + 1));
      }
    }
    for (let col = 0; col < this.cols; col += colStep) {
      for (let row = 0; row < this.rows - 1; row += 1) {
        points.push(at(row, col), at(row + 1, col));
      }
    }
    return new THREE.LineSegments(
      new THREE.BufferGeometry().setFromPoints(points),
      new THREE.LineBasicMaterial({ color: new THREE.Color(theme.textFaint), transparent: true, opacity: 0.12 }),
    );
  }
}

function triangleIndices(rows: number, cols: number): number[] {
  const indices: number[] = [];
  for (let row = 0; row < rows - 1; row += 1) {
    for (let col = 0; col < cols - 1; col += 1) {
      const a = row * cols + col;
      const b = row * cols + col + 1;
      const c = (row + 1) * cols + col + 1;
      const d = (row + 1) * cols + col;
      indices.push(a, b, d, b, c, d);
    }
  }
  return indices;
}

/** Min/max over one or more height grids, used as the default color domain. */
function heightRange(grids: ReadonlyArray<ReadonlyArray<readonly number[]>>): [number, number] {
  let min = Infinity;
  let max = -Infinity;
  for (const grid of grids) {
    for (const row of grid) {
      for (const value of row) {
        if (!Number.isFinite(value)) {
          continue;
        }
        if (value < min) min = value;
        if (value > max) max = value;
      }
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return [0, 1];
  }
  return [min, max];
}
