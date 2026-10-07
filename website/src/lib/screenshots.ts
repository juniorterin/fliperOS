import { existsSync } from 'node:fs';
import path from 'node:path';
import { HERO_SCREENSHOT, SCREENSHOT_EXTENSIONS, SCREENSHOT_IDS } from './site';

export type ScreenshotMap = Record<string, string | null>;

// Só imagem real do FliperOS: o arquivo existe em public/screenshots ou o
// slot fica como placeholder com o caminho esperado.
function find(id: string): string | null {
  for (const ext of SCREENSHOT_EXTENSIONS) {
    const file = `${id}.${ext}`;
    if (existsSync(path.join(process.cwd(), 'public', 'screenshots', file))) return `/screenshots/${file}`;
  }
  return null;
}

export function getScreenshots(): ScreenshotMap {
  const map: ScreenshotMap = { [HERO_SCREENSHOT]: find(HERO_SCREENSHOT) };
  for (const id of SCREENSHOT_IDS) map[id] = find(id);
  return map;
}
