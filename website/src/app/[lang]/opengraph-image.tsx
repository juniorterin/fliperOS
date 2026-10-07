import { ImageResponse } from 'next/og';
import { LOCALES, LOCALE_SEGMENT, localeFromSegment, messages, DEFAULT_LOCALE } from '@/i18n';

export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export function generateStaticParams() {
  return LOCALES.map((l) => ({ lang: LOCALE_SEGMENT[l] }));
}

// Um card por idioma (/en/opengraph-image/card, /pt/opengraph-image/card), com o alt traduzido.
export async function generateImageMetadata({ params }: { params: Promise<{ lang: string }> }) {
  const locale = localeFromSegment((await params).lang) ?? DEFAULT_LOCALE;
  return [{ id: 'card', alt: messages[locale].meta.ogAlt, size, contentType }];
}

// Card do Open Graph/Twitter gerado no build: arte do site, sem screenshot e
// sem a versao (redes sociais guardam o card antigo por muito tempo).
export default async function OpengraphImage({ params }: { params: Promise<{ lang: string }> }) {
  const t = messages[localeFromSegment((await params).lang) ?? DEFAULT_LOCALE];
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '80px',
          background: 'radial-gradient(circle at 30% 0%, #3b3254 0%, #21222c 55%, #191a21 100%)',
          color: '#f8f8f2',
          fontFamily: 'sans-serif',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px', fontSize: 34, color: '#50fa7b' }}>
          <div style={{ display: 'flex', width: 18, height: 18, borderRadius: 9, background: '#50fa7b' }} />
          fliperos
        </div>
        <div style={{ display: 'flex', fontSize: 120, fontWeight: 800, marginTop: 24, letterSpacing: -3 }}>
          <span>Fliper</span>
          <span style={{ color: '#bd93f9' }}>OS</span>
        </div>
        <div style={{ display: 'flex', fontSize: 54, marginTop: 8, color: '#ff79c6' }}>
          {t.hero.titleLine1} {t.hero.titleLine2}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', marginTop: 48, fontSize: 26, color: '#bfc2d4' }}>
          {t.badges.items.map((b) => (
            <div
              key={b}
              style={{
                display: 'flex',
                alignItems: 'center',
                height: 52,
                marginRight: 14,
                marginBottom: 14,
                padding: '0 22px',
                border: '2px solid #44475a',
                borderRadius: 26,
                background: '#21222c',
              }}
            >
              {b}
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
