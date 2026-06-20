"""Scalar and vector fields over space, with differential operators."""

from engine.fields.diagnostics import (
    MEASURED_FIELD_NOTE,
    MeasuredFieldGrid,
    MeasuredFieldIntegral,
    MeasuredFieldLawCheck,
    gauss_flux_check,
    line_circulation,
    measured_curl_grid,
    measured_divergence_grid,
    planar_stokes_check,
    sphere_surface_quadrature,
    surface_flux,
)
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
    "MEASURED_FIELD_NOTE",
    "MeasuredFieldGrid",
    "MeasuredFieldIntegral",
    "MeasuredFieldLawCheck",
    "ScalarField",
    "VectorField",
    "curl",
    "divergence",
    "gauss_flux_check",
    "gradient",
    "integrate_field_lines",
    "line_circulation",
    "laplacian",
    "measured_curl_grid",
    "measured_divergence_grid",
    "planar_stokes_check",
    "seeds_on_segment",
    "sphere_surface_quadrature",
    "surface_flux",
]
