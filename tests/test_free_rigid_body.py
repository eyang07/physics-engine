from __future__ import annotations

from pathlib import Path

import numpy as np
import sympy as sp

from engine.export.manifest import system_entry
from engine.mechanics import (
    InertiaTensor,
    angular_momentum_magnitude,
    euler_equations_rhs,
    quaternion_to_rotation_matrix,
    rotational_kinetic_energy,
)
from engine.numerics import integrate_adaptive
from scripts.example_specs import FREE_RIGID_BODY
from scripts.generate_free_rigid_body import (
    DEFAULT_MOMENTS,
    generate_free_rigid_body_trajectory,
    rigid_body_geometry,
    write_free_rigid_body_trajectory,
)
from systems.free_rigid_body import (
    angular_momentum_magnitude as symbolic_angular_momentum_magnitude,
    build_system,
    rotational_energy,
)


def test_free_rigid_body_symbolic_system_uses_euler_equations() -> None:
    system = build_system()
    omega_1, omega_2, omega_3 = system.state
    i1, i2, i3 = system.parameters

    assert system.rhs == (
        (i2 - i3) * omega_2 * omega_3 / i1,
        (i3 - i1) * omega_3 * omega_1 / i2,
        (i1 - i2) * omega_1 * omega_2 / i3,
    )
    assert sp.simplify(rotational_energy(system) - FREE_RIGID_BODY.conserved[0].expression_for(system)) == 0
    assert (
        sp.simplify(
            symbolic_angular_momentum_magnitude(system)
            - FREE_RIGID_BODY.conserved[1].expression_for(system)
        )
        == 0
    )


def test_intermediate_axis_is_unstable_while_extreme_axes_stay_measured_stable() -> None:
    inertia = InertiaTensor.diagonal(DEFAULT_MOMENTS)

    def rollout(initial: list[float]) -> np.ndarray:
        _time, states = integrate_adaptive(
            euler_equations_rhs(inertia),
            initial_state=initial,
            t_span=(0.0, 24.0),
            sample_dt=0.02,
            rtol=1e-11,
            atol=1e-13,
            max_step=0.02,
        )
        return states

    axis_1 = rollout([1.0, 0.02, 0.02])
    axis_2 = rollout([0.02, 1.0, 0.02])
    axis_3 = rollout([0.02, 0.02, 1.0])

    assert np.linalg.norm(axis_1[:, 1:3], axis=1).max() < 0.05
    assert np.linalg.norm(axis_3[:, :2], axis=1).max() < 0.05
    assert np.linalg.norm(axis_2[:, [0, 2]], axis=1).max() > 1.0


def test_generated_free_rigid_body_exports_measured_invariants_and_geometry() -> None:
    trajectory = generate_free_rigid_body_trajectory(t_span=(0.0, 6.0), sample_dt=0.02)

    assert trajectory.state_names == ("omega_1", "omega_2", "omega_3")
    assert trajectory.series is not None
    assert set(trajectory.series) == {"H", "L"}
    assert trajectory.metadata is not None
    residuals = trajectory.metadata["invariantResiduals"]
    assert {record["rigor"] for record in residuals} == {"measured"}
    assert {record["name"] for record in residuals} == {"H", "L"}
    assert max(record["maxRelative"] for record in residuals) < 1e-9

    geometry = trajectory.metadata["rigidBodyGeometry"]
    assert geometry["kind"] == "rigid-body-polhode"
    assert geometry["rigor"] == "measured"
    assert geometry["angularMomentumSphere"]["space"] == "body-angular-momentum"
    assert geometry["energyEllipsoid"]["space"] == "body-angular-momentum"
    assert geometry["polhode"]["space"] == "body-angular-velocity"
    assert np.asarray(geometry["polhode"]["points"], dtype=float).shape == trajectory.states.shape

    inertia = InertiaTensor.diagonal(DEFAULT_MOMENTS)
    expected_energy = rotational_kinetic_energy(inertia, trajectory.states[0])
    expected_momentum = angular_momentum_magnitude(inertia, trajectory.states[0])
    assert np.isclose(geometry["angularMomentumSphere"]["radius"], expected_momentum)
    assert np.allclose(
        geometry["energyEllipsoid"]["semiAxes"],
        np.sqrt(2.0 * expected_energy * np.asarray(DEFAULT_MOMENTS, dtype=float)),
    )


def test_manifest_entry_carries_rigid_body_geometry_contract() -> None:
    entry = system_entry(FREE_RIGID_BODY)

    assert entry["systemKind"] == "first-order-flow"
    assert entry["geometry"]["kind"] == "rigid-body-polhode"
    assert entry["geometry"]["rendererHint"] == "rigid-body-polhode"
    assert entry["geometry"]["polhode"]["source"] == "trajectory.metadata.rigidBodyGeometry.polhode"
    assert entry["lenses"] == ["freeRigidBodyPolhode"]
    assert entry["orientation"]["rendererHint"] == "rigid-body"
    assert entry["orientation"]["convention"] == "quaternion-wxyz"
    assert entry["orientation"]["source"] == "trajectory.orientation"


def test_generated_free_rigid_body_exports_integrated_orientation() -> None:
    trajectory = generate_free_rigid_body_trajectory(t_span=(0.0, 6.0), sample_dt=0.02)

    # The exported state stays the angular velocity; orientation is separate.
    assert trajectory.state_names == ("omega_1", "omega_2", "omega_3")
    orientation = trajectory.orientation
    assert orientation is not None
    assert orientation["convention"] == "quaternion-wxyz"
    quaternions = np.asarray(orientation["quaternion"], dtype=float)
    assert quaternions.shape == (trajectory.states.shape[0], 4)
    assert np.allclose(np.linalg.norm(quaternions, axis=1), 1.0)

    # Torque-free: space-frame angular momentum R(t) I omega(t) is constant.
    inertia = InertiaTensor.diagonal(DEFAULT_MOMENTS)
    space_momentum = np.array(
        [
            quaternion_to_rotation_matrix(q) @ (inertia.matrix @ w)
            for q, w in zip(quaternions, trajectory.states)
        ]
    )
    drift = float(np.max(np.linalg.norm(space_momentum - space_momentum[0], axis=1)))
    assert drift < 1e-9

    assert "orientation" in trajectory.to_dict()


def test_free_rigid_body_writer_outputs_json(tmp_path: Path) -> None:
    output = tmp_path / "free_rigid_body.json"
    viewer_output = tmp_path / "viewer" / "free_rigid_body.json"

    trajectory = write_free_rigid_body_trajectory(
        output,
        viewer_output=viewer_output,
        t_end=0.2,
        sample_dt=0.02,
    )

    assert output.exists()
    assert viewer_output.exists()
    payload = trajectory.to_dict()
    assert payload["metadata"]["rendererHints"]["kind"] == "rigid-body-polhode"
    assert payload["metadata"]["rigidBodyGeometry"]["polhode"]["points"]


def test_rigid_body_geometry_rejects_non_principal_inertia() -> None:
    inertia = InertiaTensor(np.array([[1.0, 0.1, 0.0], [0.1, 2.0, 0.0], [0.0, 0.0, 3.0]]))

    try:
        rigid_body_geometry(inertia, np.zeros((2, 3)))
    except ValueError as error:
        assert "principal-axis" in str(error)
    else:
        raise AssertionError("expected non-principal inertia to be rejected")
