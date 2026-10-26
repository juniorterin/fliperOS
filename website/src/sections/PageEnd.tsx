'use client';

import { ArrowLeft, ArrowRight, BookOpen } from 'lucide-react';
import { MediaGrid } from '@/components/MediaGrid';
import { SectionHeading } from '@/components/SectionHeading';
import { localePath, pagePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import type { Media } from '@/lib/media';
import { LINKS, PAGE_SLUGS, PAGE_WIKI, type PageSlug } from '@/lib/site';

// O fim de uma página de detalhe: todas as telas dela, a wiki e a próxima página.
export function PageEnd({ page, screens }: { page: PageSlug; screens: Media[] }) {
  const { t, locale } = useI18n();
  const next = PAGE_SLUGS[PAGE_SLUGS.indexOf(page) + 1];
  return (
    <>
      {screens.length ? (
        <section id="all-screens" aria-labelledby="all-screens-title" className="relative py-20 sm:py-28">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <SectionHeading id="all-screens" kicker={t.nav.pages[page]} title={t.pageUi.allScreens} />
            <div className="mt-10">
              <MediaGrid items={screens} className="grid-cols-2 md:grid-cols-3 lg:grid-cols-4" />
            </div>
          </div>
        </section>
      ) : null}
      <section aria-label={t.pageUi.next} className="border-t border-line/60 py-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <a
            href={`${LINKS.docs}/${PAGE_WIKI[page]}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-cyan transition-colors hover:text-fg"
          >
            <BookOpen className="size-4" aria-hidden="true" />
            {t.pageUi.docs}
            <span className="sr-only">{t.a11y.external}</span>
          </a>
          {next ? (
            <a
              href={pagePath(locale, next)}
              className="card inline-flex items-center gap-3 rounded-xl px-5 py-3 font-semibold text-fg"
            >
              <span className="font-mono text-xs font-normal text-comment uppercase">{t.pageUi.next}</span>
              {t.nav.pages[next]}
              <ArrowRight className="size-4" aria-hidden="true" />
            </a>
          ) : (
            <a href={localePath(locale)} className="card inline-flex items-center gap-3 rounded-xl px-5 py-3 font-semibold text-fg">
              <ArrowLeft className="size-4" aria-hidden="true" />
              {t.pageUi.backHome}
            </a>
          )}
        </div>
      </section>
    </>
  );
}
