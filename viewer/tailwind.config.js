/**
 * Tailwind configuration for the viewer.
 *
 * Tailwind is adopted only for the Verification-domain React shell (FE-055 and
 * later). The Systems domain stays on its vanilla CSS, so two safeguards keep
 * Tailwind from perturbing the physics renderers and their visual baselines:
 *
 *   - `preflight` is disabled: Tailwind's global element reset would otherwise
 *     restyle the Systems-domain DOM and churn its visual baselines.
 *   - utilities are emitted only for classes actually used in the verification
 *     React sources, so an unused setup adds nothing to the bundle.
 *
 * FE-063 surfaces the design tokens from `src/design/tokens.css` into this theme
 * as the single source of truth: the type scale, the four status hues plus the
 * new `--pending` graphite, the radius scale, and the light-technical sans/mono
 * faces all resolve to the same CSS custom properties the vanilla rules use, so
 * a Tailwind utility and a hand-written rule can never drift apart.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/verification/**/*.{ts,tsx}"],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      // The verification status taxonomy — the only saturated color in the view.
      colors: {
        measured: "var(--measured)",
        candidate: "var(--candidate)",
        required: "var(--required)",
        violated: "var(--violated)",
        pending: "var(--pending)",
      },
      // Light-technical faces: sans/mono only; KaTeX stays inside math spans.
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      // One type scale (tokens.css `--text-*`).
      fontSize: {
        xs: "var(--text-xs)",
        sm: "var(--text-sm)",
        base: "var(--text-base)",
        lg: "var(--text-lg)",
      },
      fontWeight: {
        normal: "var(--weight-regular)",
        medium: "var(--weight-medium)",
        bold: "var(--weight-bold)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        pill: "var(--radius-pill)",
      },
    },
  },
  plugins: [],
};
