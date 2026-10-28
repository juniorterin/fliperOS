'use client';

import { ArrowRight, Coins, Columns3, Crosshair, Radio, Smartphone, type LucideIcon } from 'lucide-react';
import Image from 'next/image';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { TubeShot } from '@/components/TubeShot';
import { pagePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media } from '@/lib/media';
import type { HighlightId, PageSlug } from '@/lib/site';

export type Highlight = { id: HighlightId; page: PageSlug; since?: string; media?: Media; extra?: Media };

// Sem tela para o tile, um ícone grande no lugar.
const ICON: Record<HighlightId, LucideIcon> = {
  web: Smartphone,
  multi: Columns3,
  gun: Crosshair,
  live: Radio,
  coin: Coins,
};

// Os dois quartos em pixel art do tile de várias telas (tools/site-art).
const ART = ['/art/arcade-2-screens.png', '/art/arcade-3-screens.png'] as const;

function Visual({ item }: { item: Highlight }) {
  const { t } = useI18n();
  const Icon = ICON[item.id];
  if (item.id === 'multi') {
    const a = t.multiMonitor.art;
    return (
      <span className="grid grid-cols-2 gap-1">
        {ART.map((src, i) => (
          <Image key={src} src={src} alt={i ? a.threeAlt : a.twoAlt} width={208} height={218} unoptimized className="h-auto w-full [image-rendering:pixelated]" />
        ))}
      </span>
    );
  }
  if (!item.media) {
    return (
      <span className="grid aspect-[4/3] w-full place-items-center rounded-xl border border-dashed border-line bg-bg-deeper/60">
        <Icon className="size-10 text-comment" aria-hidden="true" />
      </span>
    );
  }
  return <TubeShot media={item.media} sizes="(min-width: 1024px) 360px, 92vw" />;
}

// Os destaques numa grade de tiles de tamanhos diferentes: o painel web é o
// maior; cada tile leva à página do assunto.
export function Highlights({ items }: { items: Highlight[] }) {
  const { t, locale } = useI18n();
  const h = t.highlights;
  const web = items.find((i) => i.id === 'web');
  const rest = items.filter((i) => i.id !== 'web');
  const span: Record<string, string> = { multi: 'md:col-span-2', gun: 'md:col-span-2', live: 'md:col-span-3', coin: 'md:col-span-3' };
  return (
    <section id="highlights" aria-labelledby="highlights-title" className="relative py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="highlights" kicker={h.kicker} title={h.title} />
        <div className="mt-14 grid gap-4 md:grid-cols-6">
          {web ? (
            <Reveal className="md:col-span-4 md:row-span-2">
              <a href={pagePath(locale, web.page)} className="card group flex h-full flex-col gap-6 rounded-2xl p-5 sm:p-6 lg:flex-row lg:items-center">
                {web.media ? (
                  <span className="mx-auto block w-40 shrink-0 overflow-hidden rounded-[22px] border-[3px] border-line bg-black shadow-[0_20px_50px_-20px] shadow-black">
                    <Image src={web.media.src} alt={web.media.alt} width={780} height={1688} unoptimized className="h-auto w-full" />
                  </span>
                ) : null}
                <span className="flex min-w-0 flex-1 flex-col gap-3">
                  <span className="text-2xl font-semibold text-fg">{h.items.web.title}</span>
                  <span className="text-muted">{h.items.web.text}</span>
                  {web.extra ? (
                    <span className="block overflow-hidden rounded-lg border border-line">
                      <Image src={web.extra.src} alt={web.extra.alt} width={1280} height={800} unoptimized className="h-auto w-full" />
                    </span>
                  ) : null}
                  <span className="inline-flex items-center gap-1.5 font-mono text-sm text-cyan transition-colors group-hover:text-fg">
                    {t.nav.pages[web.page]}
                    <ArrowRight className="size-4" aria-hidden="true" />
                  </span>
                </span>
              </a>
            </Reveal>
          ) : null}
          {rest.map((item, i) => (
            <Reveal key={item.id} delay={i * 60} className={span[item.id]}>
              <a href={pagePath(locale, item.page)} className="card group relative flex h-full flex-col gap-4 rounded-2xl p-5 sm:p-6">
                {item.since ? (
                  <span className="absolute top-4 right-4 z-10 rounded-md bg-pink px-2 py-0.5 font-mono text-[10px] font-bold tracking-wider text-bg-deeper uppercase">
                    {h.newIn} {item.since}
                  </span>
                ) : null}
                <Visual item={item} />
                <span className="text-xl font-semibold text-fg">{h.items[item.id].title}</span>
                <span className="text-sm leading-relaxed text-muted">{h.items[item.id].text}</span>
                <span className="mt-auto inline-flex items-center gap-1.5 font-mono text-sm text-cyan transition-colors group-hover:text-fg">
                  {t.nav.pages[item.page]}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </span>
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
