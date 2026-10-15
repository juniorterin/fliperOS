'use client';

import Image from 'next/image';
import { ChevronLeft, ChevronRight, Pause, Play, X } from 'lucide-react';
import { useEffect, useRef, useState, useSyncExternalStore, type PointerEvent } from 'react';
import { track } from '@/lib/analytics';

export type Slide = { id: string; src: string; title: string; caption: string; alt: string };

type Labels = {
  label: string;
  previous: string;
  next: string;
  show: string;
  pause: string;
  play: string;
  open: string;
  close: string;
};

// Ritmo da legenda: digita, espera, apaga, e só então o prisma gira para a próxima tela.
const TYPE_MS = 34;
const ERASE_MS = 12;
const HOLD_MS = 2800;
const TURN_MS = 1100;

type Phase = 'turning' | 'typing' | 'holding' | 'erasing';

const MOTION_QUERY = '(prefers-reduced-motion: reduce)';
function subscribeMotion(onChange: () => void) {
  const query = window.matchMedia(MOTION_QUERY);
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}

function Caption({ title, caption, caret }: { title: string; caption: string; caret?: 'title' | 'caption' }) {
  return (
    <>
      <span className={`phosphor block text-sm font-semibold text-green ${caret === 'title' ? 'cursor-blink' : ''}`}>
        <span className="text-purple">&gt; </span>
        {title}
      </span>
      <span className={`mt-1 block min-h-[1lh] text-xs leading-relaxed text-muted sm:text-sm ${caret === 'caption' ? 'cursor-blink' : ''}`}>
        {caption}
      </span>
    </>
  );
}

// Os screenshots num prisma atrás do vidro do monitor: uma tela por vez,
// girando em 3D, com a legenda digitada e apagada a cada troca.
export function ScreenCarousel({ slides, labels }: { slides: Slide[]; labels: Labels }) {
  const count = slides.length;
  // Contador sem módulo: do último para o primeiro o prisma segue girando para a frente.
  const [turn, setTurn] = useState(0);
  const [phase, setPhase] = useState<Phase>('typing');
  const [typed, setTyped] = useState(0);
  const [hovered, setHovered] = useState(false);
  const [paused, setPaused] = useState(false);
  const [zoomed, setZoomed] = useState(false);
  const [announce, setAnnounce] = useState(false);
  const reduced = useSyncExternalStore(subscribeMotion, () => window.matchMedia(MOTION_QUERY).matches, () => false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const tiltRef = useRef<HTMLDivElement>(null);

  const index = ((turn % count) + count) % count;
  const slide = slides[index];
  const total = slide.title.length + slide.caption.length;
  const stopped = paused || hovered || zoomed;

  useEffect(() => {
    if (reduced) return;
    let delay = 0;
    let next = () => {};
    if (phase === 'turning') {
      delay = TURN_MS;
      next = () => setPhase('typing');
    } else if (phase === 'typing') {
      if (typed < total) {
        delay = TYPE_MS;
        next = () => setTyped(typed + 1);
      } else {
        next = () => setPhase('holding');
      }
    } else if (phase === 'holding') {
      if (stopped || count < 2) return;
      delay = HOLD_MS;
      next = () => setPhase('erasing');
    } else if (typed > 0) {
      delay = ERASE_MS;
      next = () => setTyped(Math.max(0, typed - 2));
    } else {
      delay = 150;
      next = () => {
        setTurn(turn + 1);
        setPhase('turning');
        setAnnounce(false);
      };
    }
    const id = window.setTimeout(next, delay);
    return () => window.clearTimeout(id);
  }, [phase, typed, total, stopped, count, turn, reduced]);

  const go = (target: number) => {
    setTurn(target);
    setTyped(0);
    setPhase('turning');
    setAnnounce(true);
    track('screenshot_view', { screenshot: slides[((target % count) + count) % count].id });
  };

  // Pelo caminho mais curto: do 1 para o 5 o prisma gira um passo para trás.
  const show = (i: number) => {
    let delta = i - index;
    if (delta > count / 2) delta -= count;
    if (delta < -count / 2) delta += count;
    if (delta) go(turn + delta);
  };

  const open = () => {
    setZoomed(true);
    dialogRef.current?.showModal();
    track('screenshot_view', { screenshot: slide.id });
  };

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    const tilt = tiltRef.current;
    if (reduced || e.pointerType !== 'mouse' || !tilt) return;
    const box = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - box.left) / box.width - 0.5;
    const y = (e.clientY - box.top) / box.height - 0.5;
    tilt.style.transform = `rotateX(${(-y * 12).toFixed(2)}deg) rotateY(${(x * 16).toFixed(2)}deg)`;
  };
  const onPointerLeave = () => {
    if (tiltRef.current) tiltRef.current.style.transform = '';
  };

  // Raio do prisma em frações da largura da tela: a face da frente cobre a tela inteira.
  const angle = 360 / count;
  const radius = count > 2 ? 0.5 / Math.tan(Math.PI / count) : 0;
  const shown = reduced ? total : typed;
  const titleTyped = slide.title.slice(0, shown);
  const captionTyped = slide.caption.slice(0, Math.max(0, shown - slide.title.length));

  return (
    <figure
      role="group"
      aria-roledescription="carousel"
      aria-label={labels.label}
      className="float relative mx-auto w-full max-w-xl"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocus={() => setHovered(true)}
      onBlur={(e) => !e.currentTarget.contains(e.relatedTarget) && setHovered(false)}
    >
      <div className="monitor-3d" onPointerMove={onPointerMove} onPointerLeave={onPointerLeave}>
        <div ref={tiltRef} className="monitor-tilt crt-bezel rounded-[28px] p-4 sm:p-5">
          <div className="prism-screen relative aspect-[4/3] w-full overflow-hidden rounded-[14px] bg-bg-deeper">
            <div className={`prism-lift ${phase === 'turning' ? (turn % 2 ? 'lift-a' : 'lift-b') : ''}`}>
              <div
                className="prism"
                style={{ transform: `translateZ(calc(${-radius} * 100cqw)) rotateY(${-turn * angle}deg)` }}
              >
                {slides.map((s, i) => {
                  const active = i === index;
                  return (
                    <div
                      key={s.id}
                      aria-hidden={!active}
                      className="prism-face"
                      style={{
                        transform: `rotateY(${i * angle}deg) translateZ(calc(${radius} * 100cqw))`,
                        opacity: active || (phase === 'turning' && !reduced) ? 1 : 0,
                      }}
                    >
                      <Image
                        src={s.src}
                        alt={s.alt}
                        fill
                        priority={i === 0}
                        loading={i === 0 ? undefined : 'eager'}
                        sizes="(min-width: 1024px) 560px, 92vw"
                        unoptimized
                        className="object-cover"
                      />
                      <span
                        aria-hidden="true"
                        className="absolute inset-0 bg-bg-deeper transition-opacity duration-1000"
                        style={{ opacity: active ? 0 : 0.7 }}
                      />
                    </div>
                  );
                })}
              </div>
            </div>
            <button
              type="button"
              onClick={open}
              className="absolute inset-0 z-[4] block h-full w-full cursor-zoom-in"
              aria-label={`${labels.open}: ${slide.title}`}
            />
          </div>

          <div className="mt-3 flex items-center justify-between gap-3 px-2">
            <span aria-hidden="true" className="font-mono text-[10px] tracking-[0.3em] text-comment uppercase">
              15 kHz
            </span>
            {count > 1 ? (
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => go(turn - 1)}
                  aria-label={labels.previous}
                  className="grid size-6 place-items-center rounded-md text-comment transition hover:text-fg"
                >
                  <ChevronLeft className="size-4" aria-hidden="true" />
                </button>
                {slides.map((s, i) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => show(i)}
                    aria-label={`${labels.show} ${i + 1}: ${s.title}`}
                    aria-current={i === index}
                    className="grid size-6 place-items-center"
                  >
                    <span
                      className={`size-2 rounded-full transition duration-300 ${
                        i === index ? 'bg-green shadow-[0_0_8px] shadow-green' : 'bg-comment/60 hover:bg-cyan/80'
                      }`}
                    />
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setPaused(!paused)}
                  aria-label={paused ? labels.play : labels.pause}
                  aria-pressed={paused}
                  className="grid size-6 place-items-center rounded-md text-comment transition hover:text-fg"
                >
                  {paused ? <Play className="size-3.5" aria-hidden="true" /> : <Pause className="size-3.5" aria-hidden="true" />}
                </button>
                <button
                  type="button"
                  onClick={() => go(turn + 1)}
                  aria-label={labels.next}
                  className="grid size-6 place-items-center rounded-md text-comment transition hover:text-fg"
                >
                  <ChevronRight className="size-4" aria-hidden="true" />
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <figcaption className="mt-5 grid px-2 font-mono">
        {/* Cópias invisíveis de todas as legendas reservam a altura da maior: nada pula ao digitar. */}
        {slides.map((s) => (
          <span key={s.id} aria-hidden="true" className="invisible col-start-1 row-start-1">
            <Caption title={s.title} caption={s.caption} />
          </span>
        ))}
        <span aria-hidden="true" className="col-start-1 row-start-1">
          <Caption
            title={titleTyped}
            caption={captionTyped}
            caret={reduced ? undefined : shown > slide.title.length ? 'caption' : 'title'}
          />
        </span>
        <span className="sr-only" aria-live={announce ? 'polite' : 'off'}>
          {slide.title}: {slide.caption}
        </span>
      </figcaption>

      <dialog
        ref={dialogRef}
        aria-label={slide.title}
        className="m-auto w-[min(1200px,94vw)] max-w-none rounded-2xl border border-line bg-bg-deeper p-0 text-fg"
        onClick={(e) => e.target === e.currentTarget && dialogRef.current?.close()}
        onClose={() => setZoomed(false)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') go(turn + 1);
          if (e.key === 'ArrowLeft') go(turn - 1);
        }}
      >
        {zoomed ? (
          <div>
            <div className="relative aspect-[4/3] w-full bg-black sm:aspect-[16/10]">
              <Image src={slide.src} alt={slide.alt} fill sizes="94vw" unoptimized className="object-contain" />
            </div>
            <div className="flex items-center gap-3 border-t border-line px-4 py-3 sm:px-5">
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{slide.title}</p>
                <p className="truncate text-sm text-muted">{slide.caption}</p>
              </div>
              {count > 1 ? (
                <>
                  <button type="button" onClick={() => go(turn - 1)} aria-label={labels.previous} className="rounded-lg border border-line p-2 hover:border-purple">
                    <ChevronLeft className="size-5" aria-hidden="true" />
                  </button>
                  <button type="button" onClick={() => go(turn + 1)} aria-label={labels.next} className="rounded-lg border border-line p-2 hover:border-purple">
                    <ChevronRight className="size-5" aria-hidden="true" />
                  </button>
                </>
              ) : null}
              <button
                type="button"
                onClick={() => dialogRef.current?.close()}
                aria-label={labels.close}
                className="rounded-lg border border-line p-2 hover:border-pink"
                autoFocus
              >
                <X className="size-5" aria-hidden="true" />
              </button>
            </div>
          </div>
        ) : null}
      </dialog>
    </figure>
  );
}
