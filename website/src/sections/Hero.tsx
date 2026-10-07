'use client';

import { ArrowDown } from 'lucide-react';
import { CrtMonitor } from '@/components/CrtMonitor';
import { GithubIcon } from '@/components/GithubIcon';
import { useI18n } from '@/i18n/I18nProvider';
import { HERO_SCREENSHOT, LINKS } from '@/lib/site';

export function Hero({ screenshot }: { screenshot: string | null }) {
  const { t } = useI18n();
  const h = t.hero;
  return (
    <section id="top" aria-labelledby="hero-title" className="relative overflow-hidden pt-28 pb-16 sm:pt-36 lg:pb-24">
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0" />
      <div aria-hidden="true" className="glow-purple pointer-events-none absolute -top-40 left-1/2 h-[560px] w-[900px] -translate-x-1/2" />
      <div aria-hidden="true" className="glow-pink pointer-events-none absolute top-40 -right-40 h-[420px] w-[520px]" />

      <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-4 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-10 lg:px-8">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-bg-deeper/60 px-3 py-1 font-mono text-xs text-muted">
            <span className="size-1.5 rounded-full bg-green shadow-[0_0_8px] shadow-green" aria-hidden="true" />
            {h.eyebrow}
          </p>
          <h1 id="hero-title" className="mt-6 text-5xl font-bold tracking-tight text-balance sm:text-6xl xl:text-7xl">
            <span className="rgb-split block text-fg">{h.titleLine1}</span>
            <span className="text-gradient block pb-2">{h.titleLine2}</span>
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-pretty text-muted sm:text-xl">{h.description}</p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <a
              href={LINKS.github}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2.5 rounded-xl bg-purple px-6 py-3.5 font-semibold text-bg-deeper shadow-[0_10px_40px_-10px] shadow-purple transition hover:-translate-y-0.5 hover:bg-[#c9a6fb]"
            >
              <GithubIcon className="size-5" />
              {h.ctaGithub}
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

        <figure className="float relative mx-auto w-full max-w-xl">
          <CrtMonitor
            src={screenshot}
            alt={h.screenAlt}
            placeholderTitle={h.screenPlaceholderTitle}
            placeholderHint={h.screenPlaceholderHint}
            expectedPath={`/public/screenshots/${HERO_SCREENSHOT}.webp`}
            priority
          />
          <figcaption className="mt-4 text-center font-mono text-xs text-comment">{h.screenCaption}</figcaption>
        </figure>
      </div>
    </section>
  );
}
