from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import numpy as np

from engine.export import Trajectory
from engine.mechanics import orientation_series, rotation_matrix_to_quaternion
from scripts.example_specs import SYMMETRIC_TOP
from scripts.generation import (
    generate_lagrangian_trajectory,
    potential_plot_metadata,
    write_trajectory_outputs,
)
from systems.symmetric_top import build_system


DEFAULTS = {
    "I1": 1.0,
    "I3": 0.5,
    "M": 1.0,
    "g": 9.81,
    "ell": 0.5,
}
INITIAL = {
    "theta0": 0.4,
    "phi0": 0.0,
    "psi0": 0.0,
    "theta_dot0": 0.0,
    "phi_dot0": 0.0,
    "psi_dot0": 10.0,
}
STATE_NAMES = [
    "theta",
    "phi",
    "psi",
    "theta_dot",
    "phi_dot",
    "psi_dot",
    "x",
    "y",
    "z",
]


def _zxz_rotation(theta: float, phi: float, psi: float) -> np.ndarray:
    """Return the z-x-z Euler rotation ``Rz(phi) Rx(theta) Rz(psi)``."""

    cphi, sphi = np.cos(phi), np.sin(phi)
    cth, sth = np.cos(theta), np.sin(theta)
    cpsi, spsi = np.cos(psi), np.sin(psi)
    rz_phi = np.array([[cphi, -sphi, 0.0], [sphi, cphi, 0.0], [0.0, 0.0, 1.0]])
    rx_theta = np.array([[1.0, 0.0, 0.0], [0.0, cth, -sth], [0.0, sth, cth]])
    rz_psi = np.array([[cpsi, -spsi, 0.0], [spsi, cpsi, 0.0], [0.0, 0.0, 1.0]])
    return rz_phi @ rx_theta @ rz_psi


def symmetric_top_quaternions(
    theta: np.ndarray, phi: np.ndarray, psi: np.ndarray
) -> np.ndarray:
    """Return the per-sample body quaternion from the z-x-z Euler angles."""

    return np.array(
        [
            rotation_matrix_to_quaternion(_zxz_rotation(t, p, s))
            for t, p, s in zip(theta, phi, psi)
        ],
        dtype=float,
    )


def embed_symmetry_axis(ell: float, theta: np.ndarray, phi: np.ndarray) -> np.ndarray:
    """Return the figure-axis (body 3-axis) tip on the sphere of radius ``ell``.

    Matches the third column of the z-x-z rotation so the embedded tip and the
    exported orientation agree: ``e3 = (sinθ sinφ, -sinθ cosφ, cosθ)``.
    """

    radial = ell * np.sin(theta)
    return np.column_stack(
        [
            radial * np.sin(phi),
            -radial * np.cos(phi),
            ell * np.cos(theta),
        ]
    )


def symmetric_top_renderer_hints(ell: float) -> dict[str, object]:
    return {
        "bounds": {"x": [-ell, ell], "y": [-ell, ell], "z": [-ell, ell]},
        "camera": {
            "position": [2.4 * ell, 1.6 * ell, 2.6 * ell],
            "target": [0.0, 0.0, 0.0],
        },
        "referenceGeometry": [
            {
                "kind": "rotationAxis",
                "start": [0.0, 0.0, -1.25 * ell],
                "end": [0.0, 0.0, 1.25 * ell],
            }
        ],
    }


def effective_potential_values(
    *,
    theta_values: np.ndarray,
    p_phi: float,
    p_psi: float,
    transverse_moment: float,
    mass: float,
    gravity: float,
    pivot_distance: float,
) -> np.ndarray:
    centrifugal = (p_phi - p_psi * np.cos(theta_values)) ** 2 / (
        2.0 * transverse_moment * np.sin(theta_values) ** 2
    )
    return centrifugal + mass * gravity * pivot_distance * np.cos(theta_values)


def generate_symmetric_top_trajectory(
    *,
    moments: tuple[float, float] = (DEFAULTS["I1"], DEFAULTS["I3"]),
    mass: float = DEFAULTS["M"],
    gravity: float = DEFAULTS["g"],
    pivot_distance: float = DEFAULTS["ell"],
    initial: Sequence[float] | None = None,
    t_span: tuple[float, float] = (0.0, 8.0),
    dt: float = 0.002,
) -> Trajectory:
    transverse_moment, axial_moment = moments
    if initial is None:
        initial = [
            INITIAL["theta0"],
            INITIAL["phi0"],
            INITIAL["psi0"],
            INITIAL["theta_dot0"],
            INITIAL["phi_dot0"],
            INITIAL["psi_dot0"],
        ]
    system = build_system(
        transverse_moment=transverse_moment,
        axial_moment=axial_moment,
        mass=mass,
        gravity=gravity,
        pivot_distance=pivot_distance,
    )
    physical_parameters = {
        "I1": transverse_moment,
        "I3": axial_moment,
        "M": mass,
        "g": gravity,
        "ell": pivot_distance,
    }

    theta0, _phi0, _psi0, theta_dot0, phi_dot0, psi_dot0 = initial
    spin0 = psi_dot0 + phi_dot0 * np.cos(theta0)
    p_phi = transverse_moment * phi_dot0 * np.sin(theta0) ** 2 + axial_moment * spin0 * np.cos(theta0)
    p_psi = axial_moment * spin0

    trajectory = generate_lagrangian_trajectory(
        spec=SYMMETRIC_TOP,
        system=system,
        initial_state=list(initial),
        t_span=t_span,
        dt=dt,
        state_names=STATE_NAMES,
        physical_parameters=physical_parameters,
        metadata={
            "system": "symmetric_top",
            "configuration": "precession-and-nutation",
            "conservedMomenta": {"p_phi": float(p_phi), "p_psi": float(p_psi)},
            "rendererHints": symmetric_top_renderer_hints(pivot_distance),
        },
        state_transform=lambda time, states: np.column_stack(
            [states, embed_symmetry_axis(pivot_distance, states[:, 0], states[:, 1])]
        ),
    )
    assert trajectory.series is not None

    theta_grid = np.linspace(0.05, np.pi - 0.05, 360)
    potential_values = effective_potential_values(
        theta_values=theta_grid,
        p_phi=float(p_phi),
        p_psi=float(p_psi),
        transverse_moment=transverse_moment,
        mass=mass,
        gravity=gravity,
        pivot_distance=pivot_distance,
    )
    metadata = dict(trajectory.metadata or {})
    metadata["potentialPlots"] = [
        potential_plot_metadata(
            name="symmetric_top_potential",
            coordinate="theta",
            coordinate_latex=r"\theta",
            coordinate_values=theta_grid,
            potential_values=potential_values,
            energy_series=trajectory.series["H"],
        )
    ]
    metadata.setdefault("rendererHints", {})["orientation"] = "trajectory.orientation"
    quaternions = symmetric_top_quaternions(
        trajectory.states[:, 0],
        trajectory.states[:, 1],
        trajectory.states[:, 2],
    )
    return Trajectory.from_arrays(
        time=trajectory.time,
        states=trajectory.states,
        state_names=trajectory.state_names,
        metadata=metadata,
        series=trajectory.series,
        orientation=orientation_series(quaternions),
    )


def write_symmetric_top_trajectory(
    output: Path,
    *,
    viewer_output: Path | None = None,
) -> Trajectory:
    trajectory = generate_symmetric_top_trajectory()
    return write_trajectory_outputs(trajectory, output, viewer_output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate heavy symmetric-top data.")
    parser.add_argument("--output", type=Path, default=Path("data/generated/symmetric_top.json"))
    parser.add_argument("--viewer-output", type=Path, default=Path("viewer/public/data/symmetric_top.json"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    trajectory = write_symmetric_top_trajectory(args.output, viewer_output=args.viewer_output)
    print(f"Wrote {len(trajectory.time)} samples to {args.output}")


if __name__ == "__main__":
    main()
