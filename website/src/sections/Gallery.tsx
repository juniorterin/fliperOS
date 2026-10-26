'use client';

import { ArrowRight } from 'lucide-react';
import { MediaGrid } from '@/components/MediaGrid';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { pagePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media } from '@/lib/media';
import type { PageSlug } from '@/lib/site';

// A home mostra antes de contar: um grupo de telas por página, cada um com o
// caminho para a página dele.
export function Gallery({ groups }: { groups: { page: PageSlug; items: Media[] }[] }) {
  const { t, locale } = useI18n();
  const g = t.gallery;
  return (
    <section id="screenshots" aria-labelledby="screenshots-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="screenshots" kicker={g.kicker} title={g.title} intro={g.intro} />
        <div className="mt-14 grid gap-16">
          {groups.map(({ page, items }) => (
            <Reveal key={page}>
              <div className="mb-5 flex items-end justify-between gap-4 border-b border-line/60 pb-3">
                <h3 className="text-xl font-semibold text-fg sm:text-2xl">{g.groups[page]}</h3>
                <a
                  href={pagePath(locale, page)}
                  className="inline-flex shrink-0 items-center gap-1.5 font-mono text-sm text-cyan transition-colors hover:text-fg"
                >
                  {g.seeMore}
                  <ArrowRight className="size-4" aria-hidden="true" />
                </a>
              </div>
              <MediaGrid items={items} className={items.length === 3 ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-2 lg:grid-cols-4'} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
