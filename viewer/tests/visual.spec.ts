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
    // the diagnostics panel shows a conservation-drift lane on boot.
    await expect(page.locator("#diagnostics .diagnostic__residual").first()).toBeVisible();

    await page.getByRole("button", { name: "Hamiltonian Flow" }).click();
    await page.waitForSelector("#hamiltonianScene.stage__canvas--active");
    await page.waitForTimeout(800);

    await expectCanvasNonBlank(page, "#hamiltonianScene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-hamiltonian.png`) });

    await page.getByRole("button", { name: "Potential", exact: true }).click();
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

    await page.getByRole("button", { name: "Potential", exact: true }).click();
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

    await page.getByRole("button", { name: "Potential", exact: true }).click();
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

    await page.getByRole("button", { name: "Potential", exact: true }).click();
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

}
