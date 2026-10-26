'use client';

import {
  ArrowRight,
  Cpu,
  Download,
  FlaskConical,
  Gift,
  MonitorCog,
  Network,
  PackageX,
  Usb,
  type LucideIcon,
} from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { pagePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';

const ICON: Record<string, { icon: LucideIcon; color: string }> = {
  free: { icon: Gift, color: 'text-green' },
  gpu: { icon: MonitorCog, color: 'text-purple' },
  nogames: { icon: PackageX, color: 'text-orange' },
  nolcd: { icon: Usb, color: 'text-cyan' },
  pc: { icon: Cpu, color: 'text-pink' },
  network: { icon: Network, color: 'text-green' },
  updates: { icon: Download, color: 'text-cyan' },
  status: { icon: FlaskConical, color: 'text-yellow' },
};

// O que convém saber antes de baixar: placa de vídeo, o que vem e o que não vem.
export function KeyFacts() {
  const { t, locale } = useI18n();
  const k = t.keyFacts;
  return (
    <section id="key-facts" aria-labelledby="key-facts-title" className="relative bg-bg-deeper/40 py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="key-facts" kicker={k.kicker} title={k.title} />
        <ul className="mt-12 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-4">
          {k.items.map((item, i) => {
            const { icon: Icon, color } = ICON[item.id] ?? ICON.free;
            return (
              <Reveal as="li" key={item.id} delay={i * 40}>
                <Icon className={`size-6 ${color}`} aria-hidden="true" />
                <h3 className="mt-3 font-semibold text-fg">{item.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted">{item.text}</p>
              </Reveal>
            );
          })}
        </ul>
        <a
          href={pagePath(locale, 'hardware')}
          className="mt-12 inline-flex items-center gap-2 rounded-xl border border-line px-5 py-3 font-semibold text-fg transition hover:border-cyan/70 hover:text-cyan"
        >
          {k.cta}
          <ArrowRight className="size-4" aria-hidden="true" />
        </a>
      </div>
    </section>
  );
}
