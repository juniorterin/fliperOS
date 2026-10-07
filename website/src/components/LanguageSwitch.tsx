'use client';

import { LOCALES, LOCALE_NAME, LOCALE_SHORT } from '@/i18n';
import { useI18n } from '@/i18n/I18nProvider';

export function LanguageSwitch({ className = '' }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();
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
            <button
              type="button"
              lang={code}
              aria-pressed={active}
              aria-label={`${t.a11y.switchTo} ${LOCALE_NAME[code]}`}
              onClick={() => setLocale(code)}
              className={`rounded-md px-2.5 py-1.5 font-semibold tracking-wider transition-colors ${
                active ? 'bg-line text-fg shadow-[0_0_12px_-2px] shadow-purple/50' : 'text-muted hover:text-fg'
              }`}
            >
              {LOCALE_SHORT[code]}
            </button>
          </span>
        );
      })}
    </div>
  );
}
