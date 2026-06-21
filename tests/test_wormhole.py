from __future__ import annotations

import json

import numpy as np
import pytest
import sympy as sp

from engine.export.manifest import system_entry
from scripts.example_specs import WORMHOLE
from scripts.generate_wormhole import generate_wormhole_trajectory, write_wormhole_trajectory
from systems.wormhole import (
    build_system,
    domain_assumptions,
    ellis_wormhole_metric,
    radial_throat_initial_state,
)


def _metric_norm(state: list[float], *, throat_radius: float) -> float:
    _t, ell, _phi, t_dot, ell_dot, phi_dot = state
    return -t_dot**2 + ell_dot**2 + (ell**2 + throat_radius**2) * phi_dot**2


def test_wormhole_system_uses_ellis_metric_geodesic_flow() -> None:
    system = build_system()
    assert tuple(symbol.name for symbol in system.state) == (
        "t",
        "l",
        "phi",
        "t_dot",
        "l_dot",
        "phi_dot",
    )

    geometry = ellis_wormhole_metric()
    _t, ell, _phi = geometry.coordinates
    (throat_radius,) = geometry.parameters
    gamma = geometry.christoffel_symbols()

    assert sp.simplify(gamma[1, 2, 2] + ell) == 0
    assert sp.simplify(gamma[2, 1, 2] - ell / (ell**2 + throat_radius**2)) == 0
    assert sp.simplify(gamma[2, 2, 1] - ell / (ell**2 + throat_radius**2)) == 0

    initial_state = radial_throat_initial_state()
    assert abs(_metric_norm(initial_state, throat_radius=1.0) + 1.0) < 1e-12


def test_wormhole_domain_rejects_nonpositive_throat() -> None:
    for invalid in (0.0, -1.0):
        with pytest.raises(ValueError, match="throat_radius must be positive"):
            domain_assumptions(throat_radius=invalid)


def test_wormhole_generator_rejects_invalid_throat() -> None:
    with pytest.raises(ValueError, match="throat_radius must be positive"):
        generate_wormhole_trajectory(throat_radius=0.0, t_span=(0.0, 0.2), dt=0.02)


def test_wormhole_exports_domain_assumptions() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 0.2), dt=0.02)
    domain = trajectory.metadata["domain"]

    assert domain["kind"] == "coordinate-domain"
    assert domain["background"] == "fixed-ellis-wormhole"
    assert domain["coordinates"] == ["t", "l", "phi"]
    assert domain["throatRadius"] == 1.0
    assert domain["radialCoordinateRange"] == "all-real"
    (constraint,) = domain["constraints"]
    assert constraint["quantity"] == "a"
    assert constraint["relation"] == "greater-than"
    assert constraint["value"] == 0.0


def test_wormhole_manifest_exposes_embedding_contract() -> None:
    entry = system_entry(WORMHOLE)
    geometry = entry["geometry"]

    assert entry["systemKind"] == "wormhole-geodesic"
    assert entry["domain"] == {
        "kind": "coordinate-domain",
        "source": "trajectory.metadata.domain",
    }
    assert {item["name"] for item in entry["conserved"]} == {"E", "L"}
    assert geometry["kind"] == "wormhole-geodesic"
    assert geometry["rendererHint"] == "wormhole-geodesic"
    assert geometry["embeddingMesh"]["source"] == (
        "trajectory.metadata.wormholeGeometry.embeddingMesh"
    )
    assert geometry["geodesic"]["source"] == "trajectory.metadata.wormholeGeometry.geodesic"
    assert geometry["diagnostics"]["throatTraversal"] == (
        "trajectory.metadata.diagnostics.throatTraversal"
    )
    assert geometry["diagnostics"]["geodesicDeviation"] == (
        "trajectory.metadata.diagnostics.geodesicDeviation"
    )


def test_wormhole_exports_throat_traversal_and_measured_invariants() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 32.0), dt=0.02)
    residuals = {
        record["name"]: record
        for record in trajectory.metadata["invariantResiduals"]
    }
    traversal = trajectory.metadata["diagnostics"]["throatTraversal"]
    deviation = trajectory.metadata["diagnostics"]["geodesicDeviation"]
    ell = trajectory.states[:, 1]

    assert trajectory.metadata["kind"] == "fixed-background"
    assert np.min(ell) < 0.0
    assert np.max(ell) > 0.0
    assert traversal["crossesThroat"] is True
    assert traversal["rigor"] == "measured"
    assert abs(traversal["crossingTime"] - 15.0) < 0.04
    assert {record["rigor"] for record in residuals.values()} == {"measured"}
    assert residuals["E"]["maxRelative"] < 1e-12
    assert residuals["L"]["maxAbs"] < 1e-12
    assert residuals["metricNorm"]["maxAbs"] < 1e-12
    assert deviation["kind"] == "geodesic-deviation"
    assert deviation["rigor"] == "measured"
    assert deviation["neighborInitialOffset"] == {"phi": 0.03}
    assert deviation["minRelativeSeparation"] < 0.2
    assert abs(deviation["minParameter"] - traversal["crossingTime"]) < 0.04


def test_wormhole_embedding_matches_surface_of_revolution() -> None:
    trajectory = generate_wormhole_trajectory(t_span=(0.0, 0.2), dt=0.02)
    positions = trajectory.states[:, 6:9]
    ell = trajectory.states[:, 1]
    x = positions[:, 0]
    y = positions[:, 1]
    z = positions[:, 2]
    geometry = trajectory.metadata["wormholeGeometry"]
    mesh = geometry["embeddingMesh"]

    assert np.allclose(x**2 + y**2, ell**2 + 1.0)
    assert np.allclose(z, np.arcsinh(ell))
    assert mesh["kind"] == "surface-mesh"
    assert mesh["rendererHint"] == "wormhole-geodesic"
    assert np.asarray(mesh["points"], dtype=float).shape == (73, 65, 3)
    assert np.asarray(mesh["triangles"], dtype=int).shape[1] == 3
    assert np.allclose(np.asarray(geometry["geodesic"]["points"], dtype=float), positions)


def test_wormhole_script_writes_primary_and_viewer_outputs(tmp_path) -> None:
    output = tmp_path / "data" / "wormhole.json"
    viewer_output = tmp_path / "viewer" / "wormhole.json"

    write_wormhole_trajectory(output, viewer_output=viewer_output)

    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        viewer_output.read_text(encoding="utf-8")
    )
