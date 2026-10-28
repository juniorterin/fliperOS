import { statSync } from 'node:fs';
import path from 'node:path';
import { SCREENSHOT_EXTENSIONS, SCREENSHOT_IDS } from './site';

export type ScreenshotMap = Record<string, string | null>;

function hasContent(file: string): boolean {
  try {
    return statSync(file).size > 0;
  } catch {
    return false;
  }
}

// Só imagem real do FliperOS: o arquivo existe (e não está vazio) em
// public/screenshots ou o slot fica como placeholder com o caminho esperado.
function find(id: string): string | null {
  for (const ext of SCREENSHOT_EXTENSIONS) {
    const file = `${id}.${ext}`;
    if (hasContent(path.join(process.cwd(), 'public', 'screenshots', file))) return `/screenshots/${file}`;
  }
  return null;
}

export function getScreenshots(): ScreenshotMap {
  const map: ScreenshotMap = {};
  for (const id of SCREENSHOT_IDS) map[id] = find(id);
  return map;
}
