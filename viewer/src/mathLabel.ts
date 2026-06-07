const GREEK: Record<string, string> = {
  alpha: "α",
  beta: "β",
  gamma: "γ",
  delta: "δ",
  theta: "θ",
  phi: "φ",
  lambda: "λ",
  mu: "μ",
  sigma: "σ",
  Omega: "Ω",
  ell: "ℓ",
};

const SUBSCRIPT: Record<string, string> = {
  "0": "₀",
  "1": "₁",
  "2": "₂",
  "3": "₃",
  "4": "₄",
  "5": "₅",
  "6": "₆",
  "7": "₇",
  "8": "₈",
  "9": "₉",
  "+": "₊",
  "-": "₋",
  "=": "₌",
  "(": "₍",
  ")": "₎",
  a: "ₐ",
  e: "ₑ",
  h: "ₕ",
  i: "ᵢ",
  j: "ⱼ",
  k: "ₖ",
  l: "ₗ",
  m: "ₘ",
  n: "ₙ",
  o: "ₒ",
  p: "ₚ",
  r: "ᵣ",
  s: "ₛ",
  t: "ₜ",
  u: "ᵤ",
  v: "ᵥ",
  x: "ₓ",
};

function latexAtomToText(atom: string): string {
  return atom.replace(/\\([A-Za-z]+)/g, (_match, command: string) => GREEK[command] ?? command);
}

function toSubscript(value: string): string {
  return value
    .replace(/\\mathrm\{([^}]*)\}/g, "$1")
    .replace(/\\([A-Za-z]+)/g, (_match, command: string) => GREEK[command] ?? command)
    .split("")
    .map((char) => SUBSCRIPT[char] ?? char)
    .join("");
}

export function mathLabel(label: string): string {
  return label
    .replace(/\\dot\{([^}]*)\}/g, (_match, inner: string) => `${latexAtomToText(inner)}̇`)
    .replace(/_\{\\mathrm\{([^}]*)\}\}/g, (_match, inner: string) => toSubscript(inner))
    .replace(/_\{([^}]*)\}/g, (_match, inner: string) => toSubscript(inner))
    .replace(/_([A-Za-z0-9])/g, (_match, inner: string) => toSubscript(inner))
    .replace(/\\mathrm\{([^}]*)\}/g, "$1")
    .replace(/\\([A-Za-z]+)/g, (_match, command: string) => GREEK[command] ?? command)
    .replace(/[{}]/g, "");
}
