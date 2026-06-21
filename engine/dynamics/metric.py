"""Fixed-background metric geometry for geodesic examples.

:class:`MetricGeometry` holds metric coefficients ``g_ij(q)`` on a chart
(Riemannian or Lorentzian; the formulas do not depend on signature) and
derives:

- Christoffel symbols
  ``Gamma^k_ij = g^kl (d_i g_jl + d_j g_il - d_l g_ij) / 2``;
- the geodesic equation as a first-order system in ``(q, q_dot)`` with
  ``qddot^k = -Gamma^k_ij qdot^i qdot^j``;
- symbolic curvature tensors: Riemann ``R^rho_{sigma mu nu}``, Ricci
  ``R_sigma_nu``, and scalar curvature ``R``;
- the cogeodesic Hamiltonian flow on the cotangent side, via
  :class:`~engine.dynamics.media.InverseMetricMedium`, to which the existing
  ray-bundle and ray-diagnostics utilities apply directly;
- measured geodesic-deviation diagnostics from pairs of sampled geodesic
  rollouts;
- a metric-compatibility residual ``nabla g`` that must vanish identically,
  as a self-check suitable for proof-obligation-style artifacts.

This is a backend-only helper: geodesic examples built from it must not
enter the gallery manifest until the viewer can render their geometry
honestly (see `docs/BACKEND.md` open questions).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics.first_order import FirstOrderSystem
from engine.dynamics.media import InverseMetricMedium, _detected_parameters
from engine.mechanics.coordinates import velocity_symbol


def _trig_simplify(expression: sp.Expr) -> sp.Expr:
    """Simplification strong enough to cancel double-angle combinations."""

    return sp.simplify(sp.expand_trig(expression))


@dataclass(frozen=True)
class MetricGeometry:
    """Metric coefficients ``g_ij(q)`` on a coordinate chart."""

    coordinates: tuple[sp.Symbol, ...]
    metric: sp.Matrix
    parameters: tuple[sp.Symbol, ...] | None = None

    def __post_init__(self) -> None:
        if not self.coordinates:
            raise ValueError("coordinates must be non-empty")
        matrix = sp.Matrix(self.metric)
        object.__setattr__(self, "metric", matrix)
        dimension = len(self.coordinates)
        if matrix.shape != (dimension, dimension):
            raise ValueError("metric must be a square matrix matching the coordinates")
        if sp.simplify(matrix - matrix.T) != sp.zeros(dimension, dimension):
            raise ValueError("metric must be symmetric")
        if matrix.det() == 0:
            raise ValueError("metric must be non-degenerate")
        if self.parameters is None:
            object.__setattr__(
                self,
                "parameters",
                _detected_parameters(matrix, self.coordinates),
            )

    @property
    def dimension(self) -> int:
        return len(self.coordinates)

    @property
    def velocities(self) -> tuple[sp.Symbol, ...]:
        return tuple(velocity_symbol(q) for q in self.coordinates)

    def inverse_metric(self) -> sp.Matrix:
        return sp.simplify(self.metric.inv())

    def christoffel_symbols(self) -> sp.ImmutableDenseNDimArray:
        """Second-kind Christoffel symbols indexed ``[k, i, j]``."""

        n = self.dimension
        g = self.metric
        g_inv = self.inverse_metric()
        q = self.coordinates
        symbols = [
            [
                [
                    sp.simplify(
                        sum(
                            g_inv[k, l]
                            * (
                                sp.diff(g[j, l], q[i])
                                + sp.diff(g[i, l], q[j])
                                - sp.diff(g[i, j], q[l])
                            )
                            for l in range(n)
                        )
                        / 2
                    )
                    for j in range(n)
                ]
                for i in range(n)
            ]
            for k in range(n)
        ]
        return sp.ImmutableDenseNDimArray(symbols)

    def metric_compatibility_residual(self) -> sp.ImmutableDenseNDimArray:
        """The covariant derivative ``nabla_k g_ij``; identically zero iff
        the Christoffel symbols are the Levi-Civita connection of ``g``."""

        n = self.dimension
        g = self.metric
        q = self.coordinates
        gamma = self.christoffel_symbols()
        residual = [
            [
                [
                    _trig_simplify(
                        sp.diff(g[i, j], q[k])
                        - sum(gamma[l, k, i] * g[l, j] for l in range(n))
                        - sum(gamma[l, k, j] * g[i, l] for l in range(n))
                    )
                    for j in range(n)
                ]
                for i in range(n)
            ]
            for k in range(n)
        ]
        return sp.ImmutableDenseNDimArray(residual)

    def geodesic_accelerations(self) -> tuple[sp.Expr, ...]:
        """``qddot^k = -Gamma^k_ij qdot^i qdot^j`` in the chart velocities."""

        n = self.dimension
        gamma = self.christoffel_symbols()
        v = self.velocities
        return tuple(
            sp.simplify(
                -sum(gamma[k, i, j] * v[i] * v[j] for i in range(n) for j in range(n))
            )
            for k in range(n)
        )

    def riemann_tensor(self) -> sp.ImmutableDenseNDimArray:
        """Riemann tensor indexed ``[rho, sigma, mu, nu]``.

        The convention is
        ``R^rho_{sigma mu nu} = d_mu Gamma^rho_{nu sigma}
        - d_nu Gamma^rho_{mu sigma}
        + Gamma^rho_{mu lambda} Gamma^lambda_{nu sigma}
        - Gamma^rho_{nu lambda} Gamma^lambda_{mu sigma}``.
        """

        n = self.dimension
        q = self.coordinates
        gamma = self.christoffel_symbols()
        values = [
            [
                [
                    [
                        _trig_simplify(
                            sp.diff(gamma[rho, nu, sigma], q[mu])
                            - sp.diff(gamma[rho, mu, sigma], q[nu])
                            + sum(
                                gamma[rho, mu, lam] * gamma[lam, nu, sigma]
                                - gamma[rho, nu, lam] * gamma[lam, mu, sigma]
                                for lam in range(n)
                            )
                        )
                        for nu in range(n)
                    ]
                    for mu in range(n)
                ]
                for sigma in range(n)
            ]
            for rho in range(n)
        ]
        return sp.ImmutableDenseNDimArray(values)

    def ricci_tensor(self) -> sp.Matrix:
        """Ricci tensor ``R_sigma_nu = R^rho_{sigma rho nu}``."""

        n = self.dimension
        riemann = self.riemann_tensor()
        return sp.Matrix(
            n,
            n,
            lambda sigma, nu: _trig_simplify(
                sum(riemann[rho, sigma, rho, nu] for rho in range(n))
            ),
        )

    def scalar_curvature(self) -> sp.Expr:
        """Scalar curvature ``g^ij R_ij``."""

        n = self.dimension
        ricci = self.ricci_tensor()
        inverse = self.inverse_metric()
        return _trig_simplify(
            sum(inverse[i, j] * ricci[i, j] for i in range(n) for j in range(n))
        )

    def kretschmann_scalar(self) -> sp.Expr:
        """Kretschmann scalar ``R_{abcd} R^{abcd}``.

        The fully contracted square of the Riemann tensor: the
        contravariant index of :meth:`riemann_tensor` is lowered with the
        metric, the tensor is then raised on every index, and the two are
        contracted. Unlike the scalar curvature it does not vanish in vacuum,
        so it is the natural curvature invariant for Ricci-flat backgrounds
        such as Schwarzschild (where ``R_{abcd} R^{abcd} = 12 r_s^2 / r^6``).
        """

        n = self.dimension
        g = self.metric
        g_inv = self.inverse_metric()
        riemann = self.riemann_tensor()
        lowered = [
            [
                [
                    [
                        sum(g[rho, lam] * riemann[lam, sigma, mu, nu] for lam in range(n))
                        for nu in range(n)
                    ]
                    for mu in range(n)
                ]
                for sigma in range(n)
            ]
            for rho in range(n)
        ]
        total = sp.Integer(0)
        for a in range(n):
            for b in range(n):
                for c in range(n):
                    for d in range(n):
                        raised = sum(
                            g_inv[a, e]
                            * g_inv[b, f]
                            * g_inv[c, h]
                            * g_inv[d, k]
                            * lowered[e][f][h][k]
                            for e in range(n)
                            for f in range(n)
                            for h in range(n)
                            for k in range(n)
                        )
                        total += lowered[a][b][c][d] * raised
        return _trig_simplify(total)

    def geodesic_system(self) -> FirstOrderSystem:
        """The geodesic equation as a first-order system in ``(q, q_dot)``.

        The independent variable is the affine parameter of the geodesic.
        """

        return FirstOrderSystem(
            state=(*self.coordinates, *self.velocities),
            rhs=(*self.velocities, *self.geodesic_accelerations()),
            parameters=tuple(self.parameters or ()),
            time=sp.Symbol("s", real=True),
        )

    def kinetic_energy(self) -> sp.Expr:
        """``g_ij qdot^i qdot^j / 2``, conserved along geodesics."""

        v = sp.Matrix(self.velocities)
        return sp.simplify((v.T * self.metric * v)[0, 0] / 2)

    def cogeodesic_medium(self) -> InverseMetricMedium:
        """The cotangent-side medium whose flow is the cogeodesic flow."""

        return InverseMetricMedium(
            coordinates=tuple(self.coordinates),
            inverse_metric=self.inverse_metric(),
            parameters=tuple(self.parameters or ()),
        )

    def parallel_transport(
        self,
        parameter: Sequence[float],
        curve: Sequence[Sequence[float]],
        initial_vector: Sequence[float],
        *,
        parameter_values: dict[str, float] | None = None,
    ) -> np.ndarray:
        """Numerically parallel-transport a vector along a sampled curve.

        The returned array has shape ``(sample, dimension)`` and stores vector
        components in the coordinate basis. This is a sampled ODE integration
        along the supplied curve, not a symbolic certificate.
        """

        samples = np.asarray(parameter, dtype=float)
        curve_array = np.asarray(curve, dtype=float)
        vector = np.asarray(initial_vector, dtype=float)
        if samples.ndim != 1:
            raise ValueError("parameter samples must be one-dimensional")
        if curve_array.shape != (len(samples), self.dimension):
            raise ValueError("curve must have shape (sample, dimension)")
        if vector.shape != (self.dimension,):
            raise ValueError("initial_vector must match the metric dimension")
        if len(samples) < 2:
            raise ValueError("parallel transport needs at least two curve samples")
        if np.any(np.diff(samples) <= 0.0):
            raise ValueError("parameter samples must be strictly increasing")

        gamma = self.christoffel_symbols()
        gamma_values = [
            gamma[k, i, j]
            for k in range(self.dimension)
            for i in range(self.dimension)
            for j in range(self.dimension)
        ]
        gamma_func = sp.lambdify(
            (*self.coordinates, *(self.parameters or ())),
            gamma_values,
            modules="numpy",
        )
        parameter_args = [
            float((parameter_values or {})[symbol.name])
            for symbol in (self.parameters or ())
        ]

        def connection_at(point: np.ndarray) -> np.ndarray:
            values = gamma_func(*point, *parameter_args)
            return np.asarray(values, dtype=float).reshape(
                self.dimension,
                self.dimension,
                self.dimension,
            )

        def rhs(point: np.ndarray, tangent: np.ndarray, transported: np.ndarray) -> np.ndarray:
            connection = connection_at(point)
            return -np.einsum("kij,i,j->k", connection, tangent, transported)

        transported = np.zeros_like(curve_array)
        transported[0] = vector
        for index in range(len(samples) - 1):
            ds = float(samples[index + 1] - samples[index])
            q0 = curve_array[index]
            q1 = curve_array[index + 1]
            tangent = (q1 - q0) / ds
            midpoint = 0.5 * (q0 + q1)
            current = transported[index]
            k1 = rhs(q0, tangent, current)
            k2 = rhs(midpoint, tangent, current + 0.5 * ds * k1)
            k3 = rhs(midpoint, tangent, current + 0.5 * ds * k2)
            k4 = rhs(q1, tangent, current + ds * k3)
            transported[index + 1] = current + ds * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        return transported

    def geodesic_deviation_diagnostic(
        self,
        parameter: Sequence[float],
        reference_states: Sequence[Sequence[float]],
        neighboring_states: Sequence[Sequence[float]],
        *,
        parameter_values: dict[str, float] | None = None,
    ) -> dict[str, object]:
        """Measured separation/focusing diagnostic for nearby geodesic rollouts.

        Separation is computed from the coordinate displacement using the metric
        at the reference geodesic sample. This is a finite-rollout diagnostic,
        not a symbolic Jacobi-field proof.
        """

        samples = np.asarray(parameter, dtype=float)
        reference = np.asarray(reference_states, dtype=float)
        neighboring = np.asarray(neighboring_states, dtype=float)
        if samples.ndim != 1:
            raise ValueError("parameter samples must be one-dimensional")
        if reference.shape != neighboring.shape:
            raise ValueError("reference and neighboring states must have the same shape")
        if reference.ndim != 2 or reference.shape[0] != len(samples):
            raise ValueError("states must have shape (sample, state)")
        if reference.shape[1] < self.dimension:
            raise ValueError("states must include the metric coordinates")
        if len(samples) < 2:
            raise ValueError("geodesic deviation needs at least two samples")
        if np.any(np.diff(samples) <= 0.0):
            raise ValueError("parameter samples must be strictly increasing")

        reference_coordinates = reference[:, : self.dimension]
        neighboring_coordinates = neighboring[:, : self.dimension]
        coordinate_delta = neighboring_coordinates - reference_coordinates
        metric_values = list(self.metric)
        metric_function = sp.lambdify(
            (*self.coordinates, *(self.parameters or ())),
            metric_values,
            modules="numpy",
        )
        parameter_args = [
            float((parameter_values or {})[symbol.name])
            for symbol in (self.parameters or ())
        ]
        raw_values = metric_function(
            *(reference_coordinates[:, axis] for axis in range(self.dimension)),
            *parameter_args,
        )
        components = [
            np.broadcast_to(np.asarray(value, dtype=float), (len(samples),))
            for value in raw_values
        ]
        metric_samples = np.stack(components, axis=1).reshape(
            len(samples),
            self.dimension,
            self.dimension,
        )
        signed_squared = np.einsum(
            "ni,nij,nj->n",
            coordinate_delta,
            metric_samples,
            coordinate_delta,
        )
        if np.any(signed_squared < -1e-12):
            raise ValueError("metric separation became timelike/negative")
        separation = np.sqrt(np.maximum(signed_squared, 0.0))
        initial = float(separation[0])
        if initial <= 0.0:
            raise ValueError("nearby geodesics must start with positive separation")
        relative = separation / initial
        min_index = int(np.argmin(relative))
        max_index = int(np.argmax(relative))
        return {
            "kind": "geodesic-deviation",
            "rendererHint": "geodesic-deviation",
            "coordinates": [symbol.name for symbol in self.coordinates],
            "parameter": samples.astype(float).tolist(),
            "separation": separation.astype(float).tolist(),
            "relativeSeparation": relative.astype(float).tolist(),
            "initialSeparation": initial,
            "finalSeparation": float(separation[-1]),
            "minRelativeSeparation": float(relative[min_index]),
            "maxRelativeSeparation": float(relative[max_index]),
            "minParameter": float(samples[min_index]),
            "maxParameter": float(samples[max_index]),
            "coordinateDelta": coordinate_delta.astype(float).tolist(),
            "signedSquaredSeparation": signed_squared.astype(float).tolist(),
            "evaluation": "measured-nearby-geodesic-rollout",
            "rigor": "measured",
            "note": "Measured rollout diagnostic only; not a proof of geodesic deviation.",
        }

    def oriented_angle_2d(
        self,
        point: Sequence[float],
        initial_vector: Sequence[float],
        final_vector: Sequence[float],
        *,
        parameter_values: dict[str, float] | None = None,
    ) -> float:
        """Oriented angle from ``initial_vector`` to ``final_vector`` in 2D."""

        if self.dimension != 2:
            raise ValueError("oriented angles require a two-dimensional metric")
        point_array = np.asarray(point, dtype=float)
        initial = np.asarray(initial_vector, dtype=float)
        final = np.asarray(final_vector, dtype=float)
        if point_array.shape != (2,) or initial.shape != (2,) or final.shape != (2,):
            raise ValueError("point and vectors must be two-dimensional")
        metric_func = sp.lambdify(
            (*self.coordinates, *(self.parameters or ())),
            list(self.metric),
            modules="numpy",
        )
        parameter_args = [
            float((parameter_values or {})[symbol.name])
            for symbol in (self.parameters or ())
        ]
        metric = np.asarray(metric_func(*point_array, *parameter_args), dtype=float).reshape(2, 2)
        inner = float(initial @ metric @ final)
        area = float(np.sqrt(abs(np.linalg.det(metric))) * (initial[0] * final[1] - initial[1] * final[0]))
        return float(np.arctan2(area, inner))


def schwarzschild_equatorial_metric(
    schwarzschild_radius: sp.Expr | float | None = None,
) -> MetricGeometry:
    """Equatorial-plane Schwarzschild metric in coordinates ``(t, r, phi)``.

    ``ds^2 = -(1 - rs/r) dt^2 + dr^2 / (1 - rs/r) + r^2 dphi^2``
    with geometrized units ``G = c = 1`` and ``theta = pi/2`` fixed by the
    spherical symmetry.
    """

    rs = (
        sp.Symbol("r_s", positive=True)
        if schwarzschild_radius is None
        else schwarzschild_radius
    )
    t = sp.Symbol("t", real=True)
    r = sp.Symbol("r", positive=True)
    phi = sp.Symbol("phi", real=True)
    factor = 1 - rs / r
    return MetricGeometry(
        coordinates=(t, r, phi),
        metric=sp.diag(-factor, 1 / factor, r**2),
        parameters=(rs,) if isinstance(rs, sp.Symbol) else (),
    )


def schwarzschild_metric(
    schwarzschild_radius: sp.Expr | float | None = None,
) -> MetricGeometry:
    """Full Schwarzschild metric in coordinates ``(t, r, theta, phi)``.

    ``ds^2 = -(1 - rs/r) dt^2 + dr^2 / (1 - rs/r)
    + r^2 (dtheta^2 + sin(theta)^2 dphi^2)`` in geometrized units
    ``G = c = 1``. Unlike :func:`schwarzschild_equatorial_metric` this keeps the
    full 2-sphere factor, so it is Ricci-flat and its curvature invariant is the
    vacuum Kretschmann scalar ``12 rs^2 / r^6``.
    """

    rs = (
        sp.Symbol("r_s", positive=True)
        if schwarzschild_radius is None
        else schwarzschild_radius
    )
    t = sp.Symbol("t", real=True)
    r = sp.Symbol("r", positive=True)
    theta = sp.Symbol("theta", real=True)
    phi = sp.Symbol("phi", real=True)
    factor = 1 - rs / r
    return MetricGeometry(
        coordinates=(t, r, theta, phi),
        metric=sp.diag(-factor, 1 / factor, r**2, r**2 * sp.sin(theta) ** 2),
        parameters=(rs,) if isinstance(rs, sp.Symbol) else (),
    )


def two_sphere_metric(radius: sp.Expr | float | None = None) -> MetricGeometry:
    """Round-sphere metric ``ds^2 = R^2 (dtheta^2 + sin(theta)^2 dphi^2)``."""

    radius_value = sp.Symbol("R", positive=True) if radius is None else radius
    theta = sp.Symbol("theta", real=True)
    phi = sp.Symbol("phi", real=True)
    return MetricGeometry(
        coordinates=(theta, phi),
        metric=sp.diag(radius_value**2, radius_value**2 * sp.sin(theta) ** 2),
        parameters=(radius_value,) if isinstance(radius_value, sp.Symbol) else (),
    )


__all__ = [
    "MetricGeometry",
    "schwarzschild_equatorial_metric",
    "schwarzschild_metric",
    "two_sphere_metric",
]
