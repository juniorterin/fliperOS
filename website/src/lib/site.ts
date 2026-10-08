export const REPO_URL = 'https://github.com/juniorterin/fliperOS';

export const LINKS = {
  github: REPO_URL,
  docs: `${REPO_URL}/wiki`,
  releases: `${REPO_URL}/releases`,
  // /releases/latest redireciona sempre para o release mais recente.
  latestRelease: `${REPO_URL}/releases/latest`,
  issues: `${REPO_URL}/issues`,
  instagram: 'https://www.instagram.com/juniorter.in/',
} as const;

// O repositório abre no README em inglês (o original); o site em português
// leva direto à tradução, README.pt-BR.md.
export function readmeUrl(locale: string): string {
  return locale.startsWith('pt') ? `${REPO_URL}/blob/main/README.pt-BR.md` : REPO_URL;
}

export const AUTHOR_HANDLE = '@juniorter.in';
export const AUTHOR = { name: 'juniorterin', url: 'https://github.com/juniorterin' } as const;

export const FLIPEROS_VERSION = '0.8.3';

// A ISO se chama fliperos-VERSAO.iso. Este endereco baixa o arquivo direto
// no release mais recente; se o nome mudar, a API (github.ts) manda o certo.
export function latestIsoUrl(version: string = FLIPEROS_VERSION): string {
  return `${REPO_URL}/releases/latest/download/fliperos-${version}.iso`;
}

// Contato da assessoria: mostrado como texto, sem mailto, para não virar alvo
// fácil de spam.
export const CONTACT_EMAIL = { user: 'juniorterin', domain: 'gmail', tld: 'com' } as const;

// Só o link público de doação: a chave secreta do Stripe nunca entra no site.
export const DONATE_URL = 'https://donate.stripe.com/7sYbJ3cetcU17Cm5eM3VC00';
export const PIX_KEY = 'd349cb59-3443-42cd-9aa8-3f2ccfe7601b';

export const GA_ID = process.env.NEXT_PUBLIC_GA_ID ?? 'G-FTG8120HF8';

// Canonical, hreflang, Open Graph e sitemap usam o domínio oficial;
// NEXT_PUBLIC_SITE_URL, lido no build, troca o domínio (outro ambiente).
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || 'https://fliperos.juniorter.in').replace(/\/+$/, '');

export const SECTION_IDS = ['features', 'screenshots', 'emulators', 'crt', 'multi-monitor', 'setup', 'open-source'] as const;
export type SectionId = (typeof SECTION_IDS)[number];

export const SCREENSHOT_IDS = ['setup', 'install', 'video', 'desktop'] as const;
export const HERO_SCREENSHOT = 'hero';
export const SCREENSHOT_EXTENSIONS = ['avif', 'webp', 'png', 'jpg'] as const;
