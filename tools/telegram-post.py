#!/usr/bin/env python3
"""Posta no grupo do Telegram (t.me/fliperos15khz) o texto de uma versao: fotos
e a explicacao de como funciona cada novidade.

    python3 tools/telegram-post.py VERSAO              posta docs/telegram/VERSAO.md
    python3 tools/telegram-post.py --dry-run VERSAO    so confere o arquivo e as imagens, sem rede nem token

O CHANGELOG.md e a lista tecnica do release do GitHub; o docs/telegram/VERSAO.md
e o que o grupo le: escrito para quem usa o gabinete, com uma foto por novidade.
Cada release novo escreve o seu antes da tag (o workflow Release confere).

O arquivo e uma lista de mensagens separadas por uma linha so com "---". Dentro
de cada uma, "![](caminho)" poe uma imagem (o caminho parte da raiz do
repositorio; WebP animado e GIF vao como animacao, em MP4 se houver ffmpeg) e o resto e o texto, com
**negrito**, `codigo`, [links](https://...) e listas com "- ". Com imagem, o
texto vai na legenda dela (ate 1024 caracteres; maior que isso, vai antes, como
mensagem). Sem imagem, e uma mensagem de texto (ate 4096).

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
        text = markup(re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip())
        if not text and not images:
            continue
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


def main():
    parser = argparse.ArgumentParser(description='Post a release to the FliperOS Telegram group')
    parser.add_argument('version')
    parser.add_argument('--dry-run', action='store_true', help='check the file and the images, send nothing')
    args = parser.parse_args()
    source = POSTS / ('%s.md' % args.version)
    try:
        if not source.is_file():
            raise PostError('%s does not exist: write what to tell the group about %s before publishing it'
                            % (source.relative_to(ROOT), args.version))
        messages = parse(source.read_text(encoding='utf-8'))
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
