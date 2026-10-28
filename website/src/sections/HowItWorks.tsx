'use client';

import { ArrowRight } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { TubeShot } from '@/components/TubeShot';
import { pagePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media } from '@/lib/media';
import type { PageSlug } from '@/lib/site';

// Do pendrive ao jogo em quatro passos, cada um com a tela e o caminho para a
// página que o conta em detalhe.
export function HowItWorks({ steps }: { steps: { page: PageSlug; media?: Media }[] }) {
  const { t, locale } = useI18n();
  const h = t.howItWorks;
  return (
    <section id="how-it-works" aria-labelledby="how-it-works-title" className="relative py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="how-it-works" kicker={h.kicker} title={h.title} intro={h.intro} />
        <ol className="mt-14 grid gap-8 sm:grid-cols-2 xl:grid-cols-4 xl:gap-6">
          {steps.map(({ page, media }, i) => (
            <Reveal as="li" key={page} delay={i * 80}>
              <a href={pagePath(locale, page)} className="group relative block">
                <span
                  aria-hidden="true"
                  className="absolute -top-3 -left-2 z-10 grid size-9 place-items-center rounded-full bg-purple font-mono text-sm font-bold text-bg-deeper shadow-[0_6px_20px_-6px] shadow-purple"
                >
                  {i + 1}
                </span>
                {media ? <TubeShot media={media} sizes="(min-width: 1280px) 280px, (min-width: 640px) 45vw, 92vw" className="transition group-hover:-translate-y-0.5" /> : null}
                <span className="mt-4 block text-lg font-semibold text-fg">{h.steps[i].title}</span>
                <span className="mt-1 block text-sm leading-relaxed text-muted">{h.steps[i].text}</span>
                <span className="mt-2 inline-flex items-center gap-1.5 font-mono text-sm text-cyan transition-colors group-hover:text-fg">
                  {t.nav.pages[page]}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </span>
              </a>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}
