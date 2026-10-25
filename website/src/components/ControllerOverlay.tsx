'use client';

import { useEffect, useState } from 'react';

// Simulacao da pagina do controle para o OBS (config/web/input.html): as
// mesmas medidas do input.css de fabrica (um painel de 200 x 100 --u, aqui o
// viewBox), as mesmas cores e a sequencia da demonstracao do painel web
// (input.js: meia-lua para frente + soco e os outros botoes).
const STEPS: string[][] = [
  ['down'], ['down', 'right'], ['right', 'b1'], ['right'], [], ['b2'], ['b3'], [], ['b4'], ['b5'],
  ['b6'], [], ['up'], ['up', 'left'], ['left', 'b4', 'b5'], [], ['start'], ['coin'], [],
];
// O jogador 2 espelhado: o golpe para o outro lado.
const MIRROR: Record<string, string> = { left: 'right', right: 'left' };
const COLORS = ['#ff5555', '#ffb86c', '#f1fa8c', '#50fa7b', '#8be9fd', '#bd93f9'];
const BUTTONS = [0, 1, 2, 3, 4, 5].map((i) => ({
  id: `b${i + 1}`,
  x: 105 + (i % 3) * 32,
  y: (i < 3 ? 39 : 73) + (i % 3 === 0 ? 6 : 0),
  color: COLORS[i],
}));

function Pad({ player, on, labels }: { player: number; on: Set<string>; labels: { start: string; coin: string } }) {
  const x = (on.has('right') ? 1 : 0) - (on.has('left') ? 1 : 0);
  const y = (on.has('down') ? 1 : 0) - (on.has('up') ? 1 : 0);
  const k = x && y ? 0.7 : 1;
  return (
    <svg viewBox="0 0 200 100" className="block h-auto w-full" aria-hidden="true">
      <text x="8" y="15" fontSize="9" fontWeight="800" fill={player === 1 ? '#ff79c6' : '#8be9fd'}>
        {`P${player}`}
      </text>
      <circle cx="46" cy="54" r="29.4" fill="rgba(25,26,33,.75)" stroke="#44475a" strokeWidth="1.2" />
      <g style={{ transform: `translate(${x * k * 16}px, ${y * k * 16}px)`, transition: 'transform 40ms linear' }}>
        <circle cx="46" cy="55.5" r="14" fill="rgba(0,0,0,.45)" />
        <circle cx="46" cy="54" r="14" fill={`url(#ball${player})`} />
      </g>
      <defs>
        <radialGradient id={`ball${player}`} cx="35%" cy="30%" r="75%">
          <stop offset="0%" stopColor="#ff9bd3" />
          <stop offset="45%" stopColor="#ff79c6" />
          <stop offset="100%" stopColor="#b0337f" />
        </radialGradient>
      </defs>
      {BUTTONS.map((b, i) => {
        const lit = on.has(b.id);
        return (
          <g key={b.id} style={{ opacity: lit ? 1 : 0.55, transition: 'opacity 40ms' }}>
            {lit && <circle cx={b.x} cy={b.y} r="17" fill={b.color} opacity="0.35" />}
            <circle cx={b.x} cy={b.y} r={lit ? 11.8 : 12.4} fill={b.color} stroke="rgba(25,26,33,.8)" strokeWidth="1.2"
              style={{ filter: lit ? 'brightness(1.25)' : undefined }} />
            <text x={b.x} y={b.y + 2.2} fontSize="6" fontWeight="800" textAnchor="middle" fill="#191a21">
              {i + 1}
            </text>
          </g>
        );
      })}
      {(['start', 'coin'] as const).map((id, i) => {
        const lit = on.has(id);
        return (
          <g key={id} style={{ opacity: lit ? 1 : 0.55, transition: 'opacity 40ms' }}>
            <rect x={134 + i * 30} y="6" width="26" height="11" rx="5.5" fill="#f8f8f2" stroke="rgba(25,26,33,.8)" strokeWidth="1.2" />
            <text x={147 + i * 30} y="13.3" fontSize="4.5" fontWeight="800" textAnchor="middle" fill="#191a21">
              {labels[id].toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function ControllerOverlay({ labels }: { labels: { start: string; coin: string } }) {
  const [step, setStep] = useState(2);
  useEffect(() => {
    // Quem pede menos movimento ve um quadro parado (o soco do golpe).
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = window.setInterval(() => setStep((s) => (s + 1) % STEPS.length), 280);
    return () => window.clearInterval(timer);
  }, []);
  const p1 = new Set(STEPS[step]);
  // O jogador 2 meio passo atras, para nao acender igual.
  const p2 = new Set(STEPS[(step + 6) % STEPS.length].map((c) => MIRROR[c] ?? c));
  return (
    // Na coluna do lado do texto (lg) um embaixo do outro, para cada um ficar grande.
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
      <Pad player={1} on={p1} labels={labels} />
      <Pad player={2} on={p2} labels={labels} />
    </div>
  );
}
