'use client';

import { ChevronRight } from 'lucide-react';
import { localePath } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';
import { CONTACT_EMAIL, LINKS } from '@/lib/site';

// A política de privacidade: o link que a tela de consentimento OAuth do
// Google pede (o "Entrar com o Google" do backup na nuvem, escopo drive.file).
export function Privacy() {
  const { t, locale } = useI18n();
  const p = t.privacy;
  return (
    <section id="top" aria-labelledby="privacy-title" className="relative overflow-hidden pt-28 pb-20 sm:pt-36 lg:pt-20">
      <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0" />
      <div className="relative mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
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
              {p.title}
            </li>
          </ol>
        </nav>
        <p className="mt-8 font-mono text-sm tracking-wide text-green">
          <span aria-hidden="true" className="text-comment">
            ${' '}
          </span>
          {p.kicker.toLowerCase()}
        </p>
        <h1 id="privacy-title" className="mt-3 text-4xl font-bold tracking-tight text-balance sm:text-5xl">
          <span className="text-gradient pb-2">{p.title}</span>
        </h1>
        <p className="mt-4 font-mono text-xs text-comment">{p.updated}</p>
        <p className="mt-6 text-lg leading-relaxed text-pretty text-muted">{p.intro}</p>
        {p.sections.map((s) => (
          <div key={s.title} className="mt-12">
            <h2 className="text-2xl font-semibold tracking-tight text-fg">{s.title}</h2>
            {s.paragraphs.map((text) => (
              <p key={text} className="mt-4 leading-relaxed text-pretty text-muted">
                {text}
              </p>
            ))}
          </div>
        ))}
        <p className="mt-4 font-mono text-fg">
          {CONTACT_EMAIL.user} <strong className="font-bold text-pink">@</strong> {CONTACT_EMAIL.domain}{' '}
          <strong className="font-bold text-green">.</strong> {CONTACT_EMAIL.tld}
        </p>
        <p className="mt-10">
          <a
            href={LINKS.googleUserDataPolicy}
            target="_blank"
            rel="noopener noreferrer"
            className="text-purple underline-offset-4 hover:underline"
          >
            {p.googlePolicy}
            <span className="sr-only">{t.a11y.external}</span>
          </a>
        </p>
      </div>
    </section>
  );
}
