# Verification View Redesign — Design Plan

> Status: **implemented** (light dossier direction approved). This document is the
> design record: the brief, token system, layout, and signature it was built to.

## 1. Brief & subject grounding

- **Subject.** A formal **safety-verification dossier** for a control system —
  the flagship being a guard-band feedback-controlled, geofenced drone reduced to
  its discrete `(q1, v1)` axis, certified by a box / forward-invariance **barrier
  certificate** `B(x)`.
- **Audience.** Control-theory, formal-methods, and cyber-physical-systems
  researchers and reviewers — people who read proofs, set-builder notation,
  reachability figures, and theorem environments.
- **The page's single job.** State, *honestly*, **how far a safety claim has been
  established**: what is claimed (obligations), what certificate is proposed
  (candidate), what the numerical evidence shows (measured margins), and the gap
  that still requires external discharge. The standing thesis of the whole engine
  — *it proposes and organizes; external sound methods dispose; nothing here is
  proved* — is the spine of the design, not a footnote.

## 2. The one aesthetic risk (and the decision behind it)

**Recast the Verification domain from a dark instrument panel into a light,
typeset "verification dossier" — a document, not a dashboard.**

The current view is deep-ink `#0d1117` with a single luminous-amber accent. Per
the calibration in our design guidance that is, almost exactly, **AI-default look
#2** ("near-black background with a single bright accent") — and it appears
*regardless of subject*. "Research grade" does not look like an oscilloscope; it
looks like a typeset spec, a proof script, a journal figure. So the deliberate
move is a register change: you leave the live, dark **Systems** instrument and
enter the formal, light **Verification** report. The light/dark contrast between
the two domains is intentional and communicates the shift.

This is the pivotal decision; everything below derives from it. **Guarding
against the *other* default** (warm cream + high-contrast serif + terracotta): our
paper is **cool blue-graphite, not warm cream**; the serif is a **restrained
transitional book serif, not a didone**; and there is **no single decorative
accent** — color is a semantic system mapped to the rigor taxonomy.

> _If we must keep the domain dark for app cohesion:_ the same token *system*
> ports to a dark dossier — invert paper→ink, keep the four semantic status hues
> at higher luminance, keep the typography and layout verbatim. The layout,
> typography, and signature do not depend on the flip; only the neutrals do.

## 3. Token system

### Color — a print-muted neutral base + a 4-hue *semantic* status system

Color is never decorative here. The four status hues each encode one true thing
about a claim's standing, and they are the only saturated color on the page.

| Token | Hex | Role |
|---|---|---|
| `--paper-bg` | `#E7EBEE` | page field (cool vellum, seats the panels) |
| `--paper` | `#FAFBFC` | panel / figure / card surface |
| `--ink` | `#16212B` | primary text, rules, axes (blue-graphite, not pure black) |
| `--graphite` | `#586573` | secondary text, captions, labels |
| `--hairline` | `#D2DAE0` | rules, dividers, figure grid |
| `--measured` | `#15706B` | measured evidence (deep teal) |
| `--candidate` | `#8A5A22` | candidate certificate — proposed, not certified (bronze) |
| `--required` | `#50457E` | external-required obligation — awaiting discharge (indigo) |
| `--violated` | `#9E382C` | measured violation (brick) |

Each status hue also has a ~10%-alpha tint for badge fills. Rationale: the rigor
ladder and the obligation taxonomy *are* the content, so the palette is the
taxonomy. No glows, no gradients (print has neither); hierarchy comes from weight,
rules, small-caps, and whitespace.

### Type — anchored on the mathematics

The page already typesets math in **Computer Modern via KaTeX**. We make that the
typographic anchor: the dossier reads as if set by a math system. The serif is
*reserved for formal statements* (math, obligation claims, set definitions) so the
reader learns **serif = a formal claim**; prose and chrome stay quieter.

| Role | Face | Use |
|---|---|---|
| Math / formal | **Computer Modern** (KaTeX `KaTeX_Math`/`KaTeX_Main`) | every obligation statement, set definition, certificate symbol — promoted, not incidental |
| Prose / headings | **`KaTeX_Main`** (Computer Modern text — already loaded by KaTeX) | problem title, theorem-prose, section heads. The report is *literally set in the same face as the math* — the strongest, zero-cost form of "typeset by a math system." No new webfont needed; fully offline. |
| Identifiers / data | **IBM Plex Mono** (keep) | region/obligation ids, series names, signed margins, set-element coordinates |
| Labels / eyebrows | `KaTeX_Main`, uppercase + tracking | structural labels (DOCKET, STATE SPACE, OBLIGATIONS). Computer Modern lacks true small-caps, so labels use tracked uppercase rather than faux small-caps. |

**Space Grotesk is dropped from this view** — it is the generic technical
grotesque and carries none of the subject. Anchoring prose on `KaTeX_Main`
unifies prose and math into one Computer Modern voice (a refinement on the
original "add Source Serif 4" idea: more coherent, and needs no font fetch).
Document-scale type ramp (tight, not hero-sized — this is a dense report):

```
eyebrow/label   11px  small-caps  tracking .12em  graphite
problem title   23px  serif 600
section head    13px  serif small-caps tracking .08em
body / prose    14.5px serif  line-height 1.55
inline math     ~15px (KaTeX sized to body x-height)
data / mono     12.5px Plex Mono
caption/micro   11.5px graphite
```

### Layout — a dossier with a certification spine

One concept: **a docket index on the left; a document on the right whose masthead
is the rigor scale, whose body is a figure paired with a proof-obligation table,
and whose appendix is the full IR.** Concise = tabular obligations + one
disciplined figure, not scattered cards.

### Signature — the **certification scale** (the rigor ladder, reimagined)

The single element the page is remembered by, and the one place boldness is
spent: the four-rung rigor ladder, today a vertical stack of cards, becomes a
**horizontal certification scale** that sits as the document's masthead and is
referenced by every obligation's status. It shows the four rungs — ① measured
② certified-numeric ③ certificate-accepted ④ deductively-proved — with the current
position filled and **the gap to higher rungs drawn explicitly** (open rungs, a
dashed "not yet established" track). It makes the engine's central honesty thesis
the most visually prominent, true-to-subject thing on the page. Everything else
stays quiet.

## 4. Wireframes

Desktop (≥ 1040px): docket rail + two-column document.

```
┌────────────┬──────────────────────────────────────────────────────────────┐
│  DOCKET    │  Drone — geofence axis                  drone-geofence-axis    │ ← title (serif) + model id (mono)
│            │  Claim status — measured evidence · not discharged             │ ← honesty line
│ ▸ drone    │  ┌ RIGOR ─────────────────────────────────────────────────┐   │
│   geofence │  │ ①measured ●━━② num-cert ○┄┄③ cert ○┄┄④ proved ○         │   │ ← SIGNATURE: certification scale
│   ◑ rung 1 │  └──────────────────────────────────────────────────────────┘   │
│   4 obl ·  │                                                                │
│   3 cand   │  ┌ STATE SPACE  𝒮 = {x : B(x) ≤ 0} ┐ ┌ OBLIGATIONS ──────────┐ │
│            │  │                                 │ │ B(F(x)) ≤ 0   on 𝒮    │ │ ← obligation = theorem row
│ ▸ spring   │  │   phase-plane figure:           │ │  within  speedBound,  │ │   statement (math, serif/CM)
│   ◐ rung 1 │  │   · safe set 𝒮 (filled)         │ │          dtSmall      │ │   assumptions (mono, muted)
│            │  │   · barrier sublevel sets       │ │  margin +0.01   ◑ held│ │   margin (mono) + status hue
│ ▸ pendulum │  │   · controlled rollout          │ ├───────────────────────┤ │
│   ◐ rung 1 │  │   · worst sampled point ⊙       │ │ x₀ ∈ 𝒮_in            │ │
│            │  │                                 │ │  margin +0.257  ◑ held│ │
│            │  └─────────────────────────────────┘ ├───────────────────────┤ │
│            │  ┌ CERTIFICATE TRACES (small mult.)┐ │ … 2 more              │ │
│            │  │  B ▁▂▃   V ▁▁▂   B_in ▂▅█        │ └───────────────────────┘ │
│            │  └─────────────────────────────────┘                          │
│            │  ▸ APPENDIX — dynamics · regions · candidates · assumptions · IR│ ← collapsed; full IR
└────────────┴──────────────────────────────────────────────────────────────┘
```

Narrow (< 1040px, incl. today's cramped rail): single column, same order —
masthead (title + claim status + rigor scale) → figure → obligation table →
certificate traces → appendix. The obligation rows stack their statement / meta /
status vertically (the layout we just hand-fixed becomes the system default).

## 5. Component-by-component direction

- **Docket (catalog, left).** A typeset index, not buttons-as-tiles. Each entry:
  model id (mono), problem title (serif), a small **rung glyph** (current rigor
  position) + counts (`4 obl · 3 cand`). No `01/02/03` numbering — the problems
  are a catalog, not a sequence, so numbering would encode a falsehood. Active
  entry marked by an ink rule on the leading edge, not a fill.
- **Masthead.** Problem title (serif), model id (mono, right-aligned), and the
  **claim-status line** as a formal one-liner. Then the certification scale.
- **Certification scale (signature).** Horizontal four-rung gauge; filled =
  established, open + dashed = not yet. Tooltip per rung from the existing ladder
  copy. The same rung glyph is the status token reused in the docket and the
  obligation rows — one scale, referenced everywhere.
- **State-space figure (the canvas).** Re-themed to light: paper ground, ink
  axes, hairline grid, **filled** safe/inner sets (soft teal/graphite washes, not
  just outlines), barrier sublevel rule, the rollout in ink with a measured-hue
  head, and the worst sampled point as an annotated `⊙` with its margin. A
  set-builder caption (`𝒮 = {x : B(x) ≤ 0}`) names the figure. This is a journal
  figure: precise, labeled, quiet — boldness lives in the scale, not here.
- **Certificate traces.** The lanes become **small multiples** beneath the figure
  — one compact sparkline per candidate, each labeled with its symbol and `≤ 0`
  baseline; the inner-set trace honestly crossing positive. Shared playhead.
- **Obligation table (right).** The heart of "concise + research." Each obligation
  is a theorem-environment row: the **claim as math** (serif/CM), its assumptions
  (mono, muted, "within …"), the **signed margin** (mono, tabular), and a status
  marked in its semantic hue + rung glyph. Dense, scannable, aligned columns.
- **Appendix (IR detail).** Collapsed by default. Dynamics, regions, candidates,
  assumptions, and the download/inspect exports, set as a typeset appendix
  (definition lists, not cards).

## 6. Copy pass

Words are design material; tune them to the dossier voice, active and specific.

- "Safety properties (measured)" → **"Proof obligations"** with a measured-status
  column (the parenthetical migrates into the status hue/glyph).
- "holds on samples" → **"held (sampled)"**; "violated on samples" →
  **"violated (sampled)"**; keep "awaiting external discharge".
- Honesty banner → a single masthead line: **"Claim status — measured evidence ·
  not discharged."** Keep set-builder labels verbatim (`𝒮`, `𝒮_in`, `B(x)`).
- Keep failure/empty states as direction (already honest): missing data →
  regen instruction; no certificate series → state it.

## 7. Quality floor (build to it, don't announce it)

- Responsive to mobile (single-column collapse defined above; the obligation rows
  reuse the fix already shipped).
- Visible keyboard focus (ink/teal ring, not removed).
- `prefers-reduced-motion`: the figure "draw-in" and any reveal become instant;
  trajectory playback remains user-controlled.
- Light-theme contrast meets AA for body and status text on `--paper`.

## 8. Implementation notes (for the build phase, not now)

- **Scope a token layer** to the domain: `#verificationDomain { … }` (or a
  `.dossier` theme class) overrides the chrome neutrals to paper/ink **for this
  view only**; the Systems domain stays dark. Files: `src/design/tokens.css`
  (scoped block), `src/styles.css` (verification rules).
- **Canvas theming.** `verificationStage.ts` / `pendulumCanvas.ts`
  (`drawStageBackground`) and `certificateLanes.ts` read global `theme.ts`
  colors; the light figure needs a **verification-scoped color set** passed to
  those draw paths rather than the global dark theme.
- **Add Source Serif 4** self-hosted in `src/design/fonts.css` (subset: regular +
  600 + small-caps/italic as needed); drop Space Grotesk usage from
  verification rules.
- **CSS specificity caution** (a known failure mode): scope all dossier rules
  under the domain selector and avoid element-vs-class padding/margin selectors
  that cancel between sections; verify section spacing after the theme scope is
  introduced.
- Touch points: `index.html` (verification domain markup may regroup into
  masthead / two-column), `main.ts` (docket rendering, figure draw-in),
  `verificationPanel.ts` (masthead, certification scale, obligation table,
  appendix), `verificationStage.ts` + `certificateLanes.ts` (light figure +
  small multiples), `styles.css`, `tokens.css`, `fonts.css`.

## 9. Self-critique (defaults found and removed)

- **Dark + single amber accent** → was AI-default #2; replaced with cool-vellum
  light + a 4-hue *semantic* status system.
- **Cream + didone + terracotta** (the other default) → avoided: cool not warm,
  transitional book serif not didone, semantic palette not a decorative accent.
- **`01/02/03` numbering** → rejected for the docket; problems are a catalog, not
  a sequence, so numbering would assert false order.
- **Glows / gradients / drop shadows** → removed; a document uses rules, weight,
  and whitespace.
- **Hero "big number + gradient"** → not used; the hero is the certification
  scale, which carries the subject's actual thesis.
- **Generic vertical ladder-of-cards** → reimagined as the horizontal
  certification scale and made the signature.
```
