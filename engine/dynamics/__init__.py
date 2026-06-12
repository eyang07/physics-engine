"""General dynamical-system helpers."""

from engine.dynamics.controlled import (
    Box,
    ControlledFirstOrderSystem,
    RolloutResult,
    rollout,
)
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
from engine.dynamics.metric import (
    MetricGeometry,
    schwarzschild_equatorial_metric,
    two_sphere_metric,
)
from engine.dynamics.ray_bundle import (
    RayBundleResult,
    integrate_ray_bundle,
    ray_bundle_coordinate_bounds,
    ray_bundle_snapshot_indices,
)
from engine.dynamics.ray_diagnostics import (
    caustic_proximity,
    ray_bundle_diagnostics,
    ray_spreading_factors,
    ray_travel_times,
    wavefront_envelope_records,
)
from engine.dynamics.safety import (
    BarrierCandidate,
    LyapunovCandidate,
    ObligationSample,
    ProofObligation,
    SafetySpecification,
    SublevelSet,
    TrajectorySafetyReport,
    UnsafeSetReport,
    grid_points,
    lie_derivative,
    sample_obligation,
)

__all__ = [
    "BarrierCandidate",
    "Box",
    "ControlledFirstOrderSystem",
    "CotangentHamiltonianSystem",
    "FirstOrderSystem",
    "InvariantResidual",
    "InverseMetricMedium",
    "LyapunovCandidate",
    "LyapunovResult",
    "MetricGeometry",
    "ObligationSample",
    "ProofObligation",
    "PoincareSection",
    "RayBundleResult",
    "RefractiveIndexMedium",
    "RolloutResult",
    "SafetySpecification",
    "ScalarSpeedMedium",
    "SublevelSet",
    "TrajectorySafetyReport",
    "UnsafeSetReport",
    "caustic_proximity",
    "finite_time_lyapunov",
    "gaussian_lens_speed",
    "grid_points",
    "invariant_residuals",
    "integrate_ray_bundle",
    "lie_derivative",
    "poincare_section_crossings",
    "ray_bundle_coordinate_bounds",
    "ray_bundle_diagnostics",
    "ray_bundle_snapshot_indices",
    "ray_spreading_factors",
    "ray_travel_times",
    "rollout",
    "sample_obligation",
    "schwarzschild_equatorial_metric",
    "two_sphere_metric",
    "wavefront_envelope_records",
]
