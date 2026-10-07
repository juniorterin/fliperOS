'use client';

import { Crosshair, Gauge, Joystick, Monitor, Network, ScanLine, SlidersHorizontal, type LucideIcon } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';

const STYLE: Record<string, { icon: LucideIcon; color: string; span: string }> = {
  crt: { icon: Monitor, color: 'text-purple bg-purple/10 border-purple/30', span: 'sm:col-span-2' },
  switchres: { icon: ScanLine, color: 'text-cyan bg-cyan/10 border-cyan/30', span: '' },
  latency: { icon: Gauge, color: 'text-yellow bg-yellow/10 border-yellow/30', span: '' },
  arcade: { icon: Joystick, color: 'text-pink bg-pink/10 border-pink/30', span: '' },
  network: { icon: Network, color: 'text-green bg-green/10 border-green/30', span: '' },
  lightgun: { icon: Crosshair, color: 'text-red bg-red/10 border-red/30', span: 'lg:col-span-3' },
  setup: { icon: SlidersHorizontal, color: 'text-orange bg-orange/10 border-orange/30', span: 'lg:col-span-3' },
};

// Cards de linha inteira: texto a esquerda e os pontos a direita no desktop.
const WIDE = new Set(['lightgun', 'setup']);

const ORDER = Object.keys(STYLE);

export function Features() {
  const { t } = useI18n();
  const f = t.features;
  const items = [...f.items].sort((a, b) => ORDER.indexOf(a.id) - ORDER.indexOf(b.id));
  return (
    <section id="features" aria-labelledby="features-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="features" kicker={f.kicker} title={f.title} intro={f.intro} />
        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-5">
          {items.map((item, i) => {
            const style = STYLE[item.id] ?? STYLE.crt;
            const Icon = style.icon;
            const wide = WIDE.has(item.id);
            return (
              <Reveal as="li" key={item.id} delay={i * 60} className={`${style.span} ${wide ? 'sm:col-span-2' : ''}`}>
                <article
                  className={`card h-full rounded-2xl p-6 sm:p-7 ${wide ? 'lg:flex lg:items-center lg:gap-10' : ''}`}
                >
                  <div className={wide ? 'lg:max-w-md' : ''}>
                    <span className={`inline-flex size-11 items-center justify-center rounded-xl border ${style.color}`}>
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <h3 className="mt-5 text-xl font-semibold text-fg">{item.title}</h3>
                    <p className="mt-2.5 leading-relaxed text-muted">{item.text}</p>
                  </div>
                  {item.points.length > 0 ? (
                    <ul className={`mt-5 flex flex-wrap gap-2 ${wide ? 'lg:mt-0 lg:flex-1 lg:justify-end' : ''}`}>
                      {item.points.map((p) => (
                        <li
                          key={p}
                          className="rounded-md border border-line bg-bg-deeper/70 px-2.5 py-1 font-mono text-xs text-fg"
                        >
                          {p}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </article>
              </Reveal>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
