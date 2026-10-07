'use client';

import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { messages, type Locale, type Messages } from './index';

type I18nValue = {
  locale: Locale;
  t: Messages;
};

const I18nContext = createContext<I18nValue | null>(null);

// O idioma vem da URL (/en, /pt), resolvido no servidor: o HTML já sai traduzido.
export function I18nProvider({ locale, children }: { locale: Locale; children: ReactNode }) {
  const value = useMemo(() => ({ locale, t: messages[locale] }), [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (!value) throw new Error('useI18n outside I18nProvider');
  return value;
}
