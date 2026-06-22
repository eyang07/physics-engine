# Verification UI Reconfiguration Plan

Status: approved design plan. Implementation is staged as task modules
**FE-055 … FE-066** in `task-queue.md` (Frontend Queue → "Verification UI
redesign" track). Pick up one module at a time.

## Context

The viewer's **Verification domain** is functionally rich but reads as a
decorative "dossier" rather than a serious verification pipeline. The current
register uses a light serif (Computer Modern / Georgia) paper theme remapped over
the shared layout classes, four separate HTML legend overlays on the state-space
canvas, a 4-rung "claim ladder," a dense obligation ledger, and a long collapsible
appendix. The information is honest and precise under the hood, but the
*presentation* is too dense, too ornamented, and does not put the
claim → assumptions → obligations → evidence → artifact chain front and center.

Goal: reconfigure the verification UI into a minimal, precise, formal-methods
workbench. Within 5 seconds a reader should know what model is verified, what
claim is under consideration, what is assumed, which obligations are discharged
vs. measured-only vs. failed vs. pending, what the state-space plot shows, and
what artifact is available. Measured evidence must be visually distinct from
proved/certified results; undischarged assumptions must be impossible to miss.

**Approved direction:**
- Stack: **migrate the Verification domain to React + Tailwind + Radix.**
- Theme: **light technical (no serif)** — keep a light/print-friendly background
  for paper-quality screenshots, but replace serif prose with sans + mono; KaTeX
  stays only for actual math expressions.

**Hard constraint — do NOT touch the physics animation system.** The Systems
domain (`threeScene.ts`, `pendulumCanvas.ts`, all `*Canvas.ts` physics renderers),
numerical integration, model dynamics, trajectory generation, and `PlaybackClock`
playback semantics are out of scope and must behave exactly as today. This plan
only changes the verification *shell*: information architecture, labels, visual
hierarchy, obligation display, the static/diagnostic state-space plot, and
artifact/certificate presentation.

---

## 1. Current-state audit

### Files that make up the verification UI (the redesign surface)
- `viewer/index.html` — `#verificationDomain` block: catalog rail, `verif-stage`
  masthead, figure+caption canvas, playback controls, certificate-lanes strip,
  obligations summary aside, collapsible details band.
- `viewer/src/verificationPanel.ts` — masthead, "Claim status" line, 4-rung
  certification scale, obligation ledger table, full collapsible appendix.
- `viewer/src/verificationStage.ts` — Canvas 2D state-space figure: regions
  (safe/unsafe/initial/domain), rollout polyline, playhead, violation/holds
  markers, and the four HTML legend overlays.
- `viewer/src/certificateLanes.ts` — per-candidate trace lanes (B, V, Ḃ vs.
  threshold) with worst-margin readout.
- `viewer/src/data/verification.ts` — IR types mirroring `engine/verification/ir.py`.
- `viewer/src/design/tokens.css` (`#verificationDomain` block) — the serif/paper
  theme remap and the four semantic status hues.
- `viewer/src/main.ts` — domain switching + orchestration that wires the above.

### Keep / simplify / rename / remove
- **Keep (semantics):** the IR data model, the rigor taxonomy (measured →
  certified-numeric → certificate-accepted → deductively-proved), signed worst
  margins (BE-036), `external-required` honesty, region roles, certificate series.
  These are correct and must survive verbatim in meaning.
- **Keep (animation boundary):** `PlaybackClock` and trajectory sampling from
  `playback.ts`; the rollout animation in the state-space plot reuses them
  unchanged.
- **Simplify:** the masthead (collapse eyebrow + title + model + status line into
  one compact header bar); the obligation ledger (table → scannable list with
  progressive disclosure); the rigor ladder (from a decorative 4-rung "track" into
  a compact reference popover + per-item badge).
- **Rename/relabel:** tighten verbose tooltip prose into short precise labels
  (see §4). Drop the word "dossier" from the primary UI.
- **Remove/replace:** the serif paper register (`--font-serif` remap); the four
  free-floating HTML legend overlays (`.verif-violation-legend`,
  `.verif-holds-legend`, `.verif-roles-legend`, `.verif-disturbance-annotation`)
  → fold into one compact, on-demand legend + selection-driven detail; the long
  always-expandable appendix prose → structured, collapsed-by-default sections.

### Why the current layout is not suitable for a verification pipeline
- **Serif paper theme** signals "report/essay," not "tool"; competes with the math.
- **Four separate overlays** on the plot create clutter and a legend-heavy read,
  violating "interpretable at a glance."
- **Claim ladder as a 4-rung track** spends prime vertical space on a static
  reference instead of the actual claim/obligation state.
- **Obligation ledger as a wide table** with inline glossary text is dense and
  hard to scan; status, rigor, margin, and assumptions compete equally.
- **No single, dominant verdict** — the reader cannot get the headline status in
  5 seconds.

---

## 2. Target UX principles
1. **One headline verdict.** The top bar states model, claim, and overall standing
   in one line with one dominant status token.
2. **Claim chain is the spine:** model → property/claim → assumptions →
   obligations → evidence → artifact, in that reading order.
3. **Evidence honesty is visual.** Measured ≠ certified ≠ proved is encoded by
   shape + fill + color, never by color alone, and never overstated.
4. **Progressive disclosure.** Show name + status + margin by default; reveal
   formal statement, dependencies, and discharge action on demand.
5. **Plot reads at a glance.** Safe/unsafe/rollout/initial/closest-approach are
   distinguishable without reading a legend; legend is confirmation, not decoding.
6. **Selection links panel ↔ plot.** Selecting an obligation highlights its
   geometry; hovering geometry surfaces the obligation.
7. **Minimal chrome.** Few panels, one type scale, restrained color, generous
   whitespace, no ornament that doesn't carry verification meaning.

---

## 3. Proposed layout

```
┌───────────────────────────────────────────────────────────────────────┐
│ TOP BAR  ◆ physics-engine   [Systems] [Verification]                    │
│  Model: <name>   Claim: <property>      ●  STATUS: external-required     │  ← one verdict
├──────────────┬──────────────────────────────────────┬───────────────────┤
│ DOCKET       │  STATE-SPACE  (diagnostic view)       │ OBLIGATIONS        │
│ (problem     │  ┌────────────────────────────────┐   │  assumptions ▸     │
│  list,       │  │ safe / unsafe / domain / init  │   │  ── obligations ── │
│  narrow,     │  │ rollout · closest approach ·   │   │  ▸ name  [status]  │
│  collapsible)│  │ optional barrier contour       │   │      margin -0.05  │
│              │  └────────────────────────────────┘   │  ▸ name  [status]  │
│              │  compact legend (on demand)           │  ...               │
│              │  ┌── certificate traces (tabs) ──┐    │ ── artifact ──     │
│              │  │ B≤0  V≤0  Ḃ≤0  (selected lane) │    │  export IR / pkg   │
├──────────────┴───┴───────────────────────────────┴───┴───────────────────┤
│ BOTTOM STRIP (collapsible): rollout playback ▸ · diagnostics · full detail │
└───────────────────────────────────────────────────────────────────────────┘
```

- **Top bar** (shared with Systems domain): brand + domain switch. In the
  verification domain it gains a compact identity line (Model / Claim) and a
  single overall status token.
- **Left rail** = docket (problem list), narrow and collapsible.
- **Center** = state-space diagnostic plot, dominant; certificate traces sit
  directly beneath it as selectable tabs (not always-on lanes).
- **Right panel** = the claim chain: active assumptions (top, unmissable),
  obligations list (scannable, progressive disclosure), artifact/export (bottom).
- **Bottom strip** = collapsed by default: rollout playback controls, diagnostics,
  and the full formal detail (dynamics, region definitions, enclosure boxes).
  Playback controls move here but keep identical behavior.

Rationale vs. a naive layout: assumptions belong in the right panel *above*
obligations (they gate every obligation), and certificate traces belong under the
plot (they are time-series evidence about the rollout), not in the bottom strip.

---

## 4. Verification vocabulary (precise labels)

Map existing/honest semantics to tight UI labels. Left = UI label; right = meaning.

**Overall claim status (one of):**
- `Discharged` — every obligation deductively proved or certificate-accepted.
- `Certified (numeric)` — sound numeric enclosure under stated assumptions; still
  not a theorem.
- `Measured only` — sampled evidence holds; not a certificate. (default demo case)
- `Counterexample` — at least one obligation violated on samples.
- `Pending external` — obligations awaiting external discharge (`external-required`).

**Per-obligation status badge (shape + color, see §5):**
- `proved` (deductively proved) — filled, indigo.
- `certificate-accepted` (sound method: SOS / barrier / Lyapunov / reachability).
- `certified-numeric` (validated enclosure over the stated box).
- `measured: holds` (sampled evidence satisfied — outline teal, not filled).
- `measured: violated` (≥1 sample breached — brick red).
- `pending` (`external-required`, not sampled — neutral gray, dashed).

**Evidence-kind chips:**
- `sampled evidence` (was: "measured" / "holds on samples").
- `numeric certificate` (was: "certified-numeric").
- `external theorem` (was: "externally discharged").
- `candidate` (proposed certificate function, not yet accepted).

**Structural labels:**
- `assumption` (active, undischarged precondition — amber, with "active" tag).
- `invariant candidate` (barrier/Lyapunov function under test).
- `safety property` (the obligation's claim over safe/unsafe sets).
- `counterexample` (a violating sample point + time).
- `margin` (signed slack to boundary; negative = inside unsafe set).
- `trace` (rollout time-series of a candidate value vs. its threshold).
- `disturbance set W` (kept; label as `assumption: disturbance set W`).

Tooltips carry the one-sentence honesty note (e.g., "sampled evidence — not a
proof"); the visible label stays short.

---

## 5. Visual language (light technical)

### Typography
- UI/labels/body: **IBM Plex Sans** (already self-hosted). Drop Georgia/CM prose.
- Identifiers, numbers, margins, region/obligation IDs, expressions baseline:
  **IBM Plex Mono**.
- Actual math: **KaTeX** (Computer Modern) — retained only for rendered formulae,
  not for UI prose. This is the one allowed serif, and only inside math spans.
- One type scale (reuse tokens): 11 / 13 / 15 / 20 px; weights 450 / 600 / 700.

### Spacing & layout
- Reuse the existing 4→56px spacing scale (`--space-1..6`).
- Panels separated by hairlines + whitespace, not borders/shadows stacked.
- Radius: 6px (chips/cards), pill for status tokens.

### Color semantics (light theme; status color is the only saturation)
Reuse and extend the existing four hues in `tokens.css` `#verificationDomain`:
- `proved / certificate-accepted` → indigo `--required` family (filled).
- `certified-numeric` → indigo, hatched/half-fill to read "numeric, not theorem."
- `measured: holds` → teal `--measured` (outline only — evidence, not proof).
- `assumption (active)` → ochre `--candidate` (amber) with an "active" dot.
- `measured: violated / counterexample / unsafe` → brick `--violated`.
- `pending external` → neutral graphite, dashed.
- Redundant encoding: shape/fill distinguishes proved (filled) vs. measured
  (outline) vs. pending (dashed) so status survives grayscale/screenshots.

### Badges
Compact pill = label + optional margin. At most two badges per obligation row
(status + one evidence chip); everything else behind disclosure.

### Plot styling & legend strategy
- Single coherent figure (see §6). No free-floating overlay stack.
- One compact legend, collapsible, anchored bottom-left; default shows only the
  marks actually present in the current problem.
- Selection-driven detail replaces always-on violation/holds tables: clicking an
  obligation surfaces its margin marker + value inline on the plot.

---

## 6. State-space visualization (diagnostic view only)

Redesign `verificationStage.ts`'s figure (NOT the physics pipeline). Layers,
bottom→top, with clear visual priority:
1. Light paper background + faint grid; **domain boundary** drawn as a firm
   neutral outline (currently a faint 5% fill — promote it to a clear boundary).
2. **Safe set** (teal outline + light fill) and **unsafe set** (brick fill, most
   saturated region) — unsafe should be the most visually alarming area.
3. **Initial set** (indigo outline).
4. Optional **invariant / barrier contour** (the candidate's level set) — drawn
   only when an invariant-candidate obligation is selected.
5. **Rollout / trajectory** (single ink polyline) + **initial condition** dot.
6. **Closest approach / minimum margin** marker (teal diamond) and any
   **counterexample** markers (brick ringed cross), labeled with signed margin.
7. Playhead dot (rollout animation, driven by existing `PlaybackClock`).

Interaction rules:
- **Hover geometry** → tooltip names the set/obligation and its margin.
- **Select obligation (right panel)** → highlight its region(s) + margin marker;
  dim unrelated layers; reveal its barrier contour if applicable.
- **Collapse nonessential layers** via the compact legend (toggle domain grid,
  barrier contour, holds markers).
- Default view shows only safe/unsafe/initial/rollout/closest-approach; everything
  else is opt-in to keep it glanceable.

The plot stays Canvas 2D; the drawing functions are reused/refactored into a
diagnostic renderer invoked imperatively from a React wrapper (see §8). No change
to physics, integration, or playback semantics.

---

## 7. Proof-obligations panel

Replace the wide table with a compact, formal, scannable list. Each row default:
```
▸  energy-barrier: non-increase            [pending]   margin −0.00
```
- **Collapsed row:** obligation name (mono) · status badge · signed margin chip.
- **Expanded (disclosure):**
  - formal-ish statement (KaTeX): e.g., `dB/dt ≤ 0 on {B ≤ 0}`.
  - evidence chip(s): `sampled evidence` / `numeric certificate` / `external theorem`.
  - **depends on:** assumption IDs (links that highlight the assumption block).
  - **certificate:** candidate name + worst-margin summary (links the trace tab).
  - **to discharge:** the action (e.g., "awaiting external SOS certificate").
- Assumptions block sits above the list: each active assumption as an amber row
  with its bound (KaTeX) and an "active / undischarged" tag — impossible to miss.
- No long prose; honesty notes live in tooltips.

---

## 8. Framework decision (React + Tailwind + Radix)

Adopt React + Tailwind + Radix **for the Verification domain shell only.** The
Systems domain stays vanilla to honor the animation constraint and avoid churn in
the physics renderers.

- **React (mounted into `#verificationDomain` as its own root):** componentizes
  the masthead, obligation list, assumption block, badges, legend, artifact panel.
  Systems domain keeps its current vanilla bootstrap; `main.ts` mounts/unmounts the
  React root on domain switch.
- **Tailwind:** configured to consume the existing design tokens (map
  `tokens.css` custom properties into the Tailwind theme) so spacing/type/status
  colors stay single-sourced. Replaces the verification-domain CSS in `styles.css`.
- **Radix primitives:** `Tooltip` (honesty notes), `Collapsible` (obligation
  disclosure, bottom strip), `Tabs` (certificate traces), `Dialog`/`Popover`
  (rigor-ladder reference, artifact export). Accessible, unstyled — styled by
  Tailwind.
- **State:** local React state + a small context for "selected obligation"
  (drives plot highlighting). No heavy state lib needed; avoid Zustand/Router
  unless multi-route scope appears later.
- **Canvas/Three boundary:** the state-space plot and certificate traces remain
  Canvas 2D. Wrap each in a React component that owns a `<canvas>` ref and calls
  the existing (refactored) imperative draw functions inside `useEffect`/RAF. The
  shared `PlaybackClock` and trajectory sampling are imported and used unchanged —
  no animation logic is reimplemented in React.
- **D3/Observable Plot/Pixi:** not adopted. Canvas 2D already renders the regions
  and is sufficient; adding a charting lib is unjustified churn.

Non-invasive refactor of the animation boundary: extract the pure drawing
routines in `verificationStage.ts` into a framework-free `renderStateSpace(ctx,
problem, selection, phase)` module so React only orchestrates *when* to draw, not
*how*. This preserves rollout behavior exactly and keeps physics logic out of React.

---

## 9. Acceptance criteria
- Overall verification status is understood within **5 seconds** (one headline
  token in the top bar).
- The state-space plot is readable **without** opening a legend-heavy explanation;
  safe/unsafe/rollout/closest-approach are distinguishable at a glance.
- Obligations are **scannable** (name · status · margin per row; detail on demand).
- **Measured** evidence is visually distinct (outline/teal) from **proved/
  certified** (filled/indigo) — distinct in grayscale too.
- **Undischarged assumptions are impossible to miss** (amber block above
  obligations, "active" tag).
- The shell scales from the **controlled-spring-regulator / pendulum-safety**
  demo to **drone / geofence / obstacle-avoidance** packages (multi-region,
  multi-obligation, disturbance set W) without layout breakage.
- The interface looks like a **serious research artifact** suitable for paper /
  project-page screenshots (light technical, sans+mono, no ornament).
- **Physics animation unchanged:** Systems domain and rollout playback behave
  byte-for-byte as before; `pytest -q`, `npm run build`, and `npm run test:visual`
  pass (visual baselines for Systems unchanged; verification baselines updated
  intentionally).

---

## Component tree (verification React root)
```
<VerificationApp>
  <TopBarIdentity model claim status/>          // model · claim · verdict token
  <DocketRail problems selected onSelect/>       // left, collapsible
  <StateSpacePanel>
     <StateSpaceCanvas problem selection phase/> // wraps existing Canvas draw
     <PlotLegend marks present/>                 // compact, on-demand
     <CertificateTraces tabs candidates/>        // Radix Tabs over canvas lanes
  </StateSpacePanel>
  <ClaimPanel>                                   // right
     <AssumptionsBlock assumptions/>             // amber, unmissable
     <ObligationList items selection onSelect>   // progressive disclosure
        <ObligationRow .../>                     // Radix Collapsible
     </ObligationList>
     <ArtifactPanel exports/>                    // IR / package download
  </ClaimPanel>
  <BottomStrip>                                  // Radix Collapsible
     <RolloutPlayback clock/>                    // reuses PlaybackClock
     <Diagnostics/> <FullDetail dynamics regions enclosures/>
  </BottomStrip>
</VerificationApp>
```

## Data-model assumptions
- React consumes the same IR (`data/verification.ts`) and proofStatuses /
  certificateSeries fields already exported — **no backend schema change required.**
- "Overall status" is derived in TS from existing per-obligation rigor/status
  (no new field needed initially); if a precomputed claim verdict is later wanted,
  that is a separate, documented backend addition (out of scope here).

## Visual design tokens (deltas to `tokens.css` `#verificationDomain`)
- Remove `--font-serif`/serif remap of `--font-display`/`--font-sans`; set UI font
  to IBM Plex Sans, keep `--font-mono`, restrict KaTeX to math spans.
- Keep the four status hues; add: `--pending` (graphite, dashed), fill/outline
  variants for proved-vs-measured redundancy.
- Surface Tailwind theme from these tokens (single source of truth).

## Risks
- **Animation entanglement:** mounting React must not perturb the Systems canvases
  or `PlaybackClock`. Mitigation: separate React root, no shared module rewrites,
  baseline diff Systems before/after the toolchain + extraction steps.
- **Token drift:** Tailwind + `tokens.css` could diverge. Mitigation: generate
  Tailwind theme from the CSS custom properties; single source.
- **Visual-test churn:** verification baselines will change intentionally; Systems
  baselines must not. Gate each step on a Systems-baseline no-diff check.
- **Scope creep into Systems migration:** explicitly out of scope; Systems stays
  vanilla.
- **Overstating status:** keep `external-required` honesty; "Measured only" must
  never render as "verified."

## How to verify end-to-end
- `cd viewer && npm run build` — type-check + bundle.
- `cd viewer && npm run dev` — manually drive: switch to Verification domain,
  load pendulum-safety and an intersection/geofence package; confirm verdict,
  assumptions, obligation disclosure, plot selection-highlighting, playback.
- `cd viewer && npm run test:visual` — Systems baselines unchanged; verification
  baselines updated deliberately.
- `pytest -q` — confirm no backend/export contract was touched.
- Screenshot the verification view at the pendulum-safety and a multi-region
  package to validate the 5-second-verdict and scalability acceptance criteria.

## Staged implementation checklist (tracked as FE-055 … FE-066 in `task-queue.md`)
1. **FE-055** — Add React + Tailwind + Radix; mount an empty React root in the
   verification domain (Systems untouched).
2. **FE-056** — Extract framework-free `renderStateSpace()` + certificate-lane draw
   (behavior-preserving).
3. **FE-057** — React wrappers `StateSpaceCanvas` + `CertificateTraces` over the
   extracted renderers (reuse `PlaybackClock`).
4. **FE-058** — `TopBarIdentity` with derived overall verdict.
5. **FE-059** — `AssumptionsBlock` (amber, unmissable).
6. **FE-060** — `ObligationList` with progressive disclosure.
7. **FE-061** — `ArtifactPanel` (IR / package export).
8. **FE-062** — `DocketRail` (problem list).
9. **FE-063** — Apply light-technical visual language + token deltas (drop serif).
10. **FE-064** — Replace the four legend overlays with one compact legend + linking.
11. **FE-065** — Move playback + full detail into a collapsible bottom strip.
12. **FE-066** — Update `docs/FRONTEND.md`; refresh verification visual baselines.

## Out of scope (explicit)
Physics animation/simulation/integration, model dynamics, trajectory generation,
playback semantics, and all Systems-domain renderers. Backend/IR schema changes.
