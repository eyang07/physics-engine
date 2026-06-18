from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import sympy as sp

from engine.dynamics import FirstOrderSystem
from engine.mechanics.coordinates import time_symbol


@dataclass(frozen=True)
class NBodyLayout:
    """Planar N-body state naming convention."""

    body_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.body_count, int) or self.body_count < 2:
            raise ValueError("body_count must be an integer >= 2")

    @property
    def position_names(self) -> tuple[str, ...]:
        return tuple(
            component
            for index in range(1, self.body_count + 1)
            for component in (f"x{index}", f"y{index}")
        )

    @property
    def velocity_names(self) -> tuple[str, ...]:
        return tuple(
            component
            for index in range(1, self.body_count + 1)
            for component in (f"vx{index}", f"vy{index}")
        )

    @property
    def state_names(self) -> tuple[str, ...]:
        return self.position_names + self.velocity_names

    @property
    def mass_names(self) -> tuple[str, ...]:
        return tuple(f"m{index}" for index in range(1, self.body_count + 1))


def build_system(
    body_count: int = 3,
    *,
    masses: Sequence[sp.Expr | float] | None = None,
    gravitational_constant: sp.Expr | float | None = None,
) -> FirstOrderSystem:
    """Build a planar Newtonian N-body first-order system."""

    layout = NBodyLayout(body_count)
    if masses is not None and len(masses) != body_count:
        raise ValueError("masses must match body_count")

    state = sp.symbols(" ".join(layout.state_names), real=True)
    positions = tuple(
        sp.Matrix([state[2 * index], state[2 * index + 1]])
        for index in range(body_count)
    )
    velocities = tuple(
        sp.Matrix(
            [
                state[2 * body_count + 2 * index],
                state[2 * body_count + 2 * index + 1],
            ]
        )
        for index in range(body_count)
    )
    mass_values = (
        tuple(sp.Symbol(name, positive=True) for name in layout.mass_names)
        if masses is None
        else tuple(masses)
    )
    gravity = (
        sp.Symbol("G", positive=True)
        if gravitational_constant is None
        else gravitational_constant
    )

    accelerations: list[sp.Expr] = []
    for i, position_i in enumerate(positions):
        acceleration = sp.Matrix([0, 0])
        for j, position_j in enumerate(positions):
            if i == j:
                continue
            delta = position_j - position_i
            radius_squared = delta.dot(delta)
            acceleration += gravity * mass_values[j] * delta / radius_squared ** sp.Rational(3, 2)
        accelerations.extend(acceleration)

    parameters = tuple(
        symbol
        for symbol in (gravity, *mass_values)
        if isinstance(symbol, sp.Symbol)
    )
    rhs = tuple(component for velocity in velocities for component in velocity) + tuple(accelerations)
    return FirstOrderSystem(
        state=state,
        rhs=rhs,
        parameters=parameters,
        time=time_symbol(),
        simplify_derivatives=False,
    )


def _layout_from_system(system: FirstOrderSystem) -> NBodyLayout:
    if len(system.state) % 4 != 0:
        raise ValueError("N-body state dimension must be a multiple of 4")
    return NBodyLayout(len(system.state) // 4)


def _symbol_by_name(system: FirstOrderSystem, name: str) -> sp.Symbol:
    for symbol in (*system.state, *system.parameters):
        if symbol.name == name:
            return symbol
    raise ValueError(f"system does not contain symbol {name!r}")


def total_energy(system: FirstOrderSystem) -> sp.Expr:
    layout = _layout_from_system(system)
    gravity = _symbol_by_name(system, "G")
    masses = tuple(_symbol_by_name(system, name) for name in layout.mass_names)
    state_by_name = {symbol.name: symbol for symbol in system.state}

    kinetic = 0
    potential = 0
    for i in range(layout.body_count):
        vx = state_by_name[f"vx{i + 1}"]
        vy = state_by_name[f"vy{i + 1}"]
        kinetic += sp.Rational(1, 2) * masses[i] * (vx**2 + vy**2)
        xi = state_by_name[f"x{i + 1}"]
        yi = state_by_name[f"y{i + 1}"]
        for j in range(i + 1, layout.body_count):
            xj = state_by_name[f"x{j + 1}"]
            yj = state_by_name[f"y{j + 1}"]
            radius = sp.sqrt((xj - xi) ** 2 + (yj - yi) ** 2)
            potential -= gravity * masses[i] * masses[j] / radius
    return kinetic + potential


def total_momentum_x(system: FirstOrderSystem) -> sp.Expr:
    layout = _layout_from_system(system)
    masses = tuple(_symbol_by_name(system, name) for name in layout.mass_names)
    state_by_name = {symbol.name: symbol for symbol in system.state}
    return sum(
        masses[index] * state_by_name[f"vx{index + 1}"]
        for index in range(layout.body_count)
    )


def total_momentum_y(system: FirstOrderSystem) -> sp.Expr:
    layout = _layout_from_system(system)
    masses = tuple(_symbol_by_name(system, name) for name in layout.mass_names)
    state_by_name = {symbol.name: symbol for symbol in system.state}
    return sum(
        masses[index] * state_by_name[f"vy{index + 1}"]
        for index in range(layout.body_count)
    )


def total_angular_momentum_z(system: FirstOrderSystem) -> sp.Expr:
    layout = _layout_from_system(system)
    masses = tuple(_symbol_by_name(system, name) for name in layout.mass_names)
    state_by_name = {symbol.name: symbol for symbol in system.state}
    return sum(
        masses[index]
        * (
            state_by_name[f"x{index + 1}"] * state_by_name[f"vy{index + 1}"]
            - state_by_name[f"y{index + 1}"] * state_by_name[f"vx{index + 1}"]
        )
        for index in range(layout.body_count)
    )


system = build_system()
