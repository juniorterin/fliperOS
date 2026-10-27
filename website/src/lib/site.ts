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

// Âncora do passo a passo no README: muda se o título "## Do zero ao jogo" mudar.
export function guideUrl(locale: string): string {
  const anchor = locale.startsWith('pt') ? 'do-zero-ao-jogo-passo-a-passo' : 'from-zero-to-playing-step-by-step';
  return `${readmeUrl(locale)}#${anchor}`;
}

export const AUTHOR_HANDLE = '@juniorter.in';
export const AUTHOR = { name: 'juniorterin', url: 'https://github.com/juniorterin' } as const;

// Quem ajudou o projeto (código, testes no próprio hardware, ideias). A mesma
// lista está no fim dos dois READMEs: um nome novo entra nos três.
export const CONTRIBUTORS = [{ name: 'ultimatevga-dot', url: 'https://github.com/ultimatevga-dot' }] as const;

export const FLIPEROS_VERSION = '0.14';

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

// As páginas de detalhe, na ordem do menu e do "Próxima"; o slug é o mesmo
// nos dois idiomas (/en/frontend, /pt/frontend).
export const PAGE_SLUGS = ['frontend', 'setup', 'games', 'video', 'web-panel', 'emulators', 'hardware'] as const;
export type PageSlug = (typeof PAGE_SLUGS)[number];

export function isPageSlug(value: string): value is PageSlug {
  return (PAGE_SLUGS as readonly string[]).includes(value);
}

// A página da wiki com o detalhe completo de cada uma.
export const PAGE_WIKI: Record<PageSlug, string> = {
  frontend: 'Frontends',
  setup: 'Installed-system',
  games: 'ROMs',
  video: 'Kernel-15-kHz',
  'web-panel': 'Web-panel',
  emulators: 'Emulators',
  hardware: 'Video-cards',
};

// Os ids abaixo são caminhos em public/screenshots sem a extensão; os textos
// de cada um ficam em shots no src/i18n. anim/* são WebP animados cortados
// das cenas gravadas do vídeo de apresentação (tools/video).

// O carrossel do hero: poucas telas, as que mais mostram.
export const HERO_SHOTS = [
  'anim/frontend-list',
  'gui/main',
  'anim/frontend-full',
  'anim/setup-carousel',
  'anim/frontend-grid',
  'anim/romfilter',
  'anim/frontend-play',
  'anim/setup-buttons',
  'gui/guncon-target1',
  'desktop',
];

// A galeria da home: um grupo por página, com o "ver mais" levando a ela.
// {lang} vira en ou pt (os prints do painel web têm um por idioma).
export const HOME_GALLERY: { page: PageSlug; shots: string[] }[] = [
  { page: 'frontend', shots: ['anim/frontend-grid', 'frontend/list-card', 'anim/frontend-info', 'frontend/full'] },
  { page: 'setup', shots: ['anim/setup-guncon', 'gui/video', 'anim/install', 'gui/layout-edit'] },
  { page: 'games', shots: ['anim/downloader', 'gui/filter', 'gui/filter-controls', 'anim/bios'] },
  { page: 'web-panel', shots: ['web/frontend-{lang}', 'web/phone-{lang}', 'web/status-{lang}'] },
  { page: 'video', shots: ['multi/darius-1', 'multi/darius-2', 'multi/darius-3', 'multi/punchout-1'] },
];

// "Todas as telas" no fim de cada página de detalhe.
export const PAGE_SHOTS: Record<PageSlug, string[]> = {
  frontend: [
    'frontend/list-guide',
    'frontend/list',
    'frontend/list-clones',
    'frontend/list-card',
    'frontend/list-more',
    'frontend/list-more-2',
    'frontend/list-filter',
    'frontend/list-options',
    'frontend/list-classify',
    'frontend/list-rename',
    'frontend/full',
    'frontend/full-card',
    'frontend/full-clone',
    'frontend/grid',
    'frontend/grid-card',
    'frontend/grid-options',
  ],
  setup: [
    'gui/main',
    'gui/main-setup',
    'gui/live',
    'gui/progress',
    'gui/setup',
    'gui/video',
    'gui/radio',
    'gui/joysticks',
    'gui/buttons-players',
    'gui/buttons-capture',
    'gui/layout',
    'gui/layout-edit',
    'gui/guncon',
    'gui/guncon-target1',
    'gui/guncon-target2',
    'gui/guncon-target3',
    'gui/guncon-result',
    'gui/input',
    'gui/power',
    'gui/yesno',
    'gui/error',
    'desktop',
  ],
  games: [
    'gui/setup-games',
    'gui/downloader',
    'gui/downloader-torrent',
    'gui/downloader-filter',
    'gui/filter',
    'gui/filter-scrolled',
    'gui/filter-players',
    'gui/filter-buttons',
    'gui/filter-controls',
    'gui/filter-years',
    'gui/downloader-magnet',
    'gui/downloader-magnet-browser',
    'gui/downloader-progress',
  ],
  video: [],
  'web-panel': [],
  emulators: [],
  hardware: [],
};

// Telas usadas só nos blocos das páginas de detalhe.
const ROW_ONLY_SHOTS = ['anim/frontend-systems', 'anim/setup-colour', 'anim/setup-latency', 'gui/checklist'];

const withLang = (id: string) => (id.includes('{lang}') ? ['en', 'pt'].map((l) => id.replace('{lang}', l)) : [id]);

// Todo id que pode ter um arquivo em public/screenshots.
export const SCREENSHOT_IDS = [
  ...new Set([
    ...HERO_SHOTS,
    ...HOME_GALLERY.flatMap((g) => g.shots.flatMap(withLang)),
    ...Object.values(PAGE_SHOTS).flat(),
    ...ROW_ONLY_SHOTS,
  ]),
];
// gif vale também: uma animação em GIF entra no lugar do WebP animado.
export const SCREENSHOT_EXTENSIONS = ['avif', 'webp', 'gif', 'png', 'jpg'] as const;
