import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import type { ReactNode } from 'react';
import { Header } from '@/components/Header';
import { LOCALES, LOCALE_SEGMENT, OG_LOCALE, localeFromSegment, messages, pagePath } from '@/i18n';
import { getRepoStats } from '@/lib/github';
import { mediaMap, pickMedia } from '@/lib/media';
import { getScreenshots } from '@/lib/screenshots';
import { PAGE_SHOTS, PAGE_SLUGS, SITE_URL, isPageSlug, latestIsoUrl, type PageSlug } from '@/lib/site';
import { Crt } from '@/sections/Crt';
import { Emulators } from '@/sections/Emulators';
import { FeatureRows } from '@/sections/FeatureRows';
import { Footer } from '@/sections/Footer';
import { MultiMonitor } from '@/sections/MultiMonitor';
import { OpenHardware } from '@/sections/OpenHardware';
import { PageEnd } from '@/sections/PageEnd';
import { PageHero } from '@/sections/PageHero';
import { Pixelcade } from '@/sections/Pixelcade';
import { Requirements } from '@/sections/Requirements';
import { Setup } from '@/sections/Setup';
import { WebPanel } from '@/sections/WebPanel';

export const revalidate = 3600;

// Só as páginas de PAGE_SLUGS; qualquer outra cai no 404 global.
export const dynamicParams = false;

export function generateStaticParams() {
  return PAGE_SLUGS.map((page) => ({ page }));
}

// As seções que já existiam, cada uma na página do seu assunto, depois dos blocos.
const SECTIONS: Record<PageSlug, ReactNode> = {
  frontend: null,
  setup: <Setup />,
  games: null,
  video: (
    <>
      <Crt />
      <MultiMonitor />
    </>
  ),
  'web-panel': <WebPanel />,
  emulators: <Emulators />,
  hardware: (
    <>
      <Requirements />
      <Pixelcade />
      <OpenHardware />
    </>
  ),
  install: null,
  controls: null,
  cards: null,
};

async function resolve(params: PageProps<'/[lang]/[page]'>['params']) {
  const { lang, page } = await params;
  const locale = localeFromSegment(lang);
  if (!locale || !isPageSlug(page)) notFound();
  return { locale, page };
}

export async function generateMetadata({ params }: PageProps<'/[lang]/[page]'>): Promise<Metadata> {
  const { locale, page } = await resolve(params);
  const { meta } = messages[locale].pages[page];
  const languages = {
    ...Object.fromEntries(LOCALES.map((l) => [l, pagePath(l, page)])),
    'x-default': pagePath('en-US', page),
  };
  return {
    title: meta.title,
    description: meta.description,
    alternates: { canonical: pagePath(locale, page), languages },
    openGraph: {
      type: 'website',
      url: pagePath(locale, page),
      siteName: 'FliperOS',
      title: meta.title,
      description: meta.description,
      locale: OG_LOCALE[locale],
    },
    twitter: { card: 'summary_large_image', title: meta.title, description: meta.description },
  };
}

export default async function DetailPage({ params }: PageProps<'/[lang]/[page]'>) {
  const { locale, page } = await resolve(params);
  const t = messages[locale];
  const stats = await getRepoStats();
  const media = mediaMap(getScreenshots(), t.shots, LOCALE_SEGMENT[locale]);
  // Só as telas dos blocos desta página vão para o navegador.
  const rowMedia = Object.fromEntries(pickMedia(media, t.pages[page].rows.map((r) => r.shot)).map((m) => [m.id, m]));
  const url = `${SITE_URL}${pagePath(locale, page)}`;
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebPage',
        '@id': `${url}#webpage`,
        url,
        name: t.pages[page].meta.title,
        description: t.pages[page].meta.description,
        inLanguage: locale,
        isPartOf: { '@id': `${SITE_URL}/#website` },
        about: { '@id': `${SITE_URL}/#software` },
      },
      {
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: t.nav.home, item: `${SITE_URL}${pagePath(locale)}` },
          { '@type': 'ListItem', position: 2, name: t.nav.pages[page], item: url },
        ],
      },
    ],
  };
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }} />
      <Header />
      <div className="lg:pl-64">
      <main id="main">
        <PageHero page={page} downloadUrl={stats?.release?.iso ?? latestIsoUrl()} />
        <FeatureRows page={page} media={rowMedia} />
        {SECTIONS[page]}
        <PageEnd page={page} screens={pickMedia(media, PAGE_SHOTS[page])} />
      </main>
      <Footer />
      </div>
    </>
  );
}
