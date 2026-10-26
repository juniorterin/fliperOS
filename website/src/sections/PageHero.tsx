'use client';

import { ChevronRight, Download } from 'lucide-react';
import { localePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import type { PageSlug } from '@/lib/site';

// O topo de uma página de detalhe: o caminho desde a home, o título e o download.
export function PageHero({ page, downloadUrl }: { page: PageSlug; downloadUrl: string }) {
  const { t, locale } = useI18n();
  const p = t.pages[page];
  return (
    <section id="top" aria-labelledby="page-title" className="relative overflow-hidden pt-28 pb-12 sm:pt-36 lg:pt-20 lg:pb-16">
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0" />
      <div aria-hidden="true" className="glow-purple pointer-events-none absolute -top-40 left-1/3 h-[420px] w-[720px] -translate-x-1/2" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <nav aria-label={t.pageUi.breadcrumb}>
          <ol className="flex items-center gap-1.5 font-mono text-xs text-comment">
            <li>
              <a href={localePath(locale)} className="transition-colors hover:text-fg">
                {t.nav.home}
              </a>
            </li>
            <li aria-hidden="true">
              <ChevronRight className="size-3.5" />
            </li>
            <li aria-current="page" className="text-muted">
              {t.nav.pages[page]}
            </li>
          </ol>
        </nav>
        <p className="mt-8 font-mono text-sm tracking-wide text-green">
          <span aria-hidden="true" className="text-comment">
            ${' '}
          </span>
          {p.kicker.toLowerCase()}
        </p>
        <h1 id="page-title" className="mt-3 max-w-4xl text-4xl font-bold tracking-tight text-balance sm:text-5xl xl:text-6xl">
          <span className="text-gradient pb-2">{p.title}</span>
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-pretty text-muted sm:text-xl">{p.intro}</p>
        <a
          href={downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-9 inline-flex items-center justify-center gap-2.5 rounded-xl bg-purple px-6 py-3.5 font-semibold text-bg-deeper shadow-[0_10px_40px_-10px] shadow-purple transition hover:-translate-y-0.5 hover:bg-[#c9a6fb]"
        >
          <Download className="size-5" aria-hidden="true" />
          {t.hero.ctaDownload}
          <span className="sr-only">{t.a11y.external}</span>
        </a>
      </div>
    </section>
  );
}
