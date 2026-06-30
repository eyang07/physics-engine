/**
 * Inline KaTeX math span for the Verification React shell.
 *
 * Math stays in KaTeX; the surrounding labels are plain text. Shared by the
 * certificate traces and the assumptions block so neither re-implements the
 * render-into-a-ref dance.
 */
import { useEffect, useRef } from "react";
import katex from "katex";

export function MathSpan({
  latex,
  className,
}: {
  latex: string;
  className?: string;
}): JSX.Element {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (ref.current) {
      katex.render(latex, ref.current, { throwOnError: false, displayMode: false });
    }
  }, [latex]);
  return <span ref={ref} className={className} />;
}
