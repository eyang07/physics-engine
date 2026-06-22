from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem, MetricGeometry

WormholeGeodesicKind = Literal["timelike", "null"]


def ellis_wormhole_metric(throat_radius: sp.Expr | float | None = None) -> MetricGeometry:
    """Equatorial Ellis-wormhole fixed background.

    The chart is ``(t, l, phi)`` with geometrized metric
    ``ds^2 = -dt^2 + dl^2 + (l^2 + a^2) dphi^2``. This is a fixed background
    used for geodesic visualization only; no dynamical gravity is solved.
    """

    a = sp.Symbol("a", positive=True) if throat_radius is None else throat_radius
    t = sp.Symbol("t", real=True)
    ell = sp.Symbol("l", real=True)
    phi = sp.Symbol("phi", real=True)
    return MetricGeometry(
        coordinates=(t, ell, phi),
        metric=sp.diag(-1, 1, ell**2 + sp.sympify(a) ** 2),
        parameters=(a,) if isinstance(a, sp.Symbol) else (),
    )


def build_system(throat_radius: sp.Expr | float | None = None) -> FirstOrderSystem:
    return ellis_wormhole_metric(throat_radius).geodesic_system()


def embedding_xyz(states: Sequence[Sequence[float]], *, throat_radius: float) -> np.ndarray:
    """Embed the equatorial spatial slice as a surface of revolution."""

    state_array = np.asarray(states, dtype=float)
    ell = state_array[:, 1]
    phi = state_array[:, 2]
    rho = np.sqrt(ell**2 + throat_radius**2)
    z = throat_radius * np.arcsinh(ell / throat_radius)
    return np.column_stack([rho * np.cos(phi), rho * np.sin(phi), z])


def conserved_series(
    states: Sequence[Sequence[float]],
    *,
    throat_radius: float,
) -> dict[str, list[float]]:
    state_array = np.asarray(states, dtype=float)
    ell = state_array[:, 1]
    t_dot = state_array[:, 3]
    ell_dot = state_array[:, 4]
    phi_dot = state_array[:, 5]
    angular_momentum = (ell**2 + throat_radius**2) * phi_dot
    norm = -t_dot**2 + ell_dot**2 + (ell**2 + throat_radius**2) * phi_dot**2
    return {
        "E": t_dot.astype(float).tolist(),
        "L": angular_momentum.astype(float).tolist(),
        "metricNorm": norm.astype(float).tolist(),
    }


def radial_throat_initial_state(
    *,
    throat_radius: float = 1.0,
    start_l: float = -6.0,
    l_dot: float = 0.4,
) -> list[float]:
    del throat_radius
    return [0.0, start_l, 0.0, float(np.sqrt(1.0 + l_dot**2)), l_dot, 0.0]


def angular_reflected_initial_state(
    *,
    throat_radius: float = 1.0,
    start_l: float = -6.0,
    l_dot: float = 0.4,
    phi_dot: float = 0.04,
) -> list[float]:
    """Non-radial (``L != 0``) timelike state that reflects off the barrier.

    Angular momentum raises the throat barrier ``V_eff^2(0) = 1 + L^2/a^2`` above
    the conserved energy, so a geodesic launched inward from one mouth turns
    around at the centrifugal turning point ``l = -sqrt(L^2/(E^2-1) - a^2)``
    without ever reaching the throat — the reflected contrast to the radial
    traversing preset. The proper-time normalization fixes
    ``t_dot = sqrt(1 + l_dot^2 + (l^2 + a^2) phi_dot^2)`` so the conserved metric
    norm is ``-1``.
    """

    if throat_radius <= 0.0:
        raise ValueError("throat_radius must be positive")
    rho_squared = start_l**2 + throat_radius**2
    t_dot = float(np.sqrt(1.0 + l_dot**2 + rho_squared * phi_dot**2))
    return [0.0, float(start_l), 0.0, t_dot, float(l_dot), float(phi_dot)]


def domain_assumptions(*, throat_radius: float) -> dict[str, object]:
    """Fixed-background coordinate-domain assumptions for the Ellis chart.

    The proper radial coordinate ``l`` ranges over the whole real line with the
    throat at ``l = 0`` (proper radius ``a``); the chart stays regular as long as
    the throat radius is positive. No dynamical gravity is solved.
    """

    if throat_radius <= 0.0:
        raise ValueError("throat_radius must be positive")
    return {
        "kind": "coordinate-domain",
        "background": "fixed-ellis-wormhole",
        "chart": "equatorial",
        "coordinates": ["t", "l", "phi"],
        "constraints": [
            {
                "quantity": "a",
                "relation": "greater-than",
                "value": 0.0,
                "description": (
                    "throat radius must be positive to keep the proper-radius chart regular"
                ),
            }
        ],
        "throatRadius": float(throat_radius),
        "radialCoordinateRange": "all-real",
        "note": (
            "Fixed Ellis-wormhole background; the proper radial coordinate l ranges "
            "over the whole real line with the throat at l = 0 (proper radius a)."
        ),
    }


def _epsilon(kind: WormholeGeodesicKind) -> float:
    if kind == "timelike":
        return 1.0
    if kind == "null":
        return 0.0
    raise ValueError(f"unknown wormhole geodesic kind: {kind!r}")


def geodesic_kind_from_norm(metric_norm: float) -> WormholeGeodesicKind:
    """Classify a geodesic as timelike or null from its conserved metric norm.

    With the affine normalization used here the conserved norm
    ``-t_dot^2 + l_dot^2 + (l^2 + a^2) phi_dot^2`` equals ``-epsilon``: ``-1`` for
    a proper-time timelike geodesic and ``0`` for a null one.
    """

    if metric_norm < -0.5:
        return "timelike"
    if abs(metric_norm) <= 0.5:
        return "null"
    raise ValueError(
        f"metric norm {metric_norm:.6g} is neither timelike (~-1) nor null (~0)"
    )


def conserved_constants(
    state: Sequence[float],
    *,
    throat_radius: float,
) -> tuple[float, float]:
    """Specific energy ``E`` and angular momentum ``L`` of an Ellis geodesic.

    The Ellis chart is static and axisymmetric, so ``E = t_dot`` (from
    ``g_tt = -1``) and ``L = (l^2 + a^2) phi_dot`` are conserved along the flow.
    """

    if throat_radius <= 0.0:
        raise ValueError("throat_radius must be positive")
    _t, ell, _phi, t_dot, _ell_dot, phi_dot = state
    energy = float(t_dot)
    angular_momentum = float((ell**2 + throat_radius**2) * phi_dot)
    return energy, angular_momentum


def radial_effective_potential_values(
    l_values: Sequence[float],
    *,
    throat_radius: float,
    angular_momentum: float,
    kind: WormholeGeodesicKind = "timelike",
) -> np.ndarray:
    """Squared radial effective potential ``V_eff^2(l) = epsilon + L^2/(l^2 + a^2)``.

    Reducing the geodesic with the conserved ``E`` and ``L`` gives the radial
    energy equation ``l_dot^2 = E^2 - V_eff^2(l)``; motion is allowed where
    ``E^2 >= V_eff^2``. The centrifugal term peaks at the throat (``l = 0``),
    forming the barrier ``epsilon + L^2/a^2`` a geodesic must clear to traverse.
    """

    if throat_radius <= 0.0:
        raise ValueError("throat_radius must be positive")
    epsilon = _epsilon(kind)
    ell = np.asarray(l_values, dtype=float)
    return epsilon + angular_momentum**2 / (ell**2 + throat_radius**2)


def radial_throat_barrier(
    *,
    throat_radius: float,
    angular_momentum: float,
    kind: WormholeGeodesicKind = "timelike",
) -> float:
    """Squared effective potential at the throat ``l = 0`` (the barrier height)."""

    if throat_radius <= 0.0:
        raise ValueError("throat_radius must be positive")
    return _epsilon(kind) + angular_momentum**2 / throat_radius**2


def radial_turning_points(
    *,
    throat_radius: float,
    energy: float,
    angular_momentum: float,
    kind: WormholeGeodesicKind = "timelike",
) -> tuple[float, ...]:
    """Radial turning points ``l`` where ``E^2 = V_eff^2(l)`` (``l_dot = 0``).

    A reflected geodesic has the symmetric pair ``+/- sqrt(L^2/(E^2-epsilon) -
    a^2)``; a traversing one clears the throat barrier and has none.
    """

    if throat_radius <= 0.0:
        raise ValueError("throat_radius must be positive")
    epsilon = _epsilon(kind)
    denominator = energy**2 - epsilon
    if abs(angular_momentum) < 1e-12 or denominator <= 1e-12:
        return ()
    l_squared = angular_momentum**2 / denominator - throat_radius**2
    if l_squared <= 1e-12:
        return ()
    root = float(np.sqrt(l_squared))
    return (-root, root)


@dataclass(frozen=True)
class WormholeRadialReduction:
    """Effective-potential turning-point summary for an Ellis radial geodesic."""

    classification: str
    energy: float
    angular_momentum: float
    throat_barrier: float
    turning_points: tuple[float, ...]
    kind: WormholeGeodesicKind = "timelike"
    family: str = "ellis-wormhole"
    coordinate: str = "l"
    evaluation: str = "analytic-ellis-effective-potential"

    def __post_init__(self) -> None:
        if not self.classification:
            raise ValueError("classification must be non-empty")
        if not np.isfinite(self.energy) or not np.isfinite(self.angular_momentum):
            raise ValueError("energy and angular momentum must be finite")
        if not np.isfinite(self.throat_barrier):
            raise ValueError("throat barrier must be finite")
        if any(not np.isfinite(point) for point in self.turning_points):
            raise ValueError("turning points must be finite")
        object.__setattr__(
            self,
            "turning_points",
            tuple(float(point) for point in self.turning_points),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "classification": self.classification,
            "kind": self.kind,
            "coordinate": self.coordinate,
            "energy": self.energy,
            "angularMomentum": self.angular_momentum,
            "throatBarrier": self.throat_barrier,
            "turningPoints": list(self.turning_points),
            "evaluation": self.evaluation,
        }


def classify_radial_geodesic(
    *,
    throat_radius: float,
    energy: float,
    angular_momentum: float,
    kind: WormholeGeodesicKind = "timelike",
    tolerance: float = 1e-9,
) -> WormholeRadialReduction:
    """Qualitative bound/traversing class from the radial effective potential.

    Comparing the conserved ``E^2`` with the throat barrier ``V_eff^2(0)`` gives a
    qualitative readout: ``traversing`` clears the barrier and crosses the throat,
    ``reflected`` turns around at the centrifugal barrier, and ``marginal`` is the
    measure-zero edge that asymptotes to the throat.
    """

    barrier = radial_throat_barrier(
        throat_radius=throat_radius,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    turning_points = radial_turning_points(
        throat_radius=throat_radius,
        energy=energy,
        angular_momentum=angular_momentum,
        kind=kind,
    )
    energy_squared = energy**2
    scale = max(abs(barrier), 1.0)
    if energy_squared > barrier + tolerance * scale:
        classification = "traversing"
    elif energy_squared < barrier - tolerance * scale:
        classification = "reflected"
    else:
        classification = "marginal"
    return WormholeRadialReduction(
        classification=classification,
        energy=float(energy),
        angular_momentum=float(angular_momentum),
        throat_barrier=float(barrier),
        turning_points=turning_points,
        kind=kind,
    )


system = build_system()


__all__ = [
    "WormholeGeodesicKind",
    "WormholeRadialReduction",
    "angular_reflected_initial_state",
    "build_system",
    "classify_radial_geodesic",
    "conserved_constants",
    "conserved_series",
    "domain_assumptions",
    "ellis_wormhole_metric",
    "embedding_xyz",
    "geodesic_kind_from_norm",
    "radial_effective_potential_values",
    "radial_throat_barrier",
    "radial_throat_initial_state",
    "radial_turning_points",
]
