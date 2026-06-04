/** The animated home-screen background: drifting orbits and luminous dust. */
import { theme } from "./design/theme";

export function renderHome(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D, now: number): void {
  const pixelRatio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.max(1, Math.floor(width * pixelRatio));
  canvas.height = Math.max(1, Math.floor(height * pixelRatio));
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

  const t = now * 0.001;

  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, theme.ink900);
  gradient.addColorStop(0.55, theme.ink800);
  gradient.addColorStop(1, theme.ink850);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.save();
  ctx.translate(width * 0.58, height * 0.5);
  ctx.strokeStyle = theme.cool;
  ctx.globalAlpha = 0.16;
  ctx.lineWidth = 1.4;
  for (let orbit = 0; orbit < 7; orbit += 1) {
    const radiusX = 80 + orbit * 46;
    const radiusY = 26 + orbit * 17;
    ctx.beginPath();
    for (let i = 0; i <= 180; i += 1) {
      const a = (i / 180) * Math.PI * 2 + t * (0.08 + orbit * 0.01);
      const x = Math.cos(a) * radiusX;
      const y = Math.sin(a) * radiusY + Math.sin(a * 2 + t) * 9;
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  }

  ctx.fillStyle = theme.accent;
  for (let i = 0; i < 18; i += 1) {
    const a = t * 0.45 + i * 0.9;
    const x = Math.cos(a) * (100 + (i % 5) * 54);
    const y = Math.sin(a * 1.3) * (40 + (i % 4) * 32);
    ctx.globalAlpha = 0.14 + (i % 4) * 0.04;
    ctx.beginPath();
    ctx.arc(x, y, 3 + (i % 3), 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
  ctx.globalAlpha = 1;
}
