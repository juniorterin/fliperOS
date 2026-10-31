export const REPO_URL = 'https://github.com/juniorterin/fliperOS';

export const LINKS = {
  github: REPO_URL,
  docs: `${REPO_URL}/wiki`,
  releases: `${REPO_URL}/releases`,
  // /releases/latest redireciona sempre para o release mais recente.
  latestRelease: `${REPO_URL}/releases/latest`,
  issues: `${REPO_URL}/issues`,
  instagram: 'https://www.instagram.com/juniorter.in/',
  video: 'https://www.youtube.com/watch?v=W0vrpqgefL0',
  dpVgaAdapter: 'https://a.aliexpress.com/_mPCmfYb',
  artRepairTelegram: 'https://t.me/+1XiiRQtrBVFkNGEx',
  artRepairEmail: 'mailto:art.repair80@gmail.com',
} as const;

// O id do vídeo de apresentação no YouTube (o player só carrega ao clicar).
export const VIDEO_ID = 'W0vrpqgefL0';

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

export const FLIPEROS_VERSION = '0.16';

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
export const PAGE_SLUGS = ['frontend', 'setup', 'games', 'video', 'web-panel', 'emulators', 'hardware', 'install', 'controls', 'cards'] as const;
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
  hardware: 'DIY-hardware',
  install: 'Install',
  controls: 'Controls',
  cards: 'Video-cards',
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

// Os passos da home, do pendrive ao jogo: uma tela cada, com a página que o
// conta em detalhe. O texto de cada um está em howItWorks.steps, na mesma ordem.
export const HOME_STEPS: { page: PageSlug; shot: string }[] = [
  { page: 'install', shot: 'anim/install' },
  { page: 'controls', shot: 'anim/setup-buttons' },
  { page: 'games', shot: 'anim/romfilter' },
  { page: 'frontend', shot: 'anim/frontend-grid' },
];

// Os destaques da home, numa grade com tiles de tamanhos diferentes; o texto
// de cada um está em highlights.items pelo id. {lang} vira en ou pt (os prints
// do painel web têm um por idioma). Sem arquivo, o tile fica só com o texto.
export type HighlightId = 'web' | 'multi' | 'gun' | 'live' | 'coin';
export const HOME_HIGHLIGHTS: { id: HighlightId; page: PageSlug; shot: string; extra?: string; since?: string }[] = [
  { id: 'web', page: 'web-panel', shot: 'web/phone-{lang}', extra: 'web/frontend-{lang}' },
  { id: 'multi', page: 'video', shot: 'multi/darius-1' },
  { id: 'gun', page: 'controls', shot: 'gui/guncon-target1' },
  { id: 'live', page: 'web-panel', shot: 'anim/web-controller', since: '0.13' },
  { id: 'coin', page: 'frontend', shot: 'anim/frontend-commercial', since: '0.15' },
];

// A faixa de telas da home: poucas, variadas, que rolam para o lado.
export const HOME_STRIP = [
  'anim/frontend-list',
  'anim/setup-carousel',
  'anim/setup-guncon',
  'anim/romfilter',
  'anim/frontend-info',
  'anim/setup-colour',
  'gui/main',
  'anim/bios',
];

// As últimas versões na linha do tempo da home (a mais nova primeiro). Os
// textos de cada uma estão em whatsNew.notes; um release novo entra aqui e lá,
// junto com FLIPEROS_VERSION.
export const RELEASES = [
  { version: '0.16', date: '2026-10-28' },
  { version: '0.15', date: '2026-10-28' },
  { version: '0.14', date: '2026-10-26' },
  { version: '0.13', date: '2026-10-25' },
] as const;
export type ReleaseVersion = (typeof RELEASES)[number]['version'];

export function releaseUrl(version: string): string {
  return `${REPO_URL}/releases/tag/${version}`;
}

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
  setup: ['gui/main-setup', 'gui/setup', 'gui/video', 'gui/radio', 'gui/input', 'gui/power', 'gui/yesno', 'desktop'],
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
  install: ['gui/main', 'gui/progress', 'gui/live', 'gui/error'],
  controls: [
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
  ],
  cards: [],
};

// Telas usadas só nos blocos das páginas de detalhe.
const ROW_ONLY_SHOTS = [
  'anim/frontend-systems',
  'anim/setup-colour',
  'anim/setup-latency',
  'gui/checklist',
  'gui/video-driver',
  'gui/unsupported',
  'gui/lab',
  'anim/web-library',
  'anim/web-frontend',
  'anim/web-live',
  'anim/web-settings',
  'frontend/options',
  'web/obs-{lang}',
];

const withLang = (id: string) => (id.includes('{lang}') ? ['en', 'pt'].map((l) => id.replace('{lang}', l)) : [id]);

// Todo id que pode ter um arquivo em public/screenshots.
export const SCREENSHOT_IDS = [
  ...new Set([
    ...HERO_SHOTS,
    ...HOME_STEPS.map((s) => s.shot),
    ...HOME_HIGHLIGHTS.flatMap((h) => [h.shot, ...(h.extra ? [h.extra] : [])]).flatMap(withLang),
    ...HOME_STRIP,
    ...Object.values(PAGE_SHOTS).flat(),
    ...ROW_ONLY_SHOTS.flatMap(withLang),
  ]),
];
// gif vale também: uma animação em GIF entra no lugar do WebP animado.
export const SCREENSHOT_EXTENSIONS = ['avif', 'webp', 'gif', 'png', 'jpg'] as const;
