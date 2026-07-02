from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import sympy as sp

from engine.fieldtheory import LagrangianFieldDensity


@dataclass(frozen=True)
class ScalarFieldDensitySystem:
    """A symbolic 1+1 Klein-Gordon field density plus an analytic mode."""

    mass: sp.Expr
    wavenumber: sp.Expr
    amplitude: sp.Expr

    def __post_init__(self) -> None:
        object.__setattr__(self, "mass", sp.sympify(self.mass))
        object.__setattr__(self, "wavenumber", sp.sympify(self.wavenumber))
        object.__setattr__(self, "amplitude", sp.sympify(self.amplitude))

    @property
    def coordinates(self) -> tuple[sp.Symbol, sp.Symbol]:
        return sp.Symbol("t", real=True), sp.Symbol("x", real=True)

    @property
    def field(self) -> sp.Expr:
        t, x = self.coordinates
        return sp.Function("phi")(t, x)

    @property
    def angular_frequency(self) -> sp.Expr:
        return sp.sqrt(self.wavenumber**2 + self.mass**2)

    @property
    def configuration(self) -> sp.Expr:
        t, x = self.coordinates
        return (
            self.amplitude
            * sp.sin(self.angular_frequency * t)
            * sp.cos(self.wavenumber * x)
        )

    @property
    def density(self) -> LagrangianFieldDensity:
        t, x = self.coordinates
        phi = self.field
        density = (
            sp.Rational(1, 2) * sp.diff(phi, t) ** 2
            - sp.Rational(1, 2) * sp.diff(phi, x) ** 2
            - sp.Rational(1, 2) * self.mass**2 * phi**2
        )
        return LagrangianFieldDensity(
            (t, x),
            phi,
            density,
            parameters=self.parameter_symbols(),
        )

    def parameter_symbols(self) -> tuple[sp.Symbol, ...]:
        symbols = sorted(
            (
                self.mass.free_symbols
                | self.wavenumber.free_symbols
                | self.amplitude.free_symbols
            ),
            key=lambda symbol: symbol.name,
        )
        return tuple(symbols)

    def parameter_expressions(self) -> tuple[sp.Expr, ...]:
        return (self.mass, self.wavenumber, self.amplitude, self.configuration)

    def on_shell_residual_expression(self) -> sp.Expr:
        expression = self.density.euler_lagrange_expression()
        replacements: dict[sp.Expr, sp.Expr] = {self.field: self.configuration}
        for derivative in expression.atoms(sp.Derivative):
            if derivative.expr != self.field:
                continue
            value = self.configuration
            for variable, count in derivative.variable_count:
                value = sp.diff(value, variable, count)
            replacements[derivative] = value
        return sp.simplify(expression.xreplace(replacements))

    def field_values(
        self,
        time: Sequence[float],
        x_axis: Sequence[float],
        *,
        parameters: Mapping[str, float],
    ) -> np.ndarray:
        t, x = self.coordinates
        function = sp.lambdify(
            (t, x, *self.parameter_symbols()),
            self.configuration,
            modules="numpy",
        )
        parameter_args = [float(parameters[symbol.name]) for symbol in self.parameter_symbols()]
        tt, xx = np.meshgrid(
            np.asarray(time, dtype=float),
            np.asarray(x_axis, dtype=float),
            indexing="ij",
        )
        values = function(tt, xx, *parameter_args)
        return np.asarray(values, dtype=float)

    def manifest_metadata(self) -> dict[str, object]:
        field_density = self.density
        return {
            "kind": "scalar-field-density",
            "field": "phi",
            "coordinates": [symbol.name for symbol in self.coordinates],
            "metricSignature": "(-,+)",
            "densityLatex": sp.latex(field_density.density),
            "eulerLagrangeLatex": sp.latex(field_density.euler_lagrange_equation()),
            "stressEnergyLatex": [
                [sp.latex(component) for component in row]
                for row in field_density.stress_energy_tensor().tolist()
            ],
            "configurationLatex": sp.latex(self.configuration),
            "angularFrequencyLatex": sp.latex(self.angular_frequency),
            "conservationLawLatex": r"\partial_\mu T^{\mu}{}_{\nu}=0",
            "evaluation": "symbolic-structure-plus-sampled-mode",
            "nonGoal": "No PDE time-stepping solver is provided or implied.",
        }


def build_system(
    *,
    mass: sp.Expr | float | None = None,
    wavenumber: sp.Expr | float | None = None,
    amplitude: sp.Expr | float | None = None,
) -> ScalarFieldDensitySystem:
    return ScalarFieldDensitySystem(
        mass=sp.Symbol("m", positive=True) if mass is None else mass,
        wavenumber=sp.Symbol("k", positive=True) if wavenumber is None else wavenumber,
        amplitude=sp.Symbol("A", real=True) if amplitude is None else amplitude,
    )


system = build_system()
