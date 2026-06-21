/**
 * FE-040 — a reusable rigid-body attitude primitive.
 *
 * A rotating body cannot be read from a moving point; it needs a visible frame.
 * `AttitudeBody` renders a translucent body shell, a body-fixed axis rod (the
 * symmetry / rotation axis), and the body-frame triad (e1, e2, e3) so a spin is
 * legible. The orientation is driven straight from the exported quaternion
 * series via `setQuaternion` — the viewer renders the attitude Python measured,
 * it never re-integrates Euler's equations. The rigid-body lenses (FE-040, and
 * FE-041's polhode lens) compose this rather than each rolling their own body.
 */
import * as THREE from "three";

import type { Vector3Tuple } from "./data/trajectory";
import { theme } from "./design/theme";

export interface AttitudeBodyOptions {
  /** Half-extents of the translucent body box, in body-frame units. */
  readonly halfExtents?: Vector3Tuple;
  /** Length of the body-frame triad arrows. */
  readonly triadLength?: number;
  /** A body-fixed axis rod (e.g. the symmetry axis), in body coordinates. */
  readonly axis?: { start: Vector3Tuple; end: Vector3Tuple };
  /** Opacity of the body shell. */
  readonly opacity?: number;
}

// Distinct, fixed triad colors so the three body axes stay visually separable as
// the body tumbles (warm e1, cool e2, green e3) — independent of the UI tokens.
const TRIAD_COLORS: readonly [number, number, number] = [0xf0746a, 0x6fb6c9, 0x8ed081];

export class AttitudeBody {
  readonly object = new THREE.Group();
  private readonly disposables: { dispose(): void }[] = [];

  constructor(options: AttitudeBodyOptions = {}) {
    const half = options.halfExtents ?? [0.18, 0.18, 0.32];
    const triadLength = options.triadLength ?? 0.5;
    const opacity = options.opacity ?? 0.32;

    const boxGeometry = new THREE.BoxGeometry(half[0] * 2, half[1] * 2, half[2] * 2);
    const boxMaterial = new THREE.MeshStandardMaterial({
      color: new THREE.Color(theme.cool),
      transparent: true,
      opacity,
      roughness: 0.62,
      metalness: 0.06,
      side: THREE.DoubleSide,
    });
    this.object.add(new THREE.Mesh(boxGeometry, boxMaterial));
    this.track(boxGeometry, boxMaterial);

    const edgesGeometry = new THREE.EdgesGeometry(boxGeometry);
    const edgesMaterial = new THREE.LineBasicMaterial({
      color: new THREE.Color(theme.textFaint),
      transparent: true,
      opacity: 0.4,
    });
    this.object.add(new THREE.LineSegments(edgesGeometry, edgesMaterial));
    this.track(edgesGeometry, edgesMaterial);

    if (options.axis) {
      this.object.add(this.makeAxisRod(options.axis.start, options.axis.end));
    }

    this.object.add(this.makeTriadArrow([triadLength, 0, 0], TRIAD_COLORS[0]));
    this.object.add(this.makeTriadArrow([0, triadLength, 0], TRIAD_COLORS[1]));
    this.object.add(this.makeTriadArrow([0, 0, triadLength], TRIAD_COLORS[2]));
  }

  /** Orient the body from one exported quaternion entry, ordered [w, x, y, z]. */
  setQuaternion(quaternion: readonly [number, number, number, number]): void {
    const [w, x, y, z] = quaternion;
    this.object.quaternion.set(x, y, z, w);
  }

  dispose(): void {
    for (const disposable of this.disposables) {
      disposable.dispose();
    }
    this.disposables.length = 0;
  }

  private track(...resources: { dispose(): void }[]): void {
    this.disposables.push(...resources);
  }

  private makeAxisRod(start: Vector3Tuple, end: Vector3Tuple): THREE.Group {
    const group = new THREE.Group();
    const a = new THREE.Vector3(start[0], start[1], start[2]);
    const b = new THREE.Vector3(end[0], end[1], end[2]);
    const rodGeometry = new THREE.BufferGeometry().setFromPoints([a, b]);
    const rodMaterial = new THREE.LineBasicMaterial({
      color: new THREE.Color(theme.textPrimary),
      transparent: true,
      opacity: 0.7,
    });
    group.add(new THREE.Line(rodGeometry, rodMaterial));
    this.track(rodGeometry, rodMaterial);

    const direction = b.clone().sub(a);
    if (direction.length() > 1e-6) {
      const capGeometry = new THREE.ConeGeometry(0.03, 0.1, 16);
      const capMaterial = new THREE.MeshBasicMaterial({ color: new THREE.Color(theme.textPrimary) });
      const cap = new THREE.Mesh(capGeometry, capMaterial);
      cap.position.copy(b);
      cap.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.clone().normalize());
      group.add(cap);
      this.track(capGeometry, capMaterial);
    }
    return group;
  }

  private makeTriadArrow(vector: Vector3Tuple, color: number): THREE.Group {
    const group = new THREE.Group();
    const tip = new THREE.Vector3(vector[0], vector[1], vector[2]);
    const lineGeometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), tip]);
    const lineMaterial = new THREE.LineBasicMaterial({ color: new THREE.Color(color) });
    group.add(new THREE.Line(lineGeometry, lineMaterial));
    this.track(lineGeometry, lineMaterial);

    const coneGeometry = new THREE.ConeGeometry(0.032, 0.1, 16);
    const coneMaterial = new THREE.MeshBasicMaterial({ color: new THREE.Color(color) });
    const cone = new THREE.Mesh(coneGeometry, coneMaterial);
    cone.position.copy(tip);
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tip.clone().normalize());
    group.add(cone);
    this.track(coneGeometry, coneMaterial);
    return group;
  }
}
