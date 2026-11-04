import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { ImageResponse } from 'next/og';
import { LOCALES, LOCALE_SEGMENT, localeFromSegment, messages, DEFAULT_LOCALE } from '@/i18n';

export const size = { width: 1024, height: 541 };
export const contentType = 'image/png';

// A sala isométrica do gabinete, sem texto: o título entra por cima em cada idioma.
const room = `data:image/png;base64,${await readFile(join(process.cwd(), 'public/art/og-room.png'), 'base64')}`;

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
// O título fica no canto de cima e o slogan no de baixo, fora da sala.
export default async function OpengraphImage({ params }: { params: Promise<{ lang: string }> }) {
  const t = messages[localeFromSegment((await params).lang) ?? DEFAULT_LOCALE];
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          position: 'relative',
          background: '#21222c',
          color: '#f8f8f2',
          fontFamily: 'sans-serif',
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={room} width={1024} height={541} alt="" style={{ position: 'absolute', top: 0, left: 0 }} />
        <div style={{ position: 'absolute', top: 34, left: 44, display: 'flex', fontSize: 72, fontWeight: 800, letterSpacing: -2 }}>
          <span>Fliper</span>
          <span style={{ color: '#bd93f9' }}>OS</span>
        </div>
        <div
          style={{
            position: 'absolute',
            right: 44,
            bottom: 30,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            fontSize: 34,
            fontWeight: 700,
            lineHeight: 1.15,
          }}
        >
          <span>{t.hero.titleLine1}</span>
          <span style={{ color: '#ff79c6' }}>{t.hero.titleLine2}</span>
        </div>
      </div>
    ),
    size,
  );
}
