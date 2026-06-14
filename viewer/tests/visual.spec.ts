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
  "charged-particle",
  "uniform-gravity",
  "ideal-spring",
  "kepler",
  "bead-on-hoop",
  "lorenz-attractor",
  "henon-heiles",
];

for (const viewport of [
  { name: "desktop", width: 1280, height: 820 },
  { name: "mobile", width: 390, height: 844 },
]) {
  test(`renders all example systems at ${viewport.name}`, async ({ page }, testInfo) => {
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

    await page.locator("#systemSelect").selectOption("charged-particle");
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
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-henon-heiles-potential.png`) });

    await page.getByRole("button", { name: /Poincar/ }).click();
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-henon-heiles-poincare.png`) });

    await page.locator("#systemSelect").selectOption("variable-speed-wavefront");
    await page.waitForSelector("#scene.stage__canvas--active");
    await page.waitForTimeout(500);
    await expectCanvasNonBlank(page, "#scene");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-variable-speed-wavefront.png`) });

    // The hard top-level domain menu swaps to the Verification workbench, which
    // renders the exported verification-problem IR read-only.
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationContent .verif-doc");
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
    await page.waitForSelector("#verificationContent .verif-doc");
    await expect(
      page.getByRole("heading", { name: /upright pendulum safety/i }),
    ).toBeVisible();

    // The measured proof-status surface renders sampled obligation outcomes,
    // honestly labeled (a clean sample is evidence, never a discharge).
    await expect(page.getByRole("heading", { name: /measured status/i })).toBeVisible();
    await expect(page.locator(".verif-status").first()).toBeVisible();

    // Switching back returns to the Systems workbench on the default pendulum.
    await page.getByRole("button", { name: "Systems" }).click();
    await page.waitForSelector("#systemsDomain.domain--active");
    await expect(page.locator("#systemTitle")).toHaveText("Simple Pendulum");
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
    await page.waitForSelector("#verificationContent .verif-doc");

    // The catalog lists every exported problem; the first is active by default.
    const catalogItems = page.locator("#verificationCatalog .catalog-item");
    await expect(catalogItems).toHaveCount(2);
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
    await expect(page.locator("#verificationContent .verif-empty")).toBeVisible();
    await expect(page.locator("#verificationContent .verif-empty__copy")).toContainText(
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
    await page.waitForSelector("#verificationContent .verif-doc");
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
    await page.waitForSelector("#verificationContent .verif-doc");
    await expect(page.locator("#verificationCanvas")).toHaveAttribute(
      "data-violation-markers",
      "1",
    );
    await page.waitForTimeout(400);
    await expectCanvasNonBlank(page, "#verificationCanvas");
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification-violation.png`) });
  });

  test(`Verification catalog shows counts and active selection at ${viewport.name}`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");
    await page.waitForSelector("#systemsDomain.domain--active");
    await page.getByRole("button", { name: "Verification" }).click();
    await page.waitForSelector("#verificationDomain.domain--active");
    await page.waitForSelector("#verificationContent .verif-doc");

    const items = page.locator("#verificationCatalog .catalog-item");
    await expect(items).toHaveCount(2);

    // Every item carries its obligation/candidate counts from the index summary.
    for (let index = 0; index < 2; index += 1) {
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
    await page.waitForSelector("#verificationContent .verif-doc");
    await expect(items.nth(1)).toHaveClass(/catalog-item--active/);
    await expect(items.nth(0)).not.toHaveClass(/catalog-item--active/);
    await page.screenshot({ path: testInfo.outputPath(`${viewport.name}-verification-catalog.png`) });
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
    await page.waitForSelector("#verificationContent .verif-doc");
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
    await page.waitForSelector("#verificationContent .verif-doc");

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
}
