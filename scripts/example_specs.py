"""The registry of example systems for the manifest.

This is the single place that pairs each physical system (pure definitions in
``systems/``) with its presentation metadata: titles, parameter ranges, the
named state schema, projections, conserved quantities, and visualization
lenses. Keeping it here — not in ``systems/`` — preserves the rule that a
system is a physical definition, separate from how it is shown.

Adding a system to the gallery is: write ``systems/<name>.py`` + add one spec.
"""

from __future__ import annotations

from engine.export.manifest import Conserved, Parameter, StateVar, SystemSpec
from engine.mechanics.symmetries import InfinitesimalSymmetry
from systems.charged_particle import build_uniform_magnetic_field_system
from systems.ideal_spring import build_system as build_ideal_spring
from systems.kepler_problem import build_system as build_kepler
from systems.pendulum import build_system as build_pendulum
from systems.sphere_geodesic import build_system as build_sphere_geodesic
from systems.uniform_gravity import build_system as build_uniform_gravity


def _time_translation(system):
    return InfinitesimalSymmetry.time_translation()


def _cyclic_coordinate(name: str):
    def build(system):
        coordinate = next(q for q in system.q if q.name == name)
        return InfinitesimalSymmetry.coordinate_translation(system.q, coordinate)

    return build


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
    lenses=("pendulumMotionPhase", "pendulumHamiltonian"),
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
    projections={"embedding2d": ("x", "z")},
    conserved=(
        Conserved("H", "H", "time translation", generator=_time_translation),
        Conserved("p_x", r"p_{x}", "horizontal translation",
                  generator=_cyclic_coordinate("x")),
    ),
    lenses=("uniformGravity",),
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
    lenses=("idealSpring",),
    data_path="/data/ideal_spring.json",
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
    lenses=("keplerOrbit",),
    data_path="/data/kepler_problem.json",
)


SPECS: tuple[SystemSpec, ...] = (
    PENDULUM,
    SPHERE_GEODESIC,
    CHARGED_PARTICLE,
    UNIFORM_GRAVITY,
    IDEAL_SPRING,
    KEPLER,
)
