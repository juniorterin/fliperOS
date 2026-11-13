import type { Metadata, ResolvingMetadata } from 'next';
import { notFound } from 'next/navigation';
import { Header } from '@/components/Header';
import { LOCALES, OG_LOCALE, localeFromSegment, messages, pagePath } from '@/i18n';
import { Footer } from '@/sections/Footer';
import { Privacy } from '@/sections/Privacy';

// /en/privacy e /pt/privacy: o endereço da política na tela de consentimento
// OAuth do Google (projeto fliperos-backup). Segmento fixo: vence o [page].
async function resolve(params: PageProps<'/[lang]/privacy'>['params']) {
  const locale = localeFromSegment((await params).lang);
  if (!locale) notFound();
  return locale;
}

export async function generateMetadata({ params }: PageProps<'/[lang]/privacy'>, parent: ResolvingMetadata): Promise<Metadata> {
  const locale = await resolve(params);
  const { meta } = messages[locale].privacy;
  const languages = {
    ...Object.fromEntries(LOCALES.map((l) => [l, pagePath(l, 'privacy')])),
    'x-default': pagePath('en-US', 'privacy'),
  };
  const { openGraph, twitter } = await parent;
  return {
    title: meta.title,
    description: meta.description,
    alternates: { canonical: pagePath(locale, 'privacy'), languages },
    openGraph: {
      type: 'website',
      url: pagePath(locale, 'privacy'),
      siteName: 'FliperOS',
      title: meta.title,
      description: meta.description,
      locale: OG_LOCALE[locale],
      images: openGraph?.images,
    },
    twitter: { card: 'summary_large_image', title: meta.title, description: meta.description, images: twitter?.images },
  };
}

export default async function PrivacyPage({ params }: PageProps<'/[lang]/privacy'>) {
  await resolve(params);
  return (
    <>
      <Header />
      <div className="lg:pl-64">
        <main id="main">
          <Privacy />
        </main>
        <Footer />
      </div>
    </>
  );
}
