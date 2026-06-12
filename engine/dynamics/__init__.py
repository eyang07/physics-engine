"""General dynamical-system helpers."""

from engine.dynamics.cotangent import CotangentHamiltonianSystem
from engine.dynamics.diagnostics import (
    InvariantResidual,
    LyapunovResult,
    PoincareSection,
    finite_time_lyapunov,
    invariant_residuals,
    poincare_section_crossings,
)
from engine.dynamics.first_order import FirstOrderSystem
from engine.dynamics.media import (
    InverseMetricMedium,
    RefractiveIndexMedium,
    ScalarSpeedMedium,
    gaussian_lens_speed,
)
from engine.dynamics.ray_bundle import (
    RayBundleResult,
    integrate_ray_bundle,
    ray_bundle_coordinate_bounds,
    ray_bundle_snapshot_indices,
)

__all__ = [
    "CotangentHamiltonianSystem",
    "FirstOrderSystem",
    "InvariantResidual",
    "InverseMetricMedium",
    "LyapunovResult",
    "PoincareSection",
    "RayBundleResult",
    "RefractiveIndexMedium",
    "ScalarSpeedMedium",
    "finite_time_lyapunov",
    "gaussian_lens_speed",
    "invariant_residuals",
    "integrate_ray_bundle",
    "poincare_section_crossings",
    "ray_bundle_coordinate_bounds",
    "ray_bundle_snapshot_indices",
]
