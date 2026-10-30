'use client';

import Image from 'next/image';
import { ArrowUpRight, Cpu, Gauge, HardDrive, MemoryStick, Monitor, Network, Usb, type LucideIcon } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { LINKS } from '@/lib/site';

const ROW_ICON: Record<string, LucideIcon> = {
  cpu: Cpu,
  memory: MemoryStick,
  disk: HardDrive,
  gpu: Gauge,
  monitor: Monitor,
  boot: Usb,
  network: Network,
};

// As duas colunas: o mínimo (cinza) e o ideal (em destaque).
const TIER_STYLE: Record<string, { card: string; badge: string }> = {
  minimum: { card: 'border-line bg-bg/70', badge: 'border-line text-muted' },
  ideal: {
    card: 'border-purple/60 bg-purple/5 shadow-[0_0_40px_-18px] shadow-purple',
    badge: 'border-purple/60 bg-purple/15 text-purple',
  },
};

export function Requirements() {
  const { t } = useI18n();
  const r = t.requirements;
  return (
    <section id="requirements" aria-labelledby="requirements-title" className="relative overflow-hidden py-24 sm:py-32">
      <div aria-hidden="true" className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-green/40 to-transparent" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="requirements" kicker={r.kicker} title={r.title} intro={r.intro} />

        <div className="mt-14 grid gap-6 lg:grid-cols-2">
          {r.tiers.map((tier, i) => {
            const style = TIER_STYLE[tier.id] ?? TIER_STYLE.minimum;
            return (
              <Reveal key={tier.id} delay={i * 80}>
                <div className={`h-full rounded-2xl border p-6 sm:p-8 ${style.card}`}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-2xl font-bold text-fg">{tier.title}</h3>
                    <span className={`rounded-full border px-3 py-1 font-mono text-xs ${style.badge}`}>{tier.badge}</span>
                  </div>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{tier.text}</p>
                  <dl className="mt-6 grid gap-4">
                    {tier.rows.map((row) => {
                      const Icon = ROW_ICON[row.id] ?? Cpu;
                      return (
                        <div key={row.id} className="flex gap-3">
                          <dt className="flex w-28 shrink-0 items-start gap-2 pt-0.5 font-mono text-xs tracking-wide text-comment uppercase">
                            <Icon className="size-4 shrink-0 text-cyan" aria-hidden="true" />
                            {row.label}
                          </dt>
                          <dd className="text-sm leading-relaxed text-fg">{row.value}</dd>
                        </div>
                      );
                    })}
                  </dl>
                </div>
              </Reveal>
            );
          })}
        </div>

        <Reveal className="mt-8">
          <p className="rounded-xl border border-line bg-bg-deeper/60 px-5 py-4 text-sm leading-relaxed text-muted">
            <span className="font-semibold text-fg">{r.testedLabel}</span> {r.tested}
          </p>
          <p className="mt-4 text-sm leading-relaxed text-muted">{r.note}</p>
          <a
            href={`${LINKS.docs}/Latency#recommended-hardware`}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-cyan transition-colors hover:text-fg"
          >
            {r.cta}
            <ArrowUpRight className="size-4" aria-hidden="true" />
            <span className="sr-only">{t.a11y.external}</span>
          </a>
        </Reveal>

        <Reveal className="mt-8">
          <article className="card flex flex-col gap-5 rounded-2xl p-5 sm:flex-row sm:items-center sm:p-6">
            <Image
              src="/art/displayport-vga-adapter.webp"
              alt={r.adapter.alt}
              width={740}
              height={410}
              unoptimized
              className="h-auto w-full shrink-0 rounded-xl bg-white sm:w-72"
            />
            <div>
              <h3 className="font-semibold text-fg">{r.adapter.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{r.adapter.text}</p>
              <a
                href={LINKS.dpVgaAdapter}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-cyan transition-colors hover:text-fg"
              >
                {r.adapter.cta}
                <ArrowUpRight className="size-4" aria-hidden="true" />
              </a>
            </div>
          </article>
        </Reveal>
      </div>
    </section>
  );
}
