// Bot tradutor do grupo do Telegram (t.me/fliperos15khz), Cloudflare Worker.
// O Telegram chama este worker por webhook a cada mensagem do grupo; o worker
// traduz com o Google Cloud Translation e responde na mensagem original:
//   ingles ou espanhol -> portugues;  portugues -> ingles e espanhol.
// Segredos: TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY, WEBHOOK_SECRET.
// Variavel opcional: ALLOWED_CHAT (id numerico do grupo; sem ela, qualquer chat).
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

async function translate(env, text, target) {
  const r = await fetch(
    'https://translation.googleapis.com/language/translate/v2?key=' + env.GOOGLE_API_KEY,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ q: text, target, format: 'text' }),
    });
  if (!r.ok) throw new Error('translate ' + r.status + ' ' + await r.text());
  const t = (await r.json()).data.translations[0];
  return { text: t.translatedText, source: (t.detectedSourceLanguage || '').split('-')[0] };
}

async function handle(env, msg) {
  const text = msg.text || msg.caption || '';
  if (!text || text.startsWith('/') || (msg.from && msg.from.is_bot)) return;
  if (env.ALLOWED_CHAT && String(msg.chat.id) !== String(env.ALLOWED_CHAT)) return;
  if (clean(text).length < MIN_LETTERS) return;

  const pt = await translate(env, text, 'pt');
  const parts = [];
  if (pt.source === 'pt') {
    const [en, es] = await Promise.all([translate(env, text, 'en'), translate(env, text, 'es')]);
    parts.push('🇺🇸 ' + en.text, '🇪🇸 ' + es.text);
  } else if (pt.source === 'en' || pt.source === 'es') {
    parts.push('🇧🇷 ' + pt.text);
  }
  if (!parts.length) return;

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
