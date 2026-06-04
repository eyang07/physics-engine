/**
 * The Structure panel: symbols, not numbers.
 *
 * Driven entirely by the manifest, it shows the principles (symbolic
 * Lagrangian / Hamiltonian / equations of motion), the invariants (each
 * conserved quantity drawn as a flat line — stillness is the proof), and the
 * parameters (unlabeled markers you read by feel). Per frame it advances the
 * invariant playheads and the loop-phase ring.
 */
import katex from "katex";

import { theme } from "./design/theme";
import { findSystem, loadManifest, type SystemManifest } from "./data/manifest";
import type { Trajectory } from "./data/trajectory";
import { clamp } from "./util";

type InvariantLane = {
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  series: number[];
};

const LOOP_CIRCUMFERENCE = 2 * Math.PI * 15;

function renderLatex(element: HTMLElement, latex: string): void {
  katex.render(latex, element, { throwOnError: false, displayMode: false });
}

export class StructurePanel {
  private lanes: InvariantLane[] = [];

  constructor(
    private readonly principles: HTMLElement,
    private readonly invariants: HTMLElement,
    private readonly parameters: HTMLElement,
    private readonly loopArc: SVGCircleElement,
  ) {}

  clear(): void {
    this.principles.replaceChildren();
    this.invariants.replaceChildren();
    this.parameters.replaceChildren();
    this.lanes = [];
  }

  async show(systemId: string, data: Trajectory): Promise<void> {
    try {
      const manifest = await loadManifest();
      const system = findSystem(manifest, systemId);
      if (!system) {
        this.clear();
        return;
      }
      this.renderPrinciples(system);
      this.renderInvariants(system, data);
      this.renderParameters(system);
    } catch (error) {
      console.warn("Structure panel unavailable:", error);
      this.clear();
    }
  }

  update(phase: number): void {
    this.lanes.forEach((lane) => drawInvariantLane(lane, phase));
    this.loopArc.style.strokeDashoffset = String(LOOP_CIRCUMFERENCE * (1 - clamp(phase, 0, 1)));
  }

  private renderPrinciples(system: SystemManifest): void {
    this.principles.replaceChildren();
    const derivation = system.derivation;

    this.principles.append(principleBlock("Lagrangian", [derivation.lagrangian.expression_latex]));
    this.principles.append(
      principleBlock(
        "Momenta",
        derivation.generalized_momenta.map((momentum) => momentum.equation_latex),
      ),
    );
    this.principles.append(
      principleBlock(
        "Euler-Lagrange",
        derivation.euler_lagrange.map((equation) => equation.equation_latex),
      ),
    );

    if (derivation.legendre_transform.regular && derivation.legendre_transform.velocity_solutions.length > 0) {
      this.principles.append(
        principleBlock(
          "Legendre",
          derivation.legendre_transform.velocity_solutions.map((solution) => solution.equation_latex),
        ),
      );
    }

    if (derivation.hamiltonian) {
      this.principles.append(principleBlock("Hamiltonian", [derivation.hamiltonian.expression_latex]));
      this.principles.append(
        principleBlock(
          "Hamilton Flow",
          derivation.hamiltonian.equations.map((equation) => equation.equation_latex),
        ),
      );
    }

    const generators = derivation.conserved_quantities
      .filter((quantity) => quantity.generator_latex)
      .map((quantity) => {
        const components = quantity.generator_latex ?? [];
        const tau = quantity.tau_latex ?? "0";
        return `${quantity.symbol_latex}: W=\\left(${components.join(",")}\\right),\\ \\tau=${tau}`;
      });
    if (generators.length > 0) {
      this.principles.append(principleBlock("Generators", generators));
    }

    const charges = derivation.conserved_quantities
      .filter((quantity) => quantity.charge_latex)
      .map((quantity) => `${quantity.symbol_latex}=${quantity.charge_latex}`);
    if (charges.length > 0) {
      this.principles.append(principleBlock("Noether", charges));
    }

    if (derivation.effective_potentials.length > 0) {
      this.principles.append(
        principleBlock(
          "Effective Potential",
          derivation.effective_potentials.map(
            (potential) => `${potential.latex}\\left(${potential.coordinate}\\right)=${potential.expression_latex}`,
          ),
        ),
      );
    }
  }

  private renderInvariants(system: SystemManifest, data: Trajectory): void {
    this.invariants.replaceChildren();
    this.lanes = [];
    const series = data.series ?? {};

    system.conserved.forEach((quantity) => {
      const values = series[quantity.name];
      if (!values) {
        return;
      }

      const row = document.createElement("div");
      row.className = "invariant";

      const head = document.createElement("div");
      head.className = "invariant__head";
      const symbol = document.createElement("span");
      symbol.className = "invariant__symbol";
      renderLatex(symbol, quantity.latex);
      const symmetry = document.createElement("span");
      symmetry.className = "invariant__symmetry";
      symmetry.textContent = quantity.symmetry;
      head.append(symbol, symmetry);

      const lane = document.createElement("canvas");
      lane.className = "invariant__lane";
      row.append(head, lane);
      this.invariants.append(row);

      const laneCtx = lane.getContext("2d");
      if (laneCtx) {
        this.lanes.push({ canvas: lane, ctx: laneCtx, series: values });
      }
    });
  }

  private renderParameters(system: SystemManifest): void {
    this.parameters.replaceChildren();
    system.parameters.forEach((parameter) => {
      const row = document.createElement("div");
      row.className = "param";

      const symbol = document.createElement("span");
      symbol.className = "param__symbol";
      renderLatex(symbol, parameter.latex);

      const track = document.createElement("div");
      track.className = "param__track";
      const marker = document.createElement("div");
      marker.className = "param__marker";
      const span = parameter.max - parameter.min || 1;
      marker.style.left = `${clamp((parameter.default - parameter.min) / span, 0, 1) * 100}%`;
      track.append(marker);

      row.append(symbol, track);
      this.parameters.append(row);
    });
  }
}

function principleBlock(label: string, expressions: string[]): HTMLElement {
  const block = document.createElement("div");
  block.className = "principle";
  const caption = document.createElement("p");
  caption.className = "principle__label";
  caption.textContent = label;
  block.append(caption);
  expressions.forEach((expression) => {
    const math = document.createElement("div");
    math.className = "principle__math";
    katex.render(expression, math, { throwOnError: false, displayMode: true });
    block.append(math);
  });
  return block;
}

// A conserved quantity drawn over the whole trajectory. Because it does not
// change, the line is dead flat — the stillness is the proof, no number needed.
function drawInvariantLane(lane: InvariantLane, phase: number): void {
  const { canvas, ctx, series } = lane;
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const drawWidth = Math.max(1, Math.floor(width * pixelRatio));
  const drawHeight = Math.max(1, Math.floor(height * pixelRatio));
  if (canvas.width !== drawWidth || canvas.height !== drawHeight) {
    canvas.width = drawWidth;
    canvas.height = drawHeight;
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  }
  ctx.clearRect(0, 0, width, height);

  const count = series.length;
  if (count === 0) {
    return;
  }
  const mean = series.reduce((sum, value) => sum + value, 0) / count;
  // The band represents +/-5% of the quantity's magnitude. A truly conserved
  // quantity never leaves the centerline; a drift would visibly climb.
  const half = Math.max(Math.abs(mean) * 0.05, 1e-9);
  const pad = 4;
  const yOf = (value: number) =>
    clamp(height / 2 - ((value - mean) / (2 * half)) * (height / 2 - pad), pad, height - pad);
  const xOf = (index: number) => (count <= 1 ? 0 : (index / (count - 1)) * width);

  ctx.strokeStyle = theme.hairline;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, height / 2);
  ctx.lineTo(width, height / 2);
  ctx.stroke();

  ctx.strokeStyle = theme.cool;
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  const step = Math.max(1, Math.floor(count / 240));
  for (let index = 0; index < count; index += step) {
    const x = xOf(index);
    const y = yOf(series[index]);
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  const playIndex = clamp(Math.round(phase * (count - 1)), 0, count - 1);
  ctx.fillStyle = theme.accentStrong;
  ctx.shadowColor = theme.accent;
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.arc(clamp(phase, 0, 1) * width, yOf(series[playIndex]), 3.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
}
