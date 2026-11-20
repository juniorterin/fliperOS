// Confere os textos do botão Compartilhar (src/lib/share-texts.json):
//  - os dois idiomas têm as cinco redes, com o {url} e dentro do limite;
//  - o X cabe nos 280 caracteres (o link conta 23);
//  - os textos foram revistos no último update: o "update" do JSON tem de ser
//    o número da última linha de ../updates/index. Um update novo sem esta
//    revisão faz a checagem falhar (e o tools/make-update.sh não publica).
// Os limites de cada rede vêm de src/lib/share.ts.
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const data = JSON.parse(readFileSync(path.join(root, 'src/lib/share-texts.json'), 'utf8'));
const shareTs = readFileSync(path.join(root, 'src/lib/share.ts'), 'utf8');

const limits = {};
for (const m of shareTs.matchAll(/^ {2}(\w+): \{\n\s*name: '[^']+',\n\s*max: (\d+),/gm)) {
  limits[m[1]] = { max: Number(m[2]) };
}
const networks = /SHARE_NETWORKS = \[([^\]]+)\]/.exec(shareTs)[1].match(/'(\w+)'/g).map((n) => n.slice(1, -1));

const problems = [];
// A mesma conta de shareLength em src/lib/share.ts (um emoji conta como 2).
const length = (network, text) => (network === 'x' ? text.replace(/https?:\/\/\S+/g, 'x'.repeat(23)) : text).length;

for (const locale of ['en-US', 'pt-BR']) {
  for (const network of networks) {
    const lines = data.texts[locale]?.[network];
    const where = `${locale}/${network}`;
    if (!lines) {
      problems.push(`${where}: sem texto`);
      continue;
    }
    const text = lines.join('\n').replaceAll('{url}', 'https://fliperos.juniorter.in/en').replaceAll('{version}', '0.27');
    const size = length(network, text);
    const { max } = limits[network];
    const min = Math.ceil(max * 0.95);
    console.log(`${where.padEnd(18)} ${String(size).padStart(5)} / ${max}`);
    if (!lines.join('\n').includes('{url}')) problems.push(`${where}: falta o {url}`);
    if (size > max) problems.push(`${where}: ${size} caracteres, o limite é ${max}`);
    else if (size < min) problems.push(`${where}: ${size} caracteres, tem de ocupar o máximo da rede (de ${min} a ${max})`);
    if (/\{\w+\}/.test(text)) problems.push(`${where}: marcador desconhecido ${text.match(/\{\w+\}/)[0]}`);
  }
}

// O número do último update: a primeira coluna da última linha de updates/index.
// Fora do repositório (build do site no Docker, só a pasta website) não há o arquivo.
const index = path.resolve(root, '..', 'updates', 'index');
let last = null;
if (existsSync(index)) {
  for (const line of readFileSync(index, 'utf8').split('\n')) {
    const n = /^(\d+)\t/.exec(line);
    if (n) last = Number(n[1]);
  }
  const wanted = Number(process.env.SHARE_EXPECT_UPDATE || last);
  if (data.update !== wanted) {
    problems.push(
      `os textos são do update ${data.update}, mas o último update é o ${wanted}: releia os textos em src/lib/share-texts.json, ponha a novidade nova e suba "update" para ${wanted}`,
    );
  }
}

if (problems.length) {
  console.log(problems.join('\n'));
  console.log(`\n${problems.length} problema(s) nos textos de compartilhar`);
  process.exit(1);
}
console.log(`ok: ${networks.length} redes x 2 idiomas, textos do update ${data.update}${last === null ? '' : ' (o último)'}`);
