import type { Messages } from '@/i18n';
import type { ScreenshotMap } from './screenshots';

export type Media = {
  id: string;
  src: string;
  title: string;
  caption: string;
  alt: string;
  // As animações são 320x240: ampliadas sem filtro, como no tubo.
  pixelated: boolean;
  animated: boolean;
};

export type MediaMap = Record<string, Media>;

type ShotText = { title: string; caption: string };

// Cada id com texto em shots e arquivo em public/screenshots vira uma mídia;
// {lang} escolhe o print do idioma (en ou pt).
export function mediaMap(screenshots: ScreenshotMap, shots: Messages['shots'], lang: string): MediaMap {
  const map: MediaMap = {};
  for (const [id, text] of Object.entries(shots as Record<string, ShotText>)) {
    const src = screenshots[id.replace('{lang}', lang)];
    if (!src) continue;
    const animated = id.startsWith('anim/') || src.endsWith('.gif');
    map[id] = { id, src, ...text, alt: `${text.title}. ${text.caption}`, pixelated: id.startsWith('anim/'), animated };
  }
  return map;
}

// Só as que existem, na ordem dada.
export function pickMedia(map: MediaMap, ids: readonly string[]): Media[] {
  return ids.flatMap((id) => (map[id] ? [map[id]] : []));
}
