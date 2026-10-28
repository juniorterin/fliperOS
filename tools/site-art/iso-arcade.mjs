// Gera as duas artes do site em pixel art isométrico, no estilo do logo: um
// quarto em corte com um gabinete dentro. Uma tem o Super Punch-Out!! (duas
// telas empilhadas), a outra um gabinete de corrida com três telas.
//
//   node tools/site-art/iso-arcade.mjs [pasta-de-saida]
//
// Sem dependências: o PNG é codificado aqui mesmo. A saída padrão é
// website/public/art/ (arcade-2-screens.png e arcade-3-screens.png).
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { deflateSync } from 'node:zlib';

const OUT = process.argv[2] ?? path.resolve(import.meta.dirname, '..', '..', 'website', 'public', 'art');

// ---------- cores (a paleta Dracula do site e do logo) ----------
const hex = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const C = {
  line: hex('#191a21'),
  wallL: hex('#44475a'),
  wallR: hex('#3a3d4d'),
  purpleL: hex('#765f9c'),
  purpleR: hex('#68538a'),
  purpleHi: hex('#896eb5'),
  blue: hex('#6272a4'),
  blueDark: hex('#515c83'),
  floorA: hex('#f4f4ee'),
  floorB: hex('#d3d7df'),
  cap: hex('#6272a4'),
  red: hex('#ff5555'),
  pink: hex('#ff79c6'),
  yellow: hex('#f1fa8c'),
  orange: hex('#ffb86c'),
  green: hex('#50fa7b'),
  cyan: hex('#8be9fd'),
  white: hex('#f8f8f2'),
  body: hex('#353849'),
  dark: hex('#282a36'),
};
const mul = (c, k) => c.map((v) => Math.max(0, Math.min(255, Math.round(v * k))));
const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
const hash = (x, y) => {
  let h = (Math.imul(Math.floor(x), 73856093) ^ Math.imul(Math.floor(y), 19349663)) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177) >>> 0;
  return (h ^ (h >>> 16)) / 4294967296;
};

// ---------- fonte 3x5 ----------
const FONT = {
  A: ['.#.', '#.#', '###', '#.#', '#.#'],
  C: ['###', '#..', '#..', '#..', '###'],
  E: ['###', '#..', '##.', '#..', '###'],
  G: ['###', '#..', '#.#', '#.#', '###'],
  H: ['#.#', '#.#', '###', '#.#', '#.#'],
  I: ['###', '.#.', '.#.', '.#.', '###'],
  K: ['#.#', '#.#', '##.', '#.#', '#.#'],
  N: ['#.#', '###', '###', '#.#', '#.#'],
  O: ['###', '#.#', '#.#', '#.#', '###'],
  P: ['###', '#.#', '###', '#..', '#..'],
  R: ['##.', '#.#', '##.', '#.#', '#.#'],
  T: ['###', '.#.', '.#.', '.#.', '.#.'],
  U: ['#.#', '#.#', '#.#', '#.#', '###'],
  F: ['###', '#..', '##.', '#..', '#..'],
  3: ['###', '..#', '###', '..#', '###'],
  5: ['###', '#..', '###', '..#', '###'],
  '-': ['...', '...', '###', '...', '...'],
};
// Uma função de textura que escreve `text` em colunas de `scale` unidades
// (1 por padrão; 0.5 dá letras de um pixel); (a, b) são as coordenadas em
// unidades dentro da área (a para a direita, b para baixo).
function textTex(text, on, off, scale = 1) {
  return (a, b) => {
    const col = Math.floor(a / scale);
    const row = Math.floor(b / scale) - 1;
    const ch = Math.floor(col / 4);
    const gx = col % 4;
    if (row >= 0 && row < 5 && gx < 3 && ch < text.length && FONT[text[ch]]?.[row][gx] === '#') return on;
    return off;
  };
}

// ---------- o canvas isométrico ----------
const W = 208;
const H = 218;
const OX = 104;
const OY = 112;
const N = 48; // lado do piso, em unidades
const HW = 54; // altura das paredes
const px = (x, y, z) => [OX + (x - y) * 2, OY + (x + y) - z * 2];

class Canvas {
  constructor() {
    this.rgba = new Uint8Array(W * H * 4);
    this.id = new Int32Array(W * H);
    this.cur = 0;
  }
  next() {
    return ++this.cur;
  }
  set(x, y, c, id) {
    if (x < 0 || y < 0 || x >= W || y >= H) return;
    const i = y * W + x;
    this.rgba.set([c[0], c[1], c[2], 255], i * 4);
    this.id[i] = id;
  }
  // x = c (o lado esquerdo de uma caixa); fn(y, z) devolve a cor ou null
  faceX(c, y0, y1, z0, z1, fn, id = this.cur) {
    const xs = [px(c, y0, z0), px(c, y1, z0), px(c, y0, z1), px(c, y1, z1)];
    this.scan(xs, (sx, sy) => {
      const y = c - (sx - OX) / 2;
      const z = (OY + c + y - sy) / 2;
      if (y < y0 || y >= y1 || z < z0 || z >= z1) return null;
      return fn(y, z);
    }, id);
  }
  // y = c (o lado direito de uma caixa); fn(x, z)
  faceY(c, x0, x1, z0, z1, fn, id = this.cur) {
    const xs = [px(x0, c, z0), px(x1, c, z0), px(x0, c, z1), px(x1, c, z1)];
    this.scan(xs, (sx, sy) => {
      const x = c + (sx - OX) / 2;
      const z = (OY + x + c - sy) / 2;
      if (x < x0 || x >= x1 || z < z0 || z >= z1) return null;
      return fn(x, z);
    }, id);
  }
  // plano inclinado x = a + b*z (um monitor deitado para trás); fn(y, z)
  slantX(a, b, y0, y1, z0, z1, fn, id = this.cur) {
    const xs = [px(a + b * z0, y0, z0), px(a + b * z0, y1, z0), px(a + b * z1, y0, z1), px(a + b * z1, y1, z1)];
    this.scan(xs, (sx, sy) => {
      const d = (sx - OX) / 2;
      const z = (OY + 2 * a - d - sy) / (2 - 2 * b);
      const y = a + b * z - d;
      if (y < y0 || y >= y1 || z < z0 || z >= z1) return null;
      return fn(y, z);
    }, id);
  }
  // painel vertical em ângulo: o ponto (x0 + dx*s, y0 + dy*s), s0 <= s < s1; fn(s, z)
  faceV(x0, y0, dx, dy, s0, s1, z0, z1, fn, id = this.cur) {
    const xs = [s0, s1].flatMap((s) => [z0, z1].map((z) => px(x0 + dx * s, y0 + dy * s, z)));
    this.scan(xs, (sx, sy) => {
      const d = (sx - OX) / 2;
      const s = (d - (x0 - y0)) / (dx - dy);
      const z = (OY + x0 + y0 + (dx + dy) * s - sy) / 2;
      if (s < s0 || s >= s1 || z < z0 || z >= z1) return null;
      return fn(s, z);
    }, id);
  }
  // o topo de um polígono (x, y) em z = c; fn(x, y)
  topPoly(c, poly, fn, id = this.cur) {
    const inside = (x, y) => {
      let hit = false;
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const [xi, yi] = poly[i];
        const [xj, yj] = poly[j];
        if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
      }
      return hit;
    };
    this.scan(poly.map(([x, y]) => px(x, y, c)), (sx, sy) => {
      const d = (sx - OX) / 2;
      const s = sy - OY + 2 * c;
      const x = (s + d) / 2;
      const y = (s - d) / 2;
      return inside(x, y) ? fn(x, y) : null;
    }, id);
  }
  // z = c (o topo); fn(x, y)
  top(c, x0, x1, y0, y1, fn, id = this.cur) {
    const xs = [px(x0, y0, c), px(x1, y0, c), px(x0, y1, c), px(x1, y1, c)];
    this.scan(xs, (sx, sy) => {
      const d = (sx - OX) / 2;
      const s = sy - OY + 2 * c;
      const x = (s + d) / 2;
      const y = (s - d) / 2;
      if (x < x0 || x >= x1 || y < y0 || y >= y1) return null;
      return fn(x, y);
    }, id);
  }
  scan(corners, at, id) {
    const x0 = Math.floor(Math.min(...corners.map((p) => p[0])));
    const x1 = Math.ceil(Math.max(...corners.map((p) => p[0])));
    const y0 = Math.floor(Math.min(...corners.map((p) => p[1])));
    const y1 = Math.ceil(Math.max(...corners.map((p) => p[1])));
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const c = at(x + 0.5, y + 0.5);
        if (c) this.set(x, y, c, id);
      }
    }
  }
  // uma caixa com as três faces visíveis; cada cor pode ser uma função
  box(x0, x1, y0, y1, z0, z1, base, opt = {}) {
    const id = this.next();
    const col = (v, k) => (typeof v === 'function' ? v : () => v ?? mul(base, k));
    const left = col(opt.left, 1);
    const right = col(opt.right, 0.78);
    const topc = col(opt.top, 1.18);
    this.faceX(x1, y0, y1, z0, z1, (y, z) => left(y, z), id);
    this.faceY(y1, x0, x1, z0, z1, (x, z) => right(x, z), id);
    this.top(z1, x0, x1, y0, y1, (x, y) => topc(x, y), id);
    return id;
  }
  // o contorno escuro nas bordas do objeto da frente
  outline(color = C.line) {
    const marks = [];
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const a = this.id[y * W + x];
        if (!a) continue;
        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = x + dx;
          const ny = y + dy;
          const b = nx < 0 || ny < 0 || nx >= W || ny >= H ? 0 : this.id[ny * W + nx];
          if (b < a) {
            marks.push([x, y]);
            break;
          }
        }
      }
    }
    for (const [x, y] of marks) this.rgba.set([color[0], color[1], color[2], 255], (y * W + x) * 4);
  }
  // pontos soltos (folhas, brilhos)
  dot(x, y, c) {
    this.set(Math.round(x), Math.round(y), c, ++this.cur);
  }
  line(x0, y0, x1, y1, c, id) {
    const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) || 1;
    for (let i = 0; i <= n; i++) this.set(Math.round(x0 + ((x1 - x0) * i) / n), Math.round(y0 + ((y1 - y0) * i) / n), c, id);
  }
}

// ---------- o quarto ----------
function room(cv, { glow = [], shadows = [], sign, signArea, poster, posterArea }) {
  const T = 3;
  // paredes
  let id = cv.next();
  cv.faceX(0, 0, N, -T, HW, (y, z) => wall(y, z, true), id);
  cv.top(HW, -2, 0, -2, N, () => C.cap, id);
  cv.faceY(N, -2, 0, -T, HW, (x, z) => mul(C.wallL, 0.8), id);
  id = cv.next();
  cv.faceY(0, 0, N, -T, HW, (x, z) => wall(x, z, false), id);
  cv.top(HW, 0, N, -2, 0, () => mul(C.cap, 1.1), id);
  cv.faceX(N, -2, 0, -T, HW, (y, z) => mul(C.wallR, 0.8), id);
  // cartaz e letreiro nas paredes (painéis soltos, na mesma textura)
  if (sign) {
    const [y0, y1, z0, z1] = signArea;
    cv.faceX(0, y0, y1, z0, z1, (y, z) => sign((y1 - y), z1 - z), cv.next());
  }
  if (poster) {
    const [x0, x1, z0, z1] = posterArea;
    cv.faceY(0, x0, x1, z0, z1, (x, z) => poster(x - x0, z1 - z, x1 - x0, z1 - z0), cv.next());
  }
  // piso, com a laje de baixo
  id = cv.next();
  cv.faceX(N, 0, N, -T, 0, () => mul(C.wallL, 0.85), id);
  cv.faceY(N, 0, N, -T, 0, () => mul(C.wallR, 0.7), id);
  cv.top(0, 0, N, 0, N, (x, y) => floor(x, y, glow, shadows), id);
}

function wall(a, z, left) {
  const slate = left ? C.wallL : C.wallR;
  const purple = left ? C.purpleL : C.purpleR;
  const n = hash(a * 3, z * 5);
  if (z < 2) return mul(C.blueDark, left ? 1 : 0.9); // rodapé
  if (z < 3) return mul(C.line, 1.4);
  if (z < 13) return mul(purple, 0.95 + n * 0.1);
  if (z < 14) return mul(C.purpleHi, left ? 1 : 0.9);
  return mul(slate, 0.96 + n * 0.08);
}

function floor(x, y, glow, shadows) {
  let c = (Math.floor(x / 4) + Math.floor(y / 4)) % 2 === 0 ? C.floorA : C.floorB;
  c = mul(c, 0.97 + hash(x * 2, y * 2) * 0.05);
  for (const g of glow) {
    if (x >= g.x0 && x < g.x1 && y >= g.y0 && y < g.y1) {
      const fall = 1 - (x - g.x0) / (g.x1 - g.x0);
      const dither = [0.15, 0.55, 0.85, 0.35][(Math.floor(x * 2) & 1) + 2 * (Math.floor(y * 2) & 1)];
      if (fall > dither) c = mix(c, g.color, 0.28);
    }
  }
  for (const s of shadows) if (x >= s.x0 && x < s.x1 && y >= s.y0 && y < s.y1) c = mix(c, C.line, 0.3);
  return c;
}

// ---------- objetos ----------
function plant(cv, x, y) {
  cv.box(x, x + 6, y, y + 6, 0, 6, C.orange, { left: mul(C.orange, 0.95), right: mul(C.orange, 0.7), top: mul(C.dark, 0.9) });
  const [bx, by] = px(x + 3, y + 3, 6);
  const id = cv.next();
  const leaves = [[-14, -16], [-8, -22], [-2, -26], [4, -22], [10, -17], [15, -10], [-17, -8]];
  leaves.forEach(([dx, dy], i) => {
    const col = i % 2 ? C.green : mul(C.green, 0.65);
    cv.line(bx, by, bx + dx * 0.55, by + dy * 0.5, col, id);
    cv.line(bx + 1, by, bx + dx * 0.55 + 1, by + dy * 0.5, col, id);
    cv.line(bx + dx * 0.55, by + dy * 0.5, bx + dx, by + dy, col, id);
  });
}

function chair(cv, x, y) {
  const legs = [[0, 0], [5, 0], [0, 5], [5, 5]];
  for (const [dx, dy] of legs) cv.box(x + dx, x + dx + 1, y + dy, y + dy + 1, 0, 6, C.dark, { left: mul(C.body, 1.3), right: C.body });
  cv.box(x, x + 6, y, y + 6, 6, 7, C.red);
  cv.box(x, x + 1, y, y + 6, 7, 17, C.red);
}

function tires(cv, x, y, size = 7) {
  for (let i = 0; i < 2; i++) {
    cv.box(x, x + size, y, y + size, i * 3, i * 3 + 3, C.dark, {
      top: (cx, cy) => ((cx - x - size / 2) ** 2 + (cy - y - size / 2) ** 2 < 2.2 ? C.line : mul(C.body, 0.9)),
      left: mul(C.body, 0.8),
      right: mul(C.body, 0.55),
    });
  }
}

// uma tela: moldura, brilho do vidro e linhas de varredura
function screen(cv, c, y0, y1, z0, z1, tex) {
  cv.faceX(c, y0, y1, z0, z1, (y, z) => {
    const u = (y1 - y) / (y1 - y0);
    const v = (z1 - z) / (z1 - z0);
    const col = tex(u, v);
    const k = Math.floor((z1 - z) * 4) % 2 ? 0.88 : 1;
    return mul(col, k);
  }, cv.next());
}

// ---------- Super Punch-Out!! (Nintendo, 1984) ----------
// Um upright com dois monitores empilhados: o de cima mostra as estatísticas e
// o de baixo é o jogo. Um joystick e três botões (soco esquerdo, soco direito
// e uppercut). A lateral tem o perfil de um upright: a base, o painel que
// avança, os monitores deitados para trás e o letreiro por cima.
const ell = (u, v, cx, cy, rx, ry) => ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2 < 1;

// o monitor de cima: as barras de energia dos dois lutadores, o tempo e as estrelas
function statsScreen(u, v) {
  if (v < 0.3) {
    if (v > 0.12 && v < 0.26) {
      if (u > 0.05 && u < 0.45) return u < 0.38 ? C.green : mul(C.green, 0.35);
      if (u > 0.55 && u < 0.95) return u < 0.85 ? C.yellow : mul(C.yellow, 0.35);
    }
    return C.line;
  }
  if (v > 0.38 && v < 0.62 && u > 0.38 && u < 0.62) return hash(u * 30, v * 20) > 0.5 ? C.white : C.pink; // o relógio
  if (v > 0.74 && v < 0.92) for (const cx of [0.3, 0.5, 0.7]) if (ell(u, v, cx, 0.83, 0.07, 0.1)) return C.yellow;
  return mix(C.dark, C.blueDark, 0.35);
}
// o monitor de baixo: o ringue, o adversário de frente e as luvas do jogador
function fightScreen(u, v) {
  if (ell(u, v, 0.27, 0.82, 0.1, 0.13) || ell(u, v, 0.73, 0.82, 0.1, 0.13)) return ell(u, v, 0.27, 0.82, 0.045, 0.06) || ell(u, v, 0.73, 0.82, 0.045, 0.06) ? C.white : C.red;
  if (ell(u, v, 0.5, 0.32, 0.17, 0.12) && v < 0.2) return C.line; // o cabelo
  if (ell(u, v, 0.44, 0.38, 0.035, 0.05) || ell(u, v, 0.56, 0.38, 0.035, 0.05)) return C.line;
  if (ell(u, v, 0.5, 0.57, 0.07, 0.04)) return C.red;
  if (ell(u, v, 0.5, 0.42, 0.18, 0.26)) return C.orange;
  if (ell(u, v, 0.5, 1.0, 0.36, 0.34)) return mul(C.orange, 0.85);
  if (v < 0.26) return hash(u * 24, v * 16) > 0.86 ? [C.pink, C.cyan, C.yellow][Math.floor(hash(u * 9, v * 9) * 3)] : C.dark;
  if (v < 0.32) return C.red;
  if (v < 0.36) return C.white;
  return mix(C.blue, C.blueDark, v);
}

function arcadeA() {
  const cv = new Canvas();
  room(cv, {
    glow: [{ x0: 34, x1: 48, y0: 10, y1: 38, color: C.cyan }],
    shadows: [{ x0: 12, x1: 37, y0: 14, y1: 37 }, { x0: 38, x1: 46, y0: 4, y1: 12 }, { x0: 20, x1: 28, y0: 38, y1: 46 }],
    sign: textTex('PUNCH', C.pink, mul(C.dark, 0.7)),
    signArea: [24, 24 + 19, 32, 32 + 7],
    poster: (a, b, w, h) => {
      if (a < 0.8 || b < 0.8 || a > w - 0.8 || b > h - 0.8) return C.yellow;
      return textTex('KO', C.yellow, C.red)(a - 4, b - 5);
    },
    posterArea: [30, 44, 18, 36],
  });
  plant(cv, 38, 4);

  const BODY = hex('#262836');
  const STEEL = hex('#9aa0b8');
  const Y0 = 14;
  const Y1 = 34;
  const slope = 0.12; // quanto o monitor deita para trás
  const frontX = (z) => 28 - Math.max(0, z - 19) * slope;
  const a0 = 27 + slope * 19; // o plano x = a0 - slope*z, de x=27 em z=19 a x=24 em z=44

  cv.box(12, 24, Y0 + 1, Y1 - 1, 0, 44, BODY);

  // a lateral, com o perfil do upright e a arte
  cv.faceY(Y1, 12, 34, 0, 50, (x, z) => {
    const inside = z < 3 ? x < 27 : z < 19 ? x < 28 : z < 44 ? x < frontX(z) : z < 50 && x < 30;
    if (!inside) return null;
    const luva = ell(x, z, 20.5, 31, 4.2, 4.6);
    if (luva) return ell(x, z, 20.5, 31, 1.6, 1.8) ? C.white : mul(C.red, z > 33 ? 1 : 0.85);
    if (x > 17 && x < 24 && z > 24 && z < 26.5) return C.white; // o punho da luva
    if (z > 4 && z < 11 && (Math.floor(x + z) % 6) < 2) return C.pink;
    if (z > 40 && z < 41.5) return C.red;
    return mul(BODY, 0.8);
  }, cv.next());

  // a base, com a porta de moedas
  cv.faceX(28, Y0, Y1, 0, 16, (y, z) => {
    if (z < 3) return mul(BODY, 0.55);
    if (y >= 21 && y < 28 && z >= 4 && z < 13) {
      if ((y >= 22 && y < 23.6 || y >= 25.4 && y < 27) && z >= 8.5 && z < 11) return C.yellow;
      if (y >= 23.6 && y < 25.4 && z >= 5.5 && z < 7) return C.red;
      return STEEL;
    }
    return mul(BODY, 1.08);
  }, cv.next());

  // o painel: um joystick à esquerda e três botões
  cv.box(28, 34, Y0, Y1, 16, 19, BODY, {
    left: mul(STEEL, 0.55),
    top: (x, y) => {
      for (const [by, col] of [[19.5, C.blue], [22.2, C.red], [24.9, C.yellow]]) {
        const r = Math.hypot(x - 31.5, y - by);
        if (r < 0.8) return mul(col, r < 0.35 ? 1.3 : 1);
        if (r < 1.2) return C.line;
      }
      if (Math.hypot(x - 31, y - 29) < 1.5) return C.line;
      return x > 33.2 ? C.pink : mul(C.blueDark, 0.7);
    },
  });
  cv.box(30.6, 31.4, 28.6, 29.4, 19, 22, STEEL);
  cv.box(30.2, 31.8, 28.2, 29.8, 22, 23.6, C.red, { top: mul(C.red, 1.3) });

  // o frontal inclinado: a moldura e os dois monitores
  cv.slantX(a0, -slope, Y0 + 1, Y1 - 1, 19.2, 44, (y, z) => mul(BODY, z > 31 && z < 34 && y > 19 && y < 29 ? 1.6 : 1.05), cv.next());
  const monitor = (z0, z1, tex) =>
    cv.slantX(a0, -slope, Y0 + 3, Y1 - 3, z0, z1, (y, z) => {
      const u = (Y1 - 3 - y) / (Y1 - Y0 - 6);
      const v = (z1 - z) / (z1 - z0);
      return mul(tex(u, v), Math.floor(z * 4) % 2 ? 0.88 : 1);
    }, cv.next());
  monitor(20.5, 30.5, fightScreen);
  monitor(34, 43, statsScreen);

  // o letreiro
  cv.box(12, 30, Y0, Y1, 44, 50, C.red, {
    left: (y, z) => textTex('PUNCH-OUT', C.yellow, mul(C.red, 0.9), 0.5)(Y1 - y - 1.25, 50 - z - 1.25),
    right: mul(BODY, 0.8),
    top: mul(BODY, 1.3),
  });
  chair(cv, 20, 40);
  cv.outline();
  return cv;
}

// ---------- gabinete de corrida de três telas (como o F355 Challenge Deluxe) ----------
// Uma cabine de um lugar: as três telas em volta do piloto (as laterais
// anguladas para dentro), o volante, o câmbio e os pedais, e o banco atrás.
function raceScreen(si) {
  return (u, v) => {
    const g = (si + u) / 3;
    const h = 0.42;
    if (v < h) {
      const mh = 0.1 + 0.07 * Math.sin(g * 17) + 0.05 * Math.sin(g * 6 + 1);
      if (v > h - mh) return v > h - mh + 0.02 ? C.blueDark : C.white;
      return mix(C.blue, C.cyan, v / h);
    }
    const d = (v - h) / (1 - h);
    const z = 1 / (d + 0.06);
    const band = Math.floor(z * 1.6) % 2;
    const cx = 0.5 - 0.16 * (1 - d);
    const half = 0.025 + 0.4 * d;
    const dist = Math.abs(g - cx);
    if (si === 1 && u > 0.34 && u < 0.66 && v > 0.74 && v < 0.93) return v > 0.88 ? C.line : v < 0.8 ? mul(C.red, 0.8) : u > 0.46 && u < 0.54 && v < 0.84 ? C.cyan : C.red;
    if (si === 0 && u > 0.45 && u < 0.72 && v > 0.58 && v < 0.67) return v > 0.64 ? C.line : C.yellow;
    if (dist < half) {
      if (dist < 0.012 + 0.012 * d && band) return C.white;
      if (dist > half - 0.02 - 0.03 * d) return band ? C.red : C.white;
      return band ? mul(C.blueDark, 1.3) : mul(C.blueDark, 1.1);
    }
    return band ? [47, 140, 80] : [56, 172, 98];
  };
}

function arcadeB() {
  const cv = new Canvas();
  room(cv, {
    glow: [{ x0: 27, x1: 48, y0: 6, y1: 46, color: C.cyan }],
    shadows: [{ x0: 10, x1: 48, y0: 6, y1: 48 }, { x0: 40, x1: 48, y0: 0, y1: 7 }],
    sign: textTex('RACING', C.cyan, mul(C.dark, 0.7)),
    signArea: [24, 24 + 23, 32, 32 + 7],
    poster: (a, b, w, h) => {
      if (a < 0.8 || b < 0.8 || a > w - 0.8 || b > h - 0.8) return C.yellow;
      return (Math.floor((a - 0.8) / 3) + Math.floor((b - 0.8) / 3)) % 2 ? C.line : C.white;
    },
    posterArea: [20, 36, 20, 36],
  });
  tires(cv, 41, 0, 6);
  const BLK = hex('#23242f');
  const STEEL = hex('#9aa0b8');
  const Z0 = 14;
  const Z1 = 40;
  cv.box(10, 46, 6, 46, 0, 3, C.dark, { top: mul(C.body, 0.95) });

  // o capô com as três telas: o centro de frente e as laterais anguladas
  const poly = [[10, 7], [10, 45], [26.8, 45], [22, 33], [22, 19], [26.8, 7]];
  const tex = (si, u, z) => {
    if (z >= 34) return C.red;
    if (z >= 22 && u > 0.07 && u < 0.93) return mul(raceScreen(si)((u - 0.07) / 0.86, (34 - z) / 12), Math.floor(z * 4) % 2 ? 0.88 : 1);
    if (z >= 21 && z < 22) return C.yellow;
    if (z < 21 && z > 15 && Math.floor(z * 2) % 2 && u > 0.1 && u < 0.9) return mul(BLK, 0.6);
    return mul(BLK, 1.15);
  };
  cv.topPoly(Z1, poly, () => mul(BLK, 1.5), cv.next());
  cv.faceY(45, 10, 26.8, Z0, Z1, (x, z) => {
    const band = z - (x - 10) * 0.32;
    if (band > 24 && band < 31) return textTex('F355', C.yellow, C.red, 0.5)(x - 12, 31 - band - 0.25) ?? C.red;
    if (band > 22 && band <= 24) return C.yellow;
    return mul(BLK, 0.8);
  }, cv.next());
  cv.faceV(22, 33, 0.4, 1, 0, 12, Z0, Z1, (s, z) => tex(0, (12 - s) / 12, z), cv.next());
  cv.faceV(22, 19, 0.4, -1, 0, 12, Z0, Z1, (s, z) => tex(2, s / 12, z), cv.next());
  cv.faceX(22, 19, 33, Z0, Z1, (y, z) => {
    const u = (33 - y) / 14;
    if (z >= 34) return textTex('F355', C.white, C.red, 0.5)((33 - y) - 3.25, 40 - z - 1.75);
    return tex(1, u, z);
  }, cv.next());

  // o console, o volante e os pedais
  cv.box(22, 31, 19, 33, 3, 11, BLK, { left: mul(BLK, 1.4), top: mul(BLK, 1.6) });
  cv.box(30, 31.4, 25.3, 26.7, 11, 14, STEEL);
  cv.faceX(33, 21.5, 30.5, 11, 20, (y, z) => {
    const r = Math.hypot(y - 26, z - 15.5);
    if (r < 1.3) return C.red;
    if (r < 4.5 && r > 3.2) return C.line;
    if ((Math.abs(y - 26) < 0.5 || Math.abs(z - 15.5) < 0.5) && r < 4.5) return C.line;
    return null;
  }, cv.next());
  for (const [py, col] of [[22, STEEL], [26, C.yellow], [30, C.red]]) cv.box(31.5, 33.5, py, py + 2, 3, 5, col);
  // o câmbio de seis marchas
  cv.box(34, 35.6, 34.6, 36.2, 3, 11, STEEL);
  cv.box(33.6, 36, 34.2, 36.6, 11, 13.6, C.red, { top: mul(C.red, 1.3) });

  // o banco
  cv.box(36, 44, 20, 32, 3, 8, C.body, { top: mul(C.blueDark, 1) });
  cv.box(36, 42, 20, 22, 8, 11, BLK);
  cv.box(36, 42, 30, 32, 8, 11, BLK);
  cv.box(42, 45, 20, 32, 8, 23, BLK, { left: (y, z) => (y > 22 && y < 30 && z > 10 && z < 21 ? C.red : mul(BLK, 1.3)) });
  cv.box(42, 45, 23, 29, 23, 28, BLK, { left: mul(C.red, 0.9) });
  cv.outline();
  return cv;
}

// ---------- PNG ----------
const crcTable = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
const crc = (buf) => {
  let c = 0xffffffff;
  for (const b of buf) c = crcTable[(c ^ b) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};
function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const body = Buffer.concat([Buffer.from(type), data]);
  const sum = Buffer.alloc(4);
  sum.writeUInt32BE(crc(body));
  return Buffer.concat([len, body, sum]);
}
function png(rgba) {
  const head = Buffer.alloc(13);
  head.writeUInt32BE(W, 0);
  head.writeUInt32BE(H, 4);
  head.set([8, 6, 0, 0, 0], 8);
  const raw = Buffer.alloc((W * 4 + 1) * H);
  for (let y = 0; y < H; y++) {
    raw[y * (W * 4 + 1)] = 0;
    Buffer.from(rgba.buffer, y * W * 4, W * 4).copy(raw, y * (W * 4 + 1) + 1);
  }
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', head), chunk('IDAT', deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
}

mkdirSync(OUT, { recursive: true });
for (const [name, make] of [['arcade-2-screens', arcadeA], ['arcade-3-screens', arcadeB]]) {
  const file = path.join(OUT, `${name}.png`);
  writeFileSync(file, png(make().rgba));
  console.log(file, `${W}x${H}`);
}
