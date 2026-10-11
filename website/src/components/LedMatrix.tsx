'use client';

import { useEffect, useRef } from 'react';

export type LedScript = {
  brand: string;
  wave: string;
  nowPlaying: string;
  games: readonly string[];
  coin: string;
  start: string;
};

type Props = {
  script: LedScript;
  label: string;
  className?: string;
};

const COLS = 128;
const ROWS = 32;
const PITCH = 8;
const FPS = 30;

// Fonte 5x7; acentos s?o removidos antes de desenhar e caracteres sem glifo viram espa?o.
const GLYPHS: Record<string, string[]> = {
  A: ['.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
  B: ['####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'],
  C: ['.###.', '#...#', '#....', '#....', '#....', '#...#', '.###.'],
  D: ['####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'],
  E: ['#####', '#....', '#....', '####.', '#....', '#....', '#####'],
  F: ['#####', '#....', '#....', '####.', '#....', '#....', '#....'],
  G: ['.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.###.'],
  H: ['#...#', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'],
  I: ['.###.', '..#..', '..#..', '..#..', '..#..', '..#..', '.###.'],
  J: ['..###', '...#.', '...#.', '...#.', '...#.', '#..#.', '.##..'],
  K: ['#...#', '#..#.', '#.#..', '##...', '#.#..', '#..#.', '#...#'],
  L: ['#....', '#....', '#....', '#....', '#....', '#....', '#####'],
  M: ['#...#', '##.##', '#.#.#', '#.#.#', '#...#', '#...#', '#...#'],
  N: ['#...#', '#...#', '##..#', '#.#.#', '#..##', '#...#', '#...#'],
  O: ['.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
  P: ['####.', '#...#', '#...#', '####.', '#....', '#....', '#....'],
  Q: ['.###.', '#...#', '#...#', '#...#', '#.#.#', '#..#.', '.##.#'],
  R: ['####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'],
  S: ['.####', '#....', '#....', '.###.', '....#', '....#', '####.'],
  T: ['#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'],
  U: ['#...#', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'],
  V: ['#...#', '#...#', '#...#', '#...#', '#...#', '.#.#.', '..#..'],
  W: ['#...#', '#...#', '#...#', '#.#.#', '#.#.#', '#.#.#', '.#.#.'],
  X: ['#...#', '#...#', '.#.#.', '..#..', '.#.#.', '#...#', '#...#'],
  Y: ['#...#', '#...#', '.#.#.', '..#..', '..#..', '..#..', '..#..'],
  Z: ['#####', '....#', '...#.', '..#..', '.#...', '#....', '#####'],
  '0': ['.###.', '#...#', '#..##', '#.#.#', '##..#', '#...#', '.###.'],
  '1': ['..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.'],
  '2': ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'],
  '3': ['#####', '...#.', '..#..', '...#.', '....#', '#...#', '.###.'],
  '4': ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
  '5': ['#####', '#....', '####.', '....#', '....#', '#...#', '.###.'],
  '6': ['..##.', '.#...', '#....', '####.', '#...#', '#...#', '.###.'],
  '7': ['#####', '....#', '...#.', '..#..', '.#...', '.#...', '.#...'],
  '8': ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'],
  '9': ['.###.', '#...#', '#...#', '.####', '....#', '...#.', '.##..'],
  ' ': ['...', '...', '...', '...', '...', '...', '...'],
  '!': ['#', '#', '#', '#', '#', '.', '#'],
  '.': ['..', '..', '..', '..', '..', '##', '##'],
  ':': ['..', '##', '##', '..', '##', '##', '..'],
  "'": ['#', '#', '.', '.', '.', '.', '.'],
  '-': ['....', '....', '....', '####', '....', '....', '....'],
  '+': ['.....', '..#..', '..#..', '#####', '..#..', '..#..', '.....'],
  '/': ['.....', '....#', '...#.', '..#..', '.#...', '#....', '.....'],
  '&': ['.##..', '#..#.', '#.#..', '.#...', '#.#.#', '#..#.', '.##.#'],
  '?': ['.....', '.#.#.', '#####', '#####', '.###.', '..#..', '.....'],
};

type Rgb = [number, number, number];
type Frame = (Rgb | null)[];

function normalize(text: string) {
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase();
}

function glyph(ch: string) {
  return GLYPHS[ch] ?? GLYPHS[' '];
}

function textWidth(text: string, scale: number) {
  let w = 0;
  for (const ch of normalize(text)) w += (glyph(ch)[0].length + 1) * scale;
  return Math.max(0, w - scale);
}

function hsl(h: number, s = 1, l = 0.55): Rgb {
  const k = (n: number) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [Math.round(f(0) * 255), Math.round(f(8) * 255), Math.round(f(4) * 255)];
}

function drawText(
  frame: Frame,
  text: string,
  x0: number,
  y0: number,
  scale: number,
  color: (x: number, y: number, i: number) => Rgb,
  dy: (i: number) => number = () => 0,
) {
  let x = Math.round(x0);
  let i = 0;
  for (const ch of normalize(text)) {
    const rows = glyph(ch);
    const w = rows[0].length;
    if (x + w * scale >= 0 && x < COLS) {
      const yOff = Math.round(y0 + dy(i));
      for (let r = 0; r < rows.length; r++) {
        for (let c = 0; c < w; c++) {
          if (rows[r][c] !== '#') continue;
          for (let sy = 0; sy < scale; sy++) {
            for (let sx = 0; sx < scale; sx++) {
              const px = x + c * scale + sx;
              const py = yOff + r * scale + sy;
              if (px >= 0 && px < COLS && py >= 0 && py < ROWS) frame[py * COLS + px] = color(px, py, i);
            }
          }
        }
      }
    }
    x += (w + 1) * scale;
    i++;
  }
}

type Scene = { duration: number; draw: (frame: Frame, t: number) => void };

function buildScenes(script: LedScript): Scene[] {
  const scenes: Scene[] = [];
  const speed = 42;

  const brandW = textWidth(script.brand, 2);
  scenes.push({
    duration: (COLS + brandW) / speed,
    draw: (f, t) => drawText(f, script.brand, COLS - t * speed, 9, 2, (x) => hsl((x * 4 + t * 140) % 360)),
  });

  for (const game of script.games) {
    const w = textWidth(game, 2);
    const scroll = w > COLS;
    const amber: Rgb = [255, 184, 108];
    const cyan: Rgb = [139, 233, 253];
    const headW = textWidth(script.nowPlaying, 1);
    scenes.push({
      duration: scroll ? (COLS + w) / speed : 3.2,
      draw: (f, t) => {
        drawText(f, script.nowPlaying, (COLS - headW) / 2, 2, 1, () => cyan);
        for (let x = 8; x < COLS - 8; x += 2) f[11 * COLS + x] = [68, 71, 90];
        drawText(f, game, scroll ? COLS - t * speed : (COLS - w) / 2, 15, 2, () => amber);
      },
    });
  }

  const waveW = textWidth(script.wave, 2);
  scenes.push({
    duration: 4.5,
    draw: (f, t) =>
      drawText(
        f,
        script.wave,
        (COLS - waveW) / 2,
        9,
        2,
        (_x, _y, i) => hsl((300 + i * 18 + t * 60) % 360, 1, 0.62),
        (i) => Math.sin(t * 6 - i * 0.7) * 5,
      ),
  });

  const coinW = textWidth(script.coin, 1);
  const startW = textWidth(script.start, 1);
  scenes.push({
    duration: 3,
    draw: (f, t) => {
      if (Math.floor(t * 2.5) % 2 === 0) drawText(f, script.coin, (COLS - coinW) / 2, 7, 1, () => [241, 250, 140]);
      drawText(f, script.start, (COLS - startW) / 2, 19, 1, () => [80, 250, 123]);
    },
  });

  return scenes;
}

function paint(ctx: CanvasRenderingContext2D, glow: HTMLCanvasElement, base: HTMLCanvasElement, frame: Frame) {
  const gctx = glow.getContext('2d');
  if (!gctx) return;
  const img = gctx.createImageData(COLS, ROWS);
  for (let i = 0; i < frame.length; i++) {
    const c = frame[i];
    if (!c) continue;
    img.data[i * 4] = c[0];
    img.data[i * 4 + 1] = c[1];
    img.data[i * 4 + 2] = c[2];
    img.data[i * 4 + 3] = 255;
  }
  gctx.putImageData(img, 0, 0);

  const W = COLS * PITCH;
  const H = ROWS * PITCH;
  ctx.drawImage(base, 0, 0);

  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = 0.55;
  ctx.filter = `blur(${PITCH * 1.4}px)`;
  ctx.drawImage(glow, 0, 0, W, H);
  ctx.restore();

  const r = PITCH * 0.38;
  for (let i = 0; i < frame.length; i++) {
    const c = frame[i];
    if (!c) continue;
    const cx = (i % COLS) * PITCH + PITCH / 2;
    const cy = Math.floor(i / COLS) * PITCH + PITCH / 2;
    ctx.fillStyle = `rgb(${c[0]},${c[1]},${c[2]})`;
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fill();
  }
}

function makeBase() {
  const base = document.createElement('canvas');
  base.width = COLS * PITCH;
  base.height = ROWS * PITCH;
  const b = base.getContext('2d');
  if (!b) return base;
  b.fillStyle = '#0b0b10';
  b.fillRect(0, 0, base.width, base.height);
  b.fillStyle = '#1d1e28';
  const r = PITCH * 0.36;
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      b.beginPath();
      b.arc(x * PITCH + PITCH / 2, y * PITCH + PITCH / 2, r, 0, Math.PI * 2);
      b.fill();
    }
  }
  return base;
}

// Simula um marquee Pixelcade de 128x32 LEDs (dois pain?is 64x32).
export function LedMatrix({ script, label, className = '' }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    const base = makeBase();
    const glow = document.createElement('canvas');
    glow.width = COLS;
    glow.height = ROWS;
    const scenes = buildScenes(script);
    const total = scenes.reduce((sum, s) => sum + s.duration, 0);

    const render = (time: number) => {
      let t = time % total;
      let scene = scenes[0];
      for (const s of scenes) {
        scene = s;
        if (t < s.duration) break;
        t -= s.duration;
      }
      const frame: Frame = new Array(COLS * ROWS).fill(null);
      scene.draw(frame, t);
      paint(ctx, glow, base, frame);
    };

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      render(scenes[0].duration + 0.1);
      return;
    }

    let raf = 0;
    let visible = false;
    let prev = 0;
    let drawn = 0;
    let elapsed = 0;

    const loop = (now: number) => {
      if (!visible) return;
      if (prev) elapsed += Math.min(now - prev, 100) / 1000;
      prev = now;
      if (now - drawn >= 1000 / FPS) {
        drawn = now;
        render(elapsed);
      }
      raf = requestAnimationFrame(loop);
    };

    const start = () => {
      if (visible) return;
      visible = true;
      prev = 0;
      raf = requestAnimationFrame(loop);
    };
    const stop = () => {
      visible = false;
      cancelAnimationFrame(raf);
    };

    render(0);
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) start();
        else stop();
      }
    });
    observer.observe(canvas);
    return () => {
      observer.disconnect();
      stop();
    };
  }, [script]);

  return (
    <canvas
      ref={canvasRef}
      width={COLS * PITCH}
      height={ROWS * PITCH}
      role="img"
      aria-label={label}
      className={`block h-auto w-full ${className}`}
    />
  );
}
