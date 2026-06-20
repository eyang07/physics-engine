/**
 * Data colormaps — the second half of the color system.
 *
 * These are NOT chrome (see design/tokens.css for UI color). They encode
 * *data*: scalar fields with perceptually-uniform maps, and periodic
 * quantities (angle, phase, flow direction) with a cyclic map so that 0 and
 * 2*pi share a color. The cyclic map is what carries forward to fluid
 * velocity-direction fields.
 *
 * The maps are faithful approximations of matplotlib's viridis / magma /
 * twilight, sampled at a handful of anchors and linearly interpolated. They
 * preserve the properties that matter — the luminance ramp, the hue
 * progression, and (for twilight) exact endpoint wrap — and are tuned to read
 * well on the deep-ink stage. They carry no external dependency, so the same
 * module serves both 2D canvas and three.js.
 */

/** RGB triple, each channel in 0..255. */
export type RGB = [number, number, number];

interface Anchor {
  /** Position in 0..1. */
  t: number;
  rgb: RGB;
}

export interface Colormap {
  readonly name: string;
  /** Cyclic maps wrap (at(0) === at(1)); use them for angles and directions. */
  readonly cyclic: boolean;
  /** Sample to RGB in 0..255. Input is wrapped if cyclic, else clamped to [0,1]. */
  at(t: number): RGB;
  /** Sample to RGB in 0..1 per channel (for WebGL / three.js colors). */
  atUnit(t: number): RGB;
  /** CSS color string, e.g. "rgb(38, 130, 142)" or "rgba(..., a)". */
  css(t: number, alpha?: number): string;
}

function lerp(a: number, b: number, f: number): number {
  return a + (b - a) * f;
}

function makeColormap(name: string, anchors: Anchor[], cyclic: boolean): Colormap {
  // Anchors are assumed sorted by t, spanning 0..1. For cyclic maps the first
  // and last anchor share the same color, so wrapping is seamless.
  const sample = (input: number): RGB => {
    let t = cyclic ? input - Math.floor(input) : Math.min(1, Math.max(0, input));

    // Find the segment [lo, hi] containing t.
    let hi = 1;
    while (hi < anchors.length && anchors[hi].t < t) {
      hi += 1;
    }
    if (hi >= anchors.length) {
      hi = anchors.length - 1;
    }
    const lo = hi - 1;
    const a = anchors[lo];
    const b = anchors[hi];
    const span = b.t - a.t;
    const f = span <= 0 ? 0 : (t - a.t) / span;

    return [
      Math.round(lerp(a.rgb[0], b.rgb[0], f)),
      Math.round(lerp(a.rgb[1], b.rgb[1], f)),
      Math.round(lerp(a.rgb[2], b.rgb[2], f)),
    ];
  };

  return {
    name,
    cyclic,
    at: sample,
    atUnit(t: number): RGB {
      const [r, g, b] = sample(t);
      return [r / 255, g / 255, b / 255];
    },
    css(t: number, alpha = 1): string {
      const [r, g, b] = sample(t);
      return alpha >= 1 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${alpha})`;
    },
  };
}

function anchorsFrom(stops: RGB[], cyclic: boolean): Anchor[] {
  const last = stops.length - 1;
  return stops.map((rgb, index) => ({ t: index / last, rgb, cyclic }));
}

/** Perceptually-uniform, dark -> bright. Default for scalar fields. */
export const viridis = makeColormap(
  "viridis",
  anchorsFrom(
    [
      [68, 1, 84],
      [72, 40, 120],
      [62, 74, 137],
      [49, 104, 142],
      [38, 130, 142],
      [31, 158, 137],
      [53, 183, 121],
      [143, 215, 68],
      [253, 231, 37],
    ],
    false,
  ),
  false,
);

/** Perceptually-uniform, black -> magenta -> cream. Dramatic on deep ink. */
export const magma = makeColormap(
  "magma",
  anchorsFrom(
    [
      [0, 0, 4],
      [20, 14, 54],
      [59, 15, 112],
      [100, 26, 128],
      [140, 41, 129],
      [183, 55, 121],
      [222, 73, 104],
      [251, 136, 97],
      [252, 253, 191],
    ],
    false,
  ),
  false,
);

/** Cyclic (endpoints match). Use for angle, phase, and flow direction. */
export const twilight = makeColormap(
  "twilight",
  anchorsFrom(
    [
      [230, 222, 228],
      [160, 180, 212],
      [86, 140, 196],
      [44, 96, 168],
      [40, 52, 112],
      [74, 40, 96],
      [140, 52, 84],
      [196, 98, 96],
      [224, 170, 168],
      [230, 222, 228],
    ],
    true,
  ),
  true,
);

export const colormaps: Record<string, Colormap> = { viridis, magma, twilight };

/**
 * A scalar-to-color scale — the single honest mapping from a data value in a
 * known range onto a colormap. Field magnitude, curvature, intensity, and
 * potential readouts all build their coloring on this, so the same value reads
 * as the same color everywhere. The domain is *clamped*: out-of-range values
 * saturate at the endpoints rather than wrapping or extrapolating, and a
 * degenerate (zero-width or non-finite) domain collapses to the low end instead
 * of dividing by zero.
 */
export interface ScalarScale {
  readonly colormap: Colormap;
  /** The data range the scale spans, as `[min, max]`. */
  readonly domain: readonly [number, number];
  /** Normalize a value to 0..1 within the clamped domain. */
  normalize(value: number): number;
  /** Color for a value, RGB in 0..255. */
  at(value: number): RGB;
  /** Color for a value, RGB in 0..1 per channel (for WebGL / three.js). */
  atUnit(value: number): RGB;
  /** CSS color string for a value. */
  css(value: number, alpha?: number): string;
}

export function scalarScale(colormap: Colormap, domain: readonly [number, number]): ScalarScale {
  const [lo, hi] = domain;
  const span = hi - lo;
  const normalize = (value: number): number => {
    if (!(span > 0) || !Number.isFinite(value)) {
      return 0;
    }
    const t = (value - lo) / span;
    return t < 0 ? 0 : t > 1 ? 1 : t;
  };
  return {
    colormap,
    domain: [lo, hi],
    normalize,
    at: (value) => colormap.at(normalize(value)),
    atUnit: (value) => colormap.atUnit(normalize(value)),
    css: (value, alpha = 1) => colormap.css(normalize(value), alpha),
  };
}

/**
 * Sample a colormap at evenly spaced stops as a CSS `linear-gradient` color
 * list. Shared so an on-stage legend can paint a ramp that matches exactly what
 * a `ScalarScale` built on the same colormap draws.
 */
export function gradientStops(colormap: Colormap, steps = 12): string[] {
  const count = Math.max(2, Math.floor(steps));
  const stops: string[] = [];
  for (let i = 0; i < count; i += 1) {
    stops.push(colormap.css(i / (count - 1)));
  }
  return stops;
}
