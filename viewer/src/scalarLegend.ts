/**
 * FE-038 — the shared on-stage scalar legend.
 *
 * Every scalar readout the viewer paints (potential, field magnitude, curvature,
 * intensity) colors its data with a `ScalarScale` over some colormap. This is
 * the one legend that captions that ramp, so the key reads the same way across
 * lenses instead of each lens reinventing its own swatch. It stays honest: the
 * ramp is sampled from the *same* colormap the data uses, and the endpoints are
 * labelled qualitatively (low -> high, faint -> bright) — never raw decimals,
 * which would imply a precision the colored field does not carry.
 *
 * It is a plain DOM overlay (not canvas-drawn) so it can sit over both the 2D
 * canvas lenses and the three.js scenes without a second implementation.
 */
import { type Colormap, gradientStops, viridis } from "./design/colormaps";

export type LegendCorner = "top-left" | "top-right" | "bottom-left" | "bottom-right";

export interface ScalarLegendOptions {
  /** Caption above the ramp, e.g. "potential" or "field magnitude". */
  title: string;
  /** Colormap whose ramp the legend paints. Defaults to viridis. */
  colormap?: Colormap;
  /** Qualitative label for the low end. Defaults to "low". */
  low?: string;
  /** Qualitative label for the high end. Defaults to "high". */
  high?: string;
  /** Which stage corner the legend sits in. Defaults to "top-right". */
  corner?: LegendCorner;
}

export interface ScalarLegend {
  /** The overlay element; append it to the stage container once. */
  readonly element: HTMLElement;
  /** Re-skin the ramp and labels for a new scale, reusing the same node. */
  setColormap(colormap: Colormap, title?: string, low?: string, high?: string): void;
  show(): void;
  hide(): void;
  dispose(): void;
}

export function createScalarLegend(options: ScalarLegendOptions): ScalarLegend {
  const element = document.createElement("div");
  element.className = `scalar-legend scalar-legend--${options.corner ?? "top-right"}`;
  element.hidden = true;

  const title = document.createElement("p");
  title.className = "scalar-legend__title";

  const body = document.createElement("div");
  body.className = "scalar-legend__body";

  const ramp = document.createElement("div");
  ramp.className = "scalar-legend__ramp";
  // The ramp is decorative (it duplicates the on-stage coloring), so keep it out
  // of the accessibility tree; the title + endpoint labels carry the meaning.
  ramp.setAttribute("aria-hidden", "true");

  const labels = document.createElement("div");
  labels.className = "scalar-legend__labels";
  const highLabel = document.createElement("span");
  highLabel.className = "scalar-legend__label";
  const lowLabel = document.createElement("span");
  lowLabel.className = "scalar-legend__label";
  labels.append(highLabel, lowLabel);

  body.append(ramp, labels);
  element.append(title, body);

  function setColormap(colormap: Colormap, nextTitle?: string, low?: string, high?: string): void {
    if (nextTitle !== undefined) {
      title.textContent = nextTitle;
    }
    lowLabel.textContent = low ?? "low";
    highLabel.textContent = high ?? "high";
    // Paint top -> bottom as high -> low so the ramp reads like the labels.
    const stops = gradientStops(colormap).slice().reverse();
    ramp.style.background = `linear-gradient(to bottom, ${stops.join(", ")})`;
  }

  setColormap(options.colormap ?? viridis, options.title, options.low, options.high);

  return {
    element,
    setColormap,
    show() {
      element.hidden = false;
    },
    hide() {
      element.hidden = true;
    },
    dispose() {
      element.remove();
    },
  };
}
