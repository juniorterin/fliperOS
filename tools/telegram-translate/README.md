# Bot tradutor do grupo do Telegram

Responde a cada mensagem do grupo com a tradução para os outros dois idiomas:
português vira inglês e espanhol, inglês vira português e espanhol, espanhol
vira português e inglês. Mensagens curtas, só links,
comandos e mensagens de bots são ignoradas. Roda como Cloudflare Worker
(grátis, sempre ligado) e traduz com o Workers AI.

## Uma vez só

1. Nada a contratar: a tradução usa o Workers AI (modelo m2m100) da própria
   conta Cloudflare, dentro da cota gratuita. O idioma é detectado por
   palavras comuns; mensagem ambígua fica sem tradução.
2. No @BotFather, no mesmo bot que posta as versões: `/setprivacy` > Disable,
   para ele ler todas as mensagens (como administrador do grupo ele já lê).
3. Deploy (precisa de Node e de uma conta Cloudflare):

       cd tools/telegram-translate
       npx wrangler login
       npx wrangler secret put TELEGRAM_BOT_TOKEN
       npx wrangler secret put WEBHOOK_SECRET     # texto longo e aleatório
       npx wrangler deploy

4. Aponte o webhook do Telegram para o worker (a URL que o deploy imprimiu):

       curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
         -d url=https://fliperos-telegram-translate.SUBDOMINIO.workers.dev \
         -d secret_token=$WEBHOOK_SECRET \
         -d 'allowed_updates=["message","edited_message"]'

5. Opcional: ponha o id do grupo em `ALLOWED_CHAT` no wrangler.toml e rode
   `npx wrangler deploy` de novo.

Para um tópico ficar sem tradução (como Files/Arquivos), ponha o número do
fim do link dele (`t.me/fliperos15khz/NUMERO`) em `SKIP_TOPICS` no
wrangler.toml, separado por vírgula, e rode `npx wrangler deploy`.

Para desligar: `deleteWebhook`. Os posts de versões e updates
(`tools/telegram-post.py`) só usam `sendMessage` e não dependem do webhook.
