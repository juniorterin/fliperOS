'use client';

import { LOCALES, LOCALE_COOKIE, LOCALE_NAME, LOCALE_SHORT, localePath, type Locale } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';

// Grava a escolha para a raiz (/) abrir neste idioma nas próximas visitas.
function remember(locale: Locale) {
  document.cookie = `${LOCALE_COOKIE}=${locale}; path=/; max-age=31536000; samesite=lax`;
}

export function LanguageSwitch({ className = '' }: { className?: string }) {
  const { locale, t } = useI18n();
  return (
    <div
      role="group"
      aria-label={t.a11y.language}
      className={`inline-flex items-center rounded-lg border border-line bg-bg-deeper/70 p-0.5 font-mono text-xs ${className}`}
    >
      {LOCALES.map((code, i) => {
        const active = code === locale;
        return (
          <span key={code} className="flex items-center">
            {i > 0 ? (
              <span aria-hidden="true" className="px-0.5 text-comment">
                |
              </span>
            ) : null}
            <a
              href={localePath(code)}
              hrefLang={code}
              lang={code}
              aria-current={active ? 'page' : undefined}
              aria-label={`${t.a11y.switchTo} ${LOCALE_NAME[code]}`}
              onClick={(e) => {
                remember(code);
                if (active) e.preventDefault();
                else if (window.location.hash) {
                  e.preventDefault();
                  window.location.assign(localePath(code) + window.location.hash);
                }
              }}
              className={`rounded-md px-2.5 py-1.5 font-semibold tracking-wider transition-colors ${
                active ? 'bg-line text-fg shadow-[0_0_12px_-2px] shadow-purple/50' : 'text-muted hover:text-fg'
              }`}
            >
              {LOCALE_SHORT[code]}
            </a>
          </span>
        );
      })}
    </div>
  );
}
