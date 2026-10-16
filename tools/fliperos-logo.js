// Logo do FliperOS: um quarto isometrico estilo Habbo em pixel art 240p (fliperama,
// cadeira dobravel, espada de Sao Jorge e poster), nas cores Dracula do tema.
// Desenha tudo com um rasterizador proprio (z-buffer por pixel), sem dependencias.
//   node tools/fliperos-logo.js <pasta>   -> fliperos-logo.png (recortado, transparente),
//   fliperos-logo-4x.png, fliperama-habbo-240p.png (320x240) e uma previa 4x com fundo.
// O site usa website/public/fliperos-logo.png.
const fs = require('fs');
const zlib = require('zlib');
const path = require('path');

const SW = 320, SH = 240;
const W = 96, D = 96, H = 112, T = 4, SLAB = 6;
const OX = 160, OY = 127;

// ---------- buffers ----------
const col = new Array(SW * SH).fill(null);
const dep = new Float64Array(SW * SH).fill(-1e9);
const ids = new Int32Array(SW * SH).fill(0); // 0 = bg
const outlineOf = { }; // id -> outline color or null
const ROOM = new Set();

let rng = 12345;
function rand() { rng = (rng * 1103515245 + 12345) & 0x7fffffff; return rng / 0x7fffffff; }
function hash(a, b, c = 0) { let h = (a * 374761393 + b * 668265263 + c * 2147483647) | 0; h = (h ^ (h >>> 13)) * 1274126177 | 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967295; }

const parseHex = s => [parseInt(s.slice(1, 3), 16), parseInt(s.slice(3, 5), 16), parseInt(s.slice(5, 7), 16)];
const mul = (c, f) => c.map(v => Math.max(0, Math.min(255, Math.round(v * f))));
const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));

// ---------- Dracula (FliperOS theme, fliperos-setup/lib/ui.sh) ----------
// every material colour of the scene is remapped onto the theme; shades are the
// theme colour pulled towards the Dracula background
const DR = {
  bg: '#282a36', line: '#44475a', fg: '#f8f8f2', comment: '#6272a4', cyan: '#8be9fd', green: '#50fa7b',
  orange: '#ffb86c', pink: '#ff79c6', purple: '#bd93f9', red: '#ff5555', yellow: '#f1fa8c', darker: '#191a21',
};
const dr = (a, b, t) => mix(parseHex(DR[a] || a), parseHex(DR[b] || b), t); // shade helper
const dk = (a, t) => dr(a, 'bg', t);
const REMAP = {
  // floor
  '#eceae3': DR.fg, '#ddd6c2': dr('fg', 'yellow', 0.4), '#b4b0a5': dr('fg', 'comment', 0.55), '#a8a397': dr('fg', 'comment', 0.7),
  '#8e897d': DR.comment, '#c9b996': dr('purple', 'fg', 0.35),
  '#c2beb2': dr('fg', 'comment', 0.55), '#96928a': DR.comment, '#d9d6cc': dr('fg', 'comment', 0.3), '#b9b5a9': dr('fg', 'comment', 0.45),
  // walls
  '#e8e2cc': DR.line, '#cfc6a8': dk('line', 0.3), '#4e8a69': dk('purple', 0.35), '#2f5c45': DR.pink,
  '#6f9e7e': dk('purple', 0.2), '#cfd8cd': dr('purple', 'fg', 0.35),
  '#f6f2e4': dr('comment', 'fg', 0.3), '#d6cfb6': DR.comment, '#b9b29b': dk('comment', 0.3), '#2b2620': DR.darker,
  // poster
  '#f2cf3c': DR.yellow, '#c8161d': DR.red, '#7d0c10': dk('red', 0.45), '#fbeec0': DR.fg, '#ff7a4a': DR.orange,
  '#e2401f': '#ff6e6e', '#d23417': DR.red, '#111111': DR.bg, '#b9a780': DR.comment, '#e7e2cf': DR.fg, '#3a2a14': DR.darker,
  // cabinet
  '#666a72': DR.comment, '#4c5057': dk('comment', 0.35), '#474b52': dk('comment', 0.3), '#383b41': dk('comment', 0.5),
  '#3a3d44': DR.line, '#33363c': dk('line', 0.3), '#1d1d21': DR.darker, '#1b1b1f': DR.darker, '#1d1e22': DR.darker,
  '#2a2b30': DR.bg, '#a3262b': DR.pink, '#0d0d10': DR.darker, '#f3c53a': DR.yellow, '#d5d9de': DR.fg,
  '#cfd4da': dr('fg', 'comment', 0.25), '#878d95': DR.comment, '#e6e9ed': DR.fg, '#a9aeb5': dr('fg', 'comment', 0.55),
  '#ffcf1f': DR.yellow, '#22a7d6': DR.cyan, '#2b2b30': DR.bg, '#151518': DR.darker, '#9a9aa6': DR.purple,
  '#8d9198': DR.comment, '#cdd1d7': dr('fg', 'comment', 0.2), '#7b8088': dk('comment', 0.2), '#b0b5bc': dr('fg', 'comment', 0.45),
  '#141418': DR.darker, '#2a2a2e': DR.bg, '#8a8e98': DR.purple, '#050508': '#0e0f14', '#141417': DR.darker,
  // CRT fighting game
  '#141c4a': DR.bg, '#3f68c8': DR.comment, '#25306a': DR.line, '#8a5a32': dk('orange', 0.35), '#6e4526': dk('orange', 0.55),
  '#5a381f': dk('orange', 0.7), '#ffe03a': DR.yellow, '#d02020': DR.red, '#ffffff': DR.fg, '#2a1a10': DR.bg, '#f0b080': DR.orange,
  '#f4f4f4': DR.fg, '#222222': DR.bg, '#d82828': DR.red, '#ffd23a': DR.yellow, '#2a2a2a': DR.bg, '#9fe8ff': DR.cyan,
  // chair
  '#ff7466': dr('red', 'fg', 0.45), '#e3222c': DR.red, '#bb1520': dk('red', 0.3), '#850c14': dk('red', 0.55),
  '#141414': DR.darker, '#3d0508': DR.darker,
  // plant + pot
  '#2d5a33': dk('green', 0.62), '#79a457': dk('green', 0.15), '#d9cf54': DR.yellow, '#16301b': DR.darker,
  '#d97a45': DR.orange, '#c2602e': dk('orange', 0.2), '#e08a55': dr('orange', 'fg', 0.3), '#4d3020': dk('orange', 0.75),
  '#3b2414': DR.bg, '#4a2412': DR.darker,
};
const hex = s => { const r = REMAP[s.toLowerCase()]; return r ? (typeof r === 'string' ? parseHex(r) : r.slice()) : parseHex(s); };

function proj(p) { return [OX + p[0] - p[1], OY + (p[0] + p[1]) / 2 - p[2]]; }

// face: O + a*A + b*B, poly in (a,b) units, shader(a,b,P) -> color|null
function face(O, A, B, poly, shader, id) {
  const pO = proj(O);
  const pA = [A[0] - A[1], (A[0] + A[1]) / 2 - A[2]];
  const pB = [B[0] - B[1], (B[0] + B[1]) / 2 - B[2]];
  const det = pA[0] * pB[1] - pA[1] * pB[0];
  if (Math.abs(det) < 1e-9) return;
  let minx = 1e9, maxx = -1e9, miny = 1e9, maxy = -1e9;
  for (const [a, b] of poly) {
    const sx = pO[0] + a * pA[0] + b * pB[0], sy = pO[1] + a * pA[1] + b * pB[1];
    minx = Math.min(minx, sx); maxx = Math.max(maxx, sx); miny = Math.min(miny, sy); maxy = Math.max(maxy, sy);
  }
  for (let py = Math.max(0, Math.floor(miny) - 1); py <= Math.min(SH - 1, Math.ceil(maxy) + 1); py++)
    for (let px = Math.max(0, Math.floor(minx) - 1); px <= Math.min(SW - 1, Math.ceil(maxx) + 1); px++) {
      const dx = px + 0.5 - pO[0], dy = py + 0.5 - pO[1];
      const a = (dx * pB[1] - dy * pB[0]) / det;
      const b = (pA[0] * dy - pA[1] * dx) / det;
      if (!inPoly(a, b, poly)) continue;
      const P = [O[0] + a * A[0] + b * B[0], O[1] + a * A[1] + b * B[1], O[2] + a * A[2] + b * B[2]];
      const d = P[0] + P[1] + P[2];
      const i = py * SW + px;
      if (d < dep[i] - 1e-6) continue;
      const c = shader(a, b, P);
      if (!c) continue;
      col[i] = c; dep[i] = d; ids[i] = id;
    }
}
function inPoly(x, y, poly) {
  let ins = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i], [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) ins = !ins;
  }
  return ins;
}
const rect = (la, lb) => [[0, 0], [la, 0], [la, lb], [0, lb]];
const flat = c => () => c;

let nextId = 1;
function newId(outline, room = false) { const id = nextId++; outlineOf[id] = outline ? hex(outline) : null; if (room) ROOM.add(id); return id; }

// box: visible faces only (+z, +y, +x)
function box(x0, y0, z0, x1, y1, z1, sh, id) {
  face([x0, y0, z1], [1, 0, 0], [0, 1, 0], rect(x1 - x0, y1 - y0), sh.top, id);
  face([x0, y1, z0], [1, 0, 0], [0, 0, 1], rect(x1 - x0, z1 - z0), sh.front, id);
  face([x1, y0, z0], [0, 1, 0], [0, 0, 1], rect(y1 - y0, z1 - z0), sh.side, id);
}
const tones = (top, front, side) => ({ top: flat(hex(top)), front: flat(hex(front)), side: flat(hex(side)) });

// splat a sampled surface point with depth test
function splat(P, c, id) {
  const [sx, sy] = proj(P);
  const px = Math.floor(sx), py = Math.floor(sy);
  if (px < 0 || py < 0 || px >= SW || py >= SH) return;
  const i = py * SW + px, d = P[0] + P[1] + P[2];
  if (d < dep[i]) return;
  col[i] = c; dep[i] = d; ids[i] = id;
}

// ---------- fonts ----------
const F3 = {
  C: ['.##', '#..', '#..', '#..', '.##'], A: ['.#.', '#.#', '###', '#.#', '#.#'], H: ['#.#', '#.#', '###', '#.#', '#.#'],
  'Ç': ['.##', '#..', '#..', '#..', '.##', '.#.'],
};
const F4 = {
  V: ['#..#', '#..#', '#..#', '.##.', '.##.'], I: ['###', '.#.', '.#.', '.#.', '###'], D: ['###.', '#..#', '#..#', '#..#', '###.'],
  E: ['####', '#...', '###.', '#...', '####'], O: ['.##.', '#..#', '#..#', '#..#', '.##.'], G: ['.###', '#...', '#.##', '#..#', '.###'],
  A: ['.##.', '#..#', '####', '#..#', '#..#'], M: ['#...#', '##.##', '#.#.#', '#...#', '#...#'],
};
const F7 = {
  P: ['#####.', '##..##', '##..##', '#####.', '##....', '##....', '##....'], I: ['##', '##', '##', '##', '##', '##', '##'],
  T: ['######', '..##..', '..##..', '..##..', '..##..', '..##..', '..##..'], U: ['##..##', '##..##', '##..##', '##..##', '##..##', '##..##', '.####.'],
};
function textWidth(font, s) { let w = 0; for (const ch of s) w += font[ch][0].length + 1; return w - 1; }
function drawText(tex, font, s, x, y, c) {
  for (const ch of s) { const g = font[ch]; g.forEach((row, r) => [...row].forEach((v, k) => { if (v === '#') tex.set(x + k, y + r, c); })); x += g[0].length + 1; }
}
function Tex(w, h, bg) { const d = new Array(w * h).fill(bg); return { w, h, d, set(x, y, c) { if (x >= 0 && y >= 0 && x < w && y < h) d[y * w + x] = c; }, get(x, y) { x = Math.floor(x); y = Math.floor(y); if (x < 0 || y < 0 || x >= w || y >= h) return null; return d[y * w + x]; } }; }

// ---------- layout ----------
// light comes from the front-right: +x faces lighter than +y faces
const CY0 = 8, CY1 = 38, CW = CY1 - CY0;      // cabinet on wall B, front faces +x
const CHY0 = 48, CHY1 = 66;                    // folding chair on wall B, faces +x
const PCX = 85, PCY = 11;                      // pot at the right end of wall A
const PX0 = 44, PZ1 = 92, PWID = 30, PHEI = 40; // poster on wall A
const LIGHT = (() => { const v = [0.62, 0.28, 0.73], n = Math.hypot(...v); return v.map(c => c / n); })();

// ---------- shadows ----------
function floorShadow(x, y) {
  let f = 1;
  if (x < 37 && y >= CY0 - 1 && y < CY1 + 3) f *= 0.72;
  else if (x < 40 && y >= CY0 - 3 && y < CY1 + 5) f *= 0.86;
  if (x >= 4 && x < 27 && y >= CHY0 && y < CHY1 + 2) f *= 0.86;
  const dx = x - PCX + 1.5, dy = y - PCY - 1.5;
  if (dx * dx + dy * dy < 50) f *= 0.8;
  if (x < 2.5 || y < 2.5) f *= 0.9;
  return f;
}

// ---------- room ----------
const FLOOR = newId(null, true), WALL = newId(null, true);
const tileBase = hex('#eceae3'), grout = hex('#b4b0a5');
const stains = [];
for (let i = 0; i < 9; i++) stains.push([rand() * W, rand() * D, 3 + rand() * 6, 2 + rand() * 4, 0.88 + rand() * 0.06]);
const cracks = new Set();
for (let i = 0; i < 7; i++) {
  let x = Math.floor(rand() * W), y = Math.floor(rand() * D), n = 6 + Math.floor(rand() * 9);
  const dx = rand() < 0.5 ? 1 : 0;
  for (let k = 0; k < n; k++) { cracks.add(x + ',' + y); if (dx) { x++; if (rand() < 0.45) y += rand() < 0.5 ? 1 : -1; } else { y++; if (rand() < 0.45) x += rand() < 0.5 ? 1 : -1; } }
}
function floorColor(P) {
  const x = P[0], y = P[1];
  const tx = Math.floor(x / 16), ty = Math.floor(y / 16), lx = x - tx * 16, ly = y - ty * 16;
  let c;
  if (lx < 1 || ly < 1) c = grout;
  else {
    c = mul(tileBase, 0.97 + hash(tx, ty) * 0.05);
    if (hash(tx, ty, 7) < 0.18) c = mix(c, hex('#ddd6c2'), 0.5);
    const chip = hash(tx, ty, 3);
    if (chip < 0.3 && lx + ly < 4.5) c = hex('#a8a397');
    else if (chip > 0.8 && (16 - lx) + (16 - ly) < 4) c = hex('#a8a397');
    if (cracks.has(Math.floor(x) + ',' + Math.floor(y))) c = hex('#8e897d');
  }
  for (const [sx, sy, rx, ry, f] of stains) { const u = (x - sx) / rx, v = (y - sy) / ry; if (u * u + v * v < 1) c = mul(mix(c, hex('#c9b996'), 0.35), f + 0.06); }
  return mul(c, floorShadow(x, y));
}
face([0, 0, 0], [1, 0, 0], [0, 1, 0], rect(W, D), (a, b, P) => floorColor(P), FLOOR);
face([-T, D, -SLAB], [1, 0, 0], [0, 0, 1], rect(W + T, SLAB), (a, b) => b > SLAB - 1 ? hex('#c2beb2') : hex('#96928a'), FLOOR);
face([W, -T, -SLAB], [0, 1, 0], [0, 0, 1], rect(D + T, SLAB), (a, b) => b > SLAB - 1 ? hex('#d9d6cc') : hex('#b9b5a9'), FLOOR);

const BAR = 34;
const wallStains = [];
for (let i = 0; i < 10; i++) wallStains.push([rand() * 110, 4 + rand() * 100, 2 + rand() * 6, 1.5 + rand() * 4]);
function wallColor(u, z, light, which) {
  let c;
  if (z < BAR) c = hex('#4e8a69');
  else if (z < BAR + 1.5) c = hex('#2f5c45');
  else c = hex('#e8e2cc');
  for (const [su, sz, ru, rz] of wallStains) { const a = (u - su) / ru, b = (z - sz) / rz; if (a * a + b * b < 1) c = z < BAR ? mix(c, hex('#6f9e7e'), 0.5) : mix(c, hex('#cfc6a8'), 0.6); }
  if (z >= BAR + 1.5 && hash(Math.floor(u), Math.floor(z), which) < 0.012) c = mul(c, 0.9);
  if (z < BAR && hash(Math.floor(u / 2), Math.floor(z / 2), which + 9) < 0.02) c = hex('#cfd8cd');
  if (z < 3) c = mul(c, 0.82);
  return mul(c, light);
}
// wall A: plane y=0 (right wall, faces +y, darker)
face([0, 0, 0], [1, 0, 0], [0, 0, 1], rect(W, H), (a, b, P) => {
  const x = P[0], z = P[2];
  let c = wallColor(x, z, 0.86, 1);
  if (x >= PX0 - 2 && x < PX0 && z >= PZ1 - PHEI - 1 && z < PZ1 - 1) c = mul(c, 0.85);
  if (x < 3) c = mul(c, 0.9);
  return c;
}, WALL);
// wall B: plane x=0 (left wall, faces +x, lighter)
face([0, D, 0], [0, -1, 0], [0, 0, 1], rect(D, H), (a, b, P) => {
  const y = P[1], z = P[2];
  let c = wallColor(D - y + 37, z, 1, 2);
  if (y >= CY1 && y < CY1 + 4 && z < 92 - (y - CY1) * 3) c = mul(c, 0.82);
  if (y >= CHY1 && y < CHY1 + 3 && z < 46) c = mul(c, 0.86);
  if (y < 3) c = mul(c, 0.9);
  return c;
}, WALL);
face([-T, -T, H], [1, 0, 0], [0, 1, 0], [[0, 0], [W + T, 0], [W + T, T], [T, T], [T, D + T], [0, D + T]], flat(hex('#f6f2e4')), WALL);
face([W, -T, -SLAB], [0, 1, 0], [0, 0, 1], rect(T, H + SLAB), flat(hex('#d6cfb6')), WALL);
face([-T, D, -SLAB], [1, 0, 0], [0, 0, 1], rect(T, H + SLAB), flat(hex('#b9b29b')), WALL);

// ---------- poster (Pitu) on wall A ----------
const poster = Tex(PWID, PHEI, hex('#f2cf3c'));
{
  const red = hex('#c8161d'), dred = hex('#7d0c10'), cream = hex('#fbeec0');
  for (let x = 0; x < PWID; x++) for (let y = 0; y < PHEI; y++) if (x < 1 || y < 1 || x >= PWID - 1 || y >= PHEI - 1) poster.set(x, y, red);
  for (let x = 2; x < PWID - 2; x++) { poster.set(x, 2, red); poster.set(x, PHEI - 3, red); }
  drawText(poster, F3, 'CACHAÇA', Math.floor((PWID - textWidth(F3, 'CACHAÇA')) / 2), 4, dred);
  const cx = 15, cy = 19, seg = 9;
  for (let k = 0; k < seg; k++) {
    const t = k / (seg - 1);
    const ang = Math.PI * (1.15 - 1.25 * t);
    const R = 6.2, r = 3.4 - 2.2 * t;
    const px = cx + Math.cos(ang) * R, py = cy - Math.sin(ang) * R * 0.8;
    for (let y = -4; y <= 4; y++) for (let x = -4; x <= 4; x++) if (x * x + y * y <= r * r) {
      const shade = (x + y < -1) ? hex('#ff7a4a') : (k % 2 ? hex('#e2401f') : hex('#d23417'));
      poster.set(Math.round(px + x), Math.round(py + y), shade);
    }
    if (k === seg - 1) for (const [fx, fy] of [[1, 1], [2, 2], [0, 2], [1, 3], [3, 3], [-1, 3]]) poster.set(Math.round(px + fx), Math.round(py + fy), red);
  }
  const hx = cx + Math.cos(Math.PI * 1.15) * 6.2, hy = cy - Math.sin(Math.PI * 1.15) * 6.2 * 0.8;
  poster.set(Math.round(hx) - 1, Math.round(hy) - 1, hex('#111111'));
  for (let k = 0; k < 11; k++) poster.set(Math.round(hx) - 2 + Math.round(k * 0.9), Math.round(hy) - 3 - Math.round(Math.sqrt(k) * 2.4), dred);
  for (let k = 0; k < 9; k++) poster.set(Math.round(hx) - 3 + k, Math.round(hy) - 2 - Math.round(Math.sqrt(k) * 1.6), dred);
  for (let k = 0; k < 4; k++) poster.set(cx - 3 + k * 2, cy + 3, dred);
  const pw = textWidth(F7, 'PITU'), px0 = Math.floor((PWID - pw) / 2);
  drawText(poster, F7, 'PITU', px0 + 1, 29, dred);
  drawText(poster, F7, 'PITU', px0, 28, red);
  for (let x = 0; x < PWID; x++) for (let y = 0; y < PHEI; y++) poster.set(x, y, mix(poster.get(x, y), cream, 0.12 + 0.1 * (y / PHEI)));
  for (let k = 0; k < 4; k++) for (let j = 0; j <= 3 - k; j++) poster.set(PWID - 1 - j, PHEI - 1 - k, k + j === 3 ? hex('#b9a780') : cream);
  for (let x = 1; x < 6; x++) { poster.set(x, 0, hex('#e7e2cf')); poster.set(PWID - 1 - x, 0, hex('#e7e2cf')); }
}
const POSTER = newId('#3a2a14');
face([PX0, 0.3, PZ1 - PHEI], [1, 0, 0], [0, 0, 1], rect(PWID, PHEI), (a, b) => poster.get(a, PHEI - b), POSTER);

// ---------- extrusion helper: profile in (x,z), extruded along y ----------
function extrudeY(prof, y0, y1, frontShader, sideShader, id) {
  for (let i = 0; i < prof.length - 1 + (prof.closed ? 1 : 0); i++) {
    const [x0, z0] = prof[i], [x1, z1] = prof[(i + 1) % prof.length];
    const dx = x1 - x0, dz = z1 - z0, L = Math.hypot(dx, dz);
    if (dz + -dx <= 0) continue; // outward normal (dz,-dx) must face the viewer
    face([x0, y0, z0], [0, 1, 0], [dx / L, 0, dz / L], rect(y1 - y0, L), (a, b, P) => frontShader(i, a, b, P, L), id);
  }
  face([0, y1, 0], [1, 0, 0], [0, 0, 1], prof, sideShader, id);
}
function segDist(p, a, b) { const vx = b[0] - a[0], vy = b[1] - a[1], t = Math.max(0, Math.min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / (vx * vx + vy * vy))); return Math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy); }

// ---------- arcade cabinet (against wall B, front faces +x) ----------
// body profile (x = depth from the wall, z = height); the screen sits recessed between the side panels
const prof = [[0, 0], [30, 0], [30, 42], [35, 45], [35, 49], [26, 52], [21, 73], [30, 75], [30, 88], [27, 90], [0, 83]];
const sideProf = [[0, 0], [30, 0], [30, 42], [35, 45], [35, 49], [27.5, 52], [23, 73], [30, 75], [30, 88], [27, 90], [0, 83]];
const CAB = newId('#141417');
const gray = hex('#666a72'), grayD = hex('#4c5057');
const marquee = Tex(CW, 13, hex('#0d0d10'));
{
  const gold = hex('#f3c53a'), goldD = hex('#a8761c'), chrome = hex('#d5d9de');
  const l1 = textWidth(F4, 'VIDEO'), l2 = textWidth(F4, 'GAME');
    drawText(marquee, F4, 'VIDEO', Math.floor((CW - l1) / 2), 1, gold);
    drawText(marquee, F4, 'GAME', Math.floor((CW - l2) / 2), 7, gold);
  for (let x = 0; x < CW; x++) { marquee.set(x, 0, chrome); marquee.set(x, 12, mul(chrome, 0.75)); }
  for (let y = 0; y < 13; y++) { marquee.set(0, y, chrome); marquee.set(CW - 1, y, mul(chrome, 0.75)); }
}
// CRT: a versus fighting game (health bars, two fighters, stage)
const crt = (() => {
  const t = Tex(20, 13, hex('#000000'));
  for (let y = 0; y < 13; y++) for (let x = 0; x < 20; x++) t.set(x, y, mix(hex('#141c4a'), hex('#3f68c8'), Math.min(1, y / 9)));
  for (const [x0, w, h] of [[0, 4, 2], [7, 6, 1], [15, 5, 2]]) for (let x = x0; x < x0 + w; x++) for (let y = 10 - h; y < 10; y++) t.set(x, y, hex('#25306a'));
  for (let x = 0; x < 20; x++) { t.set(x, 10, hex('#8a5a32')); t.set(x, 11, hex('#6e4526')); t.set(x, 12, hex('#5a381f')); }
  // health bars + timer
  for (let x = 1; x < 9; x++) t.set(x, 1, x < 7 ? hex('#ffe03a') : hex('#d02020'));
  for (let x = 11; x < 19; x++) t.set(x, 1, x > 14 ? hex('#ffe03a') : hex('#d02020'));
  t.set(9, 1, hex('#ffffff')); t.set(10, 1, hex('#ffffff'));
  const C = { h: '#2a1a10', s: '#f0b080', w: '#f4f4f4', b: '#222222', r: '#d82828', y: '#ffd23a', o: '#ffffff', g: '#2a2a2a' };
  const left = ['.hh...', '.ss...', '.wwwss', '.ww...', '.bb...', '.ww...', 'w..w..', 'w..w..', 'g..g..'];
  const right = ['..yy..', '..ss..', '.rrr..', 's.rr..', '..yy..', '..rr..', '.r..rr', '.r....', '.g....'];
  const put = (spr, x0, y0) => spr.forEach((r, y) => [...r].forEach((v, x) => { if (C[v]) t.set(x0 + x, y0 + y, hex(C[v])); }));
  put(left, 3, 2); put(right, 10, 2);
  t.set(9, 4, hex('#9fe8ff')); t.set(10, 4, hex('#ffffff')); // hit spark
  for (let y = 0; y < 13; y += 2) for (let x = 0; x < 20; x++) t.set(x, y, mul(t.get(x, y), 0.85));
  return t;
})();
const BTN = [[8, 3.0], [10.5, 2.6], [13, 3.0], [8, 6.0], [10.5, 5.6], [13, 6.0]];
function cabFront(i, a, b, P, L) {
  const u = CY1 - P[1]; // texture u runs left-to-right on screen
  if (i === 1) { // lower body: engraved frame + silver coin door
    const z = b;
    if (z < 2.5) return hex('#1d1e22');
    if (z >= 39.5) return grayD;
    if (u >= 8 && u < 23 && z >= 18 && z < 31) {
      if (u < 9 || u >= 22 || z < 19 || z >= 30) return hex('#8d9198');
      if (u >= 10 && u < 16 && z >= 22 && z < 28.5) { // coin mechanism plate
        if (u < 10.8 || u >= 15.2 || z < 22.8 || z >= 27.7) return hex('#7b8088');
        if (u >= 12.5 && u < 13.5 && z >= 24 && z < 27) return hex('#141418');
        return hex('#b0b5bc');
      }
      if (u >= 18.5 && u < 19.5 && z >= 24 && z < 26) return hex('#2a2a2e');
      return hex('#cdd1d7');
    }
    const fr = (Math.abs(u - 4) < 0.5 || Math.abs(u - 26.5) < 0.5) && z >= 6 && z < 36 || (Math.abs(z - 6) < 0.5 || Math.abs(z - 35.5) < 0.5) && u >= 4 && u < 27;
    if (fr) return mul(gray, 0.78);
    return gray;
  }
  if (i === 3) return b > 3 ? hex('#e6e9ed') : hex('#a9aeb5'); // control panel fascia
  if (i === 4) { // control panel top: P1 yellow, P2 blue
    for (const [bu, bv] of BTN) {
      if (Math.abs(u - bu) < 1 && Math.abs(b - bv) < 0.9) return hex('#ffcf1f');
      if (Math.abs(u - bu - 13) < 1 && Math.abs(b - bv) < 0.9) return hex('#22a7d6');
    }
    if (b > L - 0.8) return hex('#878d95');
    return hex('#cfd4da');
  }
  if (i === 5) { // bezel with the perspective grid + CRT
    const v = L - b, su = u - 5, sv = v - 6;
    if (su >= 0 && su < 20 && sv >= 0 && sv < 13) return crt.get(su, sv);
    if (su >= -1 && su < 21 && sv >= -1 && sv < 14) return hex('#050508');
    const gu = Math.floor((u - 15) / (1 + v * 0.12) + 100);
    if (v > 9 && (Math.floor(v) % 3 === 0 || gu % 4 === 0)) return hex('#8a8e98');
    return hex('#141418');
  }
  if (i === 7) return marquee.get(u, 12.999 - b);
  if (i === 8) return hex('#2a2b30');
  if (i === 9) return mul(gray, 1.12);
  return gray;
}
extrudeY(prof, CY0 + 1.5, CY1 - 1.5, cabFront, flat(hex('#3a3d44')), CAB);
const molding = () => hex('#1d1d21');
extrudeY(sideProf, CY0, CY0 + 1.5, molding, flat(hex('#33363c')), CAB);
// side panel: black T-molding and the red racing stripes
extrudeY(sideProf, CY1 - 1.5, CY1, molding, (a, b) => {
  let dmin = 1e9;
  for (let i = 0; i < sideProf.length - 1; i++) dmin = Math.min(dmin, segDist([a, b], sideProf[i], sideProf[i + 1]));
  if (dmin < 1.3) return hex('#1b1b1f');
  const base = b < 3 ? hex('#383b41') : hex('#474b52');
  const red = hex('#a3262b'), worn = false;
  const w = b - 1.7 * a;
  if (b > 54 && b < 84 && a > 3 && !worn) for (const w0 of [38, 46, 54]) if (w >= w0 && w < w0 + 4.5) return red;
  if (!worn) for (const [a0, top] of [[14, 32], [18.5, 28], [23, 24]]) if (a >= a0 && a < a0 + 2.6 && b > 12 && b < top) return red;
  return base;
}, CAB);
const JOY = newId(null);
for (const ju of [5, 18]) {
  const jx = 30.7, jy = CY1 - ju, jz = 50.4;
  for (let z = 0; z < 3.5; z += 0.1) for (let ang = 0; ang < 6.3; ang += 0.2) splat([jx + Math.cos(ang) * 0.5, jy + Math.sin(ang) * 0.5, jz + z], hex('#2b2b30'), JOY);
  for (let th = 0; th < Math.PI; th += 0.08) for (let ph = 0; ph < 6.3; ph += 0.08) {
    const n = [Math.sin(th) * Math.cos(ph), Math.sin(th) * Math.sin(ph), Math.cos(th)];
    const l = n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2];
    splat([jx + n[0] * 1.5, jy + n[1] * 1.5, jz + 4 + n[2] * 1.5], l > 0.8 ? hex('#9a9aa6') : hex('#151518'), JOY);
  }
}

// ---------- red folding metal chair (bar chair, against wall B, faces +x) ----------
// thin tubular frame, thin pressed-steel seat, short backrest plate only at the top
const R_HI = hex('#ff7466'), R_LT = hex('#e3222c'), R_MD = hex('#bb1520'), R_DK = hex('#850c14'), RUB = hex('#141414');
const TUBE = newId('#3d0508'), PANEL = newId('#3d0508');
function shadeRed(n, gloss = 0) {
  const l = n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2];
  if (l > 0.93 - gloss) return R_HI;
  if (l > 0.55) return R_LT;
  if (l > 0.15) return R_MD;
  return R_DK;
}
// a round tube from A to B; the first `foot` units are the black rubber cap
function tube(A, B, r, id, foot = 0) {
  const d = [B[0] - A[0], B[1] - A[1], B[2] - A[2]], L = Math.hypot(...d), t = d.map(c => c / L);
  const up = Math.abs(t[2]) < 0.9 ? [0, 0, 1] : [1, 0, 0];
  let e1 = [t[1] * up[2] - t[2] * up[1], t[2] * up[0] - t[0] * up[2], t[0] * up[1] - t[1] * up[0]];
  const n1 = Math.hypot(...e1); e1 = e1.map(c => c / n1);
  const e2 = [t[1] * e1[2] - t[2] * e1[1], t[2] * e1[0] - t[0] * e1[2], t[0] * e1[1] - t[1] * e1[0]];
  for (let s = 0; s <= L; s += 0.15) for (let ang = 0; ang < 6.3; ang += 0.3) {
    const n = [0, 1, 2].map(k => e1[k] * Math.cos(ang) + e2[k] * Math.sin(ang));
    splat([0, 1, 2].map(k => A[k] + t[k] * s + n[k] * r), s < foot ? RUB : shadeRed(n), id);
  }
}
{
  const yl = CHY0 + 0.5, yr = CHY1 - 0.5;           // long tubes: front legs that rise into the backrest
  const FX = 22, TX = 22 - 40 / 3, TZ = 40;
  const at = (y, z) => [FX - (FX - TX) * z / TZ, y, z];
  for (const y of [yl, yr]) tube([FX, y, 0], [TX, y, TZ], 0.45, TUBE, 1.2);
  // rear legs: floor near the wall up to the hinge just under the backrest
  const HZ = 28;
  for (const y of [yl + 1.5, yr - 1.5]) tube([2, y, 0], at(y, HZ), 0.45, TUBE, 1.2);
  // stretchers
  tube(at(yl, 3), at(yr, 3), 0.4, TUBE);
  const rx = 2 + (at(0, HZ)[0] - 2) * 5 / HZ;
  tube([rx, yl + 1.5, 5], [rx, yr - 1.5, 5], 0.4, TUBE);
  // seat: thin rounded tray
  const sx0 = 7.5, sx1 = 23, sy0 = CHY0 + 1, sy1 = CHY1 - 1, sz = 19, rc = 2;
  const inside = (x, y) => {
    const cx = Math.max(sx0 + rc, Math.min(sx1 - rc, x)), cy = Math.max(sy0 + rc, Math.min(sy1 - rc, y));
    return Math.hypot(x - cx, y - cy) <= rc;
  };
  for (let x = sx0; x <= sx1; x += 0.2) for (let y = sy0; y <= sy1; y += 0.2) {
    if (!inside(x, y)) continue;
    const edge = !inside(x + 0.5, y) || !inside(x, y + 0.5) || !inside(x - 0.5, y) || !inside(x, y - 0.5);
    const gl = Math.abs((x - sx0) - (y - sy0) * 0.9 - 3) < 0.9;
    splat([x, y, sz], edge ? R_HI : gl ? R_HI : R_LT, PANEL);
    if (edge) {
      const cx = Math.max(sx0 + rc, Math.min(sx1 - rc, x)), cy = Math.max(sy0 + rc, Math.min(sy1 - rc, y));
      let nx = x - cx, ny = y - cy;
      if (nx === 0 && ny === 0) nx = x > (sx0 + sx1) / 2 ? 1 : -1;
      const nn = Math.hypot(nx, ny);
      for (let z = sz - 1; z < sz; z += 0.2) splat([x, y, z], shadeRed([nx / nn, ny / nn, 0]), PANEL);
    }
  }
  // backrest: short curved plate across the top of the long tubes
  const d = [TX - FX, 0, TZ], dl = Math.hypot(...d), dn = d.map(c => c / dl);
  const nrm = [TZ / dl, 0, (FX - TX) / dl];
  const by0 = CHY0 - 0.2, by1 = CHY1 + 0.2, s0 = dl - 9, s1 = dl + 0.8, rr = 2.2;
  for (let s = s0; s <= s1; s += 0.15) for (let y = by0; y <= by1; y += 0.15) {
    const fromTop = s1 - s;
    const cy = Math.max(by0 + rr, Math.min(by1 - rr, y));
    if (fromTop < rr && Math.hypot(y - cy, rr - fromTop) > rr) continue;
    const bow = 0.7 * (1 - Math.pow((y - (by0 + by1) / 2) / ((by1 - by0) / 2), 2));
    const P = [FX + dn[0] * s + nrm[0] * 0.6 - bow, y, dn[2] * s + nrm[2] * 0.6];
    const edge = fromTop < 0.5 || s < s0 + 0.5;
    const gl = Math.abs(s - (s0 + 5) + (y - by0) * 0.3) < 0.6;
    splat(P, edge ? R_MD : gl ? R_HI : shadeRed([nrm[0], 0, nrm[2]]), PANEL);
  }
}

// ---------- pot + espada de São Jorge ----------
const POT = newId('#4a2412');
for (let z = 0; z <= 10; z += 0.15) {
  const r = 4.3 + z * 0.17 + (z > 8.3 ? 0.7 : 0);
  for (let ang = 0; ang < 6.3; ang += 0.03) {
    const nx = Math.cos(ang), ny = Math.sin(ang);
    const l = nx * 0.9 + ny * -0.2;
    let c = z > 8.3 ? hex('#d97a45') : hex('#c2602e');
    if (l < 0.1) c = mul(c, 0.75); else if (l > 0.7) c = mul(c, 1.1);
    splat([PCX + nx * r, PCY + ny * r, z], c, POT);
  }
}
for (let r = 0; r < 6.7; r += 0.2) for (let ang = 0; ang < 6.3; ang += 0.05) {
  const c = r > 5.9 ? hex('#e08a55') : hash(Math.floor(r * 3), Math.floor(ang * 5)) < 0.3 ? hex('#3b2414') : hex('#4d3020');
  splat([PCX + Math.cos(ang) * r, PCY + Math.sin(ang) * r, 10], c, POT);
}
{
  // each leaf grows from its own spot in the soil; depth follows the real 3D point,
  // so leaves overlap front-to-back and the pot rim hides the bases of the front ones
  const leaves = [ // world dx, dy in the pot, height, lean (px), half width
    [1, -4, 48, 4, 3.0], [-3, -2, 42, -9, 2.9], [3, -1, 40, 11, 2.8],
    [0, 0, 54, -1, 3.3], [-3, 3, 33, -12, 2.7], [3, 3, 30, 10, 2.6], [0, 4, 36, 3, 2.9],
  ];
  const dg = hex('2d5a33'.replace(/^/, "#")), lg = hex("#79a457"), ed = hex("#d9cf54");
  leaves.forEach(([dx, dy, h0, lean0, hw], li) => {
    const h = Math.round(h0 * 0.7), lean = lean0 * 0.8;
    const id = newId("#16301b");
    const B = [PCX + dx * 0.75, PCY + dy * 0.75, 9.5], pb = proj(B);
    const bx = pb[0], by = Math.floor(pb[1]);
    for (let r = 0; r < h; r++) {
      const t = r / h;
      const cx = bx + lean * Math.pow(t, 1.6);
      const w = Math.max(0.5, hw * (t < 0.12 ? 0.8 + t * 1.6 : 1 - Math.pow((t - 0.12) / 0.88, 1.8)));
      const xa = Math.round(cx - w), xb = Math.round(cx + w);
      const py = by - r, d = B[0] + B[1] + B[2] + r;
      for (let px = xa; px <= xb; px++) {
        if (px < 0 || py < 0 || px >= SW || py >= SH) continue;
        const i = py * SW + px;
        if (d < dep[i]) continue;
        let c;
        if (xb - xa >= 2 && (px === xa || px === xb)) c = ed;
        else c = ((r + li * 2 + ((px - xa) % 2)) % 5 === 0 || (r + li * 2 + ((px - xa) % 2)) % 5 === 1 && (px - xa) % 3 === 1) ? lg : dg;
        if (r > h - 3 && px === xa) c = dg;
        col[i] = c; dep[i] = d; ids[i] = id;
      }
    }
  });
}

// ---------- outlines ----------
const out = col.slice();
const roomOutline = hex('#2b2620');
for (let y = 0; y < SH; y++) for (let x = 0; x < SW; x++) {
  const i = y * SW + x, q = ids[i];
  let best = null, bestD = -1e9;
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    const xx = x + dx, yy = y + dy;
    if (xx < 0 || yy < 0 || xx >= SW || yy >= SH) continue;
    const j = yy * SW + xx, p = ids[j];
    if (p === q || p === 0) continue;
    const oc = outlineOf[p];
    if (q === 0) { const c = oc || (ROOM.has(p) ? roomOutline : null); if (c && dep[j] > bestD) { best = c; bestD = dep[j]; } continue; }
    if (!oc) continue;
    if (ROOM.has(q) || dep[j] > dep[i] + 0.25) { if (dep[j] > bestD) { best = oc; bestD = dep[j]; } }
  }
  if (best) out[i] = best;
}

// ---------- PNG ----------
function png(file, w, h, getRGBA) {
  const raw = Buffer.alloc((w * 4 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 4 + 1)] = 0; for (let x = 0; x < w; x++) { const c = getRGBA(x, y); raw.set(c, y * (w * 4 + 1) + 1 + x * 4); } }
  const crcT = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; crcT[n] = c >>> 0; }
  const crc = b => { let c = 0xffffffff; for (const v of b) c = crcT[(c ^ v) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (t, d) => { const len = Buffer.alloc(4); len.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(t), d]); const cr = Buffer.alloc(4); cr.writeUInt32BE(crc(td)); return Buffer.concat([len, td, cr]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
  fs.writeFileSync(file, Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]));
}
const dir = process.argv[2] || __dirname;
const px = (x, y) => { const c = out[y * SW + x]; return c ? [c[0], c[1], c[2], 255] : [0, 0, 0, 0]; };
png(path.join(dir, 'fliperama-habbo-240p.png'), SW, SH, px);
// tight crop around the room, transparent background (logo files)
let bx0 = SW, by0 = SH, bx1 = 0, by1 = 0;
for (let y = 0; y < SH; y++) for (let x = 0; x < SW; x++) if (out[y * SW + x]) { bx0 = Math.min(bx0, x); by0 = Math.min(by0, y); bx1 = Math.max(bx1, x); by1 = Math.max(by1, y); }
const LW = bx1 - bx0 + 1, LH = by1 - by0 + 1;
png(path.join(dir, "fliperos-logo.png"), LW, LH, (x, y) => px(bx0 + x, by0 + y));
png(path.join(dir, "fliperos-logo-4x.png"), LW * 4, LH * 4, (x, y) => px(bx0 + Math.floor(x / 4), by0 + Math.floor(y / 4)));
console.log("logo", LW, "x", LH);
const S = 4, bg = [40, 42, 54, 255];
png(path.join(dir, 'fliperama-habbo-preview-4x.png'), SW * S, SH * S, (x, y) => { const c = px(Math.floor(x / S), Math.floor(y / S)); return c[3] ? c : bg; });
if (process.env.CROP) { const [cx, cy, cw, chh] = process.env.CROP.split(",").map(Number); const Z = 8; png(path.join(dir, "crop.png"), cw * Z, chh * Z, (x, y) => { const c = px(cx + Math.floor(x / Z), cy + Math.floor(y / Z)); return c[3] ? c : bg; }); }
console.log("ok");
