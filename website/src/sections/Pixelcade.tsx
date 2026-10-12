'use client';

import { ArrowUpRight, Cpu, Download, Gamepad2, ListVideo, Medal, MoonStar, Sparkles, Swords, Trophy, Usb, type LucideIcon } from 'lucide-react';
import { LedMatrix } from '@/components/LedMatrix';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { LINKS } from '@/lib/site';

const POINT_STYLE: Record<string, { icon: LucideIcon; color: string }> = {
  install: { icon: Download, color: 'text-orange border-orange/40 bg-orange/10' },
  browse: { icon: ListVideo, color: 'text-cyan border-cyan/40 bg-cyan/10' },
  launch: { icon: Gamepad2, color: 'text-pink border-pink/40 bg-pink/10' },
  usb: { icon: Usb, color: 'text-green border-green/40 bg-green/10' },
  scores: { icon: Trophy, color: 'text-yellow border-yellow/40 bg-yellow/10' },
  attract: { icon: MoonStar, color: 'text-purple border-purple/40 bg-purple/10' },
  achievements: { icon: Medal, color: 'text-orange border-orange/40 bg-orange/10' },
  effects: { icon: Sparkles, color: 'text-cyan border-cyan/40 bg-cyan/10' },
  versus: { icon: Swords, color: 'text-pink border-pink/40 bg-pink/10' },
  zedmd: { icon: Cpu, color: 'text-green border-green/40 bg-green/10' },
};

const PIXELCADE_URL = 'https://pixelcade.org';
const ZEDMD_URL = 'https://github.com/PPUC/ZeDMD';

export function Pixelcade() {
  const { t } = useI18n();
  const p = t.pixelcade;
  return (
    <section id="pixelcade" aria-labelledby="pixelcade-title" className="relative overflow-hidden py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan/40 to-transparent" />
      <div aria-hidden="true" className="glow-purple pointer-events-none absolute -top-40 -left-40 h-[500px] w-[700px]" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="pixelcade" kicker={p.kicker} title={p.title} intro={p.intro} />

        <Reveal as="figure" className="mt-14">
          <div className="crt-bezel rounded-2xl p-3 sm:p-4">
            <div className="overflow-hidden rounded-lg border border-black/60 bg-black shadow-[inset_0_0_24px_rgba(0,0,0,0.9)]">
              <LedMatrix script={p.marquee} label={p.marqueeLabel} />
            </div>
          </div>
          <figcaption className="mt-4 font-mono text-xs tracking-widest text-comment uppercase">{p.caption}</figcaption>
        </Reveal>

        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {p.points.map((pt, i) => {
            const style = POINT_STYLE[pt.id] ?? POINT_STYLE.install;
            const Icon = style.icon;
            return (
              <Reveal as="li" key={pt.id} delay={i * 60}>
                <article className="card h-full rounded-2xl p-5">
                  <span className={`inline-flex size-10 items-center justify-center rounded-xl border ${style.color}`}>
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-4 font-semibold text-fg">{pt.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{pt.text}</p>
                </article>
              </Reveal>
            );
          })}
        </ul>

        <Reveal className="mt-14">
          <p className="font-mono text-xs tracking-widest text-comment uppercase">{p.sizesLabel}</p>
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            {p.panels.map((panel) => (
              <article key={panel.id} className="card rounded-2xl p-5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-semibold text-fg">{panel.title}</h3>
                  <span className="font-mono text-xs text-cyan">{panel.resolution}</span>
                </div>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{panel.text}</p>
                <ul className="mt-4 flex flex-wrap gap-2">
                  {panel.sizes.map((s) => (
                    <li key={s} className="rounded-md border border-line bg-bg-deeper/70 px-2.5 py-1 font-mono text-xs text-fg">
                      {s}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </Reveal>

        <Reveal className="mt-10 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <p className="max-w-2xl text-xs leading-relaxed text-comment">{p.disclaimer}</p>
          <div className="flex shrink-0 flex-wrap gap-3">
            <a
              href={`${LINKS.docs}/Frontends#pixelcade-marquee`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-cyan/60 bg-cyan/10 px-4 py-2.5 text-sm font-medium text-fg transition hover:border-cyan hover:bg-cyan/20 hover:shadow-[0_0_20px_-6px] hover:shadow-cyan"
            >
              {p.cta}
              <ArrowUpRight className="size-4" aria-hidden="true" />
              <span className="sr-only">{t.a11y.external}</span>
            </a>
            <a
              href={ZEDMD_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2.5 text-sm font-medium text-muted transition hover:border-comment hover:text-fg"
            >
              {p.zedmd}
              <ArrowUpRight className="size-4" aria-hidden="true" />
              <span className="sr-only">{t.a11y.external}</span>
            </a>
            <a
              href={PIXELCADE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2.5 text-sm font-medium text-muted transition hover:border-comment hover:text-fg"
            >
              {p.shop}
              <ArrowUpRight className="size-4" aria-hidden="true" />
              <span className="sr-only">{t.a11y.external}</span>
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
