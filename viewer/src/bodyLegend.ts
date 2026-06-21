/**
 * FE-042 — the shared on-stage categorical legend.
 *
 * The N-body orbit lens draws one colored trail per body; this overlay is the
 * key that names each color, so a reader can tell the bodies apart without
 * decoding the palette. It is the discrete sibling of the scalar legend
 * (`scalarLegend.ts`): that one captions a continuous color ramp, this one lists
 * a fixed set of labelled swatches. Like the scalar legend it is a plain DOM
 * overlay so it can sit over both the 2D canvas lenses and the three.js scenes.
 *
 * It stays honest — the swatch colors are the *same* palette the trails use, and
 * the labels identify bodies, never encoding any measured magnitude.
 */
import type { LegendCorner } from "./scalarLegend";

export interface BodyLegendEntry {
  /** The body label, e.g. "Body 1". */
  readonly label: string;
  /** The CSS swatch color — the same color the body's trail uses. */
  readonly color: string;
}

export interface BodyLegendOptions {
  /** Caption above the entries, e.g. "bodies". */
  title: string;
  /** Which stage corner the legend sits in. Defaults to "top-right". */
  corner?: LegendCorner;
}

export interface BodyLegend {
  /** The overlay element; append it to the stage container once. */
  readonly element: HTMLElement;
  /** Rebuild the swatch rows for a new set of bodies, reusing the same node. */
  setEntries(entries: readonly BodyLegendEntry[]): void;
  show(): void;
  hide(): void;
  dispose(): void;
}

export function createBodyLegend(options: BodyLegendOptions): BodyLegend {
  const element = document.createElement("div");
  element.className = `body-legend body-legend--${options.corner ?? "top-right"}`;
  element.hidden = true;

  const title = document.createElement("p");
  title.className = "body-legend__title";
  title.textContent = options.title;

  const list = document.createElement("ul");
  list.className = "body-legend__list";

  element.append(title, list);

  function setEntries(entries: readonly BodyLegendEntry[]): void {
    list.replaceChildren();
    for (const entry of entries) {
      const row = document.createElement("li");
      row.className = "body-legend__item";

      const swatch = document.createElement("span");
      swatch.className = "body-legend__swatch";
      // The swatch duplicates the on-stage color, so keep it out of the
      // accessibility tree; the label carries the meaning.
      swatch.setAttribute("aria-hidden", "true");
      swatch.style.background = entry.color;

      const label = document.createElement("span");
      label.className = "body-legend__label";
      label.textContent = entry.label;

      row.append(swatch, label);
      list.append(row);
    }
  }

  return {
    element,
    setEntries,
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
