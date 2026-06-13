"""General dynamical-system helpers."""

from engine.dynamics.candidates import (
    MeasuredInfimum,
    barrier_from_lyapunov,
    measured_infimum_over_set,
    quadratic_lyapunov_from_linearization,
)
from engine.dynamics.controlled import (
    Box,
    ControlledFirstOrderSystem,
    RolloutResult,
    rollout,
)
from engine.dynamics.cotangent import CotangentHamiltonianSystem
from engine.dynamics.discrete import (
    ControlledDiscreteSystem,
    DiscreteRolloutResult,
    DiscreteSystem,
    discrete_rollout,
    euler_discretization,
)
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
    EventEntryReport,
    LyapunovCandidate,
    ObligationSample,
    ProofObligation,
    SafetySpecification,
    SublevelSet,
    TrajectorySafetyReport,
    UnsafeEntryEvent,
    UnsafeSetReport,
    discrete_difference,
    grid_points,
    lie_derivative,
    sample_obligation,
)

__all__ = [
    "BarrierCandidate",
    "Box",
    "ControlledDiscreteSystem",
    "ControlledFirstOrderSystem",
    "CotangentHamiltonianSystem",
    "DiscreteRolloutResult",
    "DiscreteSystem",
    "EventEntryReport",
    "FirstOrderSystem",
    "InvariantResidual",
    "InverseMetricMedium",
    "LyapunovCandidate",
    "LyapunovResult",
    "MeasuredInfimum",
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
    "UnsafeEntryEvent",
    "UnsafeSetReport",
    "barrier_from_lyapunov",
    "caustic_proximity",
    "discrete_difference",
    "discrete_rollout",
    "euler_discretization",
    "finite_time_lyapunov",
    "gaussian_lens_speed",
    "grid_points",
    "invariant_residuals",
    "integrate_ray_bundle",
    "lie_derivative",
    "measured_infimum_over_set",
    "poincare_section_crossings",
    "quadratic_lyapunov_from_linearization",
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
