'use client';

import { Cookie } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useI18n } from '@/i18n/I18nProvider';
import { CONSENT_KEY, setConsent } from '@/lib/analytics';

export function CookieNotice() {
  const { t } = useI18n();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = window.localStorage.getItem(CONSENT_KEY);
    } catch {
      // localStorage bloqueado: o aviso aparece, e a escolha vale só nesta visita.
    }
    if (stored !== 'granted' && stored !== 'denied') setVisible(true);
  }, []);

  if (!visible) return null;

  const choose = (granted: boolean) => {
    setConsent(granted);
    setVisible(false);
  };

  return (
    <div
      role="region"
      aria-label={t.cookies.label}
      className="fixed inset-x-0 bottom-3 z-50 flex justify-center px-3"
    >
      <div className="flex max-w-xl flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border border-line/70 bg-bg-deeper/90 px-4 py-2.5 font-mono text-xs text-muted shadow-lg shadow-black/30 backdrop-blur">
        <p className="flex min-w-0 flex-1 items-center gap-2">
          <Cookie className="size-3.5 shrink-0 text-comment" aria-hidden="true" />
          <span>{t.cookies.text}</span>
        </p>
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            type="button"
            data-ga="cookie_decline"
            onClick={() => choose(false)}
            className="rounded-md px-2.5 py-1 text-muted transition-colors hover:text-fg"
          >
            {t.cookies.decline}
          </button>
          <button
            type="button"
            data-ga="cookie_accept"
            onClick={() => choose(true)}
            className="rounded-md bg-line px-2.5 py-1 font-semibold text-fg transition-colors hover:bg-purple/30"
          >
            {t.cookies.accept}
          </button>
        </div>
      </div>
    </div>
  );
}
