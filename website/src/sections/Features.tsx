'use client';

import {
  ArrowRight,
  Columns3,
  Crosshair,
  Download,
  Gauge,
  Globe,
  Joystick,
  LayoutGrid,
  Monitor,
  Network,
  RefreshCw,
  ScanLine,
  SlidersHorizontal,
  Smartphone,
  type LucideIcon,
} from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { pagePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import type { PageSlug } from '@/lib/site';

// Cada card leva à página que conta o recurso em detalhe.
const STYLE: Record<string, { icon: LucideIcon; color: string; page: PageSlug }> = {
  crt: { icon: Monitor, color: 'text-purple bg-purple/10 border-purple/30', page: 'video' },
  switchres: { icon: ScanLine, color: 'text-cyan bg-cyan/10 border-cyan/30', page: 'video' },
  frontend: { icon: LayoutGrid, color: 'text-pink bg-pink/10 border-pink/30', page: 'frontend' },
  setup: { icon: SlidersHorizontal, color: 'text-orange bg-orange/10 border-orange/30', page: 'setup' },
  downloads: { icon: Download, color: 'text-green bg-green/10 border-green/30', page: 'games' },
  webpanel: { icon: Globe, color: 'text-cyan bg-cyan/10 border-cyan/30', page: 'web-panel' },
  latency: { icon: Gauge, color: 'text-yellow bg-yellow/10 border-yellow/30', page: 'video' },
  multimonitor: { icon: Columns3, color: 'text-purple bg-purple/10 border-purple/30', page: 'video' },
  lightgun: { icon: Crosshair, color: 'text-red bg-red/10 border-red/30', page: 'setup' },
  network: { icon: Network, color: 'text-green bg-green/10 border-green/30', page: 'games' },
  vertical: { icon: Smartphone, color: 'text-pink bg-pink/10 border-pink/30', page: 'video' },
  updates: { icon: RefreshCw, color: 'text-orange bg-orange/10 border-orange/30', page: 'emulators' },
  arcade: { icon: Joystick, color: 'text-pink bg-pink/10 border-pink/30', page: 'setup' },
};

export function Features() {
  const { t, locale } = useI18n();
  const f = t.features;
  return (
    <section id="features" aria-labelledby="features-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="features" kicker={f.kicker} title={f.title} intro={f.intro} />
        <ul className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-5">
          {f.items.map((item, i) => {
            const style = STYLE[item.id] ?? STYLE.crt;
            const Icon = style.icon;
            return (
              <Reveal as="li" key={item.id} delay={i * 40}>
                <a href={pagePath(locale, style.page)} className="card group flex h-full items-start gap-4 rounded-2xl p-5 sm:p-6">
                  <span className={`inline-flex size-10 shrink-0 items-center justify-center rounded-xl border ${style.color}`}>
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-semibold text-fg">{item.title}</span>
                    <span className="mt-1.5 block text-sm leading-relaxed text-muted">{item.text}</span>
                  </span>
                  <ArrowRight
                    className="mt-1 size-4 shrink-0 text-comment transition group-hover:translate-x-0.5 group-hover:text-cyan"
                    aria-hidden="true"
                  />
                </a>
              </Reveal>
            );
          })}
        </ul>
      </div>
    </section>
  );
}
