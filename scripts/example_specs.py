"""The registry of example systems for the manifest.

This is the single place that pairs each physical system (pure definitions in
``systems/``) with its presentation metadata: titles, parameter ranges, the
named state schema, projections, conserved quantities, and visualization
lenses. Keeping it here — not in ``systems/`` — preserves the rule that a
system is a physical definition, separate from how it is shown.

Adding a system to the gallery is: write ``systems/<name>.py`` + add one spec.
"""

from __future__ import annotations

import sympy as sp

from engine.export.manifest import (
    Conserved,
    EffectivePotential,
    Lens,
    Parameter,
    ParameterVariant,
    StateVar,
    SystemSpec,
)
from engine.export.field_export import FIELD_LINES_HINT, SCALAR_FIELD_HINT, VECTOR_FIELD_HINT
from engine.mechanics import normal_modes
from engine.mechanics.symmetries import InfinitesimalSymmetry
from systems.bead_on_hoop import build_system as build_bead_on_hoop
from systems.charged_particle import build_uniform_magnetic_field_system
from systems.coupled_oscillators import build_system as build_coupled_oscillators
from systems.double_pendulum import build_system as build_double_pendulum
from systems.electromagnetic_field import build_system as build_electromagnetic_field
from systems.free_rigid_body import (
    angular_momentum_magnitude as free_rigid_body_angular_momentum_magnitude,
    build_system as build_free_rigid_body,
    rotational_energy as free_rigid_body_rotational_energy,
)
from systems.henon_heiles import build_system as build_henon_heiles
from systems.ideal_spring import build_system as build_ideal_spring
from systems.kepler_problem import build_system as build_kepler
from systems.lorenz_attractor import build_system as build_lorenz
from systems.membrane import build_system as build_membrane
from systems.n_body_gravity import (
    build_system as build_n_body_gravity,
    total_angular_momentum_z,
    total_energy as n_body_total_energy,
    total_momentum_x,
    total_momentum_y,
)
from systems.pendulum import build_system as build_pendulum
from systems.sphere_geodesic import build_system as build_sphere_geodesic
from systems.surface_geodesic import build_system as build_surface_geodesic
from systems.schwarzschild import build_system as build_schwarzschild
from systems.symmetric_top import (
    build_system as build_symmetric_top,
    effective_potential as symmetric_top_effective_potential,
)
from systems.uniform_gravity import build_system as build_uniform_gravity
from systems.variable_speed_wavefront import build_system as build_variable_speed_wavefront
from systems.vibrating_string import build_system as build_vibrating_string
from systems.wave_packet import build_system as build_wave_packet
from systems.wormhole import build_system as build_wormhole


def _time_translation(system):
    return InfinitesimalSymmetry.time_translation()


def _cyclic_coordinate(name: str):
    def build(system):
        coordinate = next(q for q in system.q if q.name == name)
        return InfinitesimalSymmetry.coordinate_translation(system.q, coordinate)

    return build


def _kepler_effective_potential(system):
    r = next(q for q in system.q if q.name == "r")
    m = next(symbol for symbol in system.lagrangian.free_symbols if symbol.name == "m")
    mu = next(symbol for symbol in system.lagrangian.free_symbols if symbol.name == "mu")
    ell = sp.Symbol("ell")
    return ell**2 / (2 * m * r**2) - mu * m / r


def _coupled_oscillator_modes(system):
    substitutions = {
        symbol: 1.0
        for symbol in system.lagrangian.free_symbols
        if symbol.name in {"m", "k"}
    }
    modes = normal_modes(
        system,
        {coordinate: 0.0 for coordinate in system.q},
        substitutions=substitutions,
    )
    payload = modes.to_dict()
    payload["method"] = "small-oscillation-generalized-eigenproblem"
    return payload


def _first_order_state(system, name: str):
    return next(symbol for symbol in system.state if symbol.name == name)


def _first_order_parameter(system, name: str):
    return next(symbol for symbol in system.parameters if symbol.name == name)


def _surface_geodesic_energy(system):
    u = _first_order_state(system, "u")
    u_dot = _first_order_state(system, "u_dot")
    phi_dot = _first_order_state(system, "phi_dot")
    major = _first_order_parameter(system, "R_major")
    minor = _first_order_parameter(system, "r_minor")
    rho = major + minor * sp.cos(u)
    return sp.simplify((minor**2 * u_dot**2 + rho**2 * phi_dot**2) / 2)


def _surface_geodesic_clairaut(system):
    u = _first_order_state(system, "u")
    phi_dot = _first_order_state(system, "phi_dot")
    major = _first_order_parameter(system, "R_major")
    minor = _first_order_parameter(system, "r_minor")
    return sp.simplify((major + minor * sp.cos(u)) ** 2 * phi_dot)


def _surface_geodesic_geometry(system):
    return {
        "kind": "surface-geodesic",
        "rendererHint": "surface-geodesic",
        "surfaceMesh": {
            "kind": "surface-mesh",
            "source": "trajectory.metadata.surfaceGeometry.surfaceMesh",
        },
        "geodesic": {
            "kind": "embedded-polyline",
            "source": "trajectory.metadata.surfaceGeometry.geodesic",
        },
        "curvature": {
            "kind": "scalar-field",
            "source": "trajectory.metadata.surfaceGeometry.curvature",
        },
        "parallelTransport": {
            "kind": "parallel-transport-frame",
            "source": "trajectory.metadata.parallelTransport",
        },
    }


def _schwarzschild_state(system, name: str):
    return next(symbol for symbol in system.state if symbol.name == name)


def _schwarzschild_parameter(system, name: str):
    return next(symbol for symbol in system.parameters if symbol.name == name)


def _schwarzschild_energy(system):
    r = _schwarzschild_state(system, "r")
    t_dot = _schwarzschild_state(system, "t_dot")
    rs = _schwarzschild_parameter(system, "r_s")
    return sp.simplify((1 - rs / r) * t_dot)


def _schwarzschild_angular_momentum(system):
    r = _schwarzschild_state(system, "r")
    phi_dot = _schwarzschild_state(system, "phi_dot")
    return sp.simplify(r**2 * phi_dot)


def _schwarzschild_effective_potential(system):
    r = _schwarzschild_state(system, "r")
    rs = _schwarzschild_parameter(system, "r_s")
    ell = sp.Symbol("L")
    return sp.simplify((1 - rs / r) * (1 + ell**2 / r**2))


def _wormhole_energy(system):
    return _first_order_state(system, "t_dot")


def _wormhole_angular_momentum(system):
    ell = _first_order_state(system, "l")
    phi_dot = _first_order_state(system, "phi_dot")
    throat_radius = _first_order_parameter(system, "a")
    return sp.simplify((ell**2 + throat_radius**2) * phi_dot)


def _wormhole_geometry(system):
    return {
        "kind": "wormhole-geodesic",
        "rendererHint": "wormhole-geodesic",
        "embeddingMesh": {
            "kind": "surface-mesh",
            "source": "trajectory.metadata.wormholeGeometry.embeddingMesh",
        },
        "geodesic": {
            "kind": "embedded-polyline",
            "source": "trajectory.metadata.wormholeGeometry.geodesic",
        },
        "diagnostics": {
            "throatTraversal": "trajectory.metadata.diagnostics.throatTraversal",
        },
    }


LENSES: tuple[Lens, ...] = (
    Lens(
        id="pendulumMotionPhase",
        title="Motion + Phase",
        kind="configuration-phase",
        description="Physical pendulum motion paired with its phase portrait.",
        projections=("angle", "phase"),
    ),
    Lens(
        id="pendulumHamiltonian",
        title="Hamiltonian Flow",
        kind="hamiltonian-flow",
        description="Hamiltonian surface and advected phase-space flow.",
        projections=("phase",),
        conserved=("H",),
    ),
    Lens(
        id="pendulumPotential",
        title="Potential",
        kind="potential-energy",
        description="Potential-energy curve with the conserved total energy level.",
        projections=("angle",),
        conserved=("H",),
    ),
    Lens(
        id="sphereGeodesic",
        title="Great-Circle Flow",
        kind="configuration-space",
        description="Geodesic motion embedded in three-dimensional space.",
        projections=("embedding3d",),
        conserved=("H", "p_phi"),
    ),
    Lens(
        id="surfaceGeodesic",
        title="Surface Geodesic",
        kind="configuration-space",
        description="Geodesic motion on an embedded surface of revolution.",
        projections=("embedding3d",),
        conserved=("H", "clairaut"),
    ),
    Lens(
        id="chargedParticle",
        title="Lorentz Orbit",
        kind="configuration-space",
        description="Charged-particle trajectory in a uniform magnetic field.",
        projections=("embedding3d",),
        conserved=("H", "p_z"),
    ),
    Lens(
        id="uniformGravity",
        title="Projectile Path",
        kind="configuration-space",
        description="Projectile motion in a uniform gravitational field.",
        projections=("embedding2d",),
        conserved=("H", "p_x"),
    ),
    Lens(
        id="uniformGravityVerticalPhase",
        title="Vertical Phase",
        kind="configuration-phase",
        description="Vertical position and velocity as a phase trajectory.",
        projections=("verticalPhase",),
        conserved=("H",),
    ),
    Lens(
        id="uniformGravityPotential",
        title="Potential",
        kind="potential-energy",
        description="Linear gravitational potential with the total energy level.",
        projections=("height",),
        conserved=("H",),
    ),
    Lens(
        id="idealSpring",
        title="Spring Motion",
        kind="configuration-phase",
        description="One-dimensional oscillator motion and phase trace.",
        projections=("line", "phase"),
        conserved=("H",),
    ),
    Lens(
        id="idealSpringPhase",
        title="Phase Portrait",
        kind="configuration-phase",
        description="The oscillator's closed trajectory in position-velocity space.",
        projections=("phase",),
        conserved=("H",),
    ),
    Lens(
        id="idealSpringPotential",
        title="Potential",
        kind="potential-energy",
        description="Quadratic spring potential with the conserved total energy level.",
        projections=("line",),
        conserved=("H",),
    ),
    Lens(
        id="coupledOscillatorModes",
        title="Normal Modes",
        kind="normal-modes",
        description="Mode shapes and superposed motion for a fixed-end oscillator chain.",
        projections=("chain",),
        conserved=("H",),
    ),
    Lens(
        id="keplerOrbit",
        title="Orbital Flow",
        kind="configuration-space",
        description="Planar inverse-square orbit in the physical orbital plane.",
        projections=("orbitPlane",),
        conserved=("H", "ell"),
    ),
    Lens(
        id="effectivePotential",
        title="Effective Potential",
        kind="effective-potential",
        description="One-dimensional radial reduction after fixing angular momentum.",
        projections=("phase",),
        conserved=("H", "ell"),
        effective_potentials=("kepler_radial",),
    ),
    Lens(
        id="keplerRadialPhase",
        title="Radial Phase",
        kind="configuration-phase",
        description="Radial motion after reducing the central-force orbit.",
        projections=("phase",),
        conserved=("H", "ell"),
    ),
    Lens(
        id="schwarzschildOrbit",
        title="Relativistic Orbit",
        kind="configuration-space",
        description="Timelike or null geodesic in the equatorial Schwarzschild plane.",
        projections=("orbitPlane",),
        conserved=("E", "L"),
    ),
    Lens(
        id="schwarzschildEffectivePotential",
        title="GR Effective Potential",
        kind="effective-potential",
        description="Schwarzschild radial reduction with turning points and orbit class.",
        projections=("phase",),
        conserved=("E", "L"),
        effective_potentials=("schwarzschild_radial",),
    ),
    Lens(
        id="wormholeGeodesic",
        title="Wormhole Throat",
        kind="configuration-space",
        description="Radial geodesic traversal through an embedded Ellis-wormhole throat.",
        projections=("embedding3d",),
        conserved=("E", "L"),
    ),
    Lens(
        id="beadHoop",
        title="Rotating Hoop",
        kind="configuration-space",
        description="A bead sliding on a curved constraint as the hoop rotates.",
        projections=("embedding3d",),
        conserved=("H",),
    ),
    Lens(
        id="beadHoopPhase",
        title="Phase Portrait",
        kind="configuration-phase",
        description="The bead's reduced coordinate and angular velocity.",
        projections=("phase",),
        conserved=("H",),
    ),
    Lens(
        id="beadHoopPotential",
        title="Potential",
        kind="potential-energy",
        description="Effective potential of the rotating hoop.",
        projections=("angle",),
        conserved=("H",),
    ),
    Lens(
        id="doublePendulumMotion",
        title="Coupled Motion",
        kind="configuration-space",
        description="The two-link pendulum traced through the physical plane.",
        projections=("bobPositions",),
        conserved=("H",),
    ),
    Lens(
        id="doublePendulumPhase",
        title="Phase Portraits",
        kind="configuration-phase",
        description="Angular phase slices for the two coupled pendulum links.",
        projections=("theta1Phase", "theta2Phase"),
        conserved=("H",),
    ),
    Lens(
        id="nBodyOrbits",
        title="N-body Orbits",
        kind="configuration-space",
        description="Per-body orbit trails in the center-of-mass frame.",
        projections=("body1Orbit", "body2Orbit", "body3Orbit"),
        conserved=("H", "P_x", "P_y", "L_z"),
    ),
    Lens(
        id="freeRigidBodyPolhode",
        title="Polhode Geometry",
        kind="rigid-body-polhode",
        description=(
            "Torque-free asymmetric-top motion on the angular-momentum sphere "
            "and kinetic-energy ellipsoid."
        ),
        projections=("angularVelocity",),
        conserved=("H", "L"),
    ),
    Lens(
        id="symmetricTopAxis",
        title="Precessing Axis",
        kind="configuration-space",
        description="The heavy top's symmetry axis tracing precession and nutation on the sphere.",
        projections=("embedding3d",),
        conserved=("H", "p_phi", "p_psi"),
    ),
    Lens(
        id="symmetricTopNutationPhase",
        title="Nutation Phase",
        kind="configuration-phase",
        description="The nutation angle and its rate after reducing the cyclic precession and spin.",
        projections=("nutationPhase",),
        conserved=("H", "p_phi", "p_psi"),
    ),
    Lens(
        id="symmetricTopPotential",
        title="Effective Potential",
        kind="effective-potential",
        description="The nutation-angle effective potential after fixing the precession and spin momenta.",
        projections=("nutationPhase",),
        conserved=("H", "p_phi", "p_psi"),
        effective_potentials=("symmetric_top_theta",),
    ),
    Lens(
        id="lorenzAttractor",
        title="Attractor Flow",
        kind="attractor-3d",
        description="Dissipative flow converging onto the Lorenz strange attractor.",
        projections=("embedding3d",),
    ),
    Lens(
        id="henonHeilesFlow",
        title="Hamiltonian Flow",
        kind="hamiltonian-flow",
        description="Configuration trajectory moving across the Hénon-Heiles potential landscape.",
        projections=("configurationPlane",),
        conserved=("H",),
    ),
    Lens(
        id="henonHeilesPhase",
        title="Phase Portrait",
        kind="configuration-phase",
        description="One canonical slice of the four-dimensional Hamiltonian flow.",
        projections=("xPhase",),
        conserved=("H",),
    ),
    Lens(
        id="henonHeilesPotential",
        title="Potential Contours",
        kind="potential-contour",
        description="Two-dimensional potential contours with the current configuration point.",
        projections=("configurationPlane",),
        conserved=("H",),
    ),
    Lens(
        id="henonHeilesPoincare",
        title="Poincaré Section",
        kind="poincare-section",
        description="Section crossings (x, p_x) on the surface y = 0, accreting as the orbit recurs.",
        projections=("xPhase",),
        conserved=("H",),
    ),
    Lens(
        id="variableSpeedWavefront",
        title="Wavefront",
        kind="ray-bundle",
        description="Bicharacteristic rays bending through a variable-speed medium.",
        projections=("rayPlane",),
    ),
    Lens(
        id="electromagneticField",
        title="Electromagnetic Fields",
        kind="static-fields",
        description="Static electric and magnetic field grids plus integrated field lines.",
    ),
    Lens(
        id="vibratingString",
        title="Vibrating String",
        kind="field-evolution",
        description="Analytic string displacement fields from normal modes and d'Alembert propagation.",
    ),
    Lens(
        id="membraneModes",
        title="Membrane Modes",
        kind="field-evolution",
        description="Rectangular and circular membrane mode surfaces and modal superpositions.",
    ),
    Lens(
        id="wavePacket",
        title="Dispersive Wave Packet",
        kind="field-evolution",
        description="Amplitude and intensity fields for a Gaussian packet under quadratic dispersion.",
    ),
)


PENDULUM = SystemSpec(
    id="pendulum",
    title="Simple Pendulum",
    category="Analytical Mechanics",
    description="A nonlinear oscillator viewed as physical motion, phase portrait, or Hamiltonian flow.",
    build=build_pendulum,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("ell", r"\ell", 1.0, 0.4, 2.5),
        Parameter("g", "g", 9.81, 1.0, 20.0),
        Parameter("theta0", r"\theta_0", 0.85, -3.0, 3.0, role="initial"),
        Parameter("theta_dot0", r"\dot{\theta}_0", 0.0, -3.0, 3.0, role="initial"),
    ),
    state=(
        StateVar("theta", r"\theta", "coordinate"),
        StateVar("theta_dot", r"\dot{\theta}", "velocity"),
    ),
    projections={"phase": ("theta", "theta_dot"), "angle": ("theta",)},
    conserved=(Conserved("H", "H", "time translation", generator=_time_translation),),
    lenses=("pendulumMotionPhase", "pendulumHamiltonian", "pendulumPotential"),
    data_path="/data/pendulum.json",
)


SPHERE_GEODESIC = SystemSpec(
    id="sphere-geodesic",
    title="Geodesic on a Sphere",
    category="Differential Geometry",
    description="Free motion on a curved configuration space; the path becomes a great circle.",
    build=build_sphere_geodesic,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("R", "R", 1.0, 0.5, 2.0),
        Parameter("theta0", r"\theta_0", 1.12, 0.05, 3.09, role="initial"),
        Parameter("phi0", r"\phi_0", 0.0, -3.14, 3.14, role="initial"),
        Parameter("theta_dot0", r"\dot{\theta}_0", 0.42, -2.0, 2.0, role="initial"),
        Parameter("phi_dot0", r"\dot{\phi}_0", 1.05, -2.0, 2.0, role="initial"),
    ),
    state=(
        StateVar("theta", r"\theta", "coordinate"),
        StateVar("phi", r"\phi", "coordinate"),
        StateVar("theta_dot", r"\dot{\theta}", "velocity"),
        StateVar("phi_dot", r"\dot{\phi}", "velocity"),
        StateVar("x", "x", "embedding"),
        StateVar("y", "y", "embedding"),
        StateVar("z", "z", "embedding"),
    ),
    projections={"embedding3d": ("x", "y", "z")},
    conserved=(
        Conserved("H", "H", "time translation", generator=_time_translation),
        Conserved("p_phi", r"p_{\phi}", "rotation about the polar axis",
                  generator=_cyclic_coordinate("phi")),
    ),
    lenses=("sphereGeodesic",),
    data_path="/data/sphere_geodesic.json",
)


SURFACE_GEODESIC = SystemSpec(
    id="surface-geodesic",
    title="Geodesic on a Surface of Revolution",
    category="Differential Geometry",
    description="Free motion on a torus generated from a reusable surface-of-revolution metric.",
    build=build_surface_geodesic,
    parameters=(
        Parameter("R_major", "R", 2.0, 1.2, 3.0),
        Parameter("r_minor", "r", 0.7, 0.2, 1.0),
        Parameter("u0", "u_0", 0.72, -3.14, 3.14, role="initial"),
        Parameter("phi0", r"\phi_0", 0.0, -3.14, 3.14, role="initial"),
        Parameter("u_dot0", r"\dot{u}_0", 0.38, -2.0, 2.0, role="initial"),
        Parameter("phi_dot0", r"\dot{\phi}_0", 0.92, -2.0, 2.0, role="initial"),
    ),
    state=(
        StateVar("u", "u", "coordinate"),
        StateVar("phi", r"\phi", "coordinate"),
        StateVar("u_dot", r"\dot{u}", "velocity"),
        StateVar("phi_dot", r"\dot{\phi}", "velocity"),
        StateVar("x", "x", "embedding"),
        StateVar("y", "y", "embedding"),
        StateVar("z", "z", "embedding"),
    ),
    projections={"embedding3d": ("x", "y", "z")},
    conserved=(
        Conserved("H", "H", "geodesic kinetic energy", expression=_surface_geodesic_energy),
        Conserved(
            "clairaut",
            "C",
            "azimuthal rotation / Clairaut momentum",
            expression=_surface_geodesic_clairaut,
        ),
    ),
    lenses=("surfaceGeodesic",),
    data_path="/data/surface_geodesic.json",
    geometry=_surface_geodesic_geometry,
    fields=(
        {
            "name": "gaussianCurvature",
            "kind": "scalar-field",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.surfaceGeometry.curvature",
        },
    ),
    system_kind="surface-geodesic",
)


CHARGED_PARTICLE = SystemSpec(
    id="charged-particle",
    title="Electron in a Magnetic Field",
    category="Fields",
    description="Lorentz-force motion from a velocity-dependent electromagnetic Lagrangian.",
    build=build_uniform_magnetic_field_system,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("q", "q", -1.0, -3.0, 3.0),
        Parameter("B_z", "B_z", 1.0, -3.0, 3.0),
        Parameter("x0", "x_0", 0.85, -2.0, 2.0, role="initial"),
        Parameter("y0", "y_0", 0.0, -2.0, 2.0, role="initial"),
        Parameter("z0", "z_0", -1.6, -2.0, 2.0, role="initial"),
        Parameter("x_dot0", r"\dot{x}_0", 0.0, -2.0, 2.0, role="initial"),
        Parameter("y_dot0", r"\dot{y}_0", 0.85, -2.0, 2.0, role="initial"),
        Parameter("z_dot0", r"\dot{z}_0", 0.22, -2.0, 2.0, role="initial"),
    ),
    state=(
        StateVar("x", "x", "coordinate"),
        StateVar("y", "y", "coordinate"),
        StateVar("z", "z", "coordinate"),
        StateVar("x_dot", r"\dot{x}", "velocity"),
        StateVar("y_dot", r"\dot{y}", "velocity"),
        StateVar("z_dot", r"\dot{z}", "velocity"),
    ),
    projections={"embedding3d": ("x", "y", "z")},
    conserved=(
        Conserved("H", "H", "time translation", generator=_time_translation),
        Conserved("p_z", r"p_{z}", "translation along z",
                  generator=_cyclic_coordinate("z")),
    ),
    lenses=("chargedParticle",),
    data_path="/data/charged_particle.json",
)


UNIFORM_GRAVITY = SystemSpec(
    id="uniform-gravity",
    title="Uniform Gravitational Field",
    category="Classical Motion",
    description="Projectile motion from a constant gravitational potential.",
    build=build_uniform_gravity,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("g", "g", 9.81, 1.0, 20.0),
        Parameter("x0", "x_0", 0.0, -2.0, 2.0, role="initial"),
        Parameter("z0", "z_0", 0.0, -2.0, 2.0, role="initial"),
        Parameter("x_dot0", r"\dot{x}_0", 1.7, -5.0, 5.0, role="initial"),
        Parameter("z_dot0", r"\dot{z}_0", 4.6, -5.0, 5.0, role="initial"),
    ),
    state=(
        StateVar("x", "x", "coordinate"),
        StateVar("z", "z", "coordinate"),
        StateVar("x_dot", r"\dot{x}", "velocity"),
        StateVar("z_dot", r"\dot{z}", "velocity"),
    ),
    projections={
        "embedding2d": ("x", "z"),
        "verticalPhase": ("z", "z_dot"),
        "height": ("z",),
    },
    conserved=(
        Conserved("H", "H", "time translation", generator=_time_translation),
        Conserved("p_x", r"p_{x}", "horizontal translation",
                  generator=_cyclic_coordinate("x")),
    ),
    lenses=("uniformGravity", "uniformGravityVerticalPhase", "uniformGravityPotential"),
    data_path="/data/uniform_gravity.json",
)


IDEAL_SPRING = SystemSpec(
    id="ideal-spring",
    title="Ideal Spring",
    category="Oscillators",
    description="A mass-spring oscillator with conserved quadratic energy.",
    build=build_ideal_spring,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("k", "k", 1.0, 0.2, 5.0),
        Parameter("x0", "x_0", 1.0, -3.0, 3.0, role="initial"),
        Parameter("x_dot0", r"\dot{x}_0", 0.0, -3.0, 3.0, role="initial"),
    ),
    state=(
        StateVar("x", "x", "coordinate"),
        StateVar("x_dot", r"\dot{x}", "velocity"),
    ),
    projections={"phase": ("x", "x_dot"), "line": ("x",)},
    conserved=(Conserved("H", "H", "time translation", generator=_time_translation),),
    lenses=("idealSpring", "idealSpringPhase", "idealSpringPotential"),
    data_path="/data/ideal_spring.json",
    variants=(
        ParameterVariant(
            id="k-0-5",
            label="k = 0.5",
            parameters={
                "m": 1.0,
                "k": 0.5,
                "x0": 1.0,
                "x_dot0": 0.0,
            },
            data_path="/data/ideal_spring_k_0_5.json",
        ),
        ParameterVariant(
            id="k-1",
            label="k = 1",
            parameters={
                "m": 1.0,
                "k": 1.0,
                "x0": 1.0,
                "x_dot0": 0.0,
            },
            data_path="/data/ideal_spring.json",
        ),
        ParameterVariant(
            id="k-2",
            label="k = 2",
            parameters={
                "m": 1.0,
                "k": 2.0,
                "x0": 1.0,
                "x_dot0": 0.0,
            },
            data_path="/data/ideal_spring_k_2.json",
        ),
    ),
)


COUPLED_OSCILLATORS = SystemSpec(
    id="coupled-oscillators",
    title="Coupled Oscillators",
    category="Oscillators",
    description=(
        "A fixed-end chain of four equal masses whose small oscillations split "
        "into normal modes."
    ),
    build=build_coupled_oscillators,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("k", "k", 1.0, 0.2, 5.0),
        Parameter("x1_0", "x_{1,0}", 0.34, -2.0, 2.0, role="initial"),
        Parameter("x2_0", "x_{2,0}", 0.49, -2.0, 2.0, role="initial"),
        Parameter("x3_0", "x_{3,0}", 0.06, -2.0, 2.0, role="initial"),
        Parameter("x4_0", "x_{4,0}", -0.39, -2.0, 2.0, role="initial"),
        Parameter("x1_dot0", r"\dot{x}_{1,0}", 0.0, -2.0, 2.0, role="initial"),
        Parameter("x2_dot0", r"\dot{x}_{2,0}", 0.0, -2.0, 2.0, role="initial"),
        Parameter("x3_dot0", r"\dot{x}_{3,0}", 0.0, -2.0, 2.0, role="initial"),
        Parameter("x4_dot0", r"\dot{x}_{4,0}", 0.0, -2.0, 2.0, role="initial"),
    ),
    state=(
        StateVar("x1", "x_1", "coordinate"),
        StateVar("x2", "x_2", "coordinate"),
        StateVar("x3", "x_3", "coordinate"),
        StateVar("x4", "x_4", "coordinate"),
        StateVar("x1_dot", r"\dot{x}_1", "velocity"),
        StateVar("x2_dot", r"\dot{x}_2", "velocity"),
        StateVar("x3_dot", r"\dot{x}_3", "velocity"),
        StateVar("x4_dot", r"\dot{x}_4", "velocity"),
    ),
    projections={
        "chain": ("x1", "x2", "x3", "x4"),
        "firstMassPhase": ("x1", "x1_dot"),
    },
    conserved=(Conserved("H", "H", "time translation", generator=_time_translation),),
    lenses=("coupledOscillatorModes",),
    data_path="/data/coupled_oscillators.json",
    normal_modes=_coupled_oscillator_modes,
)


KEPLER = SystemSpec(
    id="kepler",
    title="Kepler Problem",
    category="Orbital Mechanics",
    description="Planar inverse-square central-force motion with conserved angular momentum.",
    build=build_kepler,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("mu", r"\mu", 1.0, 0.2, 4.0),
        Parameter("r0", "r_0", 1.0, 0.3, 3.0, role="initial"),
        Parameter("phi0", r"\phi_0", 0.0, -3.14, 3.14, role="initial"),
        Parameter("r_dot0", r"\dot{r}_0", 0.0, -2.0, 2.0, role="initial"),
        Parameter("phi_dot0", r"\dot{\phi}_0", 1.05, -2.0, 2.0, role="initial"),
    ),
    state=(
        StateVar("r", "r", "coordinate"),
        StateVar("phi", r"\phi", "coordinate"),
        StateVar("r_dot", r"\dot{r}", "velocity"),
        StateVar("phi_dot", r"\dot{\phi}", "velocity"),
        StateVar("x", "x", "embedding"),
        StateVar("y", "y", "embedding"),
    ),
    projections={"orbitPlane": ("x", "y"), "phase": ("r", "r_dot")},
    conserved=(
        Conserved("H", "H", "time translation", generator=_time_translation),
        Conserved("ell", r"\ell", "rotational symmetry",
                  generator=_cyclic_coordinate("phi")),
    ),
    lenses=("keplerOrbit", "effectivePotential", "keplerRadialPhase"),
    data_path="/data/kepler_problem.json",
    effective_potentials=(
        EffectivePotential(
            name="kepler_radial",
            coordinate="r",
            latex=r"V_{\mathrm{eff}}",
            conserved="ell",
            conserved_latex=r"\ell",
            expression=_kepler_effective_potential,
            plot_source="trajectory.metadata.potentialPlots[name=kepler_radial]",
            turning_points_source=(
                "trajectory.metadata.potentialPlots[name=kepler_radial].turningPoints"
            ),
            classification_source="trajectory.metadata.orbitClassification",
        ),
    ),
)


SCHWARZSCHILD = SystemSpec(
    id="schwarzschild",
    title="Schwarzschild Geodesic",
    category="Relativity",
    description="Timelike and null geodesics in a fixed Schwarzschild background.",
    build=build_schwarzschild,
    parameters=(
        Parameter("r_s", "r_s", 2.0, 0.5, 4.0),
        Parameter("semi_latus_rectum", "p", 40.0, 20.0, 120.0, role="initial"),
        Parameter("eccentricity", "e", 0.1, 0.0, 0.5, role="initial"),
        Parameter("impact_parameter", "b", 30.0, 8.0, 80.0, role="initial"),
    ),
    state=(
        StateVar("t", "t", "coordinate"),
        StateVar("r", "r", "coordinate"),
        StateVar("phi", r"\phi", "coordinate"),
        StateVar("t_dot", r"\dot{t}", "velocity"),
        StateVar("r_dot", r"\dot{r}", "velocity"),
        StateVar("phi_dot", r"\dot{\phi}", "velocity"),
        StateVar("x", "x", "embedding"),
        StateVar("y", "y", "embedding"),
    ),
    projections={"orbitPlane": ("x", "y"), "phase": ("r", "r_dot")},
    conserved=(
        Conserved("E", "E", "stationarity / time translation", expression=_schwarzschild_energy),
        Conserved(
            "L",
            "L",
            "axial rotation",
            expression=_schwarzschild_angular_momentum,
        ),
    ),
    lenses=("schwarzschildOrbit", "schwarzschildEffectivePotential"),
    data_path="/data/schwarzschild.json",
    effective_potentials=(
        EffectivePotential(
            name="schwarzschild_radial",
            coordinate="r",
            latex=r"V_{\mathrm{eff}}^2",
            conserved="L",
            conserved_latex="L",
            expression=_schwarzschild_effective_potential,
            plot_source="trajectory.metadata.potentialPlots[name=schwarzschild_radial]",
            turning_points_source=(
                "trajectory.metadata.potentialPlots[name=schwarzschild_radial].turningPoints"
            ),
            classification_source="trajectory.metadata.orbitClassification",
        ),
    ),
    fields=(
        {
            "name": "ricciScalar",
            "kind": "scalar-field",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.curvatureScalars.ricciScalar",
        },
        {
            "name": "kretschmannScalar",
            "kind": "scalar-field",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.curvatureScalars.kretschmannScalar",
        },
    ),
    system_kind="schwarzschild-geodesic",
)


WORMHOLE = SystemSpec(
    id="wormhole",
    title="Ellis Wormhole Geodesic",
    category="Relativity",
    description=(
        "Timelike geodesic traversal in a fixed Ellis-wormhole background; "
        "the spacetime is prescribed, not dynamically solved."
    ),
    build=build_wormhole,
    parameters=(
        Parameter("a", "a", 1.0, 0.4, 3.0),
        Parameter("l0", "l_0", -6.0, -10.0, -0.5, role="initial"),
        Parameter("l_dot0", r"\dot{l}_0", 0.4, 0.1, 1.2, role="initial"),
    ),
    state=(
        StateVar("t", "t", "coordinate"),
        StateVar("l", "l", "coordinate"),
        StateVar("phi", r"\phi", "coordinate"),
        StateVar("t_dot", r"\dot{t}", "velocity"),
        StateVar("l_dot", r"\dot{l}", "velocity"),
        StateVar("phi_dot", r"\dot{\phi}", "velocity"),
        StateVar("x", "x", "embedding"),
        StateVar("y", "y", "embedding"),
        StateVar("z", "z", "embedding"),
    ),
    projections={"embedding3d": ("x", "y", "z"), "phase": ("l", "l_dot")},
    conserved=(
        Conserved("E", "E", "stationarity / time translation", expression=_wormhole_energy),
        Conserved("L", "L", "axial rotation", expression=_wormhole_angular_momentum),
    ),
    lenses=("wormholeGeodesic",),
    data_path="/data/wormhole.json",
    geometry=_wormhole_geometry,
    system_kind="wormhole-geodesic",
)


BEAD_ON_HOOP = SystemSpec(
    id="bead-on-hoop",
    title="Bead on a Rotating Hoop",
    category="Constrained Motion",
    description="A bead sliding on a circular constraint whose rotation reshapes the effective potential.",
    build=build_bead_on_hoop,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("R", "R", 1.0, 0.5, 2.0),
        Parameter("g", "g", 9.81, 1.0, 20.0),
        Parameter("Omega", r"\Omega", 4.0, 0.0, 8.0),
        Parameter("theta0", r"\theta_0", 0.82, -3.14, 3.14, role="initial"),
        Parameter("theta_dot0", r"\dot{\theta}_0", 0.12, -4.0, 4.0, role="initial"),
    ),
    state=(
        StateVar("theta", r"\theta", "coordinate"),
        StateVar("theta_dot", r"\dot{\theta}", "velocity"),
        StateVar("x", "x", "embedding"),
        StateVar("y", "y", "embedding"),
        StateVar("z", "z", "embedding"),
    ),
    projections={
        "phase": ("theta", "theta_dot"),
        "angle": ("theta",),
        "embedding3d": ("x", "y", "z"),
    },
    conserved=(Conserved("H", "H", "time translation", generator=_time_translation),),
    lenses=("beadHoop", "beadHoopPhase", "beadHoopPotential"),
    data_path="/data/bead_on_hoop.json",
)


DOUBLE_PENDULUM = SystemSpec(
    id="double-pendulum",
    title="Double Pendulum",
    category="Hamiltonian Chaos",
    description=(
        "A canonical two-link pendulum with full nonlinear coupling and "
        "chaotic energy exchange."
    ),
    build=build_double_pendulum,
    parameters=(
        Parameter("m1", "m_1", 1.0, 0.2, 3.0),
        Parameter("m2", "m_2", 1.0, 0.2, 3.0),
        Parameter("ell1", r"\ell_1", 1.0, 0.4, 2.5),
        Parameter("ell2", r"\ell_2", 1.0, 0.4, 2.5),
        Parameter("g", "g", 9.81, 1.0, 20.0),
        Parameter("theta1_0", r"\theta_{1,0}", 1.2, -3.0, 3.0, role="initial"),
        Parameter("theta2_0", r"\theta_{2,0}", -0.2, -3.0, 3.0, role="initial"),
        Parameter(
            "theta1_dot0",
            r"\dot{\theta}_{1,0}",
            0.0,
            -4.0,
            4.0,
            role="initial",
        ),
        Parameter(
            "theta2_dot0",
            r"\dot{\theta}_{2,0}",
            0.25,
            -4.0,
            4.0,
            role="initial",
        ),
    ),
    state=(
        StateVar("theta1", r"\theta_1", "coordinate"),
        StateVar("theta2", r"\theta_2", "coordinate"),
        StateVar("theta1_dot", r"\dot{\theta}_1", "velocity"),
        StateVar("theta2_dot", r"\dot{\theta}_2", "velocity"),
        StateVar("x1", "x_1", "embedding"),
        StateVar("y1", "y_1", "embedding"),
        StateVar("x2", "x_2", "embedding"),
        StateVar("y2", "y_2", "embedding"),
    ),
    projections={
        "bobPositions": ("x1", "y1", "x2", "y2"),
        "theta1Phase": ("theta1", "theta1_dot"),
        "theta2Phase": ("theta2", "theta2_dot"),
    },
    conserved=(Conserved("H", "H", "time translation", generator=_time_translation),),
    lenses=("doublePendulumMotion", "doublePendulumPhase"),
    data_path="/data/double_pendulum.json",
    variants=(
        ParameterVariant(
            id="chaotic",
            label="Chaotic exchange",
            parameters={
                "m1": 1.0,
                "m2": 1.0,
                "ell1": 1.0,
                "ell2": 1.0,
                "g": 9.81,
                "theta1_0": 1.2,
                "theta2_0": -0.2,
                "theta1_dot0": 0.0,
                "theta2_dot0": 0.25,
            },
            data_path="/data/double_pendulum.json",
        ),
        ParameterVariant(
            id="near-linear",
            label="Near-linear",
            parameters={
                "m1": 1.0,
                "m2": 1.0,
                "ell1": 1.0,
                "ell2": 1.0,
                "g": 9.81,
                "theta1_0": 0.25,
                "theta2_0": 0.18,
                "theta1_dot0": 0.0,
                "theta2_dot0": 0.0,
            },
            data_path="/data/double_pendulum_near_linear.json",
        ),
        ParameterVariant(
            id="unequal-links",
            label="Unequal links",
            parameters={
                "m1": 1.0,
                "m2": 0.65,
                "ell1": 1.0,
                "ell2": 0.7,
                "g": 9.81,
                "theta1_0": 1.0,
                "theta2_0": 0.35,
                "theta1_dot0": 0.1,
                "theta2_dot0": -0.35,
            },
            data_path="/data/double_pendulum_unequal_links.json",
        ),
    ),
)


_FIGURE_EIGHT_PARAMETERS = {
    "G": 1.0,
    "m1": 1.0,
    "m2": 1.0,
    "m3": 1.0,
    "x1_0": -0.97000436,
    "y1_0": 0.24308753,
    "x2_0": 0.97000436,
    "y2_0": -0.24308753,
    "x3_0": 0.0,
    "y3_0": 0.0,
    "vx1_0": 0.466203685,
    "vy1_0": 0.43236573,
    "vx2_0": 0.466203685,
    "vy2_0": 0.43236573,
    "vx3_0": -0.93240737,
    "vy3_0": -0.86473146,
}

_SUN_TWO_PLANETS_PARAMETERS = {
    "G": 1.0,
    "m1": 1.0,
    "m2": 0.001,
    "m3": 0.0005,
    "x1_0": 0.0,
    "y1_0": 0.0,
    "x2_0": 1.0,
    "y2_0": 0.0,
    "x3_0": 1.65,
    "y3_0": 0.0,
    "vx1_0": 0.0,
    "vy1_0": 0.0,
    "vx2_0": 0.0,
    "vy2_0": 1.0,
    "vx3_0": 0.0,
    "vy3_0": 0.78,
}


N_BODY_GRAVITY = SystemSpec(
    id="n-body-gravity",
    title="N-body Gravity",
    category="Classical Mechanics",
    description=(
        "A planar Newtonian three-body export, generated in the center-of-mass "
        "frame from the general N-body field."
    ),
    build=build_n_body_gravity,
    parameters=(
        Parameter("G", "G", _FIGURE_EIGHT_PARAMETERS["G"], 0.1, 5.0),
        Parameter("m1", "m_1", _FIGURE_EIGHT_PARAMETERS["m1"], 0.0001, 3.0),
        Parameter("m2", "m_2", _FIGURE_EIGHT_PARAMETERS["m2"], 0.0001, 3.0),
        Parameter("m3", "m_3", _FIGURE_EIGHT_PARAMETERS["m3"], 0.0001, 3.0),
        Parameter("x1_0", "x_{1,0}", _FIGURE_EIGHT_PARAMETERS["x1_0"], -2.0, 2.0, role="initial"),
        Parameter("y1_0", "y_{1,0}", _FIGURE_EIGHT_PARAMETERS["y1_0"], -2.0, 2.0, role="initial"),
        Parameter("x2_0", "x_{2,0}", _FIGURE_EIGHT_PARAMETERS["x2_0"], -2.0, 2.0, role="initial"),
        Parameter("y2_0", "y_{2,0}", _FIGURE_EIGHT_PARAMETERS["y2_0"], -2.0, 2.0, role="initial"),
        Parameter("x3_0", "x_{3,0}", _FIGURE_EIGHT_PARAMETERS["x3_0"], -2.0, 2.0, role="initial"),
        Parameter("y3_0", "y_{3,0}", _FIGURE_EIGHT_PARAMETERS["y3_0"], -2.0, 2.0, role="initial"),
        Parameter("vx1_0", "v_{x1,0}", _FIGURE_EIGHT_PARAMETERS["vx1_0"], -2.0, 2.0, role="initial"),
        Parameter("vy1_0", "v_{y1,0}", _FIGURE_EIGHT_PARAMETERS["vy1_0"], -2.0, 2.0, role="initial"),
        Parameter("vx2_0", "v_{x2,0}", _FIGURE_EIGHT_PARAMETERS["vx2_0"], -2.0, 2.0, role="initial"),
        Parameter("vy2_0", "v_{y2,0}", _FIGURE_EIGHT_PARAMETERS["vy2_0"], -2.0, 2.0, role="initial"),
        Parameter("vx3_0", "v_{x3,0}", _FIGURE_EIGHT_PARAMETERS["vx3_0"], -2.0, 2.0, role="initial"),
        Parameter("vy3_0", "v_{y3,0}", _FIGURE_EIGHT_PARAMETERS["vy3_0"], -2.0, 2.0, role="initial"),
    ),
    state=(
        StateVar("x1", "x_1", "coordinate"),
        StateVar("y1", "y_1", "coordinate"),
        StateVar("x2", "x_2", "coordinate"),
        StateVar("y2", "y_2", "coordinate"),
        StateVar("x3", "x_3", "coordinate"),
        StateVar("y3", "y_3", "coordinate"),
        StateVar("vx1", "v_{x1}", "velocity"),
        StateVar("vy1", "v_{y1}", "velocity"),
        StateVar("vx2", "v_{x2}", "velocity"),
        StateVar("vy2", "v_{y2}", "velocity"),
        StateVar("vx3", "v_{x3}", "velocity"),
        StateVar("vy3", "v_{y3}", "velocity"),
    ),
    projections={
        "body1Orbit": ("x1", "y1"),
        "body2Orbit": ("x2", "y2"),
        "body3Orbit": ("x3", "y3"),
        "configurationPlane": ("x1", "y1", "x2", "y2", "x3", "y3"),
    },
    conserved=(
        Conserved("H", "H", "time translation", expression=n_body_total_energy),
        Conserved("P_x", "P_x", "x translation", expression=total_momentum_x),
        Conserved("P_y", "P_y", "y translation", expression=total_momentum_y),
        Conserved("L_z", "L_z", "planar rotation", expression=total_angular_momentum_z),
    ),
    lenses=("nBodyOrbits",),
    data_path="/data/n_body_gravity.json",
    system_kind="first-order-flow",
    variants=(
        ParameterVariant(
            id="figure-eight",
            label="Figure eight",
            parameters=_FIGURE_EIGHT_PARAMETERS,
            data_path="/data/n_body_gravity.json",
        ),
        ParameterVariant(
            id="sun-two-planets",
            label="Sun + two planets",
            parameters=_SUN_TWO_PLANETS_PARAMETERS,
            data_path="/data/n_body_gravity_sun_two_planets.json",
        ),
    ),
)


_FREE_RIGID_BODY_PARAMETERS = {
    "I1": 1.0,
    "I2": 2.0,
    "I3": 3.2,
    "omega_1_0": 0.02,
    "omega_2_0": 1.0,
    "omega_3_0": 0.02,
}


def _free_rigid_body_geometry(system):
    moments = [
        _FREE_RIGID_BODY_PARAMETERS["I1"],
        _FREE_RIGID_BODY_PARAMETERS["I2"],
        _FREE_RIGID_BODY_PARAMETERS["I3"],
    ]
    omega = [
        _FREE_RIGID_BODY_PARAMETERS["omega_1_0"],
        _FREE_RIGID_BODY_PARAMETERS["omega_2_0"],
        _FREE_RIGID_BODY_PARAMETERS["omega_3_0"],
    ]
    energy = 0.5 * sum(moment * value**2 for moment, value in zip(moments, omega, strict=True))
    momentum_radius = sum(
        (moment * value) ** 2 for moment, value in zip(moments, omega, strict=True)
    ) ** 0.5
    return {
        "kind": "rigid-body-polhode",
        "rendererHint": "rigid-body-polhode",
        "principalMoments": moments,
        "defaultInitialAngularVelocity": omega,
        "angularMomentumSphere": {
            "space": "body-angular-momentum",
            "radius": momentum_radius,
        },
        "energyEllipsoid": {
            "space": "body-angular-momentum",
            "semiAxes": [(2.0 * energy * moment) ** 0.5 for moment in moments],
        },
        "polhode": {
            "space": "body-angular-velocity",
            "source": "trajectory.metadata.rigidBodyGeometry.polhode",
        },
    }


FREE_RIGID_BODY = SystemSpec(
    id="free-rigid-body",
    title="Free Asymmetric Top",
    category="Rigid Body Mechanics",
    description=(
        "Torque-free rigid-body rotation in principal axes, showing the "
        "intermediate-axis instability and the polhode curve."
    ),
    build=build_free_rigid_body,
    parameters=(
        Parameter("I1", "I_1", _FREE_RIGID_BODY_PARAMETERS["I1"], 0.2, 5.0),
        Parameter("I2", "I_2", _FREE_RIGID_BODY_PARAMETERS["I2"], 0.2, 5.0),
        Parameter("I3", "I_3", _FREE_RIGID_BODY_PARAMETERS["I3"], 0.2, 5.0),
        Parameter("omega_1_0", r"\omega_{1,0}", _FREE_RIGID_BODY_PARAMETERS["omega_1_0"], -2.0, 2.0, role="initial"),
        Parameter("omega_2_0", r"\omega_{2,0}", _FREE_RIGID_BODY_PARAMETERS["omega_2_0"], -2.0, 2.0, role="initial"),
        Parameter("omega_3_0", r"\omega_{3,0}", _FREE_RIGID_BODY_PARAMETERS["omega_3_0"], -2.0, 2.0, role="initial"),
    ),
    state=(
        StateVar("omega_1", r"\omega_1", "velocity"),
        StateVar("omega_2", r"\omega_2", "velocity"),
        StateVar("omega_3", r"\omega_3", "velocity"),
    ),
    projections={"angularVelocity": ("omega_1", "omega_2", "omega_3")},
    conserved=(
        Conserved("H", "H", "time translation", expression=free_rigid_body_rotational_energy),
        Conserved("L", r"\lVert L\rVert", "space-rotation symmetry", expression=free_rigid_body_angular_momentum_magnitude),
    ),
    lenses=("freeRigidBodyPolhode",),
    data_path="/data/free_rigid_body.json",
    geometry=_free_rigid_body_geometry,
    orientation={
        "rendererHint": "rigid-body",
        "convention": "quaternion-wxyz",
        "source": "trajectory.orientation",
    },
    system_kind="first-order-flow",
)


SYMMETRIC_TOP = SystemSpec(
    id="symmetric-top",
    title="Heavy Symmetric Top",
    category="Rigid Body Mechanics",
    description=(
        "A spinning gyroscope under gravity, precessing and nutating with two "
        "conserved angular momenta from its cyclic precession and spin angles."
    ),
    build=build_symmetric_top,
    parameters=(
        Parameter("I1", "I_1", 1.0, 0.2, 5.0),
        Parameter("I3", "I_3", 0.5, 0.2, 5.0),
        Parameter("M", "M", 1.0, 0.2, 3.0),
        Parameter("g", "g", 9.81, 1.0, 20.0),
        Parameter("ell", r"\ell", 0.5, 0.1, 2.0),
        Parameter("theta0", r"\theta_0", 0.4, 0.05, 3.09, role="initial"),
        Parameter("phi0", r"\phi_0", 0.0, -3.14, 3.14, role="initial"),
        Parameter("psi0", r"\psi_0", 0.0, -3.14, 3.14, role="initial"),
        Parameter("theta_dot0", r"\dot{\theta}_0", 0.0, -3.0, 3.0, role="initial"),
        Parameter("phi_dot0", r"\dot{\phi}_0", 0.0, -3.0, 3.0, role="initial"),
        Parameter("psi_dot0", r"\dot{\psi}_0", 10.0, -25.0, 25.0, role="initial"),
    ),
    state=(
        StateVar("theta", r"\theta", "coordinate"),
        StateVar("phi", r"\phi", "coordinate"),
        StateVar("psi", r"\psi", "coordinate"),
        StateVar("theta_dot", r"\dot{\theta}", "velocity"),
        StateVar("phi_dot", r"\dot{\phi}", "velocity"),
        StateVar("psi_dot", r"\dot{\psi}", "velocity"),
        StateVar("x", "x", "embedding"),
        StateVar("y", "y", "embedding"),
        StateVar("z", "z", "embedding"),
    ),
    projections={
        "embedding3d": ("x", "y", "z"),
        "nutationPhase": ("theta", "theta_dot"),
    },
    conserved=(
        Conserved("H", "H", "time translation", generator=_time_translation),
        Conserved("p_phi", r"p_{\phi}", "precession about the vertical",
                  generator=_cyclic_coordinate("phi")),
        Conserved("p_psi", r"p_{\psi}", "spin about the symmetry axis",
                  generator=_cyclic_coordinate("psi")),
    ),
    effective_potentials=(
        EffectivePotential(
            name="symmetric_top_theta",
            coordinate="theta",
            latex=r"V_{\mathrm{eff}}",
            conserved="p_phi",
            conserved_latex=r"p_{\phi}",
            expression=symmetric_top_effective_potential,
        ),
    ),
    lenses=("symmetricTopAxis", "symmetricTopNutationPhase", "symmetricTopPotential"),
    data_path="/data/symmetric_top.json",
    orientation={
        "rendererHint": "rigid-body",
        "convention": "quaternion-wxyz",
        "source": "trajectory.orientation",
    },
)


LORENZ = SystemSpec(
    id="lorenz-attractor",
    title="Lorenz Attractor",
    category="Dynamical Systems",
    description="A dissipative three-dimensional flow with a strange attractor.",
    build=build_lorenz,
    parameters=(
        Parameter("sigma", r"\sigma", 10.0, 1.0, 20.0),
        Parameter("rho", r"\rho", 28.0, 1.0, 40.0),
        Parameter("beta", r"\beta", 8.0 / 3.0, 0.5, 6.0),
        Parameter("x0", "x_0", 0.0, -5.0, 5.0, role="initial"),
        Parameter("y0", "y_0", 1.0, -5.0, 5.0, role="initial"),
        Parameter("z0", "z_0", 1.05, -5.0, 5.0, role="initial"),
    ),
    state=(
        StateVar("x", "x", "coordinate"),
        StateVar("y", "y", "coordinate"),
        StateVar("z", "z", "coordinate"),
    ),
    projections={"embedding3d": ("x", "y", "z")},
    conserved=(),
    lenses=("lorenzAttractor",),
    data_path="/data/lorenz_attractor.json",
    system_kind="first-order-flow",
    variants=(
        ParameterVariant(
            id="rho-20",
            label="rho = 20",
            parameters={
                "sigma": 10.0,
                "rho": 20.0,
                "beta": 8.0 / 3.0,
                "x0": 0.0,
                "y0": 1.0,
                "z0": 1.05,
            },
            data_path="/data/lorenz_attractor_rho_20.json",
        ),
        ParameterVariant(
            id="rho-28",
            label="rho = 28",
            parameters={
                "sigma": 10.0,
                "rho": 28.0,
                "beta": 8.0 / 3.0,
                "x0": 0.0,
                "y0": 1.0,
                "z0": 1.05,
            },
            data_path="/data/lorenz_attractor.json",
        ),
        ParameterVariant(
            id="rho-35",
            label="rho = 35",
            parameters={
                "sigma": 10.0,
                "rho": 35.0,
                "beta": 8.0 / 3.0,
                "x0": 0.0,
                "y0": 1.0,
                "z0": 1.05,
            },
            data_path="/data/lorenz_attractor_rho_35.json",
        ),
    ),
)


HENON_HEILES = SystemSpec(
    id="henon-heiles",
    title="Hénon-Heiles System",
    category="Hamiltonian Chaos",
    description="A two-degree conservative Hamiltonian system with nonlinear potential valleys.",
    build=build_henon_heiles,
    parameters=(
        Parameter("m", "m", 1.0, 0.2, 3.0),
        Parameter("k", "k", 1.0, 0.2, 3.0),
        Parameter("lambda", r"\lambda", 1.0, 0.0, 2.0),
        Parameter("x0", "x_0", 0.0, -1.5, 1.5, role="initial"),
        Parameter("y0", "y_0", 0.1, -1.5, 1.5, role="initial"),
        Parameter("x_dot0", r"\dot{x}_0", 0.48, -1.5, 1.5, role="initial"),
        Parameter("y_dot0", r"\dot{y}_0", 0.0, -1.5, 1.5, role="initial"),
    ),
    state=(
        StateVar("x", "x", "coordinate"),
        StateVar("y", "y", "coordinate"),
        StateVar("x_dot", r"\dot{x}", "velocity"),
        StateVar("y_dot", r"\dot{y}", "velocity"),
    ),
    projections={
        "configurationPlane": ("x", "y"),
        "xPhase": ("x", "x_dot"),
    },
    conserved=(Conserved("H", "H", "time translation", generator=_time_translation),),
    lenses=("henonHeilesFlow", "henonHeilesPhase", "henonHeilesPotential", "henonHeilesPoincare"),
    data_path="/data/henon_heiles.json",
)


ELECTROMAGNETIC_FIELD = SystemSpec(
    id="electromagnetic-field",
    title="Electromagnetic Field",
    category="Fields",
    description=(
        "A static field export with electric dipole equipotentials, Coulomb field "
        "lines, and a magnetic-dipole cross-section."
    ),
    build=build_electromagnetic_field,
    parameters=(
        Parameter("q", "q", 1.0, 0.2, 3.0),
        Parameter("d", "d", 1.4, 0.5, 2.2),
        Parameter("epsilon0", r"\epsilon_0", 1.0, 0.5, 2.0),
        Parameter("m_dipole", "m", 1.0, 0.2, 3.0),
        Parameter("mu0", r"\mu_0", 1.0, 0.5, 2.0),
        Parameter("I", "I", 1.0, 0.2, 3.0),
        Parameter("a", "a", 0.7, 0.2, 1.5),
    ),
    state=(),
    projections={},
    conserved=(),
    lenses=("electromagneticField",),
    data_path="/data/electromagnetic_field.json",
    fields=(
        {
            "name": "electricPotential",
            "kind": SCALAR_FIELD_HINT,
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.electricPotential",
        },
        {
            "name": "electricField",
            "kind": VECTOR_FIELD_HINT,
            "rendererHint": VECTOR_FIELD_HINT,
            "source": "trajectory.metadata.fields.electricField",
        },
        {
            "name": "electricFieldLines",
            "kind": FIELD_LINES_HINT,
            "rendererHint": FIELD_LINES_HINT,
            "source": "trajectory.metadata.fields.electricFieldLines",
        },
        {
            "name": "magneticField",
            "kind": VECTOR_FIELD_HINT,
            "rendererHint": VECTOR_FIELD_HINT,
            "source": "trajectory.metadata.fields.magneticField",
        },
        {
            "name": "magneticFieldLines",
            "kind": FIELD_LINES_HINT,
            "rendererHint": FIELD_LINES_HINT,
            "source": "trajectory.metadata.fields.magneticFieldLines",
        },
    ),
    system_kind="static-field",
)


def _vibrating_string_modes(system):
    return system.normal_modes(4, parameters={"L": 1.0, "c": 1.0, "rho": 1.0})


VIBRATING_STRING = SystemSpec(
    id="vibrating-string",
    title="Vibrating String",
    category="Wave Propagation",
    description=(
        "A one-dimensional string with fixed ends, exported as analytic modal "
        "and traveling-wave displacement fields."
    ),
    build=build_vibrating_string,
    parameters=(
        Parameter("L", "L", 1.0, 0.5, 3.0),
        Parameter("c", "c", 1.0, 0.5, 3.0),
        Parameter("rho", r"\rho", 1.0, 0.2, 3.0),
    ),
    state=(),
    projections={},
    conserved=(),
    lenses=("vibratingString",),
    data_path="/data/vibrating_string.json",
    normal_modes=_vibrating_string_modes,
    fields=(
        {
            "name": "standingDisplacement",
            "kind": "scalar-field-series",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.standingDisplacement",
        },
        {
            "name": "travelingDisplacement",
            "kind": "scalar-field-series",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.travelingDisplacement",
        },
    ),
    system_kind="field-evolution",
)


def _membrane_modes(system):
    return system.normal_modes(parameters={"Lx": 1.4, "Ly": 1.0, "R": 1.0, "c": 1.0})


MEMBRANE = SystemSpec(
    id="membrane",
    title="Membrane Modes",
    category="Wave Propagation",
    description=(
        "Two-dimensional membrane normal modes: rectangular sine modes and "
        "circular Bessel drum modes."
    ),
    build=build_membrane,
    parameters=(
        Parameter("Lx", "L_x", 1.4, 0.5, 3.0),
        Parameter("Ly", "L_y", 1.0, 0.5, 3.0),
        Parameter("R", "R", 1.0, 0.4, 2.0),
        Parameter("c", "c", 1.0, 0.5, 3.0),
    ),
    state=(),
    projections={},
    conserved=(),
    lenses=("membraneModes",),
    data_path="/data/membrane.json",
    normal_modes=_membrane_modes,
    fields=(
        {
            "name": "rectangularMode11",
            "kind": SCALAR_FIELD_HINT,
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.rectangularMode11",
        },
        {
            "name": "circularMode01",
            "kind": SCALAR_FIELD_HINT,
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.circularMode01",
        },
        {
            "name": "rectangularDisplacement",
            "kind": "scalar-field-series",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.rectangularDisplacement",
        },
        {
            "name": "circularDisplacement",
            "kind": "scalar-field-series",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.circularDisplacement",
        },
    ),
    system_kind="field-evolution",
)


WAVE_PACKET = SystemSpec(
    id="wave-packet",
    title="Dispersive Wave Packet",
    category="Wave Propagation",
    description=(
        "A Gaussian wave packet under quadratic dispersion, separating phase "
        "velocity, group velocity, and envelope spreading."
    ),
    build=build_wave_packet,
    parameters=(
        Parameter("alpha", r"\alpha", 0.04, 0.005, 0.2),
        Parameter("k0", "k_0", 6.0, 1.0, 12.0),
        Parameter("sigma", r"\sigma", 0.45, 0.1, 1.5),
        Parameter("x0", "x_0", -1.0, -3.0, 3.0),
    ),
    state=(),
    projections={},
    conserved=(),
    lenses=("wavePacket",),
    data_path="/data/wave_packet.json",
    fields=(
        {
            "name": "amplitude",
            "kind": "scalar-field-series",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.amplitude",
        },
        {
            "name": "intensity",
            "kind": "scalar-field-series",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.intensity",
        },
    ),
    system_kind="field-evolution",
)


VARIABLE_SPEED_WAVEFRONT = SystemSpec(
    id="variable-speed-wavefront",
    title="Variable-Speed Wavefront",
    category="Wave Propagation",
    description="A ray bundle evolving through a Gaussian slow-speed lens in geometric optics.",
    build=build_variable_speed_wavefront,
    parameters=(
        Parameter("c0", "c_0", 1.0, 0.5, 2.0),
        Parameter("alpha", r"\alpha", 0.42, 0.0, 0.75),
        Parameter("sigma", r"\sigma", 0.85, 0.25, 1.75),
    ),
    state=(
        StateVar("x", "x", "coordinate"),
        StateVar("y", "y", "coordinate"),
        StateVar("xi", r"\xi", "momentum"),
        StateVar("eta", r"\eta", "momentum"),
    ),
    projections={"rayPlane": ("x", "y")},
    conserved=(),
    lenses=("variableSpeedWavefront",),
    data_path="/data/variable_speed_wavefront.json",
    fields=(
        {
            "name": "wavefrontSurface",
            "kind": "wavefront-surface",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.wavefrontSurface",
        },
        {
            "name": "wavefrontIntensity",
            "kind": "scalar-field-series",
            "rendererHint": SCALAR_FIELD_HINT,
            "source": "trajectory.metadata.fields.wavefrontIntensity",
        },
    ),
    system_kind="ray-bundle",
)


SPECS: tuple[SystemSpec, ...] = (
    PENDULUM,
    SPHERE_GEODESIC,
    SURFACE_GEODESIC,
    CHARGED_PARTICLE,
    UNIFORM_GRAVITY,
    IDEAL_SPRING,
    COUPLED_OSCILLATORS,
    KEPLER,
    SCHWARZSCHILD,
    WORMHOLE,
    BEAD_ON_HOOP,
    DOUBLE_PENDULUM,
    N_BODY_GRAVITY,
    FREE_RIGID_BODY,
    SYMMETRIC_TOP,
    LORENZ,
    HENON_HEILES,
    ELECTROMAGNETIC_FIELD,
    VIBRATING_STRING,
    MEMBRANE,
    WAVE_PACKET,
    VARIABLE_SPEED_WAVEFRONT,
)
