// Falha se algum arquivo de public/ está vazio: uma imagem de 0 bytes aparece
// quebrada no site.
import { readdirSync, statSync } from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..', 'public');

function walk(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((e) => (e.isDirectory() ? walk(path.join(dir, e.name)) : [path.join(dir, e.name)]));
}

const empty = walk(root).filter((f) => statSync(f).size === 0);
if (empty.length) {
  for (const f of empty) console.log(`empty file: ${path.relative(root, f)}`);
  console.log(`\n${empty.length} empty file(s) in public/`);
  process.exit(1);
}
console.log('check-media: no empty files in public/');
