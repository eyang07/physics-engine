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

from engine.dynamics import CotangentHamiltonianSystem, FirstOrderSystem
from engine.mechanics.coordinates import acceleration_symbol, momentum_symbol
from engine.mechanics.hamiltonian import legendre_transform
from engine.mechanics.lagrangian import LagrangianSystem
from engine.mechanics.symmetries import InfinitesimalSymmetry, noether_charge


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
class ParameterVariant:
    """A deterministic precomputed trajectory for a named parameter set."""

    id: str
    label: str
    parameters: Mapping[str, float]
    data_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "parameters": dict(self.parameters),
            "dataPath": self.data_path,
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

    ``generator`` is the preferred Noether-first declaration: it builds the
    infinitesimal symmetry and the engine derives the charge. ``expression`` is
    kept for exceptional quantities that are not yet represented by a generator.
    """

    name: str
    latex: str
    symmetry: str
    expression: Callable[[LagrangianSystem], sp.Expr] | None = None
    generator: Callable[[LagrangianSystem], InfinitesimalSymmetry] | None = None

    def expression_for(self, system: LagrangianSystem | FirstOrderSystem) -> sp.Expr | None:
        """Return the symbolic conserved quantity for this system."""

        if self.generator is not None:
            return noether_charge(system, self.generator(system))
        if self.expression is not None:
            return self.expression(system)
        return None


@dataclass(frozen=True)
class EffectivePotential:
    """A one-dimensional reduction after fixing a conserved quantity.

    For central-force examples this is the radial potential obtained after
    fixing angular momentum, so the radial energy equation reads
    ``T_radial + V_eff(r) = constant``.
    """

    name: str
    coordinate: str
    latex: str
    conserved: str
    conserved_latex: str
    expression: Callable[[LagrangianSystem], sp.Expr]
    plot_source: str | None = None
    turning_points_source: str | None = None
    classification_source: str | None = None

    def expression_for(self, system: LagrangianSystem) -> sp.Expr:
        return self.expression(system)

    def sources_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.plot_source is not None:
            payload["plotSource"] = self.plot_source
        if self.turning_points_source is not None:
            payload["turningPointsSource"] = self.turning_points_source
        if self.classification_source is not None:
            payload["classificationSource"] = self.classification_source
        return payload


@dataclass(frozen=True)
class Lens:
    """A reusable mathematical view of a system.

    Systems reference lenses by id; the registry describes what kind of view it
    is and which exported structures it expects. Rendering code can then choose
    an implementation without baking those meanings into every system spec.
    """

    id: str
    title: str
    kind: str
    description: str
    projections: tuple[str, ...] = ()
    conserved: tuple[str, ...] = ()
    effective_potentials: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "description": self.description,
            "projections": list(self.projections),
            "conserved": list(self.conserved),
            "effectivePotentials": list(self.effective_potentials),
        }


@dataclass(frozen=True)
class SystemSpec:
    """Everything Python knows about one example, declared once."""

    id: str
    title: str
    category: str
    description: str
    build: Callable[[], Any]
    parameters: tuple[Parameter, ...]
    state: tuple[StateVar, ...]
    projections: Mapping[str, tuple[str, ...]]
    conserved: tuple[Conserved, ...]
    lenses: tuple[str, ...]
    data_path: str
    effective_potentials: tuple[EffectivePotential, ...] = ()
    normal_modes: Callable[[Any], Mapping[str, Any]] | None = None
    geometry: Callable[[Any], Mapping[str, Any]] | None = None
    orientation: Mapping[str, Any] | None = None
    fields: tuple[Mapping[str, Any], ...] = ()
    system_kind: str = "mechanics"
    variants: tuple[ParameterVariant, ...] = ()
    verification_problems: tuple[str, ...] = ()

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
        if isinstance(system, LagrangianSystem):
            state_symbols = (*system.q, *system.qdot)
            parameter_symbols = system.lagrangian.free_symbols
        elif isinstance(system, FirstOrderSystem):
            state_symbols = system.state
            parameter_symbols = set(system.parameters)
        else:
            return {}
        array = np.asarray(states, dtype=float)
        columns = [array[:, index] for index in range(len(state_symbols))]
        substitutions = {
            symbol: parameter_values[symbol.name]
            for symbol in parameter_symbols
            if symbol.name in parameter_values
        }

        sampled: dict[str, list[float]] = {}
        for quantity in self.conserved:
            expression = quantity.expression_for(system)
            if expression is None:
                continue
            expression = sp.simplify(expression).subs(substitutions)
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

    for potential in spec.effective_potentials:
        mapping[sp.Symbol(potential.conserved)] = potential.conserved_latex

    mapping[system.time] = "t"
    return mapping


def _dynamics_symbol_latex(system: FirstOrderSystem, spec: SystemSpec) -> dict[sp.Symbol, str]:
    names = _latex_by_name(spec)
    mapping = {
        symbol: names.get(symbol.name, sp.latex(symbol))
        for symbol in (*system.state, *system.parameters)
    }
    mapping[system.time] = "t"
    return mapping


def derivation_entry(
    spec: SystemSpec,
    system: LagrangianSystem,
    transform: Any | None,
    latex: Callable[[sp.Expr], str],
) -> dict[str, Any]:
    """Build structured symbolic steps for the viewer.

    This is deliberately redundant with ``physics``: ``physics`` is the compact
    display contract, while ``derivation`` preserves the mathematical path from
    Lagrangian data to equations, Hamiltonian data, and Noether charges.
    """

    momenta = system.generalized_momenta()
    momentum_symbols = tuple(momentum_symbol(q) for q in system.q)

    generalized_momenta = [
        {
            "coordinate": q.name,
            "velocity": v.name,
            "momentum": p.name,
            "momentum_latex": latex(p),
            "expression_latex": latex(sp.simplify(momentum)),
            "equation_latex": latex(sp.Eq(p, sp.simplify(momentum))),
        }
        for q, v, p, momentum in zip(system.q, system.qdot, momentum_symbols, momenta, strict=True)
    ]

    euler_lagrange = [
        {
            "coordinate": q.name,
            "equation_latex": latex(equation),
        }
        for q, equation in zip(system.q, system.euler_lagrange_equations(), strict=True)
    ]

    legendre: dict[str, Any]
    hamiltonian: dict[str, Any] | None = None
    if transform is None:
        legendre = {"regular": False, "velocity_solutions": []}
    else:
        hamiltonian_system = transform.hamiltonian_system
        velocity_solutions = [
            {
                "velocity": velocity.name,
                "expression_latex": latex(sp.simplify(expression)),
                "equation_latex": latex(sp.Eq(velocity, sp.simplify(expression))),
            }
            for velocity, expression in transform.momentum_to_velocity.items()
        ]
        legendre = {
            "regular": True,
            "velocity_solutions": velocity_solutions,
        }
        hamiltonian = {
            "expression_latex": latex(hamiltonian_system.hamiltonian),
            "equations": [
                {
                    "equation_latex": latex(equation),
                }
                for equation in hamiltonian_system.hamilton_equation_equalities()
            ],
        }

    conserved = []
    for quantity in spec.conserved:
        item: dict[str, Any] = {
            "name": quantity.name,
            "symbol_latex": quantity.latex,
            "symmetry": quantity.symmetry,
        }
        expression = quantity.expression_for(system)
        if expression is not None:
            item["charge_latex"] = latex(sp.simplify(expression))
        if quantity.generator is not None:
            generator = quantity.generator(system)
            item["generator_latex"] = [
                latex(sp.simplify(component))
                for component in generator.components(system.q)
            ]
            item["tau_latex"] = latex(sp.simplify(generator.tau))
        conserved.append(item)

    effective_potentials = [
        {
            "name": potential.name,
            "coordinate": potential.coordinate,
            "latex": potential.latex,
            "conserved": potential.conserved,
            "conserved_latex": potential.conserved_latex,
            "expression_latex": latex(sp.simplify(potential.expression_for(system))),
            **potential.sources_payload(),
        }
        for potential in spec.effective_potentials
    ]

    return {
        "lagrangian": {
            "expression_latex": latex(system.lagrangian),
        },
        "generalized_momenta": generalized_momenta,
        "euler_lagrange": euler_lagrange,
        "legendre_transform": legendre,
        "hamiltonian": hamiltonian,
        "conserved_quantities": conserved,
        "effective_potentials": effective_potentials,
    }


def system_entry(spec: SystemSpec) -> dict[str, Any]:
    """Build one manifest entry, deriving the symbolic physics from the engine."""

    system = spec.build()
    if spec.system_kind in {"static-field", "field-evolution"}:
        return field_system_entry(spec, system)
    if isinstance(system, FirstOrderSystem):
        return first_order_system_entry(spec, system)
    if isinstance(system, CotangentHamiltonianSystem):
        return first_order_system_entry(spec, system.first_order_system())

    symbol_latex = _symbol_latex(system, spec)

    def latex(expr: sp.Expr) -> str:
        return sp.latex(expr, symbol_names=symbol_latex)

    transform = None
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
        expression = quantity.expression_for(system)
        if expression is not None:
            item["expression_latex"] = latex(sp.simplify(expression))
        if quantity.generator is not None:
            generator = quantity.generator(system)
            item["generator_latex"] = [latex(sp.simplify(component)) for component in generator.components(system.q)]
            if generator.tau != 0:
                item["tau_latex"] = latex(sp.simplify(generator.tau))
        conserved.append(item)

    effective_potentials = [
        {
            "name": potential.name,
            "coordinate": potential.coordinate,
            "latex": potential.latex,
            "conserved": potential.conserved,
            "conserved_latex": potential.conserved_latex,
            "expression_latex": latex(sp.simplify(potential.expression_for(system))),
            **potential.sources_payload(),
        }
        for potential in spec.effective_potentials
    ]

    entry = {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "description": spec.description,
        "dataPath": spec.data_path,
        "parameters": [parameter.to_dict() for parameter in spec.parameters],
        "state": [variable.to_dict() for variable in spec.state],
        "projections": {name: list(group) for name, group in spec.projections.items()},
        "conserved": conserved,
        "effectivePotentials": effective_potentials,
        "lenses": list(spec.lenses),
        "physics": {
            "lagrangian": latex(system.lagrangian),
            "hamiltonian": hamiltonian_latex,
            "energy": latex(sp.simplify(system.energy())),
            "euler_lagrange": [latex(equation) for equation in system.euler_lagrange_equations()],
        },
        "derivation": derivation_entry(spec, system, transform, latex),
    }
    if spec.normal_modes is not None:
        entry["normalModes"] = dict(spec.normal_modes(system))
    if spec.geometry is not None:
        entry["geometry"] = dict(spec.geometry(system))
    if spec.orientation is not None:
        entry["orientation"] = dict(spec.orientation)
    if spec.fields:
        entry["fields"] = [dict(channel) for channel in spec.fields]
    if spec.variants:
        entry["variants"] = [variant.to_dict() for variant in spec.variants]
    if spec.verification_problems:
        entry["verificationProblems"] = list(spec.verification_problems)
    return entry


def field_system_entry(spec: SystemSpec, system: Any) -> dict[str, Any]:
    """Build a manifest entry for field payloads outside particle dynamics."""

    entry = {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "description": spec.description,
        "dataPath": spec.data_path,
        "systemKind": spec.system_kind,
        "parameters": [parameter.to_dict() for parameter in spec.parameters],
        "state": [variable.to_dict() for variable in spec.state],
        "projections": {name: list(group) for name, group in spec.projections.items()},
        "conserved": [],
        "effectivePotentials": [],
        "lenses": list(spec.lenses),
        "fields": [dict(channel) for channel in spec.fields],
    }
    metadata = getattr(system, "manifest_metadata", None)
    if callable(metadata):
        entry["fieldModel"] = dict(metadata())
    if spec.normal_modes is not None:
        entry["normalModes"] = dict(spec.normal_modes(system))
    if spec.variants:
        entry["variants"] = [variant.to_dict() for variant in spec.variants]
    return entry


def first_order_system_entry(spec: SystemSpec, system: FirstOrderSystem) -> dict[str, Any]:
    symbol_latex = _dynamics_symbol_latex(system, spec)

    def latex(expr: sp.Expr) -> str:
        return sp.latex(expr, symbol_names=symbol_latex)

    vector_field = [
        {
            "state": symbol.name,
            "equation_latex": latex(sp.Eq(sp.Symbol(f"{symbol.name}_dot", real=True), expression)),
            "expression_latex": latex(expression),
        }
        for symbol, expression in zip(system.state, system.rhs, strict=True)
    ]
    jacobian = system.jacobian()
    conserved: list[dict[str, Any]] = []
    for quantity in spec.conserved:
        item: dict[str, Any] = {
            "name": quantity.name,
            "latex": quantity.latex,
            "symmetry": quantity.symmetry,
        }
        expression = quantity.expression_for(system)
        if expression is not None:
            rendered_expression = (
                sp.simplify(expression) if system.simplify_derivatives else expression
            )
            item["expression_latex"] = latex(rendered_expression)
        conserved.append(item)
    effective_potentials = [
        {
            "name": potential.name,
            "coordinate": potential.coordinate,
            "latex": potential.latex,
            "conserved": potential.conserved,
            "conserved_latex": potential.conserved_latex,
            "expression_latex": latex(sp.simplify(potential.expression_for(system))),
            **potential.sources_payload(),
        }
        for potential in spec.effective_potentials
    ]

    entry = {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "description": spec.description,
        "dataPath": spec.data_path,
        "systemKind": spec.system_kind,
        "parameters": [parameter.to_dict() for parameter in spec.parameters],
        "state": [variable.to_dict() for variable in spec.state],
        "projections": {name: list(group) for name, group in spec.projections.items()},
        "conserved": conserved,
        "effectivePotentials": effective_potentials,
        "lenses": list(spec.lenses),
        "dynamics": {
            "vector_field": vector_field,
            "divergence_latex": latex(system.divergence()),
            "jacobian_latex": latex(jacobian),
        },
    }
    if spec.normal_modes is not None:
        entry["normalModes"] = dict(spec.normal_modes(system))
    if spec.geometry is not None:
        entry["geometry"] = dict(spec.geometry(system))
    if spec.orientation is not None:
        entry["orientation"] = dict(spec.orientation)
    if spec.fields:
        entry["fields"] = [dict(channel) for channel in spec.fields]
    if spec.variants:
        entry["variants"] = [variant.to_dict() for variant in spec.variants]
    if spec.verification_problems:
        entry["verificationProblems"] = list(spec.verification_problems)
    return entry


def build_manifest(
    specs: Mapping[str, SystemSpec] | tuple[SystemSpec, ...] | list[SystemSpec],
    lenses: Sequence[Lens] = (),
) -> dict[str, Any]:
    """Assemble the full manifest from an ordered collection of specs."""

    items = list(specs.values()) if isinstance(specs, Mapping) else list(specs)
    return {
        "version": 1,
        "lenses": [lens.to_dict() for lens in lenses],
        "systems": [system_entry(spec) for spec in items],
    }


def write_manifest(
    specs: tuple[SystemSpec, ...] | list[SystemSpec],
    *paths: str | Path,
    lenses: Sequence[Lens] = (),
) -> dict[str, Any]:
    """Build the manifest and write it (pretty-printed) to each path."""

    manifest = build_manifest(specs, lenses)
    payload = json.dumps(manifest, indent=2)
    for path in paths:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    return manifest
