from __future__ import annotations

from typing import Sequence

import numpy as np
import sympy as sp

from engine.dynamics import FirstOrderSystem, MetricGeometry


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


system = build_system()


__all__ = [
    "build_system",
    "conserved_series",
    "domain_assumptions",
    "ellis_wormhole_metric",
    "embedding_xyz",
    "radial_throat_initial_state",
]
