"""One-step image enclosure of a discrete map.

The set-propagation primitive of the level-2 (certified-numeric) reachability
lane. Given a discrete map ``x_{k+1} = F(x_k)`` — a
:class:`~engine.dynamics.discrete.DiscreteSystem` or open-loop
:class:`~engine.dynamics.discrete.ControlledDiscreteSystem` — and a *box*
assigning every free symbol an :class:`~engine.numerics.intervals.Interval`,
:func:`one_step_image` returns an interval box that soundly **over-approximates
the image** of the map: every concrete next state reachable from a state in the
box lies inside the returned box.

Each update component is lowered through the fail-closed enclosure evaluator
(:func:`~engine.verification.enclosure.enclose_expression`), so the soundness
discipline carries over unchanged: the polynomial path stays exact-rational,
only ``sqrt`` touches mpmath, and any non-whitelisted node aborts rather than
risk an unsound result.

**Bounded inputs as interval parameters.** Carrying a control, disturbance, or
velocity as a *bounded interval* — rather than substituting a feedback law — is
how the closed-loop reachable set is over-approximated soundly: if the true law
keeps the input inside the interval (e.g. a guard-band controller whose output
always lies in ``[-thrust, thrust]``), the open-loop image over that interval
contains every closed-loop successor. The guard-band closed loop itself carries
a ``Piecewise`` switch, which the whitelist refuses; enclosing the open-loop map
over the input interval is the sound way to bound it without branch handling.

Nothing here claims proof or certification. It computes a sound enclosure of the
reachable image under stated assumptions; external backends dispose.
"""

from __future__ import annotations

from typing import Mapping

import sympy as sp

from engine.dynamics.discrete import ControlledDiscreteSystem, DiscreteSystem
from engine.numerics.intervals import Interval
from engine.verification.enclosure import enclose_expression


def _free_symbol_names(expressions: tuple[sp.Expr, ...]) -> set[str]:
    names: set[str] = set()
    for expression in expressions:
        names |= {symbol.name for symbol in sp.sympify(expression).free_symbols}
    return names


def one_step_image(
    system: DiscreteSystem | ControlledDiscreteSystem,
    box: Mapping[str, Interval],
) -> dict[str, Interval]:
    """Over-approximate the one-step image of ``system`` over ``box``.

    ``box`` maps symbol names — states plus any bounded controls, disturbances,
    or parameters appearing in the update — to intervals. The result maps each
    state component name to an interval enclosing its successor over the whole
    box. Missing symbols raise, fail closed, before any partial evaluation.
    """

    required = _free_symbol_names(system.update)
    missing = sorted(required - set(box))
    if missing:
        raise ValueError(
            "box is missing intervals for symbols: " + ", ".join(missing)
        )

    image: dict[str, Interval] = {}
    for symbol, update in zip(system.state, system.update, strict=True):
        image[symbol.name] = enclose_expression(update, box)
    return image


__all__ = ["one_step_image"]
