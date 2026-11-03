#!/usr/bin/env python3
"""Posta no grupo do Telegram (t.me/fliperos15khz) o texto de uma versao: fotos
e a explicacao de como funciona cada novidade.

    python3 tools/telegram-post.py VERSAO              posta docs/telegram/VERSAO.md, ou a secao do CHANGELOG.md se nao houver
    python3 tools/telegram-post.py --changelog VERSAO  posta a secao do CHANGELOG.md mesmo havendo o arquivo
    python3 tools/telegram-post.py --backfill          posta todas as versoes do CHANGELOG.md, da mais velha para a mais nova
    python3 tools/telegram-post.py --update N          posta o update N (docs/telegram/update-NNNN.md, ou o titulo e as notas em updates/notes/pt-BR/NNNN.md e NNNN.md)
    python3 tools/telegram-post.py --dry-run ...       so confere o texto e as imagens, sem rede nem token

O CHANGELOG.md e a lista tecnica do release do GitHub, e o grupo pode le-la como
esta (sem fotos). O docs/telegram/VERSAO.md, quando existe, vai no lugar dela:
as novidades contadas uma a uma, com uma foto cada.

O arquivo e uma lista de mensagens separadas por uma linha so com "---". Dentro
de cada uma, "![](caminho)" poe uma imagem (o caminho parte da raiz do
repositorio; WebP animado e GIF vao como animacao, em MP4 se houver ffmpeg) e o resto e o texto, com
**negrito**, `codigo`, [links](https://...) e listas com "- ". Com imagem, o
texto vai na legenda dela (ate 1024 caracteres; maior que isso, vai antes, como
mensagem). Sem imagem, e uma mensagem de texto (ate 4096).

Toda mensagem vai em portugues e em ingles: o texto de cada uma tem uma parte
que comeca com uma linha "🇧🇷 ..." e outra com uma linha "🇺🇸 ...". Sem as
duas, o arquivo e recusado antes de postar.

Precisa de TELEGRAM_BOT_TOKEN (o bot do @BotFather, administrador do grupo) no
ambiente; o destino e TELEGRAM_CHAT_ID, e na falta dele, @fliperos15khz.
As imagens passam pelo Pillow (python3 -m pip install pillow): a parada vira
PNG, a animada vira GIF e, com o ffmpeg, MP4.
"""
import argparse
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / 'docs' / 'telegram'
DEFAULT_CHAT = '@fliperos15khz'
API = 'https://api.telegram.org/bot%s/%s'
CAPTION_MAX = 1024
TEXT_MAX = 4096
# O grupo aceita 20 mensagens por minuto; folga de sobra.
PAUSE = 4.0
IMAGE = re.compile(r'^!\[[^\]]*\]\(([^)\s]+)\)\s*$')
PT, EN = '🇧🇷', '🇺🇸'


class PostError(Exception):
    pass


def markup(text):
    """Markdown simples para o HTML do Telegram."""
    out = html.escape(text, quote=False)
    spans = []

    def keep(match):
        spans.append('<code>%s</code>' % match.group(1))
        return '\0%d\0' % (len(spans) - 1)

    out = re.sub(r'`([^`\n]+)`', keep, out)
    out = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', out)
    out = re.sub(r'\[([^\]\n]+)\]\((https?://[^)\s]+)\)',
                 lambda m: '<a href="%s">%s</a>' % (m.group(2).replace('"', '&quot;'), m.group(1)), out)
    out = re.sub(r'(?m)^[-*] ', '• ', out)
    return re.sub(r'\0(\d+)\0', lambda m: spans[int(m.group(1))], out)


def visible(text_html):
    return len(html.unescape(re.sub(r'<[^>]+>', '', text_html)))


def bilingual(text):
    """O texto tem a parte em portugues e a em ingles."""
    starts = [line.lstrip()[:2] for line in text.splitlines()]
    return PT in starts and EN in starts


def parse(source):
    """As mensagens do arquivo: [{'text': html, 'images': [Path]}]."""
    messages = []
    for block in re.split(r'(?m)^---\s*$', source):
        images, lines = [], []
        for line in block.strip().splitlines():
            found = IMAGE.match(line.strip())
            if found:
                path = (ROOT / found.group(1)).resolve()
                if ROOT not in path.parents or not path.is_file():
                    raise PostError('image not found in the repository: %s' % found.group(1))
                images.append(path)
            else:
                lines.append(line)
        raw = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
        text = markup(raw)
        if not text and not images:
            continue
        if text and not bilingual(raw):
            raise PostError('every message is in Portuguese and English (a "%s" line and a "%s" line): %.40s...'
                            % (PT, EN, raw))
        if visible(text) > TEXT_MAX:
            raise PostError('a message has %d characters, Telegram takes up to %d: %.40s...'
                            % (visible(text), TEXT_MAX, html.unescape(re.sub(r'<[^>]+>', '', text))))
        messages.append({'text': text, 'images': images})
    if not messages:
        raise PostError('the file has no message')
    return messages


def video(gif, width):
    """O GIF como MP4 sem som, ampliado sem suavizar (as capturas sao de 320x240):
    o Telegram toca como animacao e fica uma fracao do tamanho. Sem ffmpeg, None."""
    if not shutil.which('ffmpeg'):
        return None
    target = gif.with_suffix('.mp4')
    scale = max(1, 640 // width)
    result = subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-i', str(gif), '-an', '-movflags', 'faststart', '-pix_fmt', 'yuv420p',
         '-vf', 'scale=iw*%d:ih*%d:flags=neighbor,pad=ceil(iw/2)*2:ceil(ih/2)*2' % (scale, scale), str(target)],
        capture_output=True, text=True)
    return target if result.returncode == 0 and target.is_file() else None


def prepare(path, folder):
    """A imagem como o Telegram aceita: foto PNG, ou GIF se for animada."""
    from PIL import Image, ImageSequence
    with Image.open(path) as image:
        if getattr(image, 'n_frames', 1) > 1:
            frames, durations = [], []
            for frame in ImageSequence.Iterator(image):
                durations.append(frame.info.get('duration', 80) or 80)
                frames.append(frame.convert('RGB'))
            target = folder / (path.stem + '.gif')
            frames[0].save(target, save_all=True, append_images=frames[1:], duration=durations, loop=0)
            target = video(target, image.width) or target
            kind = 'animation'
        else:
            target = folder / (path.stem + '.png')
            image.convert('RGB').save(target)
            kind = 'photo'
    limit = 50 if kind == 'animation' else 10
    if target.stat().st_size > limit * 1024 * 1024:
        raise PostError('%s is over Telegram\'s %d MB' % (path.name, limit))
    return kind, target


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode())
    for name, path in files.items():
        body.write(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
                    'Content-Type: application/octet-stream\r\n\r\n' % (boundary, name, path.name)).encode())
        body.write(path.read_bytes())
        body.write(b'\r\n')
    body.write(('--%s--\r\n' % boundary).encode())
    return body.getvalue(), 'multipart/form-data; boundary=' + boundary


def call(token, method, fields, files=None):
    body, content_type = multipart(fields, files or {})
    for attempt in range(5):
        request = urllib.request.Request(API % (token, method), body, {'Content-Type': content_type})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            answer = json.loads(error.read() or b'{}')
            if error.code == 429:
                time.sleep(answer.get('parameters', {}).get('retry_after', 10) + 1)
                continue
            # A mensagem do Telegram, nunca o endereco (ele leva o token).
            raise PostError('Telegram refused %s: %s' % (method, answer.get('description', error.code))) from None
        except urllib.error.URLError as error:
            if attempt == 4:
                raise PostError('Telegram not reachable on %s: %s' % (method, error.reason)) from None
            time.sleep(5)
    raise PostError('Telegram kept answering "too many requests" on %s' % method)


def send(token, chat, messages, folder):
    calls = 0

    def post(method, fields, files=None):
        nonlocal calls
        if calls:
            time.sleep(PAUSE)
        calls += 1
        call(token, method, dict(fields, chat_id=chat), files)

    for message in messages:
        text, pictures = message['text'], [prepare(p, folder) for p in message['images']]
        caption_fits = bool(text) and visible(text) <= CAPTION_MAX
        if text and not (pictures and caption_fits):
            post('sendMessage', {'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': 'true'})
        for number, (kind, path) in enumerate(pictures):
            fields = {'caption': text, 'parse_mode': 'HTML'} if number == 0 and caption_fits else {}
            post('sendPhoto' if kind == 'photo' else 'sendAnimation', fields, {kind: path})


RELEASES = 'https://github.com/juniorterin/fliperOS/releases/tag/'


def changelog_versions():
    """As versoes do CHANGELOG.md, da mais nova para a mais velha."""
    return re.findall(r'(?m)^## (\S+)$', (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8'))


def changelog_messages(version):
    """A secao do CHANGELOG.md da versao, em mensagens de ate 4096 caracteres,
    cortadas nos limites de linha (sem fotos: e a lista tecnica do release)."""
    text = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    found = re.search(r'(?ms)^## %s\n(.*?)(?=^## |\Z)' % re.escape(version), text)
    if not found or not found.group(1).strip():
        raise PostError('CHANGELOG.md has no "## %s" section' % version)
    # A lista tecnica e so em ingles; o cabecalho diz isso nos dois idiomas.
    head = ('%s **FliperOS %s**: a lista de mudanças do release, em inglês ([no GitHub](%s%s))\n'
            '%s **FliperOS %s**: the release changelog ([on GitHub](%s%s))\n\n'
            % (PT, version, RELEASES, version, EN, version, RELEASES, version))
    chunks, current = [], head
    for line in found.group(1).strip().splitlines():
        if current.strip() and visible(markup(current + line + '\n')) > TEXT_MAX - 50 and current != head:
            chunks.append(current.strip())
            current = ''
        current += line + '\n'
    chunks.append(current.strip())
    messages = []
    for chunk in chunks:
        chunk = re.sub(r'\n{3,}', '\n\n', chunk)
        rendered = markup(chunk)
        if visible(rendered) > TEXT_MAX:
            raise PostError('a line of the %s section is over %d characters' % (version, TEXT_MAX))
        messages.append({'text': rendered, 'images': []})
    return messages


def messages_for(version, changelog_only):
    """O docs/telegram/VERSAO.md (com fotos), ou o CHANGELOG.md da versao."""
    source = POSTS / ('%s.md' % version)
    if changelog_only or not source.is_file():
        return changelog_messages(version)
    return parse(source.read_text(encoding='utf-8'))


UPDATES = ROOT / 'updates'


def update_messages(number):
    """O texto do update N (o que chega pela rede, sem ISO nova): o
    docs/telegram/update-NNNN.md (com fotos), ou as notas nos dois idiomas:
    updates/notes/pt-BR/NNNN.md e o updates/notes/NNNN.md (o mesmo changelog
    que o gabinete mostra) com o titulo do updates/index. Numa mensagem
    quando cabem, senao uma por idioma."""
    name = '%04d' % number
    source = POSTS / ('update-%s.md' % name)
    if source.is_file():
        return parse(source.read_text(encoding='utf-8'))
    title = None
    for line in (UPDATES / 'index').read_text(encoding='utf-8').splitlines():
        fields = line.split('\t')
        if len(fields) >= 5 and fields[0] == str(number):
            title = fields[4]
    if title is None:
        raise PostError('updates/index has no update %d' % number)
    notes = []
    for path in ('notes/pt-BR/%s.md' % name, 'notes/%s.md' % name):
        if not (UPDATES / path).is_file():
            raise PostError('updates/%s does not exist' % path)
        notes.append((UPDATES / path).read_text(encoding='utf-8').strip())
    parts = ['%s **Atualização %d do FliperOS**\n\n%s\n\nQuem já tem o FliperOS instalado recebe pela '
             'atualização do próprio Setup, sem ISO nova.' % (PT, number, notes[0]),
             '%s **FliperOS update %d:** %s\n\n%s\n\nInstalled cabinets get it from the Setup\'s own update, '
             'no new ISO.' % (EN, number, title, notes[1])]
    together, *apart = [markup(re.sub(r'\n{3,}', '\n\n', part)) for part in ['\n\n'.join(parts)] + parts]
    if visible(together) <= TEXT_MAX:
        return [{'text': together, 'images': []}]
    for text in apart:
        if visible(text) > TEXT_MAX:
            raise PostError('update %d has %d characters in one language, Telegram takes up to %d: '
                            'write docs/telegram/update-%s.md' % (number, visible(text), TEXT_MAX, name))
    return [{'text': text, 'images': []} for text in apart]


def main():
    parser = argparse.ArgumentParser(description='Post a release to the FliperOS Telegram group')
    parser.add_argument('version', nargs='?')
    parser.add_argument('--dry-run', action='store_true', help='check the file and the images, send nothing')
    parser.add_argument('--changelog', action='store_true',
                        help='post the CHANGELOG.md section even when docs/telegram has a text for the version')
    parser.add_argument('--backfill', action='store_true',
                        help='post every version of the CHANGELOG.md, oldest first (docs/telegram text when it exists)')
    parser.add_argument('--update', type=int, action='append', metavar='N',
                        help='post update N of updates/index (docs/telegram/update-NNNN.md or its notes); repeatable')
    args = parser.parse_args()
    try:
        if args.update:
            messages = [m for number in args.update for m in update_messages(number)]
        elif args.backfill:
            messages = [m for version in reversed(changelog_versions()) for m in messages_for(version, False)]
        elif args.version:
            messages = messages_for(args.version, args.changelog)
        else:
            parser.error('a version, --update or --backfill')
        with tempfile.TemporaryDirectory() as folder:
            if args.dry_run:
                for number, message in enumerate(messages, 1):
                    pictures = [prepare(p, Path(folder)) for p in message['images']]
                    print('%2d. %4d characters, %s' % (
                        number, visible(message['text']),
                        ', '.join('%s %s (%d KB)' % (kind, path.name, path.stat().st_size // 1024)
                                  for kind, path in pictures) or 'text only'))
                print('%d messages ok' % len(messages))
                return 0
            token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
            if not token:
                raise PostError('TELEGRAM_BOT_TOKEN is not set')
            chat = os.environ.get('TELEGRAM_CHAT_ID') or DEFAULT_CHAT
            send(token, chat, messages, Path(folder))
            print('%d messages posted to %s' % (len(messages), chat))
    except PostError as error:
        print('telegram-post: %s' % error, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
