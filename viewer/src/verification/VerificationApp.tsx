/**
 * Root component for the Verification-domain React shell.
 *
 * FE-055 only stands up the React + Tailwind + Radix toolchain and proves the
 * root mounts/unmounts on domain switch. The shell renders nothing yet: the
 * legacy vanilla verification panel still draws the view, living alongside this
 * (empty) root inside `#verificationDomain`. Later tasks (FE-056+) migrate the
 * masthead, obligation list, assumptions block, plot wrappers, and artifact
 * panel into this tree.
 */
export function VerificationApp(): null {
  return null;
}
