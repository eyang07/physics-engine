"""The shared example manifest — Python's single source of truth.

The viewer should not re-derive physics or hardcode constants. Instead, Python
describes each system once (here and in the per-system specs) and exports a
manifest the TypeScript layer consumes verbatim. The manifest carries two
kinds of content:

  - Presentation/schema metadata declared in the spec: title, parameters with
    ranges, the named state schema, projections (named groups of state
    variables, replacing magic indices), conserved quantities, and the
    visualization lenses that apply.
  - Symbolic physics derived from the engine and rendered as LaTeX: the
    Lagrangian, the Hamiltonian (via the Legendre transform), the energy, and
    the Euler-Lagrange equations.

Rendering the *mathematics* — not decimals — is the point: the viewer shows the
principles (the equations, the invariants), and numbers fall out only where a
flow or a shape needs coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import sympy as sp

from engine.mechanics.coordinates import acceleration_symbol, momentum_symbol
from engine.mechanics.hamiltonian import legendre_transform
from engine.mechanics.lagrangian import LagrangianSystem


@dataclass(frozen=True)
class Parameter:
    """A tunable quantity. ``physical`` params are symbols in L; ``initial``
    params are initial conditions. Ranges drive the (unlabeled) UI sliders."""

    name: str
    latex: str
    default: float
    minimum: float
    maximum: float
    role: str = "physical"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "latex": self.latex,
            "default": self.default,
            "min": self.minimum,
            "max": self.maximum,
            "role": self.role,
        }


@dataclass(frozen=True)
class StateVar:
    """One component of the exported state vector.

    ``kind`` is one of ``coordinate``, ``velocity``, ``momentum``, or
    ``embedding`` (a derived Cartesian coordinate carried only for rendering).
    """

    name: str
    latex: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "latex": self.latex, "kind": self.kind}


@dataclass(frozen=True)
class Conserved:
    """A conserved quantity and the symmetry that generates it (Noether).

    ``expression`` optionally builds the symbolic quantity from the system, so
    the same declaration can render LaTeX now and be sampled as a series later.
    """

    name: str
    latex: str
    symmetry: str
    expression: Callable[[LagrangianSystem], sp.Expr] | None = None


@dataclass(frozen=True)
class SystemSpec:
    """Everything Python knows about one example, declared once."""

    id: str
    title: str
    category: str
    description: str
    build: Callable[[], LagrangianSystem]
    parameters: tuple[Parameter, ...]
    state: tuple[StateVar, ...]
    projections: Mapping[str, tuple[str, ...]]
    conserved: tuple[Conserved, ...]
    lenses: tuple[str, ...]
    data_path: str

    def series(
        self,
        parameter_values: Mapping[str, float],
        states: Sequence[Sequence[float]],
    ) -> dict[str, list[float]]:
        """Sample the declared conserved quantities along an integrated trajectory.

        Only the leading (q, qdot) columns of ``states`` are used, so this works
        whether or not the export also carries embedding coordinates.
        ``parameter_values`` must cover the system's physical parameters by name.
        A quantity that is genuinely conserved should come back essentially flat
        — and that stillness is exactly what the viewer renders.
        """

        system = self.build()
        state_symbols = (*system.q, *system.qdot)
        array = np.asarray(states, dtype=float)
        columns = [array[:, index] for index in range(len(state_symbols))]
        substitutions = {
            symbol: parameter_values[symbol.name]
            for symbol in system.lagrangian.free_symbols
            if symbol.name in parameter_values
        }

        sampled: dict[str, list[float]] = {}
        for quantity in self.conserved:
            if quantity.expression is None:
                continue
            expression = sp.simplify(quantity.expression(system)).subs(substitutions)
            function = sp.lambdify(state_symbols, expression, modules="numpy")
            values = np.asarray(function(*columns), dtype=float)
            # Broadcast in case the quantity simplifies to a constant.
            sampled[quantity.name] = np.broadcast_to(values, (array.shape[0],)).astype(float).tolist()
        return sampled


def _latex_by_name(spec: SystemSpec) -> dict[str, str]:
    table = {sv.name: sv.latex for sv in spec.state}
    for parameter in spec.parameters:
        if parameter.role == "physical":
            table[parameter.name] = parameter.latex
    return table


def _symbol_latex(system: LagrangianSystem, spec: SystemSpec) -> dict[sp.Symbol, str]:
    """Map the system's actual symbols to LaTeX so derivatives print nicely.

    We must use the system's own Symbol objects (their assumptions matter for
    equality), not freshly constructed ones.
    """

    names = _latex_by_name(spec)
    coordinate_latex = {sv.name: sv.latex for sv in spec.state if sv.kind == "coordinate"}
    mapping: dict[sp.Symbol, str] = {}

    for symbol in (*system.q, *system.qdot):
        if symbol.name in names:
            mapping[symbol] = names[symbol.name]

    for coordinate in system.q:
        base = coordinate_latex.get(coordinate.name, sp.latex(coordinate))
        mapping[acceleration_symbol(coordinate)] = r"\ddot{" + base + "}"
        mapping[momentum_symbol(coordinate)] = "p_{" + base + "}"

    for symbol in system.lagrangian.free_symbols:
        if symbol is system.time:
            continue
        if symbol not in mapping and symbol.name in names:
            mapping[symbol] = names[symbol.name]

    mapping[system.time] = "t"
    return mapping


def system_entry(spec: SystemSpec) -> dict[str, Any]:
    """Build one manifest entry, deriving the symbolic physics from the engine."""

    system = spec.build()
    symbol_latex = _symbol_latex(system, spec)

    def latex(expr: sp.Expr) -> str:
        return sp.latex(expr, symbol_names=symbol_latex)

    hamiltonian_latex: str | None
    try:
        transform = legendre_transform(system)
        hamiltonian_latex = latex(transform.hamiltonian_system.hamiltonian)
    except Exception:
        # Singular/irregular Lagrangians have no Legendre transform; the
        # Lagrangian picture still stands.
        hamiltonian_latex = None

    conserved: list[dict[str, Any]] = []
    for quantity in spec.conserved:
        item: dict[str, Any] = {
            "name": quantity.name,
            "latex": quantity.latex,
            "symmetry": quantity.symmetry,
        }
        if quantity.expression is not None:
            item["expression_latex"] = latex(sp.simplify(quantity.expression(system)))
        conserved.append(item)

    return {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "description": spec.description,
        "dataPath": spec.data_path,
        "parameters": [parameter.to_dict() for parameter in spec.parameters],
        "state": [variable.to_dict() for variable in spec.state],
        "projections": {name: list(group) for name, group in spec.projections.items()},
        "conserved": conserved,
        "lenses": list(spec.lenses),
        "physics": {
            "lagrangian": latex(system.lagrangian),
            "hamiltonian": hamiltonian_latex,
            "energy": latex(sp.simplify(system.energy())),
            "euler_lagrange": [latex(equation) for equation in system.euler_lagrange_equations()],
        },
    }


def build_manifest(specs: Mapping[str, SystemSpec] | tuple[SystemSpec, ...] | list[SystemSpec]) -> dict[str, Any]:
    """Assemble the full manifest from an ordered collection of specs."""

    items = list(specs.values()) if isinstance(specs, Mapping) else list(specs)
    return {"version": 1, "systems": [system_entry(spec) for spec in items]}


def write_manifest(specs: tuple[SystemSpec, ...] | list[SystemSpec], *paths: str | Path) -> dict[str, Any]:
    """Build the manifest and write it (pretty-printed) to each path."""

    manifest = build_manifest(specs)
    payload = json.dumps(manifest, indent=2)
    for path in paths:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    return manifest
