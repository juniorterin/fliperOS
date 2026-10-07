import enUS, { type Messages } from './en-US';
import ptBR from './pt-BR';

export const LOCALES = ['en-US', 'pt-BR'] as const;
export type Locale = (typeof LOCALES)[number];
export type { Messages };

export const DEFAULT_LOCALE: Locale = 'en-US';
// Cookie lido pelo proxy na raiz: a escolha do seletor PT|EN vence o Accept-Language.
export const LOCALE_COOKIE = 'fliperos-lang';

export const messages: Record<Locale, Messages> = {
  'en-US': enUS,
  'pt-BR': ptBR,
};

// Segmento da URL de cada idioma: /en e /pt.
export const LOCALE_SEGMENT: Record<Locale, string> = {
  'en-US': 'en',
  'pt-BR': 'pt',
};

export const OG_LOCALE: Record<Locale, string> = {
  'en-US': 'en_US',
  'pt-BR': 'pt_BR',
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

export function localeFromSegment(segment: string): Locale | null {
  return LOCALES.find((l) => LOCALE_SEGMENT[l] === segment) ?? null;
}

export function localePath(locale: Locale): string {
  return `/${LOCALE_SEGMENT[locale]}`;
}

// pt, pt-BR, pt-PT... abrem em português; qualquer outro idioma, em inglês.
export function detectLocale(language: string | undefined | null): Locale {
  return language && language.toLowerCase().startsWith('pt') ? 'pt-BR' : 'en-US';
}

// Accept-Language em ordem de preferência ("pt-BR,pt;q=0.9,en;q=0.8"):
// vence o primeiro idioma suportado, e sem nenhum, o padrão.
export function localeFromAcceptLanguage(header: string | null): Locale {
  const langs = (header ?? '')
    .split(',')
    .map((part) => {
      const [tag, q] = part.trim().split(';q=');
      return { tag: tag.toLowerCase(), q: q ? Number(q) : 1 };
    })
    .filter((l) => l.tag && l.q > 0)
    .sort((a, b) => b.q - a.q);
  for (const { tag } of langs) {
    if (tag.startsWith('pt')) return 'pt-BR';
    if (tag.startsWith('en')) return 'en-US';
  }
  return DEFAULT_LOCALE;
}
