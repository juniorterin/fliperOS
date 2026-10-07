import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import enUS from '@/i18n/en-US';
import { I18nProvider } from '@/i18n/I18nProvider';
import { LINKS, SITE_URL } from '@/lib/site';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: enUS.meta.title,
  description: enUS.meta.description,
  applicationName: 'FliperOS',
  keywords: [
    'FliperOS',
    'arcade',
    'CRT',
    '15 kHz',
    'Switchres',
    'GroovyMAME',
    'RetroArch',
    'Linux',
    'Ubuntu 24.04',
    'arcade cabinet',
    'GroovyArcade',
  ],
  alternates: { canonical: '/' },
  openGraph: {
    type: 'website',
    url: '/',
    siteName: 'FliperOS',
    title: enUS.meta.title,
    description: enUS.meta.description,
    locale: 'en_US',
    alternateLocale: ['pt_BR'],
  },
  twitter: {
    card: 'summary_large_image',
    title: enUS.meta.title,
    description: enUS.meta.description,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: '#21222c',
  colorScheme: 'dark',
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'SoftwareApplication',
  name: 'FliperOS',
  softwareVersion: '0.7',
  applicationCategory: 'Operating system',
  operatingSystem: 'Linux (Ubuntu 24.04, amd64)',
  description: enUS.meta.description,
  url: SITE_URL,
  downloadUrl: LINKS.releases,
  sameAs: [LINKS.github],
  offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-US" suppressHydrationWarning>
      <head>
        <noscript>
          <style>{'.reveal{opacity:1;transform:none}'}</style>
        </noscript>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      </head>
      <body className="min-h-dvh overflow-x-hidden">
        <I18nProvider>{children}</I18nProvider>
      </body>
    </html>
  );
}
