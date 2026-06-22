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
 * Later tasks (FE-063) surface the design tokens from `src/design/tokens.css`
 * into this theme as the single source of truth.
 */
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/verification/**/*.{ts,tsx}"],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {},
  },
  plugins: [],
};
