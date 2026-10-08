'use client';

import { Menu, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import { readmeUrl, SECTION_IDS, type SectionId } from '@/lib/site';
import { GithubIcon } from './GithubIcon';
import { LanguageSwitch } from './LanguageSwitch';
import { LogoMark, Wordmark } from './Logo';

const NAV: { id: SectionId; key: 'features' | 'screenshots' | 'emulators' | 'crt' | 'multiMonitor' | 'setup' | 'github' }[] = [
  { id: 'features', key: 'features' },
  { id: 'screenshots', key: 'screenshots' },
  { id: 'emulators', key: 'emulators' },
  { id: 'crt', key: 'crt' },
  { id: 'multi-monitor', key: 'multiMonitor' },
  { id: 'setup', key: 'setup' },
  { id: 'open-source', key: 'github' },
];

export function Header() {
  const { t, locale } = useI18n();
  const [active, setActive] = useState<SectionId | null>(null);
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const sections = SECTION_IDS.map((id) => document.getElementById(id)).filter((el): el is HTMLElement => !!el);
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.id as SectionId);
        }
      },
      { rootMargin: '-45% 0px -50% 0px' },
    );
    sections.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  const linkClass = (id: SectionId) =>
    `relative rounded-md px-3 py-2 text-sm transition-colors ${
      active === id ? 'text-fg' : 'text-muted hover:text-fg'
    }`;

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 border-b backdrop-blur-xl transition-colors duration-300 ${
        scrolled || open ? 'border-line/70 bg-bg-deep/80' : 'border-transparent bg-bg-deep/30'
      }`}
    >
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-md focus:bg-purple focus:px-3 focus:py-2 focus:text-bg-deeper"
      >
        {t.a11y.skipToContent}
      </a>
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <a href="#top" className="flex items-center gap-2.5" aria-label="FliperOS">
          <LogoMark />
          <Wordmark />
        </a>

        <nav aria-label={t.a11y.mainNav} className="ml-6 hidden lg:block">
          <ul className="flex items-center gap-1">
            {NAV.map(({ id, key }) => (
              <li key={id}>
                <a href={`#${id}`} className={linkClass(id)} aria-current={active === id ? 'true' : undefined}>
                  {t.nav[key]}
                  <span
                    aria-hidden="true"
                    className={`absolute inset-x-3 -bottom-px h-px bg-gradient-to-r from-purple to-pink transition-opacity ${
                      active === id ? 'opacity-100' : 'opacity-0'
                    }`}
                  />
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <LanguageSwitch />
          <a
            href={readmeUrl(locale)}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden items-center gap-2 rounded-lg border border-purple/60 bg-purple/10 px-3.5 py-2 text-sm font-medium text-fg transition hover:border-purple hover:bg-purple/20 hover:shadow-[0_0_20px_-6px] hover:shadow-purple sm:inline-flex"
          >
            <GithubIcon className="size-4" />
            {t.nav.viewOnGithub}
            <span className="sr-only">{t.a11y.external}</span>
          </a>
          <button
            type="button"
            className="inline-flex size-10 items-center justify-center rounded-lg border border-line text-fg lg:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? t.a11y.closeMenu : t.a11y.openMenu}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="size-5" aria-hidden="true" /> : <Menu className="size-5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      <nav
        id="mobile-nav"
        aria-label={t.a11y.mainNav}
        hidden={!open}
        className="border-t border-line/70 bg-bg-deep/95 px-4 pt-2 pb-5 lg:hidden"
      >
        <ul className="grid gap-1">
          {NAV.map(({ id, key }) => (
            <li key={id}>
              <a
                href={`#${id}`}
                onClick={() => setOpen(false)}
                aria-current={active === id ? 'true' : undefined}
                className={`flex items-center justify-between rounded-lg px-3 py-3 text-base ${
                  active === id ? 'bg-line/50 text-fg' : 'text-muted'
                }`}
              >
                {t.nav[key]}
                <span aria-hidden="true" className="font-mono text-xs text-comment">
                  #{id}
                </span>
              </a>
            </li>
          ))}
        </ul>
        <a
          href={readmeUrl(locale)}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 flex items-center justify-center gap-2 rounded-lg bg-purple px-4 py-3 font-medium text-bg-deeper"
        >
          <GithubIcon className="size-4" />
          {t.nav.viewOnGithub}
          <span className="sr-only">{t.a11y.external}</span>
        </a>
      </nav>
    </header>
  );
}
