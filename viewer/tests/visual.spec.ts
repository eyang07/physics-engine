import { readFileSync } from "node:fs";

import { expect, type Page, test } from "@playwright/test";

async function expectCanvasNonBlank(page: Page, selector: string) {
  const nonBlankPixels = await page.locator(selector).evaluate((canvas: HTMLCanvasElement) => {
    const context2d = canvas.getContext("2d");
    if (context2d) {
      const { width, height } = canvas;
      const sample = context2d.getImageData(0, 0, width, height).data;
      let count = 0;
      for (let i = 0; i < sample.length; i += 16) {
        const alpha = sample[i + 3];
        const isLightBackground = sample[i] > 235 && sample[i + 1] > 235 && sample[i + 2] > 235;
        if (alpha > 0 && !isLightBackground) {
          count += 1;
        }
      }
      return count;
    }

    const gl = canvas.getContext("webgl2") ?? canvas.getContext("webgl");
    if (!gl) {
      return 0;
    }

    const width = gl.drawingBufferWidth;
    const height = gl.drawingBufferHeight;
    const pixels = new Uint8Array(width * height * 4);
    gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);

    let count = 0;
    for (let i = 0; i < pixels.length; i += 16) {
      const alpha = pixels[i + 3];
      const isLightBackground = pixels[i] > 235 && pixels[i + 1] > 235 && pixels[i + 2] > 235;
      if (alpha > 0 && !isLightBackground) {
        count += 1;
      }
    }
    return count;
  });

  expect(nonBlankPixels).toBeGreaterThan(200);
}

// The verbose IR (obligation/candidate/assumption cards, evidence toggles) lives
// in a collapsed <details>; open it before interacting with those elements.
async function openVerificationDetails(page: Page) {
  await page.locator(".verif-details").evaluate((node) => {
    (node as HTMLDetailsElement).open = true;
  });
}

async function expectFitToSystemKeepsSceneRendered(page: Page) {
  await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
  await expect(page.locator("#fitToSystem")).toBeVisible();
  await page.locator("#fitToSystem").click();
  await page.waitForTimeout(300);
  await expectCanvasNonBlank(page, "#hamiltonianScene");
}

const threeJsSystems = [
  "sphere-geodesic",
  "surface-geodesic",
  "wormhole",
  "charged-particle",
  "uniform-gravity",
  "ideal-spring",
  "kepler",
  "bead-on-hoop",
  "lorenz-attractor",
  "henon-heiles",
  "free-rigid-body",
  "n-body-gravity",
  "membrane",
];

for (const viewport of [
  { name: "desktop", width: 1280, height: 820 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`renders all example systems at ${viewport.name}`, async ({ page }, testInfo) => {
    // This test walks the full example gallery, so it runs longer than the
    // 30s default; give it headroom as more systems land.
    test.setTimeout(60_000);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    // Boot straight into the Systems workbench — no splash gate, no gallery page.
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-workbench.png`) });

    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-pendulum.png`) });

    // The pendulum exports an invariant-residual diagnostic (energy drift), so
    // the diagnostics panel shows a conservation-drift lane on boot. Candidate
    // certificates and the safety-region overlay now live in the Verification
    // workbench (covered separately), not the Systems diagnostics panel.
    await expect(page.locator("#diagnostics .diagnostic__residual").first()).toBeVisible();

    await page.getByRole("button", { name: "Hamiltonian Flow" }).click();
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);

    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-hamiltonian.png`) });

    await page.getByRole("button", { name: "Potential" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-pendulum-potential.png`) });

    await page.locator("#systemSelect").selectOption("sphere-geodesic");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);

    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-sphere-geodesic.png`) });

    // FE-049: the surface-geodesic lens draws the exported surface-of-revolution
    // embedding mesh with the geodesic drawn on the surface (here a torus).
    // FE-050: the mesh is tinted by the exported Gaussian curvature, keyed by a
    // qualitative viridis legend (saddle → dome) with no raw decimals.
    await page.locator("#systemSelect").selectOption("surface-geodesic");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);

    await expectCanvasNonBlank(page, "#hamiltonianScene");
    const curvatureLegend = page.locator("#systemsDomain .scalar-legend--top-right");
    await expect(curvatureLegend).toBeVisible();
    await expect(curvatureLegend.locator(".scalar-legend__title")).toHaveText("Gaussian curvature");
    await expect(curvatureLegend.locator(".scalar-legend__label")).toHaveText(["dome", "saddle"]);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-surface-geodesic.png`) });

    // FE-051: the parallel-transported frame animates along the curve. Let
    // playback advance and capture a second frame; the scene must keep rendering
    // (the transport-arrow animation runs without breaking the render loop).
    await page.waitForTimeout(1200);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-surface-geodesic-transport.png`) });

    await page.locator("#systemSelect").selectOption("charged-particle");
    // Leaving the curvature-colored surface for a plain 3D lens hides the legend.
    await expect(curvatureLegend).toBeHidden();
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);

    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-charged-particle.png`) });

    await page.locator("#systemSelect").selectOption("uniform-gravity");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-uniform-gravity.png`) });

    await page.getByRole("button", { name: "Vertical Phase" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-uniform-gravity-phase.png`) });

    await page.getByRole("button", { name: "Potential" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-uniform-gravity-potential.png`) });

    await page.locator("#systemSelect").selectOption("ideal-spring");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-ideal-spring.png`) });

    await page.getByRole("button", { name: "Phase Portrait" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-ideal-spring-phase.png`) });

    await page.getByRole("button", { name: "Potential" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-ideal-spring-potential.png`) });

    await page.locator("#systemSelect").selectOption("kepler");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-kepler.png`) });

    // FE-052: the effective-potential lens draws the exported V(r) curve, energy
    // line, and turning points alongside the orbit itself (the closed Kepler
    // ellipse) with its qualitative class — all from exported data, never re-derived.
    await page.getByRole("button", { name: "Effective Potential" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-effective-potential.png`) });

    await page.getByRole("button", { name: "Radial Phase" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-kepler-radial-phase.png`) });

    await page.locator("#systemSelect").selectOption("bead-on-hoop");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-bead-hoop.png`) });

    await page.getByRole("button", { name: "Phase Portrait" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-bead-hoop-phase.png`) });

    await page.getByRole("button", { name: "Potential" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-bead-hoop-potential.png`) });

    await page.locator("#systemSelect").selectOption("lorenz-attractor");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-lorenz-attractor.png`) });

    // The parameter-family switch loads a backend-generated variant in place.
    await page.getByRole("button", { name: "rho = 20" }).click();
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-lorenz-rho-20.png`) });

    await page.locator("#systemSelect").selectOption("henon-heiles");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-henon-heiles.png`) });

    await page.getByRole("button", { name: "Phase Portrait" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-henon-heiles-phase.png`) });

    await page.getByRole("button", { name: "Potential Contours" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    // FE-038: the shared scalar legend captions the potential field with a
    // colormap ramp and qualitative (decimal-free) endpoints. Target the
    // top-right (scalar) legend specifically; the field-magnitude legend (FE-045)
    // is a second scalar legend in the opposite corner.
    const scalarLegend = page.locator("#systemsDomain .scalar-legend--top-right");
    await expect(scalarLegend).toBeVisible();
    await expect(scalarLegend.locator(".scalar-legend__title")).toHaveText("potential");
    await expect(scalarLegend.locator(".scalar-legend__label")).toHaveText(["high", "low"]);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-henon-heiles-potential.png`) });

    await page.getByRole("button", { name: /Poincar/ }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    // Non-scalar lenses hide the legend rather than leaving a stale key.
    await expect(scalarLegend).toBeHidden();
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-henon-heiles-poincare.png`) });

    await page.locator("#systemSelect").selectOption("variable-speed-wavefront");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    // FE-048: the wavefront colors its reached fronts by the measured intensity
    // proxy (bright near caustics), keyed by a qualitative magma legend.
    await expect(scalarLegend).toBeVisible();
    await expect(scalarLegend.locator(".scalar-legend__title")).toHaveText("wavefront intensity");
    await expect(scalarLegend.locator(".scalar-legend__label")).toHaveText(["focused", "spread"]);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-variable-speed-wavefront.png`) });

    // FE-047: the membrane opens on its mode-surface lens — an animated
    // displacement surface (FE-039) with a rectangular/circular shape selector.
    await page.locator("#systemSelect").selectOption("membrane");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    const membraneModes = page.locator("#membraneModesSection");
    await expect(membraneModes).toBeVisible();
    await expect(membraneModes.locator(".mode-switch__button")).toHaveCount(2);
    // Leaving the wavefront for a non-scalar 3D lens hides the intensity legend.
    await expect(scalarLegend).toBeHidden();
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-membrane-rectangular.png`) });

    // Switching to the circular shape rebuilds the surface from exported data.
    await page.getByRole("button", { name: "circular displacement" }).click();
    await page.waitForTimeout(600);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-membrane-circular.png`) });

    // Switching to a system without a membrane hides the shape selector again.
    await page.locator("#systemSelect").selectOption("free-rigid-body");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(300);
    await expect(membraneModes).toBeHidden();

    // FE-040: the heavy symmetric top opens on its attitude-playback lens, a
    // Three.js scene that spins the body from the exported orientation series.
    await page.locator("#systemSelect").selectOption("symmetric-top");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-symmetric-top-axis.png`) });

    // The top's nutation-angle phase portrait renders on the generic 2D phase
    // lens (no bespoke code — the exported projection drives it).
    await page.getByRole("button", { name: "Nutation Phase" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-symmetric-top-nutation.png`) });

    // The nutation effective potential renders on the shared data-driven
    // effective-potential lens (exported V(theta) curve + energy line).
    await page.getByRole("button", { name: "Effective Potential" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-symmetric-top-potential.png`) });

    // The double pendulum's theta1 phase portrait also renders on the shared 2D
    // phase lens.
    await page.locator("#systemSelect").selectOption("double-pendulum");
    await page.getByRole("button", { name: "Phase Portraits" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-double-pendulum-phase.png`) });

    // Schwarzschild's GR effective potential renders from the exported relativistic
    // V(r) curve, turning points, and orbit classification (same data-driven lens).
    // FE-052: the lens also draws the precessing GR orbit (a rosette) next to the
    // potential, so the precession is visible against the closed Kepler ellipse.
    await page.locator("#systemSelect").selectOption("schwarzschild");
    await page.getByRole("button", { name: "GR Effective Potential" }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-schwarzschild-potential.png`) });

    // FE-054: the Schwarzschild orbit carries a measured geodesic-deviation lane —
    // the neighbor's relative separation along the geodesic, labeled "measured"
    // with a qualitative trend (diverging/converging) and the neighbor's initial
    // offset. It is honest measured evidence of tidal focusing, never a proof.
    const deviationLane = page.locator("#diagnostics .diagnostic__deviation");
    await expect(deviationLane).toHaveCount(1);
    await expectCanvasNonBlank(page, "#diagnostics .diagnostic__deviation >> nth=0");
    const deviationRow = page
      .locator("#diagnostics .diagnostic")
      .filter({ has: page.locator(".diagnostic__deviation") });
    await expect(deviationRow.locator(".diagnostic__measured")).toHaveText("measured");
    await expect(deviationRow.locator(".diagnostic__caption")).toHaveText(
      /diverging|converging|neutral/,
    );
    await expect(deviationRow.locator(".diagnostic__offset")).toContainText("neighbor");

    // FE-053: the Ellis wormhole opens on its embedding-funnel lens — the exported
    // surface mesh (the funnel through the throat) with the geodesic drawn on the
    // surface, reusing the FE-049 surface-geodesic primitive. The default radial
    // variant traverses the throat (passes through to the far sheet).
    await page.locator("#systemSelect").selectOption("wormhole");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-wormhole-traversing.png`) });

    // The angular-reflection variant loads its backend-generated geodesic in place:
    // the curve turns back at the throat instead of crossing, read from the data.
    await page.getByRole("button", { name: "Angular reflection" }).click();
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-wormhole-reflected.png`) });

    // FE-041: the free asymmetric top opens on its polhode lens — the
    // momentum-sphere ∩ energy-ellipsoid construction with the tumbling body,
    // drawn from the exported rigid-body geometry (a Three.js scene).
    await page.locator("#systemSelect").selectOption("free-rigid-body");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-free-rigid-body-polhode.png`) });

    // FE-042: the N-body gravity system opens on its orbit-trail lens — per-body
    // trails framed on the center of mass, keyed by a categorical body legend.
    await page.locator("#systemSelect").selectOption("n-body-gravity");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    const bodyLegend = page.locator(".body-legend");
    await expect(bodyLegend).toBeVisible();
    await expect(bodyLegend.locator(".body-legend__item")).toHaveCount(3);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-n-body-figure-eight.png`) });

    // The Sun–planets variant loads its own backend-generated data in place and
    // still frames sensibly on the COM (no browser-side regeneration).
    await page.getByRole("button", { name: "Sun + two planets" }).click();
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);
    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-n-body-sun-planets.png`) });

    // Switching to a non-N-body system hides the body legend again.
    await page.locator("#systemSelect").selectOption("free-rigid-body");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(400);
    await expect(bodyLegend).toBeHidden();

    // FE-043: the coupled-oscillator chain opens on its normal-mode lens — an
    // animated mode shape on the 2D canvas with a mode selector and a
    // superposition scrub, driven by the exported eigenvectors/frequencies.
    await page.locator("#systemSelect").selectOption("coupled-oscillators");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(600);
    await expectCanvasNonBlank(page, "#scene");
    const modeControls = page.locator("#modeControlsSection");
    await expect(modeControls).toBeVisible();
    await expect(modeControls.locator("#modeSelector .mode-switch__button")).toHaveCount(4);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-coupled-oscillators-mode1.png`) });

    // Selecting a higher mode and scrubbing the superposition keeps it rendering
    // and updates the qualitative caption (no raw decimals).
    await page.locator("#modeSelector .mode-switch__button").nth(2).click();
    await page.locator("#modeBlend").evaluate((element) => {
      const input = element as HTMLInputElement;
      input.value = "0.5";
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await page.waitForTimeout(600);
    await expectCanvasNonBlank(page, "#scene");
    await expect(page.locator("#modeBlendLabel")).toContainText("superpose");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-coupled-oscillators-superpose.png`) });

    // Switching to a system without modes hides the mode controls again.
    await page.locator("#systemSelect").selectOption("free-rigid-body");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(300);
    await expect(modeControls).toBeHidden();

    // FE-044/FE-045: the electromagnetic field opens on its static-fields lens —
    // the exported electric-potential grid as a heatmap with iso-contours
    // (scalar legend), overlaid with the electric field's glyph quiver and field
    // lines colored by magnitude (a second, field-magnitude legend).
    const magnitudeLegend = page.locator("#systemsDomain .scalar-legend--bottom-right");
    await page.locator("#systemSelect").selectOption("electromagnetic-field");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await expect(scalarLegend).toBeVisible();
    await expect(scalarLegend.locator(".scalar-legend__title")).toHaveText("electric potential");
    await expect(scalarLegend.locator(".scalar-legend__label")).toHaveText(["high", "low"]);
    await expect(magnitudeLegend).toBeVisible();
    await expect(magnitudeLegend.locator(".scalar-legend__title")).toHaveText("field magnitude");
    await expect(magnitudeLegend.locator(".scalar-legend__label")).toHaveText(["strong", "weak"]);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-electromagnetic-field.png`) });

    // Switching to a non-scalar Three.js lens hides both field legends again.
    await page.locator("#systemSelect").selectOption("free-rigid-body");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(300);
    await expect(scalarLegend).toBeHidden();
    await expect(magnitudeLegend).toBeHidden();

    // FE-046: the vibrating string opens on its 1D wave lens — an animated
    // displacement curve from the exported series, with a standing/traveling
    // toggle (two exported solutions).
    await page.locator("#systemSelect").selectOption("vibrating-string");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    const waveSeries = page.locator("#waveSeriesSection");
    await expect(waveSeries).toBeVisible();
    await expect(waveSeries.locator(".mode-switch__button")).toHaveCount(2);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-vibrating-string-standing.png`) });

    // Toggling to the traveling solution keeps the lens animating from exported
    // data.
    await page.getByRole("button", { name: "traveling displacement" }).click();
    await page.waitForTimeout(400);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-vibrating-string-traveling.png`) });

    // FE-046: the dispersive wave packet animates its exported amplitude /
    // envelope-intensity series (the envelope spreads over time).
    await page.locator("#systemSelect").selectOption("wave-packet");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await expect(waveSeries.locator(".mode-switch__button")).toHaveCount(2);
    await page.getByRole("button", { name: "intensity" }).click();
    await page.waitForTimeout(400);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-wave-packet.png`) });

    // Switching to a system without a wave series hides the toggle again.
    await page.locator("#systemSelect").selectOption("free-rigid-body");
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(300);
    await expect(waveSeries).toBeHidden();

    // FE-067: the relativistic free particle opens on its Minkowski spacetime
    // diagram — the backend worldline (BE-119) plotted on a light-cone reference
    // frame with coordinate time running up the vertical axis. No physics is
    // recomputed here; the worldline, apex, and signal speed are read from the
    // export.
    await page.locator("#systemSelect").selectOption("relativistic-free-particle");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-relativistic-worldline.png`) });

    // The hard top-level domain menu swaps to the Verification workbench, which
    // renders the exported verification-problem IR read-only.
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(
      page.getByRole("heading", { name: /upright pendulum safety/i }),
    ).toBeVisible();
    await expect(page.getByText("external-required").first()).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification.png`) });
    await page.getByRole("button", { name: "Systems" }).click();
    await page.waitForSelector("#systemsDomain.domain--active");
  });

  test(`fit-to-system reset preserves Three.js rendering at ${viewport.name}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.waitForSelector("#scene.stage__canvas--active");

    await page.getByRole("button", { name: "Hamiltonian Flow" }).click();
    await expectFitToSystemKeepsSceneRendered(page);

    for (const systemId of threeJsSystems) {
      await page.locator("#systemSelect").selectOption(systemId);
      await expectFitToSystemKeepsSceneRendered(page);
    }
  });

  test(`navigates between Systems and Verification workbenches at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.waitForSelector("#scene.stage__canvas--active");

    // The top-level workbench switch opens the Verification domain and loads the
    // default problem read-only.
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(
      page.getByRole("heading", { name: /upright pendulum safety/i }),
    ).toBeVisible();

    // The dossier leads with the proof obligations and their measured outcomes,
    // honestly labeled (a clean sample is evidence, never a discharge).
    await expect(page.getByRole("heading", { name: /proof obligations/i })).toBeVisible();
    await expect(page.locator("#verifLedger .verif-status").first()).toBeVisible();

    // Switching back returns to the Systems workbench on the default pendulum.
    await page.getByRole("button", { name: "Systems" }).click();
    await page.waitForSelector("#systemsDomain.domain--active");
    await expect(page.locator("#systemTitle")).toHaveText("Simple Pendulum");
  });

  test(`Verification catalog badges each entry's Tier/regime at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Every catalog entry carries its regime descriptor from the discovery index.
    const items = page.locator("#verificationCatalog .catalog-item");
    await expect(items).toHaveCount(12);
    await expect(page.locator("#verificationCatalog .catalog-item__regime")).toHaveCount(12);

    // The disturbance-robust (Tier-3) packages read "robust"; the rest are
    // "nominal".
    const robust = page.locator("#verificationCatalog .catalog-item__regime--robust");
    await expect(robust).toHaveCount(4);
    await expect(robust.first()).toHaveText("robust");
    await expect(page.locator("#verificationCatalog .catalog-item__regime--nominal")).toHaveCount(8);

    // The disturbed geofence package is badged robust; the nominal geofence
    // package is badged nominal.
    await expect(
      page
        .locator('#verificationCatalog .catalog-item[data-problem-id="drone-disturbed-geofence-axis"] .catalog-item__regime')
        .first(),
    ).toHaveText("robust");
    await expect(
      page
        .locator('#verificationCatalog .catalog-item[data-problem-id="drone-geofence-axis"] .catalog-item__regime')
        .first(),
    ).toHaveText("nominal");
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-regime-badges.png`),
    });
  });

  test(`Verification catalog omits regime badges without the discovery index at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // No discovery index (older export): the catalog still lists every problem,
    // but no entry carries a regime badge.
    await page.route("**/data/verification/packages/packages.index.json", (route) =>
      route.fulfill({ status: 404, body: "" }),
    );

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(page.locator("#verificationCatalog .catalog-item")).toHaveCount(12);
    await expect(page.locator("#verificationCatalog .catalog-item__regime")).toHaveCount(0);
  });

  test(`Verification masthead restates the open problem's Tier/regime at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    const regime = page.locator("#verificationMasthead .verif-masthead__regime");

    // A nominal package: the masthead restates "nominal" with no disturbance
    // detail.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-geofence-axis"]')
      .click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();
    await expect(regime).toHaveClass(/verif-masthead__regime--nominal/);
    await expect(regime.locator(".verif-masthead__regime-kind")).toHaveText("nominal");
    await expect(regime.locator(".verif-masthead__regime-detail")).toHaveCount(0);

    // A disturbance-robust package: the masthead names the regime, the
    // disturbance parameters, and the robust obligation ids it cites.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-disturbed-geofence-axis"]')
      .click();
    await expect(
      page.getByRole("heading", { name: /drone disturbed geofence axis/i }),
    ).toBeVisible();
    await expect(regime).toHaveClass(/verif-masthead__regime--robust/);
    await expect(regime.locator(".verif-masthead__regime-kind")).toHaveText("disturbance-robust");
    await expect(regime).toContainText(/disturbance/i);
    await expect(regime).toContainText("w1");
    await expect(regime).toContainText(/robust obligations/i);
    await expect(regime).toContainText(/geofence-barrier-robust-forward-invariance/);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-masthead-regime.png`),
    });
  });

  test(`Verification masthead omits the regime without the discovery index at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // No discovery index: the masthead carries no regime line.
    await page.route("**/data/verification/packages/packages.index.json", (route) =>
      route.fulfill({ status: 404, body: "" }),
    );

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(page.locator("#verificationMasthead .verif-masthead__regime")).toHaveCount(0);
  });

  test(`Verification stage renders trajectory and certificate lanes at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");

    // Enter the Verification workbench and let its stage animation spin up.
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The catalog lists every exported problem; the first is active by default.
    const catalogItems = page.locator("#verificationCatalog .catalog-item");
    await expect(catalogItems).toHaveCount(12);
    await expect(page.locator("#verificationCatalog .catalog-item--active")).toHaveCount(1);

    // The default problem animates its controlled trajectory on the exported
    // region geometry: the stage canvas must actually paint, not stay blank.
    await page.waitForTimeout(600);
    await expectCanvasNonBlank(page, "#verificationCanvas");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification-stage.png`) });

    // Each linked candidate certificate gets a tracking lane that renders the
    // sampled series against its obligation threshold.
    const certificateLanes = page.locator("#verificationCertificateLanes .diagnostic__certificate");
    await expect(certificateLanes.first()).toBeVisible();
    expect(await certificateLanes.count()).toBeGreaterThan(0);
    await expectCanvasNonBlank(page, "#verificationCertificateLanes .diagnostic__certificate >> nth=0");

    // Switching problems swaps the stage in place and keeps it rendering.
    await catalogItems.nth(1).click();
    await expect(
      page.getByRole("heading", { name: /controlled spring regulator safety/i }),
    ).toBeVisible();
    await page.waitForTimeout(600);
    await expectCanvasNonBlank(page, "#verificationCanvas");

    // Unavailable problem data must degrade honestly: the panel shows a regen
    // message and the stage clears its certificate lanes instead of leaving a
    // stale, misleading overlay painted under the error.
    await page.route("**/data/verification/upright-pendulum-safety.json", (route) =>
      route.abort(),
    );
    await catalogItems.nth(0).click();
    await expect(page.locator("#verificationSummary .verif-empty")).toBeVisible();
    await expect(page.locator("#verificationSummary .verif-empty__copy")).toContainText(
      /could not load/i,
    );
    await expect(certificateLanes).toHaveCount(0);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-unavailable.png`),
    });
  });

  test(`Verification stage marks measured violations at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");

    // No-marker path: the default problem's samples all hold, so the stage draws
    // zero violation markers.
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(page.locator("#verificationCanvas")).toHaveAttribute(
      "data-violation-markers",
      "0",
    );

    // Marker path: inject two measured-violated samples into the pendulum problem
    // — one whose worst point projects onto the stage's (theta, omega) axes, and
    // one sampled on an unrelated projection. Only the mappable one is drawn; the
    // unmappable sample must not produce a misleading marker.
    const mappableViolation = {
      id: "injected-violation-mappable",
      obligationId: "energy-barrier-excludes-near-bottom",
      status: "measured-violated",
      worst: { value: 1.5, point: [2.5, 0.3] },
      evaluation: {
        kind: "region-grid",
        sampleCount: 10,
        source: "injected",
        variables: ["theta", "omega"],
        stateAxes: ["theta", "omega"],
        variableToStateAxis: { theta: "theta", omega: "omega" },
      },
    };
    const unmappableViolation = {
      id: "injected-violation-unmappable",
      obligationId: "energy-barrier-excludes-near-bottom",
      status: "measured-violated",
      worst: { value: 2.0, point: [1.0, 1.0] },
      evaluation: {
        kind: "region-grid",
        sampleCount: 10,
        source: "injected",
        variables: ["phi", "psi"],
        stateAxes: ["phi", "psi"],
        variableToStateAxis: { phi: "phi", psi: "psi" },
      },
    };
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.proofStatuses.push(mappableViolation, unmappableViolation);
      await route.fulfill({ response, json });
    });

    // Reload from scratch so the workbench re-fetches the (now injected) payload
    // and re-selects the default problem.
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(page.locator("#verificationCanvas")).toHaveAttribute(
      "data-violation-markers",
      "1",
    );
    await page.waitForTimeout(400);
    await expectCanvasNonBlank(page, "#verificationCanvas");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification-violation.png`) });
  });

  test(`Verification renders the measured violation reference scenario at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    const legend = page.locator(".verif-violation-legend");

    // A holding keep-out package draws no violation markers and hides the
    // violation legend.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-obstacle-keepout"]')
      .click();
    await expect(page.getByRole("heading", { name: /^drone obstacle keepout$/i })).toBeVisible();
    await page.waitForTimeout(300);
    await expect(page.locator("#verificationCanvas")).toHaveAttribute("data-violation-markers", "0");
    await expect(legend).toBeHidden();

    // The boundary-corner violation scenario exports a measured-violated run: the
    // stage draws the violation marker, names the obligation the run left, and
    // headlines its negative margin — labeled measured evidence, never a disproof.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-obstacle-keepout-violation"]')
      .click();
    await expect(
      page.getByRole("heading", { name: /drone obstacle keepout violation/i }),
    ).toBeVisible();
    await page.waitForTimeout(400);
    await expect(page.locator("#verificationCanvas")).toHaveAttribute("data-violation-markers", "1");
    await expect(legend).toBeVisible();
    await expect(legend.locator(".verif-violation-legend__name")).toContainText(
      /obstacle-keepout.*avoidance/,
    );
    await expect(legend.locator(".verif-violation-legend__margin")).toHaveText("-0.25");
    await expect(legend.locator(".verif-violation-legend__note")).toContainText(
      /entered the unsafe set/i,
    );
    await expect(legend.locator(".verif-violation-legend__note")).toContainText(
      /not a disproof/i,
    );
    await expectCanvasNonBlank(page, "#verificationCanvas");
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-violation-scenario.png`),
    });
  });

  test(`Verification stage marks when the violation occurs on the rollout at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The violation scenario's run carries a worst.time (1.54): the legend names
    // the moment the simulated run crossed into the unsafe set.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-obstacle-keepout-violation"]')
      .click();
    await expect(
      page.getByRole("heading", { name: /drone obstacle keepout violation/i }),
    ).toBeVisible();
    await page.waitForTimeout(400);
    const time = page.locator(".verif-violation-legend .verif-violation-legend__time");
    await expect(time).toHaveCount(1);
    await expect(time).toContainText(/entered at t = 1\.54/);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-violation-time.png`),
    });
  });

  test(`Verification stage omits the violation time when none is exported at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject a measured-violated sample that maps onto the pendulum's (theta,
    // omega) axes but carries no worst.time — the marker draws, but no time
    // annotation appears.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.proofStatuses.push({
        id: "injected-violation-no-time",
        obligationId: "energy-barrier-excludes-near-bottom",
        status: "measured-violated",
        worst: { value: 1.5, point: [2.5, 0.3] },
        evaluation: {
          kind: "region-grid",
          sampleCount: 10,
          source: "injected",
          variables: ["theta", "omega"],
          stateAxes: ["theta", "omega"],
          variableToStateAxis: { theta: "theta", omega: "omega" },
        },
      });
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The violation marker is drawn, but with no exported time there is no time
    // annotation.
    await expect(page.locator("#verificationCanvas")).toHaveAttribute("data-violation-markers", "1");
    await expect(page.locator(".verif-violation-legend")).toBeVisible();
    await expect(page.locator(".verif-violation-legend__time")).toHaveCount(0);
  });

  test(`Verification catalog shows counts and active selection at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    const items = page.locator("#verificationCatalog .catalog-item");
    await expect(items).toHaveCount(12);

    // Every item carries its obligation/candidate counts from the index summary.
    for (let index = 0; index < 3; index += 1) {
      await expect(
        items.nth(index).locator('.catalog-item__count[data-count="obligations"]'),
      ).toHaveText(/\d+ obligations/);
      await expect(
        items.nth(index).locator('.catalog-item__count[data-count="candidates"]'),
      ).toHaveText(/\d+ candidates/);
    }

    // The first problem is active by default; selecting another moves the marker
    // and clears it from the previous item.
    await expect(items.nth(0)).toHaveClass(/catalog-item--active/);
    await expect(items.nth(1)).not.toHaveClass(/catalog-item--active/);

    await items.nth(1).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(items.nth(1)).toHaveClass(/catalog-item--active/);
    await expect(items.nth(0)).not.toHaveClass(/catalog-item--active/);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification-catalog.png`) });
  });

  test(`Verification catalog is grounded in the package discovery index at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    const items = page.locator("#verificationCatalog .catalog-item");
    await expect(items).toHaveCount(12);

    // Grounded in the discovery index, each entry now lists the full
    // region/obligation/candidate counts and the package status.
    const first = items.nth(0);
    await expect(first.locator('.catalog-item__count[data-count="regions"]')).toHaveText(
      /\d+ regions/,
    );
    await expect(first.locator('.catalog-item__count[data-count="obligations"]')).toHaveText(
      /\d+ obligations/,
    );
    await expect(first.locator('.catalog-item__count[data-count="candidates"]')).toHaveText(
      /\d+ candidates/,
    );
    await expect(first.locator(".catalog-item__status")).toHaveText("candidate");
    // Every entry carries the status chip and a region count.
    await expect(page.locator("#verificationCatalog .catalog-item__status")).toHaveCount(12);
    await expect(
      page.locator('#verificationCatalog .catalog-item__count[data-count="regions"]'),
    ).toHaveCount(12);

    // Selecting an entry still opens its problem.
    await items.nth(2).click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-catalog-grounded.png`),
    });
  });

  test(`Verification catalog degrades without the discovery index at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // No discovery index (older export): the catalog still lists every problem,
    // grounded in the per-example viewer index, and selection still works.
    await page.route("**/data/verification/packages/packages.index.json", (route) =>
      route.fulfill({ status: 404, body: "" }),
    );

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    const items = page.locator("#verificationCatalog .catalog-item");
    await expect(items).toHaveCount(12);
    // Counts still render from the viewer summary; no regime badge survives.
    await expect(
      items.nth(0).locator('.catalog-item__count[data-count="obligations"]'),
    ).toHaveText(/\d+ obligations/);
    await expect(page.locator("#verificationCatalog .catalog-item__regime")).toHaveCount(0);
    await items.nth(2).click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();
  });

  test(`Verification stage legends measured violations at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");

    // No-violation path: the default problem holds on every sample, so the stage
    // draws no markers and shows no legend.
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(page.locator(".verif-violation-legend")).toBeHidden();

    // Violation path: inject a mappable measured-violated sample referencing a
    // real obligation. The legend appears and names that obligation against its
    // numbered marker tag.
    const violation = {
      id: "injected-violation-legend",
      obligationId: "energy-barrier-excludes-near-bottom",
      status: "measured-violated",
      worst: { value: 1.5, point: [2.5, 0.3] },
      evaluation: {
        kind: "region-grid",
        sampleCount: 10,
        source: "injected",
        variables: ["theta", "omega"],
        stateAxes: ["theta", "omega"],
        variableToStateAxis: { theta: "theta", omega: "omega" },
      },
    };
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.proofStatuses.push(violation);
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    const legend = page.locator(".verif-violation-legend");
    await expect(legend).toBeVisible();
    await expect(legend.locator(".verif-violation-legend__entry")).toHaveCount(1);
    // The name (colon-delimited) rather than the obligation id (hyphenated)
    // confirms the legend resolves the obligation, not just echoes the link.
    await expect(legend.locator(".verif-violation-legend__name")).toHaveText(
      "energy-barrier:excludes:near-bottom",
    );
    await expect(legend.locator(".verif-violation-legend__tag")).toHaveText("1");
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-violation-legend.png`),
    });
  });

  test(`Verification stage focuses a violation from its legend at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject two mappable measured-violated samples so the legend offers more
    // than one entry to focus between, and the dimming of the unfocused marker
    // is meaningful.
    const violation = (id: string, point: [number, number]) => ({
      id,
      obligationId: "energy-barrier-excludes-near-bottom",
      status: "measured-violated",
      worst: { value: 1.5, point },
      evaluation: {
        kind: "region-grid",
        sampleCount: 10,
        source: "injected",
        variables: ["theta", "omega"],
        stateAxes: ["theta", "omega"],
        variableToStateAxis: { theta: "theta", omega: "omega" },
      },
    });
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.proofStatuses.push(
        violation("injected-violation-a", [2.5, 0.3]),
        violation("injected-violation-b", [-2.4, -0.4]),
      );
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    const canvas = page.locator("#verificationCanvas");
    const entries = page.locator(".verif-violation-legend__entry");
    await expect(entries).toHaveCount(2);
    // Nothing is focused until a legend entry is activated.
    await expect(canvas).toHaveAttribute("data-focused-violation", "");
    await expect(entries.nth(0)).toHaveAttribute("aria-pressed", "false");

    // Activating an entry emphasizes only its marker: the canvas records the
    // focused index and exactly that entry reads as pressed.
    await entries.nth(1).click();
    await expect(canvas).toHaveAttribute("data-focused-violation", "2");
    await expect(entries.nth(1)).toHaveAttribute("aria-pressed", "true");
    await expect(entries.nth(0)).toHaveAttribute("aria-pressed", "false");
    await expect(entries.nth(1)).toHaveClass(/verif-violation-legend__entry--focused/);
    await page.waitForTimeout(200);
    await expectCanvasNonBlank(page, "#verificationCanvas");
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-violation-focus.png`),
    });

    // Re-activating the focused entry toggles the focus back off.
    await entries.nth(1).click();
    await expect(canvas).toHaveAttribute("data-focused-violation", "");
    await expect(entries.nth(1)).toHaveAttribute("aria-pressed", "false");

    // Switching problems updates the marker set, which must drop any focus so a
    // stale index can't emphasize a marker that no longer exists.
    await entries.nth(0).click();
    await expect(canvas).toHaveAttribute("data-focused-violation", "1");
    await page.locator("#verificationCatalog .catalog-item").nth(1).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(canvas).toHaveAttribute("data-focused-violation", "");
  });

  test(`Verification stage marks measured closest-approach for holding obligations at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Select the drone (third catalog entry): all four obligations hold within
    // their stated assumption regions, so the stage marks each one's closest
    // approach and draws no violation marker.
    await page.locator("#verificationCatalog .catalog-item").nth(2).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();
    await page.waitForTimeout(400);

    const canvas = page.locator("#verificationCanvas");
    // A closest-approach marker per holding obligation whose worst point maps onto
    // the (q1, v1) axes; the violation path is unchanged (no breach on this run).
    await expect(canvas).toHaveAttribute("data-holds-markers", /^[1-9][0-9]*$/);
    await expect(canvas).toHaveAttribute("data-violation-markers", "0");
    await expectCanvasNonBlank(page, "#verificationCanvas");

    // The closest-approach legend names each holding obligation and shows its
    // signed measured margin (BE-036) — distinct from the measured-violations
    // legend, which stays hidden because nothing was breached.
    const holdsLegend = page.locator(".verif-holds-legend");
    await expect(holdsLegend).toBeVisible();
    await expect(holdsLegend.locator(".verif-holds-legend__title")).toHaveText(
      "measured closest approach",
    );
    const entries = holdsLegend.locator(".verif-holds-legend__entry");
    expect(await entries.count()).toBeGreaterThan(0);
    // The name resolves the obligation (colon-delimited), and the chip carries an
    // explicitly signed margin (measured slack to the boundary).
    await expect(holdsLegend.locator(".verif-holds-legend__name").first()).toContainText(":");
    await expect(holdsLegend.locator(".verif-holds-legend__value").first()).toHaveText(/[+-]/);
    await expect(page.locator(".verif-violation-legend")).toBeHidden();
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification-holds.png`) });
  });

  test(`Verification stage shows worst measured values in the legend at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject two mappable measured-violated samples: one carrying a worst value,
    // one whose worst point exists but with no exported value. Both map onto the
    // stage's (theta, omega) axes so both draw markers and legend entries.
    const evaluation = {
      kind: "region-grid",
      sampleCount: 10,
      source: "injected",
      variables: ["theta", "omega"],
      stateAxes: ["theta", "omega"],
      variableToStateAxis: { theta: "theta", omega: "omega" },
    };
    const withValue = {
      id: "injected-violation-valued",
      obligationId: "energy-barrier-excludes-near-bottom",
      status: "measured-violated",
      worst: { value: 1.5, point: [2.5, 0.3] },
      evaluation,
    };
    const withoutValue = {
      id: "injected-violation-unvalued",
      obligationId: "energy-barrier-excludes-near-bottom",
      status: "measured-violated",
      worst: { point: [-2.4, -0.4] },
      evaluation,
    };
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.proofStatuses.push(withValue, withoutValue);
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    const entries = page.locator(".verif-violation-legend__entry");
    await expect(entries).toHaveCount(2);

    // The valued violation shows its worst value, formatted deterministically.
    await expect(entries.nth(0).locator(".verif-violation-legend__value")).toHaveText("1.5");
    // The value-less violation omits the chip rather than rendering broken chrome.
    await expect(entries.nth(1).locator(".verif-violation-legend__value")).toHaveCount(0);

    // The focus interaction still works alongside the value chip.
    const canvas = page.locator("#verificationCanvas");
    await entries.nth(0).click();
    await expect(canvas).toHaveAttribute("data-focused-violation", "1");
    await page.waitForTimeout(150);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-violation-value.png`),
    });
  });

  test(`Verification candidate obligation link jumps to its obligation card at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // A candidate's obligation links are interactive; activating one scrolls to
    // and emphasizes the matching obligation card further down the doc.
    await openVerificationDetails(page);
    const jump = page.locator("#verifCandidates button.verif-link--jump").first();
    const obligationId = (await jump.textContent())?.trim() ?? "";
    expect(obligationId).not.toEqual("");
    await jump.click();

    const card = page.locator(`#verif-obligation-${obligationId}`);
    await expect(card).toHaveClass(/verif-card--targeted/);
    await expect(card).toBeInViewport();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-obligation-jump.png`),
    });
  });

  test(`Verification candidate obligation link stays inert for an unknown obligation at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject an obligation id the problem does not define; its link must stay an
    // inert code label, not a jump button pointing at a missing card.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.candidates[0].obligationIds.push("ghost-obligation");
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(
      page.locator("#verifCandidates code.verif-link", { hasText: "ghost-obligation" }),
    ).toHaveCount(1);
    await expect(
      page.locator("#verifCandidates button.verif-link--jump", { hasText: "ghost-obligation" }),
    ).toHaveCount(0);
    // The problem's real obligation links remain interactive jump buttons.
    await expect(page.locator("#verifCandidates button.verif-link--jump")).toHaveCount(3);
  });

  test(`Verification measured-status card jumps to its obligation card at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Each measured-status card names the obligation it sampled; activating that
    // name scrolls to and emphasizes the matching obligation card.
    await openVerificationDetails(page);
    const statusName = page.locator("button.verif-card__name--jump").first();
    await statusName.click();

    const targeted = page.locator("#verifObligations .verif-card--targeted");
    await expect(targeted).toHaveCount(1);
    await expect(targeted).toBeInViewport();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-status-jump.png`),
    });
  });

  test(`Verification measured-status card stays inert for an unknown obligation at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject a measured status referencing an obligation the problem does not
    // define; its name must stay an inert heading, not a jump to a missing card.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.proofStatuses.push({
        id: "injected-status-ghost",
        obligationId: "ghost-obligation",
        status: "measured-holds",
        evaluation: { kind: "region-grid", sampleCount: 5, source: "injected" },
      });
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(
      page.locator("strong.verif-card__name", { hasText: "ghost-obligation" }),
    ).toHaveCount(1);
    await expect(
      page.locator("button.verif-card__name--jump", { hasText: "ghost-obligation" }),
    ).toHaveCount(0);
    // The problem's real measured-status names remain interactive jumps.
    await expect(page.locator("button.verif-card__name--jump")).toHaveCount(3);
  });

  test(`Verification obligations without assumptions show no assumption affordance at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // An obligation with no assumptions must expose no "assumes:" affordance — and
    // no broken chrome. The exported problems all carry assumptions now (BE-034),
    // so clear them on the payload to exercise the empty branch deterministically.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      for (const obligation of json.obligations) {
        obligation.assumptionIds = [];
      }
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await openVerificationDetails(page);
    await expect(
      page.locator("#verifObligations .verif-card__links-label", { hasText: "assumes:" }),
    ).toHaveCount(0);
  });

  test(`Verification obligation assumption link jumps to its assumption card at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject an assumption plus an obligation that depends on it (and on an
    // unknown assumption id), since the exported problems carry none.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.assumptions = [{ id: "small-angle", description: "theta stays near upright" }];
      json.obligations[0].assumptionIds = ["small-angle", "ghost-assumption"];
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The known assumption is an interactive jump; the unknown id stays inert.
    await openVerificationDetails(page);
    const known = page.locator("#verifObligations button.verif-link--jump", {
      hasText: "small-angle",
    });
    await expect(known).toHaveCount(1);
    await expect(
      page.locator("#verifObligations code.verif-link", { hasText: "ghost-assumption" }),
    ).toHaveCount(1);
    await expect(
      page.locator("#verifObligations button.verif-link--jump", { hasText: "ghost-assumption" }),
    ).toHaveCount(0);

    // Activating the known assumption scrolls to and emphasizes its card.
    await known.click();
    const card = page.locator("#verif-assumption-small-angle");
    await expect(card).toHaveClass(/verif-card--targeted/);
    await expect(card).toBeInViewport();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-assumption-jump.png`),
    });
  });

  test(`Verification obligation ledger summarizes outcomes and navigates at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // One ledger row per obligation. The pendulum's obligations all hold on
    // samples but still await external discharge — measured, never proved.
    const rows = page.locator("#verifLedger .verif-ledger__row");
    await expect(rows).toHaveCount(3);
    await expect(
      page.locator("#verifLedger .verif-status", { hasText: "holds on samples" }),
    ).toHaveCount(3);
    await expect(
      page.locator("#verifLedger .verif-badge", { hasText: "external-required" }),
    ).toHaveCount(3);

    // A ledger row navigates to the obligation's full card.
    await page.locator("#verifLedger .verif-ledger__name").first().click();
    const targeted = page.locator("#verifObligations .verif-card--targeted");
    await expect(targeted).toHaveCount(1);
    await expect(targeted).toBeInViewport();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-ledger.png`),
    });
  });

  test(`Verification renders the flagship drone with margins and assumption regions at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // The drone is the first problem with multiple barrier candidates and an
    // assumption-restricted measured ledger; its generic rendering must stay
    // honest and free of console errors.
    const consoleErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") {
        consoleErrors.push(message.text());
      }
    });
    page.on("pageerror", (error) => consoleErrors.push(error.message));

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Select the drone (third catalog entry) and confirm it loads.
    await page.locator("#verificationCatalog .catalog-item").nth(2).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();

    // The (q1, v1) phase plane animates the controlled rollout on its region
    // geometry: the stage canvas must paint, not stay blank.
    await page.waitForTimeout(600);
    await expectCanvasNonBlank(page, "#verificationCanvas");

    // Three barrier candidates -> three certificate lanes (geofence, velocity,
    // inner-set). The inner-set value coasts positive as the rollout leaves S_in;
    // the lane renders that measured signal honestly (the verdict lives in the
    // ledger, not the lane).
    const certificateLanes = page.locator("#verificationCertificateLanes .diagnostic__certificate");
    await expect(certificateLanes).toHaveCount(3);
    await expectCanvasNonBlank(page, "#verificationCertificateLanes .diagnostic__certificate >> nth=0");

    // Four obligations, each measured-holding within its stated region, every row
    // surfacing a signed margin (BE-036). Measured evidence — still external.
    const rows = page.locator("#verifLedger .verif-ledger__row");
    await expect(rows).toHaveCount(4);
    await expect(
      page.locator("#verifLedger .verif-status", { hasText: "holds on samples" }),
    ).toHaveCount(4);
    await expect(page.locator("#verifLedger .verif-ledger__margin")).toHaveCount(4);
    await expect(page.locator("#verifLedger .verif-ledger__margin").first()).toContainText(
      /margin [+-]/,
    );

    // The obligations sampled under spec-G assumptions name the assumption region
    // their evidence was restricted to (forward-invariance, velocity, inner-set);
    // initial-containment carries no domain assumption, so it shows no region.
    await expect(
      page.locator("#verifLedger .verif-ledger__within-label", { hasText: "within" }),
    ).toHaveCount(3);
    await expect(
      page.locator("#verifLedger .verif-ledger__within-ids", {
        hasText: "speed-within-half-guard-reach",
      }),
    ).toBeVisible();

    // The measured-status cards (in the IR detail) carry the same signed margin
    // and the verbatim sampling note stating the assumption region.
    await openVerificationDetails(page);
    await expect(
      page.locator("#verificationDetails .verif-card__meta", { hasText: /margin: [+-]/ }).first(),
    ).toBeVisible();
    await expect(
      page.locator("#verificationDetails .verif-card__desc", {
        hasText: /Sampled only where the stated assumption region holds/i,
      }).first(),
    ).toBeVisible();

    expect(consoleErrors).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification-drone.png`) });
  });

  test(`Verification obligation ledger marks disturbance-robust obligations at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Nominal Tier-1 geofence package: no robust badge anywhere.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-geofence-axis"]')
      .click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();
    await expect(page.locator("#verifLedger .verif-badge--robust")).toHaveCount(0);

    // Tier-3 disturbance-robust geofence package: its robust obligations carry the
    // honest "robust ∀ d ∈ W" badge and surface the cited wind box, while still
    // reading external-required (never discharged).
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-disturbed-geofence-axis"]')
      .click();
    await expect(
      page.getByRole("heading", { name: /drone disturbed geofence axis/i }),
    ).toBeVisible();
    const robustBadges = page.locator("#verifLedger .verif-badge--robust");
    expect(await robustBadges.count()).toBeGreaterThan(0);
    await expect(robustBadges.first()).toContainText("robust");
    // The cited disturbance box appears alongside the robust obligation rows.
    await expect(page.locator("#verifLedger .verif-ledger__disturbance").first()).toBeVisible();
    // The robustness changes nothing about the obligation's rigor: still external.
    await expect(
      page.locator("#verifLedger .verif-badge--external-required").first(),
    ).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-robust-ledger.png`),
    });
  });

  test(`Verification stage annotates the disturbance set on Tier-3 packages at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    const geofenceAxis = page.locator(
      '#verificationCatalog .catalog-item[data-problem-id="drone-geofence-axis"]',
    );
    const disturbedGeofenceAxis = page.locator(
      '#verificationCatalog .catalog-item[data-problem-id="drone-disturbed-geofence-axis"]',
    );
    const annotation = page.locator(".verif-disturbance-annotation");

    // Nominal Tier-1 geofence package: no disturbance annotation.
    await geofenceAxis.click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();
    await page.waitForTimeout(300);
    await expect(annotation).toBeHidden();

    // Tier-3 disturbance-robust geofence package: the wind box `W` it is
    // quantified over is annotated on the stage, honestly labeled assumed (not
    // discharged), while the rollout keeps painting.
    await disturbedGeofenceAxis.click();
    await expect(
      page.getByRole("heading", { name: /drone disturbed geofence axis/i }),
    ).toBeVisible();
    await page.waitForTimeout(600);
    await expect(annotation).toBeVisible();
    await expect(annotation).toContainText(/disturbance set/i);
    await expect(annotation).toContainText(/not discharged/i);
    await expect(annotation.locator(".katex").first()).toBeVisible();
    await expectCanvasNonBlank(page, "#verificationCanvas");

    // Switching back to a nominal package hides the annotation again.
    await geofenceAxis.click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();
    await page.waitForTimeout(300);
    await expect(annotation).toBeHidden();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-disturbance-set.png`),
    });
  });

  test(`Verification obligation ledger reads unsampled obligations as not sampled at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject an obligation with no measured status; its ledger row must read as
    // not sampled rather than implying any measured outcome.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.obligations.push({ id: "extra-untested" });
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(page.locator("#verifLedger .verif-ledger__row")).toHaveCount(4);
    const row = page.locator("#verifLedger .verif-ledger__row", {
      has: page.locator(".verif-ledger__name", { hasText: "extra-untested" }),
    });
    await expect(row.locator(".verif-status")).toHaveText("not sampled");
  });

  test(`Verification rigor ladder marks the problem at the measured level at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // All four rigor levels are listed.
    const steps = page.locator("#verifRigorLadder .verif-ladder__step");
    await expect(steps).toHaveCount(4);

    // Exactly one is marked current, and it is level 1 (measured evidence).
    const current = page.locator("#verifRigorLadder .verif-ladder__step--current");
    await expect(current).toHaveCount(1);
    await expect(current).toHaveAttribute("data-level", "1");
    await expect(current).toContainText("Measured");

    // The current marker must never imply proof or certification.
    const currentText = ((await current.textContent()) ?? "").toLowerCase();
    expect(currentText).not.toContain("proved");
    expect(currentText).not.toContain("certified");
    // A problem with no certified-numeric enclosure carries no certified badge.
    await expect(page.locator("#verifLedger .verif-badge--certified")).toHaveCount(0);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-rigor-ladder.png`),
    });
  });

  test(`Verification rigor ladder reaches certified-numeric (level 2) at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The geofence package: the trusted evaluator certified all four obligations
    // at level 2 (sound enclosures under stated assumptions).
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-geofence-axis"]')
      .click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();

    // Each obligation carries a certified-numeric badge in the ledger, distinct
    // from its external-required rigor badge — still not discharged.
    const certified = page.locator("#verifLedger .verif-badge--certified");
    await expect(certified).toHaveCount(4);
    await expect(certified.first()).toHaveText("certified-numeric");
    await expect(
      page.locator("#verifLedger .verif-badge--external-required").first(),
    ).toBeVisible();

    // The masthead claim and certification scale reflect the highest established
    // rung (2), honestly labeled sound-under-assumptions, not discharged.
    const claim = page.locator("#verificationMasthead .verif-claim__text");
    await expect(claim).toContainText(/certified-numeric/i);
    await expect(claim).toContainText(/not discharged/i);
    await expect(
      page.locator('#verificationMasthead .verif-scale__rung[data-level="2"]'),
    ).toHaveClass(/verif-scale__rung--current/);
    await expect(page.locator("#verificationMasthead .verif-scale__caption")).toContainText(
      /certified-numeric/i,
    );

    // The rigor ladder marks level 2 as the current rung.
    const current = page.locator("#verifRigorLadder .verif-ladder__step--current");
    await expect(current).toHaveCount(1);
    await expect(current).toHaveAttribute("data-level", "2");

    // The obligation card surfaces the certified enclosure box it is sound over —
    // concrete and honest, still not a proof.
    await openVerificationDetails(page);
    const enclosure = page.locator("#verifObligations .verif-enclosure").first();
    await expect(enclosure).toBeVisible();
    await expect(enclosure).toContainText(/sound over box/i);
    await expect(enclosure.locator(".verif-enclosure__label")).toHaveText("certified-numeric");
    // The honest disclaimer rides along verbatim — a sound enclosure, not a proof.
    await expect(enclosure).toContainText(/sound enclosure/i);
    await expect(enclosure).toContainText(/not.{0,4}proof/i);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-certified-level2.png`),
    });
  });

  test(`Verification obligation evidence emphasizes its certificate lanes at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // No lane emphasis until an obligation's evidence is selected.
    await expect(page.locator("#verificationCertificateLanes .diagnostic--emphasized")).toHaveCount(
      0,
    );

    // The non-increase obligation bears on exactly the flow-derivative lane;
    // selecting its evidence emphasizes only that lane and dims the rest.
    await openVerificationDetails(page);
    const toggle = page.locator(
      '#verif-obligation-energy-barrier-non-increase .verif-evidence-toggle',
    );
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-pressed", "true");
    const emphasized = page.locator("#verificationCertificateLanes .diagnostic--emphasized");
    await expect(emphasized).toHaveCount(1);
    await expect(emphasized).toHaveAttribute("data-obligations", /energy-barrier-non-increase/);
    await expect(
      page.locator("#verificationCertificateLanes .diagnostic--dimmed"),
    ).toHaveCount(1);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-evidence-emphasis.png`),
    });

    // Re-selecting clears the emphasis.
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-pressed", "false");
    await expect(page.locator("#verificationCertificateLanes .diagnostic--emphasized")).toHaveCount(
      0,
    );
    await expect(page.locator("#verificationCertificateLanes .diagnostic--dimmed")).toHaveCount(0);
  });

  test(`Verification certificate lane shows the selected obligation's worst margin at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The drone (3rd entry) has a geofence barrier lane bearing on the
    // initial-containment obligation, whose ledger margin is non-trivial.
    await page.locator("#verificationCatalog .catalog-item").nth(2).click();
    await expect(page.getByRole("heading", { name: /drone geofence axis/i })).toBeVisible();

    // The ledger headlines that obligation's signed worst margin (BE-036).
    const ledgerMargin = page
      .locator('#verifLedger .verif-ledger__row[data-obligation="geofence-barrier-initial-containment"] .verif-ledger__margin');
    const ledgerText = (await ledgerMargin.textContent())?.replace(/^margin\s+/, "").trim() ?? "";
    expect(ledgerText).toMatch(/[+-]\d/);

    // No margin readout on the lanes until that obligation's evidence is selected.
    await expect(page.locator("#verificationCertificateLanes .diagnostic__margin:visible")).toHaveCount(
      0,
    );

    // Selecting the obligation's evidence reveals its worst margin on the lane
    // that bears on it, aligned to the rollout — and it matches the ledger value.
    await openVerificationDetails(page);
    const toggle = page.locator(
      "#verif-obligation-geofence-barrier-initial-containment .verif-evidence-toggle",
    );
    await toggle.click();
    const readout = page.locator(
      "#verificationCertificateLanes .diagnostic--emphasized .diagnostic__margin",
    );
    await expect(readout).toBeVisible();
    await expect(readout.locator(".diagnostic__margin-value")).toHaveText(ledgerText);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-margin-readout.png`),
    });

    // Re-selecting clears the readout along with the emphasis.
    await toggle.click();
    await expect(page.locator("#verificationCertificateLanes .diagnostic__margin:visible")).toHaveCount(
      0,
    );
  });

  test(`Verification evidence selection clears when the problem changes at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await openVerificationDetails(page);
    await page
      .locator("#verif-obligation-energy-barrier-non-increase .verif-evidence-toggle")
      .click();
    await expect(page.locator("#verificationCertificateLanes .diagnostic--emphasized")).toHaveCount(
      1,
    );

    // Switching problems rebuilds the lanes, dropping any prior emphasis.
    await page.locator("#verificationCatalog .catalog-item").nth(1).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(page.locator("#verificationCertificateLanes .diagnostic--emphasized")).toHaveCount(
      0,
    );
  });

  test(`Verification obligation without a certificate lane has no evidence affordance at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject an obligation that no certificate series references; it must expose
    // no evidence toggle while the lane-backed obligations still do.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.obligations.push({ id: "extra-untested" });
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(
      page.locator("#verif-obligation-extra-untested .verif-evidence-toggle"),
    ).toHaveCount(0);
    // The three lane-backed obligations still expose the affordance.
    await expect(page.locator("#verifObligations .verif-evidence-toggle")).toHaveCount(3);
  });

  test(`Verification problem downloads its backend-agnostic IR artifact at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Exports live in the collapsed appendix; open it first.
    await openVerificationDetails(page);

    // The download targets the IR artifact (.ir.json), not the viewer payload.
    const download = page.locator(".verif-download-ir");
    await expect(download).toBeVisible();
    await expect(download).toHaveAttribute("href", /upright-pendulum-safety\.ir\.json$/);

    const [downloaded] = await Promise.all([
      page.waitForEvent("download"),
      download.click(),
    ]);
    expect(downloaded.suggestedFilename()).toBe(
      "upright-pendulum-safety.verification-problem.json",
    );

    // The downloaded artifact is the backend-agnostic IR: the problem structure
    // without the viewer-only trajectory.
    const path = await downloaded.path();
    const ir = JSON.parse(readFileSync(path, "utf-8"));
    expect(ir).not.toHaveProperty("trajectory");
    expect(ir).toHaveProperty("obligations");
    expect(ir.id).toBe("upright-pendulum-safety");
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-download-ir.png`),
    });
  });

  test(`Verification problem shows no download when no IR is published at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Strip irPath from the index (older export with no published IR); the
    // download affordance must be absent rather than point nowhere.
    await page.route("**/data/verification/index.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.problems.forEach((problem: { irPath?: string }) => delete problem.irPath);
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(page.locator(".verif-download-ir")).toHaveCount(0);
  });

  test(`Verification problem exports a self-contained package bundle at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Exports live in the collapsed appendix; open it first.
    await openVerificationDetails(page);

    // The package export is visibly distinct from the IR download and lists the
    // components the bundle indexes, claiming no discharge.
    await expect(page.locator(".verif-download-ir")).toBeVisible();
    const packageDownload = page.locator(".verif-download-package");
    await expect(packageDownload).toBeVisible();
    await expect(page.locator(".verif-package__inspect")).toContainText("problem-ir");
    await expect(page.locator(".verif-package__inspect")).toContainText("viewer-trajectory");
    await expect(page.locator(".verif-package__note")).toContainText(/discharges nothing/i);

    // The read-only inventory (FE-022) lists the manifest's model/status/counts
    // and each indexed component, inspectable without downloading the bundle.
    const inventory = page.locator("#verifPackage");
    await expect(inventory).toBeVisible();
    await expect(inventory.locator(".verif-package-meta")).toContainText("candidate");
    const components = inventory.locator(".verif-package-component");
    expect(await components.count()).toBeGreaterThan(0);
    await expect(inventory.locator(".verif-package-component__kind").first()).toBeVisible();
    await expect(inventory.locator(".verif-package-component__file").first()).toBeVisible();

    // Downloading assembles one file whose embedded manifest re-reads to the same
    // components the backend wrote, each component's payload embedded by kind.
    const [downloaded] = await Promise.all([
      page.waitForEvent("download"),
      packageDownload.click(),
    ]);
    expect(downloaded.suggestedFilename()).toBe(
      "upright-pendulum-safety.verification-package.json",
    );
    const bundle = JSON.parse(readFileSync(await downloaded.path(), "utf-8"));
    expect(bundle.schemaVersion).toBe("verification-package/v1");
    const kinds = bundle.manifest.components.map((component: { kind: string }) => component.kind);
    expect(kinds).toContain("problem-ir");
    expect(kinds).toContain("viewer-trajectory");
    // Single-file JSON components are inlined; a directory component (the
    // reachability handoff) stays referenced by the manifest but is not embedded.
    const embedded = Object.keys(bundle.components);
    expect(embedded).toContain("problem-ir");
    expect(embedded).toContain("viewer-trajectory");
    expect(kinds).toEqual(expect.arrayContaining(embedded));
    const directoryComponents = bundle.manifest.components.filter(
      (component: { path: string }) => !component.path.endsWith(".json"),
    );
    for (const component of directoryComponents) {
      expect(embedded).not.toContain(component.kind);
    }
    // The embedded IR is the backend-agnostic problem (no viewer trajectory); the
    // viewer-trajectory component carries the animated series.
    expect(bundle.components["problem-ir"].id).toBe("upright-pendulum-safety");
    expect(bundle.components["problem-ir"]).not.toHaveProperty("trajectory");
    expect(bundle.components["viewer-trajectory"]).toHaveProperty("series");
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-download-package.png`),
    });
  });

  test(`Verification problem shows no package export when none is published at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Strip packagePath from the index (older export with no published bundle);
    // the package affordance must be absent while the IR download remains.
    await page.route("**/data/verification/index.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.problems.forEach((problem: { packagePath?: string }) => delete problem.packagePath);
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // Exports live in the collapsed appendix; open it first.
    await openVerificationDetails(page);

    await expect(page.locator(".verif-download-package")).toHaveCount(0);
    await expect(page.locator(".verif-download-ir")).toBeVisible();

    // With no published package the inventory section is absent entirely.
    await expect(page.locator("#verifPackage")).toHaveCount(0);
  });

  test(`Verification IR details list non-discharging adapter stubs at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The default problem publishes adapter stubs; they live in the appendix.
    await openVerificationDetails(page);
    const stubsSection = page.locator("#verifAdapterStubs");
    await expect(stubsSection).toBeVisible();
    // Each stub names an external backend category and is marked non-discharging.
    await expect(stubsSection.locator(".verif-adapter-stub__category").first()).toBeVisible();
    const discharges = stubsSection.locator(".verif-adapter-stub__discharges");
    expect(await discharges.count()).toBeGreaterThan(0);
    await expect(discharges.first()).toHaveText("discharges: false");
    // The obligation shape each category would have to handle is surfaced.
    await expect(stubsSection.locator(".verif-adapter-stub__shape").first()).toContainText(
      /target/,
    );
    // The honesty note (no stub attempts/records/claims discharge) rides along.
    await expect(stubsSection).toContainText(/discharge/i);

    // The backend categories overview (FE-034) lists each category once with its
    // summary and consumes/produces, every category non-discharging.
    const categories = stubsSection.locator(".verif-adapter-category");
    expect(await categories.count()).toBeGreaterThan(0);
    await expect(
      stubsSection.locator(".verif-adapter-category__name", { hasText: "reachability" }),
    ).toBeVisible();
    await expect(
      stubsSection.locator(".verif-adapter-category__io-label", { hasText: /consumes/i }).first(),
    ).toBeVisible();
    await expect(
      stubsSection.locator(".verif-adapter-category__io-label", { hasText: /produces/i }).first(),
    ).toBeVisible();
    await expect(categories.first().locator(".verif-adapter-category__discharges")).toHaveText(
      "discharges: false",
    );
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-adapter-stubs.png`),
    });
  });

  test(`Verification IR details omit adapter stubs when none are published at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Strip the adapter-stubs component from the manifest (older export with no
    // published stubs); the manifest still indexes its other components.
    await page.route("**/data/verification/packages/**/package.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.components = (json.components ?? []).filter(
        (component: { kind?: string }) => component.kind !== "adapter-stubs",
      );
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await openVerificationDetails(page);

    // The manifest is still published (inventory shows), but with no stubs
    // component the adapter-stub section is absent entirely.
    await expect(page.locator("#verifPackage")).toBeVisible();
    await expect(page.locator("#verifAdapterStubs")).toHaveCount(0);
  });

  test(`Verification certificate lane emphasizes the obligations it bears on at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // No obligation is referenced until a lane is selected.
    await expect(page.locator("#verificationDetails .verif-card--referenced")).toHaveCount(0);

    // The flow-derivative lane bears on the non-increase obligation; selecting it
    // emphasizes exactly that obligation card and ledger row.
    const lane = page.locator(
      '#verificationCertificateLanes [data-obligations~="energy-barrier-non-increase"]',
    );
    await lane.click();
    await expect(lane).toHaveAttribute("aria-pressed", "true");
    await expect(
      page.locator("#verif-obligation-energy-barrier-non-increase"),
    ).toHaveClass(/verif-card--referenced/);
    await expect(page.locator("#verificationDetails .verif-card--referenced")).toHaveCount(1);
    await expect(
      page.locator("#verifLedger .verif-ledger__row--referenced"),
    ).toHaveCount(1);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-lane-to-obligation.png`),
    });

    // Re-selecting the lane clears the emphasis.
    await lane.click();
    await expect(lane).toHaveAttribute("aria-pressed", "false");
    await expect(page.locator("#verificationDetails .verif-card--referenced")).toHaveCount(0);
  });

  test(`Verification lane selection clears when the problem changes at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await page
      .locator('#verificationCertificateLanes [data-obligations~="energy-barrier-non-increase"]')
      .click();
    await expect(page.locator("#verificationDetails .verif-card--referenced")).toHaveCount(1);

    await page.locator("#verificationCatalog .catalog-item").nth(1).click();
    await page.waitForSelector("#verificationSummary .verif-summary");
    await expect(page.locator("#verificationDetails .verif-card--referenced")).toHaveCount(0);
  });

  test(`Verification certificate lane with no obligation stays inert at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // Inject a certificate series that references no obligation; its lane must
    // not be selectable while the obligation-backed lanes still are.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      const first = json.trajectory.certificateSeries[0];
      json.trajectory.certificateSeries.push({
        ...first,
        obligationIds: [],
        comparisonBaselines: [],
        label: "unlinked series",
      });
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    await expect(page.locator("#verificationCertificateLanes .diagnostic")).toHaveCount(3);
    // Only the two obligation-backed lanes are selectable.
    await expect(
      page.locator("#verificationCertificateLanes .diagnostic--selectable"),
    ).toHaveCount(2);
  });

  test(`Verification certificate lanes name barriers for an intersection safe set at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // A single-barrier keep-out package: lanes are unchanged — no barrier name
    // labels and no intersection note.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-obstacle-keepout"]')
      .click();
    await expect(page.getByRole("heading", { name: /drone obstacle keepout/i })).toBeVisible();
    await expect(page.locator("#verificationCertificateLanes .diagnostic__barrier")).toHaveCount(0);
    await expect(page.locator("#verificationCertificateLanes .diagnostic-intersection")).toHaveCount(
      0,
    );

    // The geofence∩obstacle package carries two candidate barriers whose
    // intersection is the safe set: each lane is named, and the intersection
    // semantics are stated once — both stay candidates.
    await page
      .locator('#verificationCatalog .catalog-item[data-problem-id="drone-geofence-obstacle"]')
      .click();
    await expect(page.getByRole("heading", { name: /drone geofence obstacle/i })).toBeVisible();
    const barriers = page.locator("#verificationCertificateLanes .diagnostic__barrier");
    await expect(barriers).toHaveCount(2);
    await expect(barriers.filter({ hasText: /geofence/i })).toHaveCount(1);
    await expect(barriers.filter({ hasText: /keepout|keep out/i })).toHaveCount(1);
    const note = page.locator("#verificationCertificateLanes .diagnostic-intersection");
    await expect(note).toBeVisible();
    await expect(note).toContainText(/intersection/i);
    await expect(note).toContainText(/candidate/i);
    await expect(note.locator(".katex")).toBeVisible();
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-intersection-barriers.png`),
    });
  });

  test(`Verification surfaces show honest empty states at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });

    // A problem with no measured certificate series and no proof statuses.
    await page.route("**/data/verification/upright-pendulum-safety.json", async (route) => {
      const response = await route.fetch();
      const json = await response.json();
      json.trajectory.certificateSeries = [];
      json.proofStatuses = [];
      await route.fulfill({ response, json });
    });

    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The absence is stated rather than left as empty panels.
    await expect(page.locator("#verificationCertificateLanes .diagnostic-empty")).toHaveText(
      /no measured certificate series/i,
    );
    await expect(page.locator("#verificationDetails .verif-empty-note")).toContainText(
      /no measured status sampled/i,
    );
    // No certificate lanes rendered.
    await expect(page.locator("#verificationCertificateLanes .diagnostic")).toHaveCount(0);
    await page.screenshot({
      path: testInfo.outputPath(`${viewport.name}-verification-empty-states.png`),
    });
  });

  test(`Verification populated case shows no empty-state notes at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The default problem has measured series and statuses, so no placeholders.
    await expect(page.locator("#verificationCertificateLanes .diagnostic-empty")).toHaveCount(0);
    await expect(page.locator("#verificationDetails .verif-empty-note")).toHaveCount(0);
    await expect(
      page.locator("#verificationCertificateLanes .diagnostic"),
    ).not.toHaveCount(0);
  });

  test(`Verification IR details are collapsed by default and open on jump at ${viewport.name}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationSummary .verif-summary");

    // The verbose IR lives in a collapsed details band by default.
    const details = page.locator(".verif-details");
    await expect(details).toHaveJSProperty("open", false);

    // Jumping from a summary safety-property row opens the details and brings its
    // obligation card into view.
    await page.locator("#verifLedger .verif-ledger__name").first().click();
    await expect(details).toHaveJSProperty("open", true);
    await expect(page.locator("#verifObligations .verif-card--targeted")).toBeInViewport();
  });
}
