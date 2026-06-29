"""Special-relativity primitives.

Phase 1 of the backend physics roadmap (``BACKEND_PHYSICS_ROADMAP.md``). The
single global signature convention lives here and is reused by every later
relativity and electrodynamics module.
"""

from __future__ import annotations

from engine.relativity.four_vectors import (
    CONTRAVARIANT,
    COVARIANT,
    FourVector,
)
from engine.relativity.lorentz import (
    LorentzTransform,
    boost_along_axis,
    boost_from_rapidity,
    boost_from_velocity,
    rapidity_from_velocity,
    spatial_rotation,
    velocity_addition,
    velocity_from_rapidity,
)
from engine.relativity.minkowski import (
    SIGNATURE,
    SIGNATURE_NAME,
    MinkowskiMetric,
    minkowski_eta,
)
from engine.relativity.worldline import ProperTimeWorldline

__all__ = [
    "CONTRAVARIANT",
    "COVARIANT",
    "FourVector",
    "LorentzTransform",
    "boost_along_axis",
    "boost_from_rapidity",
    "boost_from_velocity",
    "rapidity_from_velocity",
    "spatial_rotation",
    "velocity_addition",
    "velocity_from_rapidity",
    "SIGNATURE",
    "SIGNATURE_NAME",
    "MinkowskiMetric",
    "minkowski_eta",
    "ProperTimeWorldline",
]
