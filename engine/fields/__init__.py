"""Scalar and vector fields over space, with differential operators."""

from engine.fields.field_lines import integrate_field_lines, seeds_on_segment
from engine.fields.fields import (
    ScalarField,
    VectorField,
    curl,
    divergence,
    gradient,
    laplacian,
)

__all__ = [
    "ScalarField",
    "VectorField",
    "curl",
    "divergence",
    "gradient",
    "integrate_field_lines",
    "laplacian",
    "seeds_on_segment",
]
