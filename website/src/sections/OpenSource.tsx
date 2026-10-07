'use client';

import { GitBranch, GitFork, Star, Tag } from 'lucide-react';
import { GithubIcon } from '@/components/GithubIcon';
import { Reveal } from '@/components/Reveal';
import { useI18n } from '@/i18n/I18nProvider';
import type { RepoStats } from '@/lib/github';
import { LINKS } from '@/lib/site';

export function OpenSource({ stats }: { stats: RepoStats | null }) {
  const { t, locale } = useI18n();
  const o = t.openSource;
  const fmt = new Intl.NumberFormat(locale);
  return (
    <section id="open-source" aria-labelledby="open-source-title" className="relative py-24 sm:py-32">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <Reveal>
          <div className="relative overflow-hidden rounded-3xl border border-purple/40 bg-gradient-to-br from-bg via-bg-deep to-bg-deeper px-6 py-14 text-center sm:px-12 sm:py-20">
            <div aria-hidden="true" className="bg-grid pointer-events-none absolute inset-0 opacity-70" />
            <div aria-hidden="true" className="glow-purple pointer-events-none absolute -top-32 left-1/2 h-80 w-[640px] -translate-x-1/2" />
            <div className="relative">
              <span className="inline-flex size-14 items-center justify-center rounded-2xl border border-green/40 bg-green/10 text-green">
                <GitBranch className="size-7" aria-hidden="true" />
              </span>
              <p className="mt-6 font-mono text-sm text-green">
                <span aria-hidden="true" className="text-comment">
                  ${' '}
                </span>
                {o.kicker.toLowerCase()}
              </p>
              <h2 id="open-source-title" className="mt-3 text-4xl font-bold tracking-tight text-fg sm:text-5xl">
                {o.title}
              </h2>
              <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-pretty text-muted">{o.text}</p>

              <a
                href={LINKS.github}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-10 inline-flex items-center gap-3 rounded-2xl bg-purple px-7 py-4 text-lg font-semibold text-bg-deeper shadow-[0_14px_50px_-12px] shadow-purple transition hover:-translate-y-0.5 hover:bg-[#c9a6fb] sm:px-9 sm:py-5"
              >
                <GithubIcon className="size-6" />
                {o.cta}
                <span className="sr-only">{t.a11y.external}</span>
              </a>

              {stats ? (
                <dl className="mx-auto mt-10 flex max-w-xl flex-wrap justify-center gap-3 font-mono text-sm">
                  <div className="flex items-center gap-2 rounded-lg border border-line bg-bg-deeper/70 px-4 py-2">
                    <Star className="size-4 text-yellow" aria-hidden="true" />
                    <dt className="text-muted">{o.stars}</dt>
                    <dd className="font-semibold text-fg">{fmt.format(stats.stars)}</dd>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg border border-line bg-bg-deeper/70 px-4 py-2">
                    <GitFork className="size-4 text-cyan" aria-hidden="true" />
                    <dt className="text-muted">{o.forks}</dt>
                    <dd className="font-semibold text-fg">{fmt.format(stats.forks)}</dd>
                  </div>
                  <div className="flex items-center gap-2 rounded-lg border border-line bg-bg-deeper/70 px-4 py-2">
                    <Tag className="size-4 text-pink" aria-hidden="true" />
                    <dt className="text-muted">{o.release}</dt>
                    <dd className="font-semibold text-fg">
                      {stats.release ? (
                        <a href={stats.release.url} target="_blank" rel="noopener noreferrer" className="underline-offset-4 hover:underline">
                          {stats.release.tag}
                        </a>
                      ) : (
                        o.noRelease
                      )}
                    </dd>
                  </div>
                </dl>
              ) : null}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
