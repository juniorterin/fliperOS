// Bot tradutor do grupo do Telegram (t.me/fliperos15khz), Cloudflare Worker.
// O Telegram chama este worker por webhook a cada mensagem do grupo; o worker
// traduz com o Workers AI (m2m100, gratis no plano free) e responde na mensagem:
//   cada mensagem vai para os outros dois idiomas (pt, en, es).
// Segredos: TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET. Binding AI no wrangler.toml.
// Variavel opcional: ALLOWED_CHAT (id numerico do grupo; sem ela, qualquer chat).
// SKIP_TOPICS: topicos sem traducao (o numero no fim do link do topico,
// t.me/fliperos15khz/NUMERO), separados por virgula.
// Pacotes de jogo custom (.fliperos-customgame.zip): vao ao GitHub, que posta os
// dados no topico Files (dispatchPackage, mais abaixo). Os que vem em partes (.zip.001,
// .002...) esperam no KV PARTS ate a ultima e vao juntos (collectPart). Um nome quase certo (os pontos e hifens
// trocados por "_") ganha uma resposta com o nome certo, sem card (warnBadName).
// Deploy e webhook: tools/telegram-translate/README.md.

const MIN_LETTERS = 4;

function clean(text) {
  return text
    .replace(/https?:\/\/\S+/g, ' ')
    .replace(/@\w+/g, ' ')
    .replace(/[^\p{L}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const NAMES = { pt: 'portuguese', en: 'english', es: 'spanish' };
const FLAGS = { pt: '🇧🇷', en: '🇺🇸', es: '🇪🇸' };

// Palavras que distinguem os tres idiomas; o idioma com mais acertos ganha.
const WORDS = {
  pt: 'não nao você voce está esta estou uma com para por que isso também tambem muito obrigado olá ola são sao tem então entao dos das nos mas pra né ne bom vai fazer',
  en: 'the and you are is with for that this have not what how can will just from your they but was it its do does there hello thanks please',
  es: 'el los las una con para pero que está esta estoy muy gracias hola también tambien porque cómo como qué por favor tengo tiene hay y es son del al más mas',
};
const SETS = Object.fromEntries(Object.entries(WORDS).map(([k, v]) => [k, new Set(v.split(' '))]));

function detect(text) {
  const words = clean(text).toLowerCase().split(' ');
  const score = {};
  for (const k in SETS) score[k] = words.filter(w => SETS[k].has(w)).length;
  // acento exclusivo: ã/õ/ç -> pt, ñ/¿/¡ -> es
  if (/[ãõç]/i.test(text)) score.pt += 2;
  if (/[ñ¿¡]/.test(text)) score.es += 2;
  const [best, second] = Object.entries(score).sort((a, b) => b[1] - a[1]);
  return best[1] > 0 && best[1] > second[1] ? best[0] : '';
}

async function translate(env, text, source, target) {
  const r = await env.AI.run('@cf/meta/m2m100-1.2b', {
    text, source_lang: NAMES[source], target_lang: NAMES[target],
  });
  return r.translated_text;
}

// Um pacote de jogo custom (GAME.fliperos-customgame.zip) mandado ao grupo: o
// worker so avisa o GitHub (repository_dispatch); quem abre o zip e posta no
// topico Files e o workflow Telegram custom game (tools/telegram-customgame.py),
// que roda o tempo que precisar (aqui o limite de CPU e de segundos).
// Segredos: GITHUB_TOKEN (um token com acesso de escrita ao repositorio, so para
// o repository_dispatch) e a variavel GITHUB_REPO (dono/repositorio).
// O que o workflow precisa saber de um arquivo mandado ao grupo (9 campos: o repository_dispatch aceita ate 10).
function fileFields(msg) {
  const doc = msg.document;
  const from = msg.from ? [msg.from.first_name, msg.from.last_name].filter(Boolean).join(' ') : '';
  return {
    chat_id: msg.chat.id,
    chat_username: msg.chat.username || '',
    message_id: msg.message_id,
    thread_id: msg.is_topic_message ? msg.message_thread_id : 0,
    file_id: doc.file_id,
    file_name: doc.file_name,
    file_size: doc.file_size || 0,
    from,
    username: (msg.from && msg.from.username) || '',
  };
}

async function dispatchGithub(env, clientPayload) {
  const r = await fetch('https://api.github.com/repos/' + env.GITHUB_REPO + '/dispatches', {
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + env.GITHUB_TOKEN,
      accept: 'application/vnd.github+json',
      'user-agent': 'fliperos-telegram-bot',
      'content-type': 'application/json',
    },
    body: JSON.stringify({ event_type: 'customgame-zip', client_payload: clientPayload }),
  });
  if (!r.ok) throw new Error('dispatch ' + r.status + ' ' + await r.text());
}

// O nome de um pacote: GAME.fliperos-customgame.zip, exatamente assim (o gabinete nao reconhece outro). Um nome em que algum
// programa de quem mandou trocou os pontos e hifens por "_" ganha uma resposta com o nome certo (warnBadName, mais abaixo).
const PACKAGE_NAME = /\.fliperos-customgame\.zip$/i;

async function dispatchPackage(env, msg) {
  const doc = msg.document;
  if (!doc || !PACKAGE_NAME.test(doc.file_name || '')) return false;
  if (msg.from && msg.from.is_bot) return true;
  if (env.ALLOWED_CHAT && String(msg.chat.id) !== String(env.ALLOWED_CHAT)) return true;
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO) return true;
  await dispatchGithub(env, fileFields(msg));
  return true;
}

// Um pacote maior que o arquivo do plano gratuito do Telegram (2 GB) chega em partes, GAME.fliperos-customgame.zip.001,
// .002... (o painel web as faz). Cada parte vira uma chave no KV (binding PARTS); quando as partes 1..k estao todas aqui e
// a ultima e menor que a primeira (o fim do pacote), quem recebeu a parte que chegou por ultimo chama o GitHub UMA vez, com
// todas em "parts" (o robo trata como um pacote so). Sem o binding PARTS as partes sao ignoradas.
const PART_NAME = /^(.+\.fliperos-customgame\.zip)\.(\d{3})$/i;
const PART_TTL = 172800; // o KV esquece as partes de um pacote que nunca completou, em dois dias

// splitReady: as partes numeradas de 1 a k sem furo (k >= 2) e a ultima menor que a primeira.
function splitReady(parts) {
  const ordered = parts.slice().sort((a, b) => a.n - b.n);
  if (ordered.length < 2 || !ordered.every((p, i) => p.n === i + 1)) return false;
  return ordered[ordered.length - 1].file_size < ordered[0].file_size;
}

async function collectPart(env, msg) {
  const doc = msg.document;
  const name = doc && PART_NAME.exec(doc.file_name || '');
  if (!name) return false;
  if (msg.from && msg.from.is_bot) return true;
  if (env.ALLOWED_CHAT && String(msg.chat.id) !== String(env.ALLOWED_CHAT)) return true;
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO) return true;
  if (!env.PARTS) {
    console.error('split package ' + doc.file_name + ': the KV binding PARTS is missing (tools/telegram-translate/README.md)');
    return true;
  }
  const prefix = 'part:' + msg.chat.id + ':' + ((msg.from && msg.from.id) || 0) + ':' + name[1].toLowerCase() + ':';
  const mine = Object.assign({ n: parseInt(name[2], 10), at: Date.now() }, fileFields(msg));
  await env.PARTS.put(prefix + name[2], JSON.stringify(mine), { expirationTtl: PART_TTL });
  // Duas partes que chegam juntas escrevem quase ao mesmo tempo: espera um pouco para ver tudo o que ja foi escrito.
  await new Promise(resolve => setTimeout(resolve, Number(env.PART_WAIT_MS === undefined ? 3000 : env.PART_WAIT_MS)));
  const listed = await env.PARTS.list({ prefix });
  const parts = [];
  for (const key of listed.keys) {
    const part = await env.PARTS.get(key.name, 'json');
    if (part) parts.push(part);
  }
  if (!splitReady(parts)) return true;
  // So a parte que chegou por ultima chama o GitHub (as outras ja saberiam do conjunto incompleto).
  const last = parts.reduce((a, b) => (b.at > a.at || (b.at === a.at && b.n > a.n) ? b : a));
  if (last.n !== mine.n || last.at !== mine.at) return true;
  const ordered = parts.sort((a, b) => a.n - b.n);
  const first = ordered[0];
  await dispatchGithub(env, {
    chat_id: first.chat_id,
    chat_username: first.chat_username,
    message_id: first.message_id,
    thread_id: first.thread_id,
    file_id: first.file_id,
    file_name: first.file_name,
    file_size: first.file_size,
    from: first.from,
    username: first.username,
    parts: ordered.map(p => ({
      n: p.n, message_id: p.message_id, thread_id: p.thread_id, file_id: p.file_id, file_name: p.file_name, file_size: p.file_size,
    })),
  });
  await Promise.all(listed.keys.map(key => env.PARTS.delete(key.name)));
  return true;
}

// Um nome quase certo: o de um pacote ou de uma parte em que algum programa (o Telegram de quem mandou, o navegador que
// baixou...) trocou os pontos, hifens ou espacos por "_" (COTTOn_fliperos_customgame_zip.002), ou uma parte sem os tres
// digitos (.zip.2). O gabinete nao reconhece esse arquivo (nem o duplo clique, nem o Setup, nem o painel), entao ele nao
// vira card: o robo responde dizendo que o nome esta invalido e como deveria ser, e o pacote sai quando vier com o nome certo.
const LOOSE_NAME = /^(.+?)[._ -]+fliperos[._ -]*customgame[._ -]*zip(?:[._ -]*(\d{1,3}))?$/i;

function rightName(stem, n) {
  return stem + '.fliperos-customgame.zip' + (n === null ? '' : '.' + String(n).padStart(3, '0'));
}

const escapeHtml = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// badNameText: o aviso, nos dois idiomas, com cada nome errado e o certo (o <code> o Telegram copia com um toque).
function badNameText(names) {
  const many = names.length > 1;
  const lines = [
    '🇧🇷 ⚠️ <b>Nome de arquivo inválido.</b> O FliperOS só reconhece ' + (many ? 'as partes do pacote' : 'o pacote') +
      ' com o nome assim: renomeie e mande de novo.',
    '🇺🇸 ⚠️ <b>Invalid file name.</b> FliperOS only recognises ' + (many ? 'the parts of the package' : 'the package') +
      ' named like this: rename ' + (many ? 'them' : 'it') + ' and send ' + (many ? 'them' : 'it') + ' again.',
  ];
  const shown = names.slice(0, 10);
  for (const [wrong, right] of shown) lines.push('', '❌ <code>' + escapeHtml(wrong) + '</code>', '✅ <code>' + escapeHtml(right) + '</code>');
  if (names.length > shown.length) lines.push('', '… +' + (names.length - shown.length));
  return lines.join('\n');
}

async function sendReply(env, msg, text) {
  const body = {
    chat_id: msg.chat.id,
    text,
    parse_mode: 'HTML',
    reply_to_message_id: msg.message_id,
    allow_sending_without_reply: true,
    link_preview_options: { is_disabled: true },
  };
  if (msg.is_topic_message && msg.message_thread_id) body.message_thread_id = msg.message_thread_id;
  const r = await fetch('https://api.telegram.org/bot' + env.TELEGRAM_BOT_TOKEN + '/sendMessage', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('sendMessage ' + r.status + ' ' + await r.text());
}

// As partes de um mesmo pacote com o nome errado ganham UM aviso, com todas as que ja chegaram: cada parte fica no KV (como em
// collectPart) e so a primeira a chegar responde; as que vierem depois (dentro de dois dias) ja foram avisadas. Sem o KV, cada
// parte ganha o seu aviso.
async function warnBadName(env, msg) {
  const doc = msg.document;
  const loose = doc && LOOSE_NAME.exec(doc.file_name || '');
  if (!loose) return false;
  if (msg.from && msg.from.is_bot) return true;
  if (env.ALLOWED_CHAT && String(msg.chat.id) !== String(env.ALLOWED_CHAT)) return true;
  const stem = loose[1];
  const n = loose[2] === undefined ? null : parseInt(loose[2], 10);
  let names = [[doc.file_name, rightName(stem, n)]];
  if (n !== null && env.PARTS) {
    const prefix = 'badname:' + msg.chat.id + ':' + ((msg.from && msg.from.id) || 0) + ':' + stem.toLowerCase() + ':';
    const mine = { n, at: Date.now(), file_name: doc.file_name };
    await env.PARTS.put(prefix + 'p:' + String(n).padStart(3, '0'), JSON.stringify(mine), { expirationTtl: PART_TTL });
    await new Promise(resolve => setTimeout(resolve, Number(env.PART_WAIT_MS === undefined ? 3000 : env.PART_WAIT_MS)));
    if (await env.PARTS.get(prefix + 'warned')) return true;
    const listed = await env.PARTS.list({ prefix: prefix + 'p:' });
    const parts = [];
    for (const key of listed.keys) {
      const part = await env.PARTS.get(key.name, 'json');
      if (part) parts.push(part);
    }
    const first = parts.reduce((a, b) => (b.at < a.at || (b.at === a.at && b.n < a.n) ? b : a), mine);
    if (first.n !== mine.n || first.at !== mine.at) return true;
    await env.PARTS.put(prefix + 'warned', '1', { expirationTtl: PART_TTL });
    names = parts.sort((a, b) => a.n - b.n).map(p => [p.file_name, rightName(stem, p.n)]);
  }
  await sendReply(env, msg, badNameText(names));
  return true;
}

async function handle(env, msg) {
  if (await dispatchPackage(env, msg)) return;
  if (await collectPart(env, msg)) return;
  if (await warnBadName(env, msg)) return;
  const text = msg.text || msg.caption || '';
  if (!text || text.startsWith('/') || (msg.from && msg.from.is_bot)) return;
  if (env.ALLOWED_CHAT && String(msg.chat.id) !== String(env.ALLOWED_CHAT)) return;
  const skip = String(env.SKIP_TOPICS || '').split(',').map(x => x.trim()).filter(Boolean);
  if (msg.is_topic_message && skip.includes(String(msg.message_thread_id))) return;
  if (clean(text).length < MIN_LETTERS) return;

  const src = detect(text);
  if (!src) return;
  const targets = Object.keys(NAMES).filter(l => l !== src);
  const done = await Promise.all(targets.map(l => translate(env, text, src, l)));
  const parts = targets.map((l, i) => FLAGS[l] + ' ' + done[i]);

  const body = {
    chat_id: msg.chat.id,
    text: parts.join('\n\n').slice(0, 4000),
    reply_to_message_id: msg.message_id,
    allow_sending_without_reply: true,
    link_preview_options: { is_disabled: true },
  };
  if (msg.is_topic_message && msg.message_thread_id) body.message_thread_id = msg.message_thread_id;
  const r = await fetch('https://api.telegram.org/bot' + env.TELEGRAM_BOT_TOKEN + '/sendMessage', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('sendMessage ' + r.status + ' ' + await r.text());
}

export default {
  async fetch(request, env, ctx) {
    if (request.method !== 'POST') return new Response('fliperos translate bot');
    if (request.headers.get('x-telegram-bot-api-secret-token') !== env.WEBHOOK_SECRET) {
      return new Response('forbidden', { status: 403 });
    }
    const update = await request.json();
    const msg = update.message || update.edited_message;
    if (msg) ctx.waitUntil(handle(env, msg).catch(e => console.error(String(e))));
    return new Response('ok');
  },
};
