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

## Pacotes de jogo custom (o robô do tópico Files)

O mesmo worker avisa o GitHub quando alguém manda um `JOGO.fliperos-customgame.zip`
ao grupo (em qualquer tópico). O workflow **Telegram custom game**
(`.github/workflows/telegram-customgame.yml`, `tools/telegram-customgame.py`) abre o
pacote e posta no tópico **Files/Arquivos** um álbum com a imagem, o logotipo e o
vídeo do jogo, uma mensagem com os dados (modo de vídeo, categoria, ano,
desenvolvedora, jogadores, botões, controles, mapa do controle, `.ppdb`, tamanho) e a
descrição, em português e em inglês, e o próprio arquivo. Um zip mandado no próprio
tópico Files recebe a resposta com os dados, sem repetir o arquivo. Um pacote que não
serve volta com a lista de problemas, no lugar onde foi mandado.

Uma vez só:

1. Um token do GitHub só para isso (fine-grained, repositório `juniorterin/fliperOS`,
   permissão **Contents: Read and write**, que é a que o `repository_dispatch` pede):

       npx wrangler secret put GITHUB_TOKEN

   O repositório é `GITHUB_REPO` no `wrangler.toml`. `npx wrangler deploy` de novo.
2. Nos *secrets* do repositório (Settings > Secrets and variables > Actions):
   `TELEGRAM_BOT_TOKEN` (o do bot do grupo). Na aba *Variables*, se precisar,
   `TELEGRAM_CHAT_ID` (`@fliperos15khz` sem ela) e `TELEGRAM_FILES_TOPIC` (578, o
   número no fim do link do tópico Files).
3. **Pacotes grandes.** Um pacote leva a pasta do jogo inteira e costuma ter centenas
   de MB; a Bot API só entrega arquivos de até 20 MB. Para ler os maiores, crie um
   *api_id* e um *api_hash* em https://my.telegram.org e ponha os dois nos secrets
   `TELEGRAM_API_ID` e `TELEGRAM_API_HASH`: o robô entra como bot pelo MTProto
   (Telethon) e lê só o fim do zip e os arquivos pequenos (cfg, imagem, vídeo, texto),
   sem baixar o jogo. Sem eles, o post sai com o arquivo e o aviso de que os detalhes
   não deram para ler.
4. O bot precisa ser administrador do grupo (ou ter o `/setprivacy` desligado) para ver
   os arquivos mandados, como já precisa para a tradução.

Rodar à mão: *Actions > Telegram custom game > Run workflow*, com o JSON do pedido
(`chat_id`, `message_id`, `file_id`, `file_name`, `file_size`…). Para ver o post de
um zip do disco sem rede: `python3 tools/telegram-customgame.py --zip JOGO.fliperos-customgame.zip --out pasta`.

Para desligar: `deleteWebhook`. Os posts de versões e updates
(`tools/telegram-post.py`) só usam `sendMessage` e não dependem do webhook.
