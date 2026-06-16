/**
 * The Verification "dossier" figure palette.
 *
 * A light, print-grade color set for the state-space figure and certificate
 * traces. Kept explicit here — not read from the global dark chrome `theme` —
 * so the verification figure renders as a typeset journal figure regardless of
 * the app's dark chrome, and so the canvas never depends on the cached `:root`
 * token values. Mirrors the scoped CSS tokens in tokens.css
 * (`#verificationDomain`); keep the two in step.
 *
 * Color is semantic, not decorative: the four status hues each encode one true
 * thing about a claim's standing and are the only saturated color in the figure.
 */
export const dossier = {
  // Neutrals — cool vellum + blue-graphite ink.
  paper: "#FAFBFC",
  paperEdge: "#E7EBEE",
  ink: "#16212B",
  graphite: "#586573",
  hairline: "#D2DAE0",
  grid: "#E3E8ED",

  // Semantic status hues (print-muted).
  measured: "#15706B",
  candidate: "#8A5A22",
  required: "#50457E",
  violated: "#9E382C",
} as const;

// Region-role colors on the figure, mapped to the semantic system: the safe set
// reads measured-teal, the initial set required-indigo, the domain graphite, and
// any unsafe set the violation brick. Each set is drawn as a soft wash under a
// firmer outline so the regions read as filled areas, not just contours.
export const dossierRole: Record<string, { stroke: string; fill: string }> = {
  safe: { stroke: dossier.measured, fill: "rgba(21, 112, 107, 0.10)" },
  initial: { stroke: dossier.required, fill: "rgba(80, 69, 126, 0.11)" },
  domain: { stroke: dossier.graphite, fill: "rgba(88, 101, 115, 0.05)" },
  unsafe: { stroke: dossier.violated, fill: "rgba(158, 56, 44, 0.09)" },
};
