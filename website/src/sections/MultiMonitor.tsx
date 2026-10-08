'use client';

import Image from 'next/image';
import { ArrowUpRight, Joystick, Plane, SlidersHorizontal, ToggleRight, type LucideIcon } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { LINKS } from '@/lib/site';

const POINT_STYLE: Record<string, { icon: LucideIcon; color: string }> = {
  setup: { icon: SlidersHorizontal, color: 'text-orange border-orange/40 bg-orange/10' },
  groovymame: { icon: Joystick, color: 'text-pink border-pink/40 bg-pink/10' },
  flycast: { icon: Plane, color: 'text-cyan border-cyan/40 bg-cyan/10' },
  toggle: { icon: ToggleRight, color: 'text-green border-green/40 bg-green/10' },
};

// Saidas de exemplo, na ordem das telas do jogo (screens= do fliperos.conf).
const ROW_OUTPUTS = ['DVI-I-1', 'VGA-1', 'DVI-I-2'];
const STACK_OUTPUTS = ['VGA-1', 'DVI-I-1'];

// Captura do MAME cortada por tela; o CRT estica cada uma para 4:3, entao a
// imagem preenche o tubo sem cortar, e as scanlines do .crt-screen ficam por cima.
function Screen({ src, alt, label, output, sizes }: {
  src: string;
  alt: string;
  label: string;
  output: string;
  sizes: string;
}) {
  return (
    <div className="crt-bezel rounded-2xl p-2.5 sm:p-3">
      <div className="crt-screen aspect-[4/3] w-full">
        <Image src={src} alt={alt} fill unoptimized sizes={sizes} className="object-fill [image-rendering:pixelated]" />
      </div>
      <p className="mt-2 text-center font-mono text-[10px] tracking-[0.25em] text-comment uppercase">
        {`${label} \u00b7 ${output}`}
      </p>
    </div>
  );
}

export function MultiMonitor() {
  const { t } = useI18n();
  const m = t.multiMonitor;
  return (
    <section id="multi-monitor" aria-labelledby="multi-monitor-title" className="relative overflow-hidden py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-pink/40 to-transparent" />
      <div aria-hidden="true" className="glow-pink pointer-events-none absolute -top-40 -right-40 h-[500px] w-[700px]" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="multi-monitor" kicker={m.kicker} title={m.title} intro={m.intro} />

        <div className="mt-14 grid gap-6 lg:grid-cols-3 lg:items-end">
          <Reveal as="figure" className="lg:col-span-2">
            <div className="grid grid-cols-3 gap-2 sm:gap-4">
              {ROW_OUTPUTS.map((output, i) => (
                <Screen
                  key={output}
                  src={`/screenshots/multi/darius-${i + 1}.webp`}
                  alt={`${m.rowLabel} (${m.screen} ${i + 1})`}
                  label={`${m.screen} ${i + 1}`}
                  output={output}
                  sizes="(min-width: 1024px) 280px, 30vw"
                />
              ))}
            </div>
            <figcaption className="mt-4 font-mono text-xs tracking-widest text-comment uppercase">{m.rowLabel}</figcaption>
          </Reveal>
          <Reveal as="figure" delay={120} className="mx-auto w-full max-w-[220px]">
            <div className="grid gap-2 sm:gap-3">
              {STACK_OUTPUTS.map((output, i) => (
                <Screen
                  key={output}
                  src={`/screenshots/multi/punchout-${i + 1}.webp`}
                  alt={`${m.stackLabel} (${m.screen} ${i + 1})`}
                  label={`${m.screen} ${i + 1}`}
                  output={output}
                  sizes="220px"
                />
              ))}
            </div>
            <figcaption className="mt-4 font-mono text-xs tracking-widest text-comment uppercase">{m.stackLabel}</figcaption>
          </Reveal>
        </div>

        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {m.points.map((p, i) => {
            const style = POINT_STYLE[p.id] ?? POINT_STYLE.setup;
            const Icon = style.icon;
            return (
              <Reveal as="li" key={p.id} delay={i * 60}>
                <article className="card h-full rounded-2xl p-5">
                  <span className={`inline-flex size-10 items-center justify-center rounded-xl border ${style.color}`}>
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-4 font-semibold text-fg">{p.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{p.text}</p>
                </article>
              </Reveal>
            );
          })}
        </ul>

        <Reveal className="mt-10 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="font-mono text-xs tracking-widest text-comment uppercase">{m.gamesLabel}</p>
            <ul className="mt-3 flex flex-wrap gap-2">
              {m.games.map((g) => (
                <li key={g} className="rounded-md border border-line bg-bg-deeper/70 px-2.5 py-1 font-mono text-xs text-fg">
                  {g}
                </li>
              ))}
            </ul>
          </div>
          <a
            href={`${LINKS.docs}/Multiple-Monitors`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex shrink-0 items-center gap-2 self-start rounded-lg border border-pink/60 bg-pink/10 px-4 py-2.5 text-sm font-medium text-fg transition hover:border-pink hover:bg-pink/20 hover:shadow-[0_0_20px_-6px] hover:shadow-pink lg:self-auto"
          >
            {m.cta}
            <ArrowUpRight className="size-4" aria-hidden="true" />
            <span className="sr-only">{t.a11y.external}</span>
          </a>
        </Reveal>
      </div>
    </section>
  );
}
