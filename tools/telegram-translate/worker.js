// Bot tradutor do grupo do Telegram (t.me/fliperos15khz), Cloudflare Worker.
// O Telegram chama este worker por webhook a cada mensagem do grupo; o worker
// traduz com o Workers AI (m2m100, gratis no plano free) e responde na mensagem:
//   cada mensagem vai para os outros dois idiomas (pt, en, es).
// Segredos: TELEGRAM_BOT_TOKEN, WEBHOOK_SECRET. Binding AI no wrangler.toml.
// Variavel opcional: ALLOWED_CHAT (id numerico do grupo; sem ela, qualquer chat).
// SKIP_TOPICS: topicos sem traducao (o numero no fim do link do topico,
// t.me/fliperos15khz/NUMERO), separados por virgula.
// Pacotes de jogo custom (.fliperos-customgame.zip): vao ao GitHub, que posta os
// dados no topico Files (dispatchPackage, mais abaixo).
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
async function dispatchPackage(env, msg) {
  const doc = msg.document;
  if (!doc || !/\.fliperos-customgame\.zip$/i.test(doc.file_name || '')) return false;
  if (msg.from && msg.from.is_bot) return true;
  if (env.ALLOWED_CHAT && String(msg.chat.id) !== String(env.ALLOWED_CHAT)) return true;
  if (!env.GITHUB_TOKEN || !env.GITHUB_REPO) return true;
  const from = msg.from ? [msg.from.first_name, msg.from.last_name].filter(Boolean).join(' ') : '';
  const r = await fetch('https://api.github.com/repos/' + env.GITHUB_REPO + '/dispatches', {
    method: 'POST',
    headers: {
      authorization: 'Bearer ' + env.GITHUB_TOKEN,
      accept: 'application/vnd.github+json',
      'user-agent': 'fliperos-telegram-bot',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      event_type: 'customgame-zip',
      client_payload: {
        chat_id: msg.chat.id,
        chat_username: msg.chat.username || '',
        message_id: msg.message_id,
        thread_id: msg.is_topic_message ? msg.message_thread_id : 0,
        file_id: doc.file_id,
        file_name: doc.file_name,
        file_size: doc.file_size || 0,
        from,
        username: (msg.from && msg.from.username) || '',
      },
    }),
  });
  if (!r.ok) throw new Error('dispatch ' + r.status + ' ' + await r.text());
  return true;
}

async function handle(env, msg) {
  if (await dispatchPackage(env, msg)) return;
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
