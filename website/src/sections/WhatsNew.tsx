'use client';

import { ArrowRight } from 'lucide-react';
import { Reveal } from '@/components/Reveal';
import { SectionHeading } from '@/components/SectionHeading';
import { useI18n } from '@/i18n/I18nProvider';
import { FLIPEROS_VERSION, LINKS, RELEASES, releaseUrl } from '@/lib/site';

// As últimas versões numa linha do tempo, cada uma com o que ela trouxe e o
// link para a nota do release no GitHub.
export function WhatsNew() {
  const { t, locale } = useI18n();
  const w = t.whatsNew;
  const date = new Intl.DateTimeFormat(locale, { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  return (
    <section id="whats-new" aria-labelledby="whats-new-title" className="relative py-16 sm:py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <SectionHeading id="whats-new" kicker={w.kicker} title={w.title} />
        <ol className="relative mt-14 grid gap-4 lg:grid-cols-4 lg:gap-5 lg:pt-7">
          <span aria-hidden="true" className="absolute top-2 right-0 left-0 hidden h-0.5 bg-gradient-to-r from-purple via-pink to-line lg:block" />
          {RELEASES.map(({ version, date: day }, i) => {
            const current = version === FLIPEROS_VERSION;
            return (
              <Reveal as="li" key={version} delay={i * 70}>
                <a href={releaseUrl(version)} target="_blank" rel="noopener noreferrer" className="card relative block h-full rounded-2xl p-5">
                  <span
                    aria-hidden="true"
                    className={`absolute -top-7 left-5 hidden size-3.5 rounded-full border-[3px] lg:block ${current ? 'border-green bg-green shadow-[0_0_12px] shadow-green' : 'border-purple bg-bg-deep'}`}
                  />
                  <span className="flex items-baseline gap-2">
                    <span className="font-mono text-2xl font-bold text-fg">{version}</span>
                    {current ? <span className="rounded-md bg-green px-1.5 py-0.5 font-mono text-[10px] font-bold text-bg-deeper uppercase">{w.current}</span> : null}
                  </span>
                  <span className="block font-mono text-xs text-comment">{date.format(new Date(day))}</span>
                  <ul className="mt-3 grid list-disc gap-1.5 pl-5 text-sm text-muted marker:text-comment">
                    {w.notes[version].map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                  <span className="sr-only">{t.a11y.external}</span>
                </a>
              </Reveal>
            );
          })}
        </ol>
        <a
          href={LINKS.releases}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-6 inline-flex items-center gap-1.5 font-mono text-sm text-cyan transition-colors hover:text-fg"
        >
          {w.all}
          <ArrowRight className="size-4" aria-hidden="true" />
          <span className="sr-only">{t.a11y.external}</span>
        </a>
      </div>
    </section>
  );
}
