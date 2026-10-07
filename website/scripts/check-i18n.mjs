// Procura texto de interface fixo no JSX de src/components e src/sections:
// todo texto visível deve vir de src/i18n. Siglas e nomes técnicos que não se
// traduzem ficam em ALLOW.
import { readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..', 'src');
const ALLOW = new Set(['|', '15 kHz', 'switchres', 'SR-1_384x224@59.64', 'fliperos@fliperos:~$', 'Fliper', 'OS']);

const files = ['components', 'sections'].flatMap((dir) =>
  readdirSync(path.join(root, dir))
    .filter((f) => f.endsWith('.tsx'))
    .map((f) => path.join(root, dir, f)),
);

let problems = 0;
for (const file of files) {
  const src = readFileSync(file, 'utf8');
  for (const match of src.matchAll(/>\s*([^<>{}\n]*[A-Za-zÀ-ÿ][^<>{}\n]*?)\s*</g)) {
    const text = match[1].trim();
    if (!text || ALLOW.has(text) || /^[=&|?:.,;()[\]'"`$#!+\-*/\s\w]*=>/.test(text)) continue;
    if (/[;=]|\) =>|&&/.test(text)) continue;
    const line = src.slice(0, match.index).split('\n').length;
    console.log(`${path.relative(root, file)}:${line}: ${text}`);
    problems++;
  }
}

if (problems) {
  console.log(`\n${problems} hardcoded string(s)`);
  process.exit(1);
}
console.log(`ok: ${files.length} files, no hardcoded UI strings`);
