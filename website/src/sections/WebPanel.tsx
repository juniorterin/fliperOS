'use client';

import Image from 'next/image';
import {
  Activity,
  ArrowUpRight,
  FolderOpen,
  Gamepad2,
  Radio,
  SlidersHorizontal,
  SquareTerminal,
  Video,
  Wand2,
  type LucideIcon,
} from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { LINKS } from '@/lib/site';

const POINT_STYLE: Record<string, { icon: LucideIcon; color: string }> = {
  play: { icon: Gamepad2, color: 'text-pink border-pink/40 bg-pink/10' },
  live: { icon: Video, color: 'text-cyan border-cyan/40 bg-cyan/10' },
  obs: { icon: Radio, color: 'text-purple border-purple/40 bg-purple/10' },
  settings: { icon: SlidersHorizontal, color: 'text-orange border-orange/40 bg-orange/10' },
  files: { icon: FolderOpen, color: 'text-green border-green/40 bg-green/10' },
  romfilter: { icon: Wand2, color: 'text-yellow border-yellow/40 bg-yellow/10' },
  status: { icon: Activity, color: 'text-cyan border-cyan/40 bg-cyan/10' },
  terminal: { icon: SquareTerminal, color: 'text-pink border-pink/40 bg-pink/10' },
};

// A janela de navegador desenhada em volta do print do painel.
function BrowserFrame({ src, alt, url }: { src: string; alt: string; url: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-bg-deep shadow-2xl shadow-black/40">
      <div className="flex items-center gap-2 border-b border-line px-3 py-2">
        <span aria-hidden="true" className="size-2.5 rounded-full bg-red/70" />
        <span aria-hidden="true" className="size-2.5 rounded-full bg-yellow/70" />
        <span aria-hidden="true" className="size-2.5 rounded-full bg-green/70" />
        <span className="ml-2 truncate rounded-md bg-black/30 px-2 py-0.5 font-mono text-xs text-muted">{url}</span>
      </div>
      <Image src={src} alt={alt} width={1280} height={800} unoptimized className="block h-auto w-full" />
    </div>
  );
}

export function WebPanel() {
  const { t, locale } = useI18n();
  const w = t.webPanel;
  const lang = locale.startsWith('pt') ? 'pt' : 'en';
  return (
    <section id="web-panel" aria-labelledby="web-panel-title" className="relative overflow-hidden py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-pink/40 to-transparent" />
      <div aria-hidden="true" className="glow-purple pointer-events-none absolute -top-40 -right-40 h-[500px] w-[700px]" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="web-panel" kicker={w.kicker} title={w.title} intro={w.intro} />

        <Reveal className="mt-6">
          <p className="inline-flex flex-wrap items-center gap-2 rounded-xl border border-pink/40 bg-pink/10 px-4 py-2 font-mono text-sm text-fg">
            <span className="text-comment">{w.addressLabel}</span>
            <span className="font-semibold text-pink">http://fliperos.local</span>
          </p>
        </Reveal>

        <Reveal as="figure" className="relative mt-14">
          <div className="grid items-end gap-6 lg:grid-cols-[minmax(0,1fr)_240px]">
            <BrowserFrame src={`/screenshots/web/frontend-${lang}.webp`} alt={w.shots.frontend} url="fliperos.local/#frontend" />
            <div className="mx-auto w-[220px] overflow-hidden rounded-[2rem] border-[6px] border-line bg-black shadow-2xl shadow-black/50 lg:w-full">
              <Image
                src={`/screenshots/web/phone-${lang}.webp`}
                alt={w.shots.phone}
                width={780}
                height={1688}
                unoptimized
                className="block h-auto w-full"
              />
            </div>
          </div>
          <figcaption className="mt-4 font-mono text-xs tracking-widest text-comment uppercase">{w.caption}</figcaption>
        </Reveal>

        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {w.points.map((pt, i) => {
            const style = POINT_STYLE[pt.id] ?? POINT_STYLE.play;
            const Icon = style.icon;
            return (
              <Reveal as="li" key={pt.id} delay={i * 50}>
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

        <Reveal className="mt-10">
          <BrowserFrame src={`/screenshots/web/status-${lang}.webp`} alt={w.shots.status} url="fliperos.local/#status" />
        </Reveal>

        <Reveal className="mt-8">
          <a
            href={`${LINKS.docs}/Web-panel`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm font-medium text-pink transition hover:text-fg"
          >
            {w.cta}
            <ArrowUpRight className="size-4" aria-hidden="true" />
            <span className="sr-only">{t.a11y.external}</span>
          </a>
        </Reveal>
      </div>
    </section>
  );
}
