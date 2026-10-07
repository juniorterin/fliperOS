import type { Metadata, Viewport } from 'next';
import { notFound } from 'next/navigation';
import { Analytics } from '@/components/Analytics';
import { LOCALES, LOCALE_SEGMENT, OG_LOCALE, localeFromSegment, localePath, messages } from '@/i18n';
import { I18nProvider } from '@/i18n/I18nProvider';
import { AUTHOR, FLIPEROS_VERSION, LINKS, SITE_URL } from '@/lib/site';
import '../globals.css';

// Só /en e /pt existem; qualquer outro segmento cai no 404 global.
export const dynamicParams = false;

export function generateStaticParams() {
  return LOCALES.map((l) => ({ lang: LOCALE_SEGMENT[l] }));
}

const languages = {
  ...Object.fromEntries(LOCALES.map((l) => [l, localePath(l)])),
  'x-default': '/',
};

export async function generateMetadata({ params }: LayoutProps<'/[lang]'>): Promise<Metadata> {
  const locale = localeFromSegment((await params).lang);
  if (!locale) return {};
  const { meta } = messages[locale];
  return {
    metadataBase: new URL(SITE_URL),
    title: meta.title,
    description: meta.description,
    applicationName: 'FliperOS',
    keywords: meta.keywords,
    authors: [{ name: AUTHOR.name, url: AUTHOR.url }],
    creator: AUTHOR.name,
    publisher: AUTHOR.name,
    category: 'technology',
    alternates: { canonical: localePath(locale), languages },
    openGraph: {
      type: 'website',
      url: localePath(locale),
      siteName: 'FliperOS',
      title: meta.title,
      description: meta.description,
      locale: OG_LOCALE[locale],
      alternateLocale: LOCALES.filter((l) => l !== locale).map((l) => OG_LOCALE[l]),
    },
    twitter: {
      card: 'summary_large_image',
      title: meta.title,
      description: meta.description,
    },
    robots: {
      index: true,
      follow: true,
      googleBot: { index: true, follow: true, 'max-image-preview': 'large', 'max-snippet': -1, 'max-video-preview': -1 },
    },
    formatDetection: { telephone: false, email: false, address: false },
  };
}

export const viewport: Viewport = {
  themeColor: '#21222c',
  colorScheme: 'dark',
};

function jsonLd(locale: (typeof LOCALES)[number]) {
  const { meta } = messages[locale];
  const url = `${SITE_URL}${localePath(locale)}`;
  const author = { '@type': 'Person', name: AUTHOR.name, url: AUTHOR.url, sameAs: [AUTHOR.url, LINKS.instagram] };
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        url: SITE_URL,
        name: 'FliperOS',
        inLanguage: LOCALES,
        publisher: author,
      },
      {
        '@type': 'WebPage',
        '@id': `${url}#webpage`,
        url,
        name: meta.title,
        description: meta.description,
        inLanguage: locale,
        isPartOf: { '@id': `${SITE_URL}/#website` },
        about: { '@id': `${SITE_URL}/#software` },
        primaryImageOfPage: `${url}/opengraph-image/card`,
      },
      {
        '@type': 'SoftwareApplication',
        '@id': `${SITE_URL}/#software`,
        name: 'FliperOS',
        softwareVersion: FLIPEROS_VERSION,
        applicationCategory: 'OperatingSystem',
        applicationSubCategory: 'Linux distribution',
        operatingSystem: 'Linux (Ubuntu 24.04, amd64)',
        description: meta.description,
        keywords: meta.keywords.join(', '),
        url,
        image: `${url}/opengraph-image/card`,
        downloadUrl: LINKS.releases,
        releaseNotes: LINKS.releases,
        codeRepository: LINKS.github,
        isAccessibleForFree: true,
        author,
        sameAs: [LINKS.github],
        offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
      },
    ],
  };
}

export default async function LangLayout({ children, params }: LayoutProps<'/[lang]'>) {
  const locale = localeFromSegment((await params).lang);
  if (!locale) notFound();
  return (
    <html lang={locale}>
      <head>
        <noscript>
          <style>{'.reveal{opacity:1;transform:none}'}</style>
        </noscript>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd(locale)).replace(/</g, '\\u003c') }}
        />
      </head>
      <body className="min-h-dvh overflow-x-hidden">
        <I18nProvider locale={locale}>{children}</I18nProvider>
        <Analytics />
      </body>
    </html>
  );
}
