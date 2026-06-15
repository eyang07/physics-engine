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

---

*End of specification.*
