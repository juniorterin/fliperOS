'use client';

import { BookOpen, CircleDot, Package } from 'lucide-react';
import { GithubIcon } from '@/components/GithubIcon';
import { LogoMark, Wordmark } from '@/components/Logo';
import { useI18n } from '@/i18n/I18nProvider';
import { AUTHOR_HANDLE, LINKS, readmeUrl } from '@/lib/site';

export function Footer() {
  const { t, locale } = useI18n();
  const f = t.footer;
  const links = [
    { href: readmeUrl(locale), label: f.github, icon: <GithubIcon className="size-4" /> },
    { href: LINKS.docs, label: f.docs, icon: <BookOpen className="size-4" aria-hidden="true" /> },
    { href: LINKS.releases, label: f.releases, icon: <Package className="size-4" aria-hidden="true" /> },
    { href: LINKS.issues, label: f.issues, icon: <CircleDot className="size-4" aria-hidden="true" /> },
  ];
  return (
    <footer className="border-t border-line/70 bg-bg-deeper">
      <div className="mx-auto flex max-w-7xl flex-col gap-10 px-4 py-14 sm:px-6 md:flex-row md:items-start md:justify-between lg:px-8">
        <div className="max-w-sm">
          <div className="flex items-center gap-2.5">
            <LogoMark />
            <Wordmark />
          </div>
          <p className="mt-3 text-muted">{f.tagline}</p>
        </div>
        <nav aria-label={f.linksLabel}>
          <ul className="grid grid-cols-2 gap-x-10 gap-y-3 sm:flex sm:gap-6">
            {links.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-muted transition-colors hover:text-purple"
                >
                  {link.icon}
                  {link.label}
                  <span className="sr-only">{t.a11y.external}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="border-t border-line/50">
        <div className="mx-auto flex max-w-7xl flex-col items-center gap-3 px-4 py-6 font-mono text-xs leading-relaxed text-comment sm:px-6 md:flex-row md:justify-between lg:px-8">
          <p className="text-center md:text-left">{f.disclaimer}</p>
          <p className="shrink-0">
            {f.madeBy}{' '}
            <a
              href={LINKS.instagram}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-pink underline-offset-4 transition-colors hover:text-purple hover:underline"
            >
              {AUTHOR_HANDLE}
              <span className="sr-only"> {f.instagramLabel}</span>
            </a>
          </p>
        </div>
      </div>
    </footer>
  );
}
