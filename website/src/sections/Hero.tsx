'use client';

import { ArrowDown, Download } from 'lucide-react';
import Image from 'next/image';
import { CrtMonitor } from '@/components/CrtMonitor';
import { ScreenCarousel } from '@/components/ScreenCarousel';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media } from '@/lib/media';
import { HERO_SHOTS } from '@/lib/site';

// slides: as telas de HERO_SHOTS que têm arquivo em public/screenshots.
export function Hero({ slides, downloadUrl }: { slides: Media[]; downloadUrl: string }) {
  const { t } = useI18n();
  const h = t.hero;
  return (
    <section id="top" aria-labelledby="hero-title" className="relative overflow-hidden pt-28 pb-16 sm:pt-36 lg:pt-20 lg:pb-24">
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0" />
      <div aria-hidden="true" className="glow-purple pointer-events-none absolute -top-40 left-1/2 h-[560px] w-[900px] -translate-x-1/2" />
      <div aria-hidden="true" className="glow-pink pointer-events-none absolute top-40 -right-40 h-[420px] w-[520px]" />

      <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10 lg:px-8">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-bg-deeper/60 px-3 py-1 font-mono text-xs text-muted">
            <span className="size-1.5 rounded-full bg-green shadow-[0_0_8px] shadow-green" aria-hidden="true" />
            {h.eyebrow}
          </p>
          <div className="mt-6 flex items-center gap-4 sm:gap-6">
            {/* Logo em pixel art 240p: no tamanho nativo (xl) os pixels ficam nítidos. */}
            <Image
              src="/fliperos-logo.png"
              alt=""
              width={202}
              height={220}
              unoptimized
              priority
              className="h-auto w-24 shrink-0 sm:w-36 xl:w-[202px] xl:[image-rendering:pixelated]"
            />
            <h1 id="hero-title" className="text-4xl font-bold tracking-tight text-balance sm:text-5xl xl:text-6xl">
              <span className="rgb-split block text-fg">{h.titleLine1}</span>
              <span className="text-gradient block pb-2">{h.titleLine2}</span>
            </h1>
          </div>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-pretty text-muted sm:text-xl">{h.description}</p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <a
              href={downloadUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2.5 rounded-xl bg-purple px-6 py-3.5 font-semibold text-bg-deeper shadow-[0_10px_40px_-10px] shadow-purple transition hover:-translate-y-0.5 hover:bg-[#c9a6fb]"
            >
              <Download className="size-5" aria-hidden="true" />
              {h.ctaDownload}
              <span className="sr-only">{t.a11y.external}</span>
            </a>
            <a
              href="#features"
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-line bg-bg/60 px-6 py-3.5 font-semibold text-fg transition hover:border-cyan/70 hover:text-cyan"
            >
              {h.ctaFeatures}
              <ArrowDown className="size-4" aria-hidden="true" />
            </a>
          </div>
        </div>

        {slides.length ? (
          <ScreenCarousel slides={slides} labels={h.carousel} />
        ) : (
          <figure className="float relative mx-auto w-full max-w-xl">
            <CrtMonitor
              src={null}
              alt={h.titleLine1}
              placeholderTitle={h.screenPlaceholderTitle}
              placeholderHint={h.screenPlaceholderHint}
              expectedPath={`/public/screenshots/${HERO_SHOTS[0]}.webp`}
            />
          </figure>
        )}
      </div>
    </section>
  );
}
