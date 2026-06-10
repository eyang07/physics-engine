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
from engine.mechanics.symmetries import InfinitesimalSymmetry
from systems.bead_on_hoop import build_system as build_bead_on_hoop
from systems.charged_particle import build_uniform_magnetic_field_system
from systems.henon_heiles import build_system as build_henon_heiles
from systems.ideal_spring import build_system as build_ideal_spring
from systems.kepler_problem import build_system as build_kepler
from systems.lorenz_attractor import build_system as build_lorenz
from systems.pendulum import build_system as build_pendulum
from systems.sphere_geodesic import build_system as build_sphere_geodesic
from systems.uniform_gravity import build_system as build_uniform_gravity
from systems.variable_speed_wavefront import build_system as build_variable_speed_wavefront


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
        id="variableSpeedWavefront",
        title="Wavefront",
        kind="ray-bundle",
        description="Bicharacteristic rays bending through a variable-speed medium.",
        projections=("rayPlane",),
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
        ),
    ),
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
    lenses=("henonHeilesFlow", "henonHeilesPhase", "henonHeilesPotential"),
    data_path="/data/henon_heiles.json",
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
    system_kind="ray-bundle",
)


SPECS: tuple[SystemSpec, ...] = (
    PENDULUM,
    SPHERE_GEODESIC,
    CHARGED_PARTICLE,
    UNIFORM_GRAVITY,
    IDEAL_SPRING,
    KEPLER,
    BEAD_ON_HOOP,
    LORENZ,
    HENON_HEILES,
    VARIABLE_SPEED_WAVEFRONT,
)
