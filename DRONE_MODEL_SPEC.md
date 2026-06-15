# Drone Verification Model Specification

*Extraction target: a theory-first mechanics engine where Python/SymPy is the
source of mathematical truth (continuous field `x' = f(x,u,d;θ)` or discrete map
`x_{k+1} = F(x_k,u_k,d_k;θ)`), controllers are symbolic laws `u = K(x)`,
admissible controls/disturbances are box bounds, sets are sublevel sets in the
`g(x) <= level` convention, and barrier/Lyapunov functions are **candidate**
certificates that yield proof obligations (discharged externally, e.g. by Lean).*

All math below is distilled from `paper/main.tex` (canonical for the math), the
Lean development (`lean/DroneLean/DroneLean/`), and the TLA+/nuSMV fixed-point
encodings. Where artifacts disagree, the disagreement is flagged explicitly.
Expressions are written to be SymPy-parseable. Implicit/assumed items are flagged
**[IMPLICIT]**.

---

## A. Identity & provenance

- **Model name:** Guard-band feedback-controlled drone (point-mass, geofenced),
  studied across three complexity tiers.
- **Paper:** Tianrun (Eric) Yang, *"Deductive Verification vs. Model Checking for
  Physical Safety of a Feedback-Controlled Drone."* (`paper/main.tex`; repo
  `https://github.com/eyang07/DroneV`).
- **Artifact coverage (one line each):**
  - **paper** (`paper/main.tex`) — canonical real-valued math: continuous
    dynamics, exact sampled-data update, controllers, LTL properties, all three
    tiers; appendices give the fixed-point encoding and raw data.
  - **Lean 4** (`lean/.../Tier1`, `Tier2`) — *deductive* proof of the exact
    real-valued model, universally over all parameters satisfying a validity
    predicate; proves safety/invariance (P1, P2, P4), not liveness (P3).
  - **TLA+/TLC** (`tla/`) — explicit-state model checking of a *finite
    fixed-point abstraction* (scale F=32, Δt=1/4); checks P1–P4 by enumeration.
  - **nuSMV** (`nusmv/DroneTier1.smv`, `DroneTier2.smv`) — symbolic (BDD) model
    checking of the *same* finite fixed-point abstraction as TLA+.
  - **fixed-point** (paper App. A.2 / the `.tla`/`.smv` files) — the
    quantization (binary lattice, scale F=32, Δt=1/4, velocity lattice
    {−8,0,8}) shared by TLA+ and nuSMV. **Treat as a modeling abstraction, not
    as the canonical model.**

**Canonical model for re-implementation = the exact real-valued *discrete*
sampled-data system** (Section C). The continuous ODE is its physical origin; the
fixed-point lattice is a downstream finite abstraction used only by the model
checkers.

---

## B. State space

State `x = (q, v) ∈ ℝ³ × ℝ³ ≅ ℝ⁶`. The model is **3D** (full spatial position +
velocity). Axes indexed `0,1,2` in Lean; `1,2,3` in the paper. **Axis 2 (= axis 3
in paper) is altitude.**

| Symbol | Lean index | Physical meaning | Units (normalized) |
| --- | --- | --- | --- |
| `q1` | `q 0` | horizontal position, axis 1 | length L |
| `q2` | `q 1` | horizontal position, axis 2 | length L |
| `q3` | `q 2` | **altitude** | length L |
| `v1` | `v 0` | horizontal velocity, axis 1 | L / T |
| `v2` | `v 1` | horizontal velocity, axis 2 | L / T |
| `v3` | `v 2` | vertical (climb) velocity | L / T |

- **State dimension:** 6.
- **Units:** normalized, mass `m = 1`, gravity `g = 1`. Physical units recovered
  by rescaling time and thrust (paper §A.1). Thrust/acceleration units are
  L/T².
- **Equilibrium / setpoint:** the controller is a *guard-band* regulator, not a
  point-stabilizer — it has **no single setpoint**. The natural equilibrium of
  the open-loop drift under hover thrust `u=(0,0,1)` is *any* state with `v=0`
  (zero net acceleration): `{(q, 0) : q ∈ ℝ³}`. The control objective is
  **set membership** (stay in the safe box `S`), not convergence to a point.
  **[IMPLICIT]** there is no asymptotically-stable equilibrium; the certificate
  is a barrier/invariance certificate, not a Lyapunov function (see J).

---

## C. Dynamics

### Canonical model: DISCRETE exact sampled-data map

The verified system is the **discrete** closed loop. The paper stresses (Remark,
§A.2) that this is the *exact* sampled-data system under zero-order hold — **not**
a Forward-Euler/RK approximation — so no integration error is introduced.

Open-loop update `F : ℝ⁶ × ℝ³ → ℝ⁶`, with `e3 = (0,0,1)` and timestep `dt = Δt`:

```python
# state x = [q1,q2,q3, v1,v2,v3]; control u = [u1,u2,u3]; e3 = [0,0,1]
q1_next = q1 + dt*v1 + (dt**2/2)*(u1 - 0)
q2_next = q2 + dt*v2 + (dt**2/2)*(u2 - 0)
q3_next = q3 + dt*v3 + (dt**2/2)*(u3 - 1)
v1_next = v1 + dt*(u1 - 0)
v2_next = v2 + dt*(u2 - 0)
v3_next = v3 + dt*(u3 - 1)
```

Vector form (`F(x,u)`): `q⁺ = q + dt·v + ½·dt²·(u − e3)`,
`v⁺ = v + dt·(u − e3)`.

Closed loop: `f(x) = F(x, g(x))` where `g` is the controller (Section F).

### Continuous origin (NOT canonical, but exact integrand)

Point mass, Lagrangian `L = ½‖q̇‖² − q3` (potential `V = q3`, gravity along −e3):

```python
# x' = f(x,u): first-order ODE
q1_dot = v1;   v1_dot = u1 - 0
q2_dot = v2;   v2_dot = u2 - 0
q3_dot = v3;   v3_dot = u3 - 1     # gravity = 1 along altitude
```

i.e. `q̇ = v`, `v̇ = u − e3`. Linear in state, affine in control, constant
gravity drift. Because control is held constant on each sample (ZOH), integrating
this ODE over `[t_k, t_{k+1})` yields the discrete map above **exactly** (the
½dt²(u−e3) term is the closed-form position integral, not a truncation).

**Derivation tag for the engine:** discrete = exact ZOH integral of the
continuous field; if the engine derives the discrete map itself it should use the
exact double integral, *not* `Euler`.

---

## D. Inputs

### Control `u = (u1, u2, u3) ∈ ℝ³` (acceleration/thrust, units L/T²)

Admissible control box `U` (Lean `admissible`; paper Def. "Control space"):

| Input | Meaning | Admissible interval |
| --- | --- | --- |
| `u1` | horizontal thrust, axis 1 | `[-uh, uh]` |
| `u2` | horizontal thrust, axis 2 | `[-uh, uh]` |
| `u3` | vertical thrust | `[u3Min, u3Max]` with `0 ≤ u3Min < 1 < u3Max` |

The *controller* only ever emits values from a finite alphabet
`U_ctrl ⊆ U` (Section F), but the admissibility box `U` is the box bound the
engine should register.

### Disturbance `d` — only at Tier 3

- **Tiers 1–2: no disturbance** (`d` absent; deterministic).
- **Tier 3:** additive acceleration disturbance `d = (d1,d2,d3) ∈ W = [-w, w]³`,
  `w > 0`, entering as `u − e3 + d` in both update lines. **Adversarial**
  (worst-case): properties must hold for *every* admissible disturbance sequence
  `(d_k) ∈ W^ℕ` (zero-sum safety game, Lygeros-style). This makes the Tier-3
  closed loop **branching** (set-valued: one successor per `d ∈ W`).

---

## E. Parameters

The canonical (Lean) model is **parametric** — theorems hold for *all* `Params`
satisfying `Params.Valid` (Section G). The numeric column gives the concrete
**fixed-point instantiation** used by TLA+/nuSMV (unscaled values; the lattice
scale is F=32). Lean uses no fixed numbers.

| Symbol | Meaning | Units | Numeric (MC instantiation, unscaled) |
| --- | --- | --- | --- |
| `m` | mass | M | 1 (normalized) |
| `g` | gravity | L/T² | 1 (normalized) |
| `dt` (`Δt`) | sample period | T | `1/4` |
| `q1Min,q1Max` | geofence x-bounds | L | `-1, 1` |
| `q2Min,q2Max` | geofence y-bounds | L | `-1, 1` |
| `q3Min,q3Max` | geofence altitude bounds | L | `0, 2` |
| `δh` | horizontal guard-band width | L | `1/4` |
| `δ3Low` (`δ3⁻`) | lower (floor) guard band | L | `1/4` |
| `δ3High` (`δ3⁺`) | upper (ceiling) guard band | L | `1/4` |
| `uh` | horizontal corrective thrust mag | L/T² | `1` |
| `uHov` | hover thrust (cancels gravity) | L/T² | `1` (fixed; `uHov = 1` always) |
| `u3Min` | min vertical thrust (brake down) | L/T² | `0` |
| `u3Max` | max vertical thrust (brake up) | L/T² | `2` |

**Derived bounds** (Lean `Params.Bh/B3/Vmax`):
```python
Bh   = uh * dt                                  # horizontal velocity bound  = 1/4
B3   = max((u3Max - 1)*dt, (1 - u3Min)*dt)      # vertical velocity bound    = 1/4
Vmax = max(Bh, B3)                              # overall per-axis vel bound = 1/4
```

**Tier-2 obstacle parameters** (Lean `Obstacle`; paper App. `app:tier2`):

| Symbol | Meaning | Numeric (MC, unscaled) |
| --- | --- | --- |
| `o1Min,o1Max` | obstacle x-extent (open) | `-1/4, 1/4` |
| `o2Min,o2Max` | obstacle y-extent (open) | `-1/4, 1/4` |
| `o3Min,o3Max` | obstacle altitude extent (open) | `3/4, 5/4` |
| `β1,β2,β3` (`δO`) | per-axis avoidance/dilation band | `1/4, 1/4, 1/4` |

**Tier-3 parameter:** `w` (wind bound), `W = [-w,w]³`. No numeric instantiation
in current artifacts (Tier 3 is design-only / not yet verified).

> **Cross-artifact note (scale):** scaled fixed-point values are `q̂ = 32·q` etc.:
> geofence `q̂1,q̂2 ∈ [-32,32]`, `q̂3 ∈ [0,64]`; guard widths `δ̂ = 8`; controls
> `û_h = 32`, `û_hov = 32`, `û3Min = 0`, `û3Max = 64`; velocity lattice
> `{-8,0,8}` per axis; obstacle `Ô = (-8,8)×(-8,8)×(24,40)`, `β̂ = 8`.

---

## F. Controllers

There are **two** finite-valued, memoryless state-feedback laws (Tier 1 `g`,
Tier 2 `g₂`). Both select from the finite alphabet
```python
U_ctrl = {-uh,0,uh} × {-uh,0,uh} × {u3Min, uHov, u3Max}     # uHov = 1
```
and satisfy `g(x) ∈ U_ctrl ⊆ U` for all `x` (proved: Lean `controller_admissible`,
`controllerT2_admissible`).

### ✅ CANONICAL controller to route end-to-end first: **Tier 1 `g`** (guard-band)

Simplest; deterministic; per-axis. For each axis the law is a piecewise constant
selection on thresholds + velocity sign. With geofence walls `[qiMin,qiMax]`:

```python
# Horizontal axes i in {1,2}  (Lean controlH):
def u_horiz(qi, vi, qiMin, qiMax):
    if qi <= qiMin + dh and vi < 0:   return  uh    # near lower wall, moving out -> push in
    if qi >= qiMax - dh and vi > 0:   return -uh    # near upper wall, moving out -> push in
    return 0                                        # interior -> coast

# Vertical axis  (Lean controlV):
def u_vert(q3, v3):
    if q3 <= q3Min + d3Low  and v3 < 0:  return u3Max   # near floor, descending -> max up
    if q3 >= q3Max - d3High and v3 > 0:  return u3Min   # near ceiling, ascending -> min up
    return uHov                                         # otherwise -> hover (= 1)
```
Full law `g(x) = (u_horiz(q1,v1,q1Min,q1Max), u_horiz(q2,v2,q2Min,q2Max),
u_vert(q3,v3))`. **Not switched/hybrid in the mode sense** — it is a single
piecewise-constant feedback map (closed-loop substitution `u = g(x)`).

### Tier 2 `g₂` (avoidance overlay) — summary

Adds an interior open obstacle box `O`. `g₂` = Tier 1 `g` **plus two
obstacle-braking branches per axis**, which *override* the geofence rule when the
drone is within band `βi` of an obstacle face, **aligned** with the obstacle on
the other two axes (dilated cross-section), and **moving toward** it:

```python
# Horizontal (Lean ctrlH2), al = aligned_i(q):
def u_horiz2(qi, vi, qiMin, qiMax, oiMin, oiMax, bi, al):
    if (oiMin - bi <= qi <= oiMin) and al and vi > 0:  return -uh   # lower face: brake (-)
    if (oiMax <= qi <= oiMax + bi) and al and vi < 0:  return  uh   # upper face: brake (+)
    return u_horiz(qi, vi, qiMin, qiMax)                            # else: Tier 1 rule

# Vertical (Lean ctrlV2):
def u_vert2(q3, v3, o3Min, o3Max, b3, al):
    if (o3Min - b3 <= q3 <= o3Min) and al and v3 > 0:  return u3Min # below floor: brake down
    if (o3Max <= q3 <= o3Max + b3) and al and v3 < 0:  return u3Max # above ceiling: brake up
    return u_vert(q3, v3)
```
where the **dilated alignment** flag for axis `i` is "the other two coordinates
lie in the obstacle cross-section dilated by their bands":
```python
aligned1(q) = (o2Min-b2 < q2 < o2Max+b2) and (o3Min-b3 < q3 < o3Max+b3)
aligned2(q) = (o1Min-b1 < q1 < o1Max+b1) and (o3Min-b3 < q3 < o3Max+b3)
aligned3(q) = (o1Min-b1 < q1 < o1Max+b1) and (o2Min-b2 < q2 < o2Max+b2)
```
Dilation is **load-bearing** (non-vacuous): with the bare (undilated) slab,
nuSMV finds a diagonal corner counterexample that enters `O` (see L). The
avoidance branches and geofence branches are provably disjoint under
`Obstacle.Valid`, so `g₂` is single-valued.

> **Tie-break discrepancy across artifacts (flagged):** the Lean controller uses
> **strict** outward-motion tests (`vi < 0`, `vi > 0`). The TLA+/nuSMV encodings
> use **non-strict** tests (`vi <= 0`, `vi >= 0`) at the relevant faces. This
> differs only on zero-velocity threshold states, but means the model-checking
> arms and Lean are *not literally identical* transition systems there. For the
> engine, use the **strict** Lean convention (it matches the canonical
> real-valued model).

---

## G. Assumptions

All as inequalities, with the part of the argument that depends on each.

### Parameter validity `Params.Valid` (every Lean theorem hypothesis)
```python
0 < dh ;  0 < d3Low ;  0 < d3High                 # guard bands positive
2*dh        < q1Max - q1Min                        # inner x-interval nonempty
2*dh        < q2Max - q2Min                        # inner y-interval nonempty
d3Low+d3High< q3Max - q3Min                        # inner z-interval nonempty
0 < uh                                             # horizontal authority
0 <= u3Min ;  u3Min < 1 ;  1 < u3Max               # vertical authority both ways
0 < dt
```
- Positivity + nonempty-inner: needed for the controller to be **well-defined /
  single-valued** (opposite guard bands disjoint) and for `S_in ⊆ S`.
- `u3Min<1<u3Max`: needed so vertical thrust can produce both net descent and net
  ascent (corrective authority against gravity), used in P1/P2 vertical bounds.

### Speed precondition `speedBound` (the **half-bound**; precond. of P1)
```python
abs(v1) <= uh*dt/2
abs(v2) <= uh*dt/2
abs(v3) <= (u3Max-1)*dt/2
abs(v3) <= (1-u3Min)*dt/2
```
Needed by **P1 geofence invariance** (`closedLoop_safe`) and by P4. **Caveat:**
`speedBound` is **not self-reproducing** — a single step can grow speed to the
looser `velBound` (`uh·dt`) level — so all-iterate P1/P4 are stated *conditionally*
on `speedBound` holding at each visited state.

### Velocity bound `velBound` (the self-reproducing bound; P2 invariant)
```python
abs(v1) <= Bh ;  abs(v2) <= Bh ;  abs(v3) <= B3       # Bh=uh*dt, B3 per E
```
This *is* preserved by the closed loop (Lean `closedLoop_velBound`), hence holds
for all iterates (P2). Note the paper's P2 is the **norm** form `‖v‖ ≤ v_max`;
Lean proves the **per-axis** form; the model checkers check `‖v‖² ≤ VMaxSq`. See
N for reconciliation.

### Timestep smallness `dtSmall` (precond. of P1)
```python
uh*dt**2/2        <= dh
(u3Max-1)*dt**2/2 <= d3Low
(1-u3Min)*dt**2/2 <= d3High
(u3Max-1)*dt**2/2 <= d3High
(1-u3Min)*dt**2/2 <= d3Low
```
"One step's worst displacement under corrective thrust fits inside the guard
band." Needed by **P1 geofence invariance**.

### Drift bound `driftBound` (state-dependent; precond. of S_in invariance / P3 support)
```python
q1Min+dh   <= q1 + dt*v1 <= q1Max-dh
q2Min+dh   <= q2 + dt*v2 <= q2Max-dh
q3Min+d3Low<= q3 + dt*v3 <= q3Max-d3High
```
A discrete control-barrier-style condition: the *linear drift* stays in the inner
set. **Why it is needed (do not weaken):** a uniform velocity bound is provably
**insufficient** for `S_in` invariance — a point just inside `S_in` does not
trigger the guard, so any inward velocity can exit `S_in` in one step. Used by
`innerSafeSet_invariant` (and the Tier-2 analogue).

### Obstacle validity `Obstacle.Valid` (Tier 2 only; paper Assumption `ass:obstacle`)
```python
0 < b1, 0 < b2, 0 < b3                             # bands positive
o1Min<o1Max ; o2Min<o2Max ; o3Min<o3Max            # nonempty obstacle
# (1) dilated obstacle inside inner safe set  (O (+) b ⊆ S_in):
q1Min+dh    <= o1Min-b1 ; o1Max+b1 <= q1Max-dh
q2Min+dh    <= o2Min-b2 ; o2Max+b2 <= q2Max-dh
q3Min+d3Low <= o3Min-b3 ; o3Max+b3 <= q3Max-d3High
# (2) separation: band narrower than half the obstacle (single-valued ctrl):
2*b1 < o1Max-o1Min ; 2*b2 < o2Max-o2Min ; 2*b3 < o3Max-o3Min
# (3) braking adequacy: band dominates one-step drift at the velocity cap:
dt*Bh <= b1 ; dt*Bh <= b2 ; dt*B3 <= b3
```
- (1) keeps avoidance away from the geofence band (no interference).
- (2) keeps `g₂` single-valued.
- (3) is the braking-margin condition: corrective thrust arrests inward motion
  before the open obstacle is entered (used in P4).

### Fixed-point / quantization assumption — **modeling assumption, not arithmetic**
The TLA+/nuSMV arms assume state/control live on a binary lattice (scale F=32,
Δt=1/4, velocity lattice {−8,0,8}³, positions integer on the geofence box).
**Stated as a modeling restriction**, this is:
```python
v_axis in {-Vmax, 0, Vmax}          # ternary velocity per axis (unscaled {-1/4,0,1/4})
q_axis on the integer/scale-F grid within the geofence box
```
Under the reachable control alphabet all update divisions are exact (no rounding),
so the lattice is closed under `F` — i.e. this is a *restriction of the domain*,
not a numerical approximation. **The canonical real-valued model makes no such
assumption** (Lean proves over all of ℝ⁶).

---

## H. Geometry / sets  (engine convention: `g(x) <= level`, sublevel = inside)

All sets are on position `q` (the velocity bound is handled separately as P2).

### Geofence safe box `S` (SAFE set; Lean `safeRegion`)
```python
S = { q :  q1Min<=q1<=q1Max  and  q2Min<=q2<=q2Max  and  q3Min<=q3<=q3Max }
# Sublevel form  g_S(q) <= 0 :
g_S(q) = max(q1Min-q1, q1-q1Max, q2Min-q2, q2-q2Max, q3Min-q3, q3-q3Max)
```

### Inner safe set `S_in` (Lean `innerSafeSet`) — recovery target
```python
S_in = { q : q1Min+dh    <= q1 <= q1Max-dh    and
             q2Min+dh    <= q2 <= q2Max-dh    and
             q3Min+d3Low <= q3 <= q3Max-d3High }
```

### Guard band `B = S \ S_in` (Lean `inGuard`) — where corrective thrust fires
```python
inGuard(q) = (q in S) and not (q in S_in)
```

### Obstacle `O` (Tier 2, UNSAFE set; **open** box; Lean `inObstacle`)
```python
# OPEN box -> strict inequalities; resting on a face is SAFE
O = { q : o1Min<q1<o1Max and o2Min<q2<o2Max and o3Min<q3<o3Max }
# q in O iff  h_O(q) < 0 ,  where
h_O(q) = max(o1Min-q1, q1-o1Max, o2Min-q2, q2-o2Max, o3Min-q3, q3-o3Max)
# Tier-2 SAFE region (nonconvex):  S' = S \ O = { q in S and h_O(q) >= 0 }
```

### Dilated obstacle / braking buffer (Tier 2; gating + initial-set only — NOT invariant)
```python
O_plus_b = { q : o1Min-b1<=q1<=o1Max+b1 and o2Min-b2<=q2<=o2Max+b2
                                          and o3Min-b3<=q3<=o3Max+b3 }   # closed
obstacleBuffer = O_plus_b \ O           # the braking guard band B_O
innerSafeSet'  = S_in \ O_plus_b        # obstacle-aware inner set (Tier-2 recovery target)
```
> **NB:** `O_plus_b` is a *braking guard band that trajectories may legitimately
> enter*, **not** a keep-out set. The verified obstacle property is avoidance of
> the open `O` (P4), never avoidance of `O_plus_b`.

### Roles
- **Safe set:** `S` (Tier 1); `S' = S \ O` (Tier 2).
- **Unsafe set:** complement of `S` (geofence escape); plus `O` (Tier 2).
- **Concrete initial set the system starts inside** (Lean/MC `Init`):
  Tier 1: `X_init = S_in × {velocities with speedBound}`. In the MC instantiation,
  `q ∈ S_in` and `v ∈ {-Vmax,0,Vmax}³` (scaled `{-8,0,8}³`).
  Tier 2: `X_init = (S_in \ O_plus_b) × {velocities}` (excludes the dilated buffer).

---

## I. Safety property (exact claim, controller, assumptions)

LTL over the closed-loop orbit `x_{k+1}=f(x_k)`. Properties:

- **P1 (geofence safety):** `□(q ∈ S)` — `S` is **forward-invariant**.
- **P2 (speed bound):** `□(‖v‖ ≤ v_max)`.
- **P3 (recovery, liveness):** `□(q ∈ B → ◇ q ∈ S_in)`.
- **P4 (obstacle avoidance, Tier 2):** `□(q ∉ O)`.

What is actually **established**, by arm:

| Property | Lean (real-valued, ∀ params) | TLA+ & nuSMV (fixed-point) |
| --- | --- | --- |
| **P1** `S` invariant | ✅ one-step `closedLoop_safe` under `speedBound`+`dtSmall`; Tier-2 all-iterate **conditional** on per-step `speedBound` | ✅ by enumeration (`GeofenceInv`, witnessed by `NoOverflow`) |
| **P2** speed bound | ✅ one-step + **all iterates** (`closedLoop_velBound`, `iterate_velBound`), per-axis `velBound`, unconditional under `Valid` | ✅ `SpeedInv: ‖v̂‖² ≤ 192` |
| **P3** recovery | ❌ **not proved**; instead proves supporting `innerSafeSet_invariant` **under `driftBound`**. Tier-2 recovery theorems are `sorry` (deferred) | ✅ under fairness (`FairSpec`, TLC) / no fairness needed (nuSMV, total deterministic) |
| **P4** `q ∉ O` (Tier 2) | ✅ one-step (part of `closedLoopT2_safeRegion'`); all-iterate **conditional** on per-step `speedBound` | ✅ `ObstacleInv: !InObstacle` |

- **Under which controller:** P1–P3 hold under Tier 1 `g`; P1–P4 under Tier 2 `g₂`.
- **Under which assumptions:** P1 needs `Valid + speedBound + dtSmall`
  (+ `Obstacle.Valid` for Tier 2 / P4). P2 needs `Valid + velBound`. S_in
  invariance (P3 support) needs `Valid + driftBound`.
- **Guarantee-strength caveat:** Lean = universal over ℝ⁶ and all valid params;
  TLA+/nuSMV = exhaustive but only over the finite fixed-point abstraction.

---

## J. Certificate candidate

The proof is **barrier / forward-invariance** based — **not** Lyapunov (there is
no point equilibrium; see B). The engine should register these as **candidate
barrier certificates** whose discrete invariance conditions become obligations.

### Primary candidate — geofence box barrier (P1), Tier 1
- **Type:** barrier / invariant-set indicator (sublevel set `B(q) ≤ 0`).
- **Expression:**
  ```python
  B_geofence(q) = max(q1Min-q1, q1-q1Max, q2Min-q2, q2-q2Max, q3Min-q3, q3-q3Max)
  ```
  Safe set = `{B_geofence ≤ 0} = S`. Level constant `0`.
- **Discrete invariance condition (one-step):**
  `B_geofence(q) ≤ 0  ⟹  B_geofence( f(x).q ) ≤ 0`, on `{speedBound, dtSmall}`.
  (Lean discharges this per-axis: `safe_axis_h_lower/upper`, `safe_axis_v_lower/upper`.)

### Velocity-bound candidate (P2)
- **Type:** invariant (per-axis ∞-norm) barrier on velocity.
- **Expression (per-axis):**
  ```python
  B_vel(v) = max(abs(v1) - Bh, abs(v2) - Bh, abs(v3) - B3)     # <= 0 is velBound
  ```
- **Decrease/invariance:** `B_vel(v) ≤ 0 ⟹ B_vel(f(x).v) ≤ 0`, **unconditional**
  under `Valid`. This is the self-reproducing certificate (proved for all iterates).

### Obstacle candidate (P4), Tier 2
- **Type:** barrier keeping the state out of the **open** box `O`.
- **Expression:** safe iff `h_O(q) ≥ 0`, i.e. candidate barrier
  ```python
  B_obstacle(q) = -h_O(q)        # <= 0  means q not in O
  # h_O(q) = max(o1Min-q1, q1-o1Max, o2Min-q2, q2-o2Max, o3Min-q3, q3-o3Max)
  ```
- **Invariance (one-step):** `q ∉ O ⟹ f(x).q ∉ O`, on
  `{speedBound, Obstacle.Valid}`. The braking band `βi` (with `dt·Bh ≤ βi`,
  `dt·B3 ≤ β3`) is the buffer that makes this hold.

### Inner-set candidate (P3 support, NOT a clean invariant)
- `S_in` (`innerSafeSet`) is invariant **only under the extra state-dependent
  `driftBound`** — record `driftBound` as a required side-condition, not a global
  invariant. There is **no** verified Lyapunov/ranking function for the liveness
  P3 (the discrete progress measure is open / deferred).

---

## K. Proof obligations (mirror these as generated obligations)

Each: predicate, region it must hold on, assumptions. Stated for closed loop
`f` (Tier 1) / `f₂` (Tier 2). `q⁺ = f(x).q`, `v⁺ = f(x).v`.

1. **Controller admissibility.** `g(x) ∈ U` for all `x ∈ ℝ⁶`.
   *Region:* all of `ℝ⁶`. *Assumes:* `Valid` (and `Obstacle.Valid` for `g₂`).
   *(Lean `controller_admissible` / `controllerT2_admissible`.)*

2. **P1 one-step geofence invariance.** `q ∈ S ⟹ q⁺ ∈ S`.
   *Region:* `{ x : q∈S }`. *Assumes:* `Valid, speedBound(v), dtSmall`.
   Decomposes per-axis into 6 obligations (lower/upper × 3 axes).
   *(Lean `closedLoop_safe`.)*

3. **P2 one-step velocity invariance.** `velBound(v) ⟹ velBound(v⁺)`.
   *Region:* `{ x : velBound(v) }`. *Assumes:* `Valid`. Per-axis:
   `abs(vi + dt·controlH(...)) ≤ uh·dt` and the vertical analogue.
   *(Lean `closedLoop_velBound`; iterate via induction `iterate_velBound`.)*

4. **S_in one-step invariance (P3 support).**
   `q ∈ S_in ⟹ q⁺ ∈ S_in`. *Region:* `{ x : q∈S_in }`.
   *Assumes:* `Valid, driftBound(q,v)`. Key sublemmas: on `S_in` the controller
   collapses to `0` horizontally and `uHov` vertically (`controlH_zero_inner`,
   `controlV_hover_inner`). *(Lean `innerSafeSet_invariant`.)*

5. **P4 one-step obstacle avoidance (Tier 2).** `q ∉ O ⟹ q⁺ ∉ O`.
   *Region:* `{ x : q∈S, q∉O }`. *Assumes:* `Valid, Obstacle.Valid,
   speedBound, dtSmall`. Sublemmas: displacement bound
   `abs(dt·vi + ½dt²·u) ≤ uh·dt²`; `outside_low_stays`/`outside_high_stays`
   (if already ≥βi clear of a face, one step keeps it clear); avoidance branch
   keeps-out lemmas. *(Lean `not_inObstacle_preserved`, combined into
   `closedLoopT2_safeRegion'` = P1∧P4 one-step.)*

6. **All-iterate P1∧P4 (Tier 2), conditional.**
   `q∈S' ∧ (∀k<n: speedBound(v_k)) ⟹ (f₂^n x).q ∈ S'`.
   *Assumes:* `Valid, Obstacle.Valid, dtSmall`, **plus per-step `speedBound`**
   (carried explicitly because `speedBound` is not self-reproducing).
   *(Lean `iterate_safeRegion'_under_speedBound`, corollary
   `closedLoopT2_obstacle_under_speedBound`.)*

7. **P3 recovery (liveness) — OPEN.** `∃ N, (f^N x).q ∈ S_in` from the guard
   band (and the obstacle-aware analogue to `S_in \ O_plus_b`).
   *Assumes:* needs a discrete ranking/progress measure (not supplied).
   **Currently `sorry` in Lean (deferred); discharged only by the model checkers
   on the finite abstraction** (TLC under fairness; nuSMV without, since total +
   deterministic).

---

## L. Reference scenarios

### (1) Deterministic SAFE rollout
- **Tier:** 1, controller `g`. **Params:** the MC instantiation (Section E,
  unscaled): box `[-1,1]²×[0,2]`, `dh=d3Low=d3High=1/4`, `uh=uHov=1, u3Min=0,
  u3Max=2`, `dt=1/4`.
- **Initial condition (inside `X_init = S_in × {velocities}`):**
  `q0 = (0, 0, 1)` (geometric center, well inside `S_in = [-3/4,3/4]²×[1/4,7/4]`),
  `v0 = (1/4, 0, 0)` (= `Vmax` on axis 1; scaled `(8,0,0)`).
- **Horizon / step:** `N = 8` steps (= the model-checkers' reachability diameter),
  `dt = 1/4`.
- **Expected qualitative behavior:** drone coasts in +x with hover holding
  altitude; as `q1` approaches the band `q1 ≥ 3/4` it triggers `-uh` braking,
  decelerates, and never leaves `S`; `‖v‖` stays ≤ `v_max`; altitude stays at 1
  (hover). P1, P2 hold throughout.

### (2) Boundary-approaching / margin scenario (Tier 2, the load-bearing corner)
- From the nuSMV non-vacuity check (paper Remark, App. data). **Scaled** admissible
  initial state `q̂ = (18,18,32)`, `v̂ = (-8,-8,0)`; **unscaled**
  `q = (9/16, 9/16, 1)`, `v = (-1/4, -1/4, 0)`, obstacle
  `O = (-1/4,1/4)²×(3/4,5/4)`, bands `β = 1/4`.
- **With the correct dilated alignment:** avoidance engages in time; `q ∉ O`
  holds (P4 true).
- **With the bare (undilated) slab:** the drone coasts diagonally to
  `q̂ = (7,7,32)` (`q = (7/32,7/32,1)`) — **inside `O`** — before braking engages.
  This is the measured-margin / boundary-violation test: it demonstrates the
  buffer `βi ≥ dt·Bh` is exactly what provides the one-step braking margin.

---

## M. Visualization

- **Primary phase plane:** for a horizontal axis, plot **position `q1` (x-axis)
  vs. velocity `v1` (y-axis)** — shows the guard-band switching surfaces
  `q1 = q1Min+dh` and `q1 = q1Max-dh` and the `v1`-sign flip lines, and the
  invariant box `[q1Min,q1Max] × [-Bh,Bh]`.
  - Ranges (MC units): `q1 ∈ [-1.1, 1.1]`, `v1 ∈ [-0.35, 0.35]` (slightly beyond
    `±Vmax = ±0.25`). Units: length L vs L/T.
- **Spatial projection (Tier 2):** plot the **horizontal plane `(q1, q2)`** at
  fixed altitude `q3 ≈ 1` (obstacle mid-height), showing the geofence box
  `[-1,1]²`, the inner box, the open obstacle `(-1/4,1/4)²`, the dilated buffer
  `[-1/2,1/2]²`, and a trajectory braking around the corner (the scenario L-2).
  Ranges `q1,q2 ∈ [-1.1,1.1]`.
- **Altitude phase plane:** `q3` vs `v3 ∈ [-0.35,0.35]`, `q3 ∈ [-0.1, 2.1]`,
  showing floor/ceiling guard bands at `q3 = 1/4` and `q3 = 7/4`.

---

# TIER 2 — FULL SPECIFICATION (interior obstacle / no-fly zone)

*Verified in all three arms (Lean Tier2, `tla/tier2/DroneTLCV2.tla`,
`nusmv/DroneTier2.smv`). Reuses Tier 1 verbatim and adds an obstacle. Sections
mirror A–N; "unchanged from Tier 1" is stated plainly where it holds.*

## Tier 2 — Dynamics vs. Tier 1

**Equations of motion: IDENTICAL to Tier 1.** Tier 2 is the *same* point-mass
double integrator with the *same* exact ZOH sampled-data map `F(x,u)`, the same
`dt`, the same `e3=(0,0,1)`, the same unit gravity drift. There is **no** drag,
**no** attitude/rotational dynamics, **no** nonlinear thrust, **no** mass/inertia
change, and **no** inter-axis coupling. Lean reuses `Tier1.updateOpenLoop`
unchanged — deliberately there is **no** `Tier2/Dynamics.lean`; the TLA+/nuSMV
update equations are byte-for-byte the Tier 1 ones.

The added "complexity" lives in exactly three places, and nowhere else:
1. **Sets** — the safe region becomes the **nonconvex** `S' = S \ O`, where `O`
   is an open axis-aligned obstacle box strictly interior to `S_in`.
2. **Controller** — `g → g₂`: two obstacle-braking branches per axis overlay the
   Tier 1 law.
3. **Property** — adds **P4** `□(q ∉ O)`.

The closed loop `f₂(x) = F(x, g₂(x))` stays **deterministic and single-valued**
(outdegree 1), so this is *not* a hybrid/branching extension — only the geometry
and feedback law change.

## Tier 2 — State space

Unchanged from Tier 1: `x = (q,v) ∈ ℝ³×ℝ³ ≅ ℝ⁶`, dimension **6**, axis 2 =
altitude. **No added state variables.** Obstacle bounds `oiMin/oiMax` and bands
`βi` are constant parameters, not states.

## Tier 2 — Dynamics

Identical to §C (reprinted for completeness):
```python
q1_next = q1 + dt*v1 + (dt**2/2)*(u1 - 0)
q2_next = q2 + dt*v2 + (dt**2/2)*(u2 - 0)
q3_next = q3 + dt*v3 + (dt**2/2)*(u3 - 1)
v1_next = v1 + dt*(u1 - 0)
v2_next = v2 + dt*(u2 - 0)
v3_next = v3 + dt*(u3 - 1)
```
Closed loop `f₂(x) = F(x, g₂(x))`. Exact ZOH (no Euler/RK approximation), as in
Tier 1.

## Tier 2 — Inputs

- **Controls:** identical to Tier 1. `u ∈ U = [-uh,uh]×[-uh,uh]×[u3Min,u3Max]`;
  emitted alphabet `U_ctrl = {-uh,0,uh}² × {u3Min,uHov,u3Max}` (unchanged).
- **Disturbance:** **none** (deterministic; Tier 3 only).

## Tier 2 — Parameters

All Tier 1 parameters (Section E) **plus** the obstacle (units L for extents/bands):

| Symbol | Meaning | Numeric (MC, unscaled) | Scaled (F=32) |
| --- | --- | --- | --- |
| `o1Min,o1Max` | obstacle x-extent (**open**) | `-1/4, 1/4` | `-8, 8` |
| `o2Min,o2Max` | obstacle y-extent (**open**) | `-1/4, 1/4` | `-8, 8` |
| `o3Min,o3Max` | obstacle altitude extent (**open**) | `3/4, 5/4` | `24, 40` |
| `β1,β2,β3` (`δO`) | per-axis avoidance/dilation band | `1/4, 1/4, 1/4` | `8, 8, 8` |

Derived closed dilated box `O⊕β = [o_iMin-β_i, o_iMax+β_i]`:
MC unscaled `[-1/2,1/2]×[-1/2,1/2]×[1/2,3/2]` (scaled `[-16,16]²×[16,48]`),
which sits inside `S_in = [-3/4,3/4]²×[1/4,7/4]`. The obstacle parameters reuse
the Tier 1 actuator limits — **no new thrust parameters**.

## Tier 2 — Controllers (full symbolic law `g₂`)

`g₂` is the Tier 1 guard-band law with two obstacle-braking branches **prepended**
(avoidance overrides geofence) per axis. Dilated-alignment flags (open/strict
cross-section — see disagreement flag below):
```python
aligned1(q) = (o2Min-b2 < q2 < o2Max+b2) and (o3Min-b3 < q3 < o3Max+b3)
aligned2(q) = (o1Min-b1 < q1 < o1Max+b1) and (o3Min-b3 < q3 < o3Max+b3)
aligned3(q) = (o1Min-b1 < q1 < o1Max+b1) and (o2Min-b2 < q2 < o2Max+b2)
```
Per-axis components (full, every branch; `Piecewise`, first true branch wins):
```python
# Horizontal axes i in {1,2}  (Lean ctrlH2):  al = aligned_i(q)
def u_horiz2(qi, vi, qiMin, qiMax, oiMin, oiMax, bi, al):
    if (oiMin - bi <= qi <= oiMin) and al and (vi > 0):  return -uh   # lower face, moving in -> brake (-)
    if (oiMax <= qi <= oiMax + bi) and al and (vi < 0):  return  uh   # upper face, moving in -> brake (+)
    # ---- fall back to Tier 1 geofence rule ----
    if qi <= qiMin + dh and vi < 0:                      return  uh
    if qi >= qiMax - dh and vi > 0:                      return -uh
    return 0

# Vertical axis  (Lean ctrlV2):  al = aligned3(q)
def u_vert2(q3, v3, o3Min, o3Max, b3, al):
    if (o3Min - b3 <= q3 <= o3Min) and al and (v3 > 0):  return u3Min # below floor, rising into O -> max net descent
    if (o3Max <= q3 <= o3Max + b3) and al and (v3 < 0):  return u3Max # above ceiling, sinking into O -> max net ascent
    # ---- fall back to Tier 1 vertical rule ----
    if q3 <= q3Min + d3Low  and v3 < 0:                  return u3Max
    if q3 >= q3Max - d3High and v3 > 0:                  return u3Min
    return uHov
```
`g₂(x) = (u_horiz2(q1,v1,q1Min,q1Max,o1Min,o1Max,b1,aligned1),
u_horiz2(q2,...,aligned2), u_vert2(q3,...,aligned3))`.

- **Emitted alphabet:** still `U_ctrl` (avoidance thrusts `±uh`, `u3Min`, `u3Max`
  are already alphabet members) ⟹ `g₂(x) ∈ U_ctrl ⊆ U` (Lean
  `controllerT2_admissible`).
- **Single-valuedness:** guaranteed by `Obstacle.Valid` (below): (1) puts the
  obstacle bands inside `S_in`, disjoint from the geofence bands; (2) keeps the
  two obstacle-side buffer ranges `[oMin-β,oMin]` and `[oMax,oMax+β]` disjoint.
  Corrections on different axes act independently (componentwise), so no
  tie-break is needed near edges/corners.

> **Disagreement flags (controller):**
> - **Alignment open vs. closed.** Lean `aligned_i` uses **strict `<`** (open
>   dilated cross-section); the paper (App. `app:tier2`) writes alignment with
>   **closed `[·,·]`** intervals. Differs only on the dilated-slab boundary.
> - **Tie-break `<`/`>` vs `≤`/`≥`.** As in Tier 1, Lean uses strict
>   outward-motion tests; TLA+/nuSMV use non-strict. Use the **strict** (Lean)
>   convention as canonical.

## Tier 2 — Assumptions

Inherits Tier 1 `Params.Valid`, `speedBound`, `dtSmall`, `driftBound`
(Section G). **Adds** `Obstacle.Valid` (Lean; = paper Assumption `ass:obstacle`):
```python
0 < b1, 0 < b2, 0 < b3                                   # bands positive
o1Min<o1Max ; o2Min<o2Max ; o3Min<o3Max                 # nonempty obstacle
# (1) O (+) b  inside  S_in  (no interference with geofence band):
q1Min+dh    <= o1Min-b1 ; o1Max+b1 <= q1Max-dh
q2Min+dh    <= o2Min-b2 ; o2Max+b2 <= q2Max-dh
q3Min+d3Low <= o3Min-b3 ; o3Max+b3 <= q3Max-d3High
# (2) separation (single-valued controller):
2*b1 < o1Max-o1Min ; 2*b2 < o2Max-o2Min ; 2*b3 < o3Max-o3Min
# (3) braking adequacy (one-step drift fits in band, at the velocity cap):
dt*Bh <= b1 ; dt*Bh <= b2 ; dt*B3 <= b3
```
Dependence: (1) → P1 geofence invariance does not conflict with avoidance and
inner-set collapse holds; (2) → `g₂` single-valued / admissible; (3) → **P4**
obstacle avoidance (the braking margin).

> **Disagreement flag (separation, strict vs. non-strict).** Lean (2) is
> **strict** `2βi < dim`. The paper's Assumption `ass:obstacle`(i) is
> **non-strict** `o_iMax-o_iMin ≥ 2δO`. The MC instantiation has obstacle
> dimension **exactly** `2δO` (e.g. `o1Max-o1Min = 1/2 = 2·β1`), which satisfies
> the paper's `≥` **with equality** but is the **boundary case excluded by
> Lean's strict `<`**. So the literal fixed-point numbers are *not* a valid
> instance of the Lean `Obstacle.Valid` predicate (Lean is parametric and never
> uses these numbers; single-valuedness still holds at equality, so this is a
> conservative-vs-tight mismatch, not a soundness gap).

## Tier 2 — Sets (sublevel, `g(x) <= level`)

```python
# UNSAFE obstacle (OPEN box; resting on a face is SAFE):
h_O(q) = max(o1Min-q1, q1-o1Max, o2Min-q2, q2-o2Max, o3Min-q3, q3-o3Max)
#   q in O  iff  h_O(q) <  0          (strict, open)
#   q not in O iff h_O(q) >= 0

# SAFE region (nonconvex): S' = S \ O = { g_S(q) <= 0  AND  h_O(q) >= 0 }
#   g_S as in Section H.  Candidate combined barrier (both <= 0 == safe):
B_safe2(q) = max( g_S(q) , -h_O(q) )          # <= 0  iff  q in S'

# Braking buffer (gating + initial-set only; NOT kept invariant):
O_plus_b      = { o_iMin-b_i <= q_i <= o_iMax+b_i  (all i) }   # closed
obstacleBuffer = O_plus_b \ O                                  # B_O
innerSafeSet'  = S_in \ O_plus_b                               # Tier-2 recovery target
```
- **Safe set:** `S' = S \ O`. **Unsafe sets:** complement of `S`; **and** the
  open obstacle `O`.
- **Concrete initial set** (Lean/MC `Init`):
  `X_init^(2) = (S_in \ O⊕β) × {velocities with speedBound}`. MC: `q ∈ S_in`,
  `q ∉ O⊕β`, `v ∈ {-Vmax,0,Vmax}³` (scaled `{-8,0,8}³`).

## Tier 2 — Safety property & what is actually established

P1 (geofence `S`), P2 (`‖v‖≤v_max`), P3 (recovery to **Tier 1** `S_in` — *geofence
recovery only*, not obstacle-aware), **P4** `□(q ∉ O)`.

| Property | Lean (real-valued, ∀ params + `Obstacle.Valid`) | TLA+/nuSMV (fixed-point) |
| --- | --- | --- |
| **P1** `S` invariant | ✅ one-step (geofence part of `closedLoopT2_safeRegion'`); all-iterate **conditional** on per-step `speedBound` | ✅ enumerated (`GeofenceInv` = `S\O`) |
| **P2** speed bound | ✅ one-step + **all iterates** (`closedLoopT2_velBound`, `iterate_velBoundT2`), unconditional under `Valid` | ✅ `SpeedInv` |
| **P3** recovery | ❌ **`sorry` (deferred)** — both `closedLoopT2_recovery` (to `S_in`) and `obstacleBuffer_recovery` (to `S_in\O⊕β`) are unproved liveness; needs a ranking measure. Supporting `innerSafeSet'_step_innerSafeSet` proved under `driftBound` | ✅ geofence recovery to Tier-1 `S_in` (TLC FairSpec / nuSMV no fairness). Obstacle-aware recovery **not** checked |
| **P4** `q ∉ O` | ✅ one-step (`not_inObstacle_preserved`, in `closedLoopT2_safeRegion'`); all-iterate **conditional** on per-step `speedBound` (`closedLoopT2_obstacle_under_speedBound`) | ✅ `ObstacleInv: !InObstacle` |

- **Holds under:** `g₂`. **Assumes:** `Valid + Obstacle.Valid + speedBound +
  dtSmall` for P1∧P4; `Valid` for P2; `driftBound` for the inner-set support.
- **Honesty note:** P3 (recovery) is **model-checked only**, on the finite
  abstraction, and only in its geofence form. Lean proves **no** recovery at
  Tier 2. The obstacle-aware recovery (to `S_in \ O⊕β`) is verified by **no**
  arm.

## Tier 2 — Certificate candidates

- **Nonconvex safe-region barrier (P1∧P4):** `B_safe2(q) = max(g_S(q), -h_O(q))`,
  type **barrier**, level `0`, safe set `{B_safe2 ≤ 0} = S'`. Discrete
  invariance: `B_safe2(q) ≤ 0 ⟹ B_safe2(f₂(x).q) ≤ 0` on
  `{speedBound, dtSmall, Obstacle.Valid}`. Lean encodes this as the conjunction
  `safeRegion'` and proves one-step invariance `closedLoopT2_safeRegion'`; the
  obstacle half `-h_O ≤ 0` is the avoidance barrier whose margin is the band
  `βi ≥ dt·Bh` (resp. `dt·B3`).
- **Velocity barrier (P2):** identical to Tier 1
  `B_vel(v) = max(|v1|-Bh, |v2|-Bh, |v3|-B3)`, self-reproducing, unconditional.
- **Inner-set (P3 support):** `S_in` is preserved from `innerSafeSet'` **only
  under `driftBound`** (and only to the *Tier 1* `S_in`, since `¬dilatedObstacle`
  is **not** invariant — trajectories may legitimately enter the braking buffer).
  No Lyapunov/ranking certificate exists for the liveness itself.

## Tier 2 — Proof obligations

1. **`g₂` admissibility.** `g₂(x) ∈ U` ∀ `x`. *Region:* `ℝ⁶`. *Assumes:* `Valid`.
   *(Lean `controllerT2_admissible`.)*
2. **P2 one-step.** `velBound(v) ⟹ velBound(f₂(x).v)`. *Region:*
   `{velBound(v)}`. *Assumes:* `Valid`. *(`closedLoopT2_velBound`; iterate
   `iterate_velBoundT2`.)*
3. **P1 one-step geofence.** `q ∈ S ⟹ f₂(x).q ∈ S`. *Region:* `{q∈S}`.
   *Assumes:* `Valid, Obstacle.Valid, speedBound, dtSmall`. Per-axis
   (`safe_axis_h2_lower/upper`, `safe_axis_v2_lower/upper`).
4. **P4 one-step avoidance.** `q ∉ O ⟹ f₂(x).q ∉ O`. *Region:* `{q∈S, q∉O}`.
   *Assumes:* `Valid, Obstacle.Valid, speedBound, dtSmall`. Sublemmas:
   displacement bound `|dt·vi + ½dt²·u| ≤ uh·dt²`; `outside_low/high_stays`
   (already clear of a face by ≥βi stays clear); `avoidance_low/high_keeps_out`
   (braking thrust keeps `q⁺` outside the face); per-axis "outside-or-unaligned"
   case split. *(`not_inObstacle_preserved`.)*
5. **P1∧P4 one-step combined.** `q∈S' ⟹ f₂(x).q∈S'`.
   *(`closedLoopT2_safeRegion'`.)*
6. **All-iterate P1∧P4 (conditional).**
   `q∈S' ∧ (∀k<n: speedBound(v_k)) ⟹ (f₂^n x).q ∈ S'`. *Assumes:*
   `Valid, Obstacle.Valid, dtSmall` **+ per-step `speedBound`** (not
   self-reproducing). *(`iterate_safeRegion'_under_speedBound`,
   `closedLoopT2_obstacle_under_speedBound`.)*
7. **Inner-set step (P3 support).** `q∈innerSafeSet' ∧ driftBound ⟹ f₂(x).q ∈
   S_in` (Tier 1 inner set). *Region:* `{innerSafeSet', driftBound}`. *Assumes:*
   `Valid, Obstacle.Valid`. Key: off the closed `O⊕β`, all avoidance guards are
   false so `g₂ = g` (`controllerT2_eq_controller_of_not_dilated`), reducing to
   Tier 1. *(`innerSafeSet'_step_innerSafeSet`.)*
8. **P3 recovery (liveness) — OPEN.** `∃N, (f₂^N x).q ∈ S_in` from the geofence
   guard band, and `∃N, (f₂^N x).q ∈ S_in\O⊕β` from the obstacle buffer.
   *Assumes:* a discrete ranking/progress measure (not supplied). **`sorry` in
   Lean; only the geofence form is model-checked.**

## Tier 2 — Reference scenarios

### (1) Deterministic SAFE rollout
- **Tier 2, controller `g₂`, MC params** (Section E + obstacle above).
- **Initial condition** (inside `X_init^(2) = (S_in\O⊕β) × {vel}`): single-axis
  approach to the obstacle. `q0 = (9/16, 0, 1)` — outside `O⊕β` horizontally
  (`q1 = 0.5625 > 1/2`), aligned on axes 2,3 (`q2=0∈(-1/2,1/2)`,
  `q3=1∈(1/2,3/2)`). `v0 = (-1/4, 0, 0)` (= `-Vmax` on axis 1; scaled
  `(-8,0,0)`).
- **Horizon / step:** `N = 8`, `dt = 1/4`.
- **Expected behavior:** drone coasts in `-x` toward the obstacle's `+x` face
  (`o1Max=1/4`); upon entering the upper-face buffer `q1 ∈ [1/4, 1/2]` while
  aligned and `v1 < 0`, the avoidance branch fires `u1 = +uh`, braking it to rest
  at/above `q1 = 1/4` (`∂O` is safe). `q ∉ O` throughout (P4), `q ∈ S` (P1),
  `‖v‖ ≤ v_max` (P2). Altitude held at 1 by hover.

### (2) Boundary / VIOLATION scenario (the load-bearing diagonal corner)
- From the nuSMV non-vacuity re-run (paper App. data). **Scaled**
  `q̂ = (18,18,32)`, `v̂ = (-8,-8,0)`; **unscaled** `q = (9/16, 9/16, 1)`,
  `v = (-1/4,-1/4,0)`. Obstacle/bands as above; `dt=1/4`, `N=8`.
- **With correct dilated alignment:** avoidance engages on both horizontal axes
  before the corner; `q ∉ O` holds (P4 true).
- **With the bare (undilated) slab** (alignment checked on `[oMin,oMax]` instead
  of `[oMin-β,oMax+β]`): the drone coasts diagonally to `q̂ = (7,7,32)`
  (`q = (7/32, 7/32, 1)`) — **inside `O`** — before braking engages. nuSMV
  returns **P1 and P4 false** with this counterexample. This is the
  measured-margin test: it shows the dilation/band is exactly the one-step
  braking margin (`βi ≥ dt·Bh`), not vacuous.

## Tier 2 — Visualization

- **Primary spatial projection:** horizontal plane `(q1, q2)` at fixed altitude
  `q3 ≈ 1` (obstacle mid-height). Draw: geofence `[-1,1]²`, inner box
  `[-3/4,3/4]²`, **open** obstacle `(-1/4,1/4)²`, closed dilated buffer
  `[-1/2,1/2]²`, and the corner trajectory (scenario 2) braking around the
  corner. Ranges `q1,q2 ∈ [-1.1, 1.1]`, units L.
- **Vertical slice:** `(q1, q3)` plane at `q2 ≈ 0`, showing the obstacle
  `(-1/4,1/4)×(3/4,5/4)` and floor/ceiling bands; ranges `q1∈[-1.1,1.1]`,
  `q3∈[-0.1,2.1]`.
- **Phase planes:** as Tier 1 (`q1` vs `v1`, `q3` vs `v3`), additionally marking
  the obstacle-face thresholds.

---

# TIER 3 — FULL SPECIFICATION (adversarial wind) — DESIGN-ONLY / UNVERIFIED

> **Verification status up front:** Tier 3 exists **only as a mathematical design
> in the paper** (App. `app:tier3`). There is **no Lean module, no TLA+ module,
> and no nuSMV file** for Tier 3. **Nothing is proved or model-checked.** Every
> claim below is a *specification/design intent*, not an established result. Do
> **not** mark any Tier 3 property verified.

## Tier 3 — Dynamics vs. Tier 1

**Equations of motion: GENUINELY DIFFERENT from Tier 1 — but only by an additive
bounded disturbance term.** Tier 3 adds a wind disturbance `d ∈ W = [-w,w]³` that
enters the acceleration channel **additively and matched to the control**
(`u − e3 → u − e3 + d`). The system remains a **linear double integrator** — there
is still **no drag (no `−c·v` velocity-dependent term), no attitude/rotational
dynamics, no nonlinear thrust, no mass/inertia change, and no inter-axis
coupling** — but the RHS gains the `d` term and the closed loop becomes
**set-valued / branching** (one successor per admissible `d`).

> **Disagreement / terminology flag.** The repo summaries (`CLAUDE.md`) describe
> Tier 3 as **"drag/wind"**, but the paper's actual Tier 3 math is **purely
> additive wind** `d` — there is **no drag term**. True linear drag would be
> `v̇ = u − e3 − c·v + d` (a different, dissipative RHS); the paper does **not**
> model it. **[IMPLICIT]** If drag is later wanted, it is a distinct dynamics
> change not covered by the current design.

Continuous (forced EOM, App. `app:tier3`): `q̈ = u − e3 + d`, i.e.
```python
q1_dot = v1;  v1_dot = u1 - 0 + d1
q2_dot = v2;  v2_dot = u2 - 0 + d2
q3_dot = v3;  v3_dot = u3 - 1 + d3
```
Discrete exact ZOH map `F : ℝ⁶ × U × W → ℝ⁶` (`d` held constant per interval,
same exact double-integral derivation as Tier 1 — **not** Euler):
```python
# state x=[q1,q2,q3,v1,v2,v3]; control u=[u1,u2,u3]; disturbance d=[d1,d2,d3]; e3=[0,0,1]
q1_next = q1 + dt*v1 + (dt**2/2)*(u1 - 0 + d1)
q2_next = q2 + dt*v2 + (dt**2/2)*(u2 - 0 + d2)
q3_next = q3 + dt*v3 + (dt**2/2)*(u3 - 1 + d3)
v1_next = v1 + dt*(u1 - 0 + d1)
v2_next = v2 + dt*(u2 - 0 + d2)
v3_next = v3 + dt*(u3 - 1 + d3)
```
**Branching closed loop** (set-valued): `f3(x) = { F(x, g(x), d) : d ∈ W }`.

## Tier 3 — State space

Unchanged: `x = (q,v) ∈ ℝ⁶`, dimension **6**, axis 2 = altitude. The disturbance
`d` is an **input, not a state** (no augmentation). **No added state variables.**

## Tier 3 — Inputs

- **Controls:** same control box as Tier 1, `u ∈ U =
  [-uh,uh]×[-uh,uh]×[u3Min,u3Max]`.
- **Disturbance (NEW):** `d = (d1,d2,d3) ∈ W = [-w,w]³`, `w > 0`. **Adversarial /
  worst-case:** the safety requirement is quantified over **every** admissible
  disturbance sequence `(d_k) ∈ W^ℕ` (zero-sum safety game, control maximizing
  safety vs. disturbance minimizing it; disturbance gets the benefit of the
  doubt). Consequently the closed loop is **set-valued / branching** (outdegree
  > 1): each state has one successor per `d ∈ W`.

## Tier 3 — Parameters

All Tier 1 parameters **plus**:

| Symbol | Meaning | Units | Numeric |
| --- | --- | --- | --- |
| `w` | wind/disturbance bound (per axis, ∞-norm box) | L/T² | **none fixed** (no MC instantiation; Tier 3 unimplemented) |

Derived (design): the velocity bound is **enlarged** to absorb the per-step
disturbance increment `dt·w` (paper): `v_max^(3) = v_max + dt·w`. Exact per-axis
constants are not separately derived in the paper. **[IMPLICIT]** a natural
robust per-axis bound is `Bh^(3) = (uh + w)·dt` horizontally and
`B3^(3) = max(u3Max-1, 1-u3Min)+w)·dt` vertically, but the paper only states the
`+dt·w` enlargement, not these closed forms.

## Tier 3 — Controllers

**No controller is fixed in any artifact.** The paper proves that *a* robust
guard band **exists** under the authority condition, but does not pin down a
concrete `g`. **Design intent** (what a re-implementation should use):

- Reuse the Tier 1 guard-band law `g` (or Tier 2 `g₂`), emitting the same finite
  alphabet `U_ctrl`, with guard-band widths / braking margins **enlarged** so
  that corrective authority strictly dominates the worst-case wind on every axis.
- The corrective branches are unchanged in form; what changes is that the
  `dtSmall`-style braking-margin inequalities must hold with the extra `+w`
  acceleration (see Assumptions). **[IMPLICIT]** the exact enlarged widths are a
  design choice; the paper gives the *existence* condition, not the synthesis.

## Tier 3 — Assumptions

Inherits Tier 1 `Params.Valid`. **Adds** the **authority condition** (paper
Prop. `prop:authority`) — corrective thrust must beat the worst-case wind on each
axis:
```python
uh - w          > 0      # horizontal: brake -uh vs outward gust +w
u3Max - 1 - w   > 0      # vertical floor: max-up thrust vs gravity + downdraft
1 - u3Min - w   > 0      # vertical ceiling: min thrust vs gravity + updraft
```
Dependence: this is exactly the condition under which a **robust
controlled-invariant** subset of `S` exists (it shrinks as `w` grows); all robust
safety claims (P1, P2) depend on it. **Robust braking-margin** analogue of
`dtSmall` **[IMPLICIT]**: the per-step worst-case displacement under net
acceleration `(±uh + w)` etc. must fit inside the (enlarged) guard band —
required for robust geofence invariance. **Fairness** assumption for P3: the wind
does not adversarially hold the drone in the guard region indefinitely (without
it an adversary defeats any liveness guarantee).

## Tier 3 — Sets (sublevel, `g(x) <= level`)

Geometry of `S`, `S_in`, `B` is **unchanged** from Tier 1 (Section H). The
substantive change is that forward invariance must hold against all `d`, so the
*verified* invariant is a **robust controlled-invariant subset** `Σ ⊆ S`:
```python
# Robust invariant set Sigma (design): the largest subset of S with
#   for all d in W:  x in Sigma  ==>  F(x, g(x), d) in Sigma
# Sigma is a sub-box of S that shrinks as w grows; no closed form given in artifacts.
g_Sigma(x) <= 0      # candidate sublevel description of Sigma (UNSPECIFIED constants)
```
- **Safe set:** `S` (target); the *invariant witness* is `Σ ⊆ S`.
- **Unsafe set:** complement of `S` (plus `O` if combined with Tier 2 — not done).
- **Initial set:** `X_init^(3) ⊆ Σ` (must start in the robust invariant subset).
  **No concrete set is specified** (Tier 3 unimplemented).

## Tier 3 — Safety property & what is actually established

Robust analogues, quantified over all `(d_k) ∈ W^ℕ`:
- **P1 (robust geofence):** `□(q ∈ S)` for every disturbance sequence.
- **P2 (robust speed bound):** `□(‖v‖ ≤ v_max^(3))`, `v_max` enlarged by `dt·w`.
- **P3 (robust recovery):** `□(q ∈ B → ◇ q ∈ S_in)` under the **fairness**
  assumption above.

| Property | Lean | TLA+ | nuSMV | Paper |
| --- | --- | --- | --- | --- |
| P1 robust | ❌ none | ❌ none | ❌ none | design: holds on `Σ` under authority cond. |
| P2 robust | ❌ none | ❌ none | ❌ none | design: enlarged `v_max` |
| P3 robust | ❌ none | ❌ none | ❌ none | design: under fairness |

**Nothing is proved or model-checked at Tier 3.** The paper establishes only the
*algebraic authority condition* and the *existence* of a robust guard band; it
does not verify the closed loop in any tool.

## Tier 3 — Certificate candidate

- **Type:** robust **barrier** / robust-controlled-invariant-set certificate (not
  Lyapunov; still no point equilibrium).
- **Candidate:** the geofence barrier `B_geofence(q)` (Section J) restricted to a
  shrunken sub-box `Σ`, with the **robust** one-step invariance condition:
  ```python
  for all d in W:   B_Sigma(x) <= 0  ==>  B_Sigma( F(x, g(x), d) ) <= 0
  ```
  Equivalently, the worst-case successor (adversary maximizing the barrier) must
  remain ≤ 0. **No certificate has been formalized**; `Σ` and its level constants
  are unspecified.

## Tier 3 — Proof obligations (would-be; NONE discharged)

1. **Robust admissibility.** `g(x) ∈ U` ∀ `x` (carries over from Tier 1 if `g`
   reused).
2. **Authority lemma.** `uh-w>0 ∧ u3Max-1-w>0 ∧ 1-u3Min-w>0` ⟹ each wall's
   worst-case disturbed velocity step is reversible. *(Paper Prop.
   `prop:authority` — the only Tier 3 result with a proof, and it is a pencil
   proof, not mechanized.)*
3. **Robust P1.** `∀ d∈W: x∈Σ ⟹ F(x,g(x),d).q ∈ Σ`. *Region:* `Σ`. *Assumes:*
   authority + robust braking margin.
4. **Robust P2.** `∀ d∈W:` enlarged `velBound` invariant. *Assumes:* authority.
5. **Robust P3 (liveness).** recovery from `B` to `S_in` under **fairness**;
   needs a ranking measure robust to the adversary.

All five are **open** (unimplemented in every arm).

## Tier 3 — Reference scenarios

**Illustrative only — unverified.** Suppose hypothetically `uh=1, u3Min=0,
u3Max=2, dt=1/4` and a wind bound `w = 1/2` (authority holds: `uh-w = 1/2 > 0`,
`u3Max-1-w = 1/2 > 0`, `1-u3Min-w = 1/2 > 0`).

- **(1) "Safe under worst wind" rollout:** drone near the `+x` wall,
  `q0 = (3/4, 0, 1)` (`= q1Max-dh`), `v0 = (1/4, 0, 0)` (outward). Controller
  emits `u1 = -uh = -1`; adversary picks the worst gust `d1 = +w = +1/2`. Net
  horizontal acceleration `= -1 + 1/2 = -1/2 < 0`, so outward velocity strictly
  decreases each step — the drone still does not cross `q1Max = 1`. Branching:
  every `d1 ∈ [-1/2, 1/2]` gives `≤ -1/2 + ... `; the worst case still brakes.
  Horizon `N = 8`, `dt = 1/4`. Expected: stays in `S` for **all** disturbance
  sequences (robust P1) — *design expectation, not verified*.
- **(2) Authority-violation / margin scenario:** set `w = 1` (so `uh - w = 0`).
  Now at the `+x` wall the worst gust `d1 = +1` exactly cancels braking
  (`-uh + w = 0`): outward velocity no longer decreases, and over enough steps a
  trajectory drifts out of `S` — the boundary case showing the authority
  condition `uh - w > 0` is **load-bearing**. *Illustrative; not model-checked.*

## Tier 3 — Visualization

- **Phase plane `q1` vs `v1`** with a **branching tube**: from one state, plot the
  *set* of successors over `d1 ∈ [-w,w]` (a reachable interval, not a point) to
  show the set-valued closed loop. Overlay the **shrunken robust invariant box**
  `Σ` vs. the full geofence `S`. Ranges `q1 ∈ [-1.1,1.1]`,
  `v1 ∈ [-(v_max+dt·w)-0.1, (v_max+dt·w)+0.1]` (enlarged velocity axis).
- **`w`-sweep plot:** robust-invariant-set width vs. `w` (shrinks to empty as `w`
  approaches the authority limit `uh`), illustrating the existence boundary.

---

## N. Cross-artifact consistency

| Aspect | paper | Lean | TLA+ | nuSMV |
| --- | --- | --- | --- | --- |
| Model | canonical real-valued discrete | exact real-valued discrete, **parametric over ℝ⁶** | finite **fixed-point** abstraction | **same** fixed-point abstraction as TLA+ |
| `dt` | symbolic; `1/4` in MC remark | **symbolic** (theorem hypotheses) | `1/4` | `1/4` |
| Scale | F=32 (App. A.2) | none (real-valued) | F=32 | F=32 |
| Velocities | ℝ³ | ℝ³ | lattice `{-8,0,8}³` | lattice `{-8,0,8}³` |
| Controller tie-break | (controller def. strict) | **strict** `<,>` | **non-strict** `≤,≥` | **non-strict** `≤,≥` |
| P2 form | `‖v‖ ≤ v_max` (norm) | **per-axis** `velBound` | `‖v̂‖² ≤ 192` | `‖v̂‖² ≤ 192` |
| P3 recovery | stated | **not proved** (sorry/deferred) | proved (FairSpec) | proved (no fairness) |
| Domain escape | n/a | n/a (all ℝ⁶) | `overflow` latch | `overflow` latch |

**Same dynamics or different abstractions?** All arms share the *same closed-form
update equations*. Lean verifies them over the continuum; TLA+ and nuSMV verify a
**finite quantization** of them (binary lattice). TLA+ ↔ nuSMV are *identical
discrete systems* — they must agree on the reachable-state count
(**Tier 1: 3,709,475**; **Tier 2: 2,949,788**; both at **diameter 8**, outdegree 1).

**Where timestep / bounds / quantization differ:**
- `dt`: symbolic in paper/Lean, fixed `1/4` in TLA+/nuSMV.
- Bounds: Lean carries `speedBound`, `dtSmall`, `driftBound`, `Obstacle.Valid` as
  *explicit hypotheses*; the MC arms bake the corresponding numeric choices into
  the lattice (e.g. `δ̂=8`, `β̂=8`, `u3Max=64`) so the conditions hold by
  construction and need no hypothesis.
- Quantization: only TLA+/nuSMV quantize (lattice + `overflow` latch). Divisions
  are exact for the reachable alphabet, so the quantization restricts the domain
  without introducing rounding — it is a *modeling abstraction*, recorded in G as
  an assumption rather than as arithmetic.
- **Tie-break (`≤` vs `<`):** the one genuine semantic divergence — the MC arms
  and Lean are not literally the same transition system at zero-velocity threshold
  states. Use the **strict** (Lean) convention as canonical.
- P2 is stated three ways (norm / per-axis / scaled-square) that coincide
  numerically: per-axis `|v_i| ≤ 1/4` ⟺ `‖v‖ ≤ (√3)/4 = √192/32`, the MC bound.

### N.1 Dynamics / controller / quantization differences, **per tier**

| | Tier 1 | Tier 2 | Tier 3 |
| --- | --- | --- | --- |
| **EOM vs. Tier 1** | baseline double integrator | **identical** (`F` reused verbatim; no `Tier2/Dynamics`) | **different**: `+d` additive matched wind; **set-valued/branching**. No drag/attitude/inertia |
| **What changes** | — | sets (`S\O`), controller (`g₂`), +P4 | dynamics (`d`), inputs (`W`), robust property forms |
| **Controller** | `g` (guard-band) | `g₂` (avoidance overlay, single-valued under `Obstacle.Valid`) | **none fixed** (design intent: enlarged guard band) |
| **Determinism** | deterministic (outdeg 1) | deterministic (outdeg 1) | **branching** (outdeg >1, one per `d∈W`) |
| **Disturbance** | none | none | `d∈W=[-w,w]³`, adversarial |
| **Lean arm** | present, `sorry`-free (P1,P2; P3 support) | present, P1/P2/P4 proved (recovery `sorry`) | **absent** |
| **TLA+ arm** | `DroneTLCV1.tla` | `tla/tier2/DroneTLCV2.tla` | **absent** |
| **nuSMV arm** | `DroneTier1.smv` | `DroneTier2.smv` | **absent** |
| **Quantization (MC)** | F=32, Δt=1/4, vel `{-8,0,8}³` | **same lattice** + open obstacle `Ô=(-8,8)²×(24,40)`, `β̂=8` | n/a (no MC) |
| **Reachable states (TLC=nuSMV)** | **3,709,475** | **2,949,788** | n/a |
| **Diameter / max outdegree** | 8 / 1 | 8 / 1 | n/a |

### N.2 Verification status of each property, **per tier and per artifact**

Legend: ✅ established · ⚠️ conditional/partial · MC = model-checked on the finite
abstraction only (not a universal proof) · ❌ not done · — not applicable.

| Property | Tier | Lean (∀ ℝ⁶, params) | TLA+ (fixed-pt) | nuSMV (fixed-pt) |
| --- | --- | --- | --- | --- |
| **P1** geofence `□(q∈S)` | 1 | ✅ one-step; iterate via P2 | ✅ MC | ✅ MC |
| | 2 | ⚠️ one-step ✅; all-iterate conditional on per-step `speedBound` | ✅ MC (`S\O`) | ✅ MC (`S\O`) |
| | 3 | ❌ | ❌ | ❌ |
| **P2** speed `□(‖v‖≤v_max)` | 1 | ✅ one-step **+ all iterates** (unconditional) | ✅ MC | ✅ MC |
| | 2 | ✅ one-step **+ all iterates** (unconditional) | ✅ MC | ✅ MC |
| | 3 | ❌ | ❌ | ❌ |
| **P3** recovery `□(q∈B→◇q∈S_in)` | 1 | ❌ not proved (only `S_in` invariance under `driftBound`) | ✅ MC (FairSpec) | ✅ MC (no fairness) |
| | 2 | ❌ `sorry` (geofence **and** obstacle-aware forms) | ✅ MC, geofence form only | ✅ MC, geofence form only |
| | 3 | ❌ | ❌ | ❌ |
| **P4** avoidance `□(q∉O)` | 1 | — | — | — |
| | 2 | ⚠️ one-step ✅; all-iterate conditional on per-step `speedBound` | ✅ MC | ✅ MC |
| | 3 | — | — | — |

**Honesty discipline (restated):**
- **Nothing is marked "proved" that is only model-checked.** "✅ MC" means
  exhaustive over the **finite fixed-point abstraction only** — *not* a
  universal/real-valued guarantee. Only the Lean ✅ entries are universal proofs.
- **P3 is never a Lean proof** at any tier (Tier 1: only `S_in` invariance under
  `driftBound`; Tier 2: explicit `sorry`). Recovery is established **only** by the
  model checkers, **only** on the abstraction, and **only** in its geofence form.
- **Tier 2 all-iterate P1/P4 are conditional** in Lean on the non-self-reproducing
  per-step `speedBound`; the unconditional all-time `□` form is not a Lean proof.
- **Tier 3 is entirely design-only** — no module, nothing proved or model-checked
  in any arm. The sole Tier 3 result is the pencil-proof *authority condition*
  (Prop. `prop:authority`).

### N.3 Tier-specific cross-artifact disagreements (flagged)

- **Tier 2 alignment open vs. closed:** Lean `aligned_i` strict `<` (open) vs.
  paper closed `[·,·]`. (Tier 2 — Controllers.)
- **Tier 2 separation strict vs. non-strict:** Lean `2βi < dim` vs. paper
  `≥ 2δO`; MC obstacle dim **= 2δO exactly**, so the MC numbers satisfy the paper
  but not Lean's strict predicate. (Tier 2 — Assumptions.)
- **Tie-break `<`/`>` vs `≤`/`≥`:** all tiers, Lean strict vs. MC non-strict;
  diverges only at zero-velocity threshold states. Canonical = strict (Lean).
- **Tier 3 "drag" vs wind:** repo `CLAUDE.md` says "drag/wind", but the paper's
  Tier 3 is **additive wind only** (no `−c·v` drag term). (Tier 3 — Dynamics.)
- **Tier 3 `v_max` enlargement:** paper states `+dt·w` absorption only; no
  closed-form robust bound or concrete `w` exists. **[IMPLICIT]**

---

*End of specification.*
