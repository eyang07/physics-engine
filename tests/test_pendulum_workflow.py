import json

import numpy as np
import sympy as sp

from scripts.generate_pendulum import generate_pendulum_trajectory, write_pendulum_trajectory
from systems.pendulum import build_system


def test_pendulum_euler_lagrange_equation():
    m, ell, g = sp.symbols("m ell g")
    system = build_system(mass=m, length=ell, gravity=g)
    (theta,) = system.q
    (theta_ddot,) = system.qddot

    (equation,) = system.euler_lagrange_equations()
    expected = m * ell**2 * theta_ddot + m * g * ell * sp.sin(theta)

    assert sp.simplify(equation.lhs - expected) == 0


def test_generated_pendulum_trajectory_has_small_energy_drift():
    trajectory = generate_pendulum_trajectory(t_span=(0.0, 8.0), dt=0.01)
    theta = trajectory.states[:, 0]
    theta_dot = trajectory.states[:, 1]
    energy = 0.5 * theta_dot**2 + 9.81 * (1 - np.cos(theta))

    assert trajectory.state_names == ("theta", "theta_dot")
    assert np.max(np.abs(energy - energy[0])) < 1e-7


def test_pendulum_exports_certificate_series_for_linked_verification_problem():
    trajectory = generate_pendulum_trajectory(t_span=(0.0, 0.05), dt=0.01)
    assert trajectory.series is not None
    assert trajectory.metadata is not None

    value_series = trajectory.series["certificate_energy_barrier_value"]
    derivative_series = trajectory.series["certificate_energy_barrier_flow_derivative"]
    assert np.asarray(value_series, dtype=float).shape == trajectory.time.shape
    assert np.asarray(derivative_series, dtype=float).shape == trajectory.time.shape

    records = trajectory.metadata["certificateSeries"]
    records_by_kind = {record["kind"]: record for record in records}
    assert set(records_by_kind) == {"candidate-value", "flow-derivative"}

    value_record = records_by_kind["candidate-value"]
    assert value_record["problemId"] == "upright-pendulum-safety"
    assert value_record["candidateId"] == "energy-barrier"
    assert value_record["series"] == "certificate_energy_barrier_value"
    assert value_record["rigor"] == "measured"
    assert value_record["obligationIds"] == [
        "energy-barrier-initial-containment",
        "energy-barrier-excludes-near-bottom",
    ]
    assert {baseline["comparison"] for baseline in value_record["comparisonBaselines"]} == {
        "<=",
        ">",
    }

    derivative_record = records_by_kind["flow-derivative"]
    assert derivative_record["series"] == "certificate_energy_barrier_flow_derivative"
    assert derivative_record["obligationIds"] == ["energy-barrier-non-increase"]
    assert derivative_record["comparisonBaselines"] == [
        {
            "obligationId": "energy-barrier-non-increase",
            "comparison": "<=",
            "rhs": 0.0,
            "regionId": "domain-energy-barrier-region",
        }
    ]


def test_generate_pendulum_script_writes_primary_and_viewer_outputs(tmp_path):
    output = tmp_path / "data" / "pendulum.json"
    viewer_output = tmp_path / "viewer" / "public" / "data" / "pendulum.json"

    trajectory = write_pendulum_trajectory(
        output,
        viewer_output=viewer_output,
        t_end=0.05,
        dt=0.01,
    )

    assert output.exists()
    assert viewer_output.exists()
    assert json.loads(output.read_text(encoding="utf-8")) == json.loads(
        viewer_output.read_text(encoding="utf-8")
    )
    assert len(trajectory.time) == 6
