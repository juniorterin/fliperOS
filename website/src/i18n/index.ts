import enUS, { type Messages } from './en-US';
import ptBR from './pt-BR';

export const LOCALES = ['en-US', 'pt-BR'] as const;
export type Locale = (typeof LOCALES)[number];
export type { Messages };

export const DEFAULT_LOCALE: Locale = 'en-US';
export const STORAGE_KEY = 'fliperos-lang';

export const messages: Record<Locale, Messages> = {
  'en-US': enUS,
  'pt-BR': ptBR,
};

export const LOCALE_SHORT: Record<Locale, string> = {
  'en-US': 'EN',
  'pt-BR': 'PT',
};

export const LOCALE_NAME: Record<Locale, string> = {
  'en-US': 'English',
  'pt-BR': 'Português',
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && (LOCALES as readonly string[]).includes(value);
}

// pt, pt-BR, pt-PT... abrem em português; qualquer outro idioma, em inglês.
export function detectLocale(language: string | undefined | null): Locale {
  return language && language.toLowerCase().startsWith('pt') ? 'pt-BR' : 'en-US';
}
