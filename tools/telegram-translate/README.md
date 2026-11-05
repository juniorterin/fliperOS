# Bot tradutor do grupo do Telegram

Responde a cada mensagem do grupo com a tradução: inglês ou espanhol viram
português; português vira inglês e espanhol. Mensagens curtas, só links,
comandos e mensagens de bots são ignoradas. Roda como Cloudflare Worker
(grátis, sempre ligado) e traduz com o Google Cloud Translation.

## Uma vez só

1. Chave do Google: console.cloud.google.com, ative a "Cloud Translation API"
   e crie uma chave de API (restrinja à Translation API).
2. No @BotFather, no mesmo bot que posta as versões: `/setprivacy` > Disable,
   para ele ler todas as mensagens (como administrador do grupo ele já lê).
3. Deploy (precisa de Node e de uma conta Cloudflare):

       cd tools/telegram-translate
       npx wrangler login
       npx wrangler secret put TELEGRAM_BOT_TOKEN
       npx wrangler secret put GOOGLE_API_KEY
       npx wrangler secret put WEBHOOK_SECRET     # texto longo e aleatório
       npx wrangler deploy

4. Aponte o webhook do Telegram para o worker (a URL que o deploy imprimiu):

       curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
         -d url=https://fliperos-telegram-translate.SUBDOMINIO.workers.dev \
         -d secret_token=$WEBHOOK_SECRET \
         -d 'allowed_updates=["message","edited_message"]'

5. Opcional: ponha o id do grupo em `ALLOWED_CHAT` no wrangler.toml e rode
   `npx wrangler deploy` de novo.

Para desligar: `deleteWebhook`. Os posts de versões e updates
(`tools/telegram-post.py`) só usam `sendMessage` e não dependem do webhook.
