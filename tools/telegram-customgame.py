#!/usr/bin/env python3
"""O robo dos pacotes de jogo custom no grupo do Telegram (t.me/fliperos15khz).

Quando alguem manda um GAME.fliperos-customgame.zip ao grupo, o robo abre o
pacote, le o que ele diz (o GAME.cfg, a imagem, o logotipo, o video, o texto, o
mapa do controle) e faz um post no topico Files/Arquivos: as imagens e o video
juntos, os dados todos em portugues e em ingles, a descricao e o proprio arquivo.

    python3 tools/telegram-customgame.py --zip GAME.fliperos-customgame.zip [--out PASTA]
        so mostra o post que sairia (o texto, e as imagens salvas em PASTA); sem rede
    python3 tools/telegram-customgame.py --payload-env PAYLOAD [--dry-run]
        o que o workflow Telegram custom game faz: PAYLOAD e um JSON com chat_id,
        message_id, thread_id, file_id, file_name, file_size, from, username e
        chat_username, o que o Worker (tools/telegram-translate/worker.js) manda

Como o robo le o pacote (um pacote leva a pasta do jogo inteira: costuma ter
centenas de MB):
  - ate 20 MB, pela Bot API (getFile), baixando o arquivo;
  - acima disso a Bot API nao entrega o arquivo. Com TELEGRAM_API_ID e
    TELEGRAM_API_HASH (de https://my.telegram.org) o robo entra como bot pelo
    MTProto (pip install telethon) e le so os pedacos que precisa: o fim do zip
    (a lista de arquivos) e os poucos arquivos pequenos do pacote (cfg, imagem,
    video, texto), nunca a pasta do jogo (RangeFile);
  - sem isso, o post sai assim mesmo, com o nome e o tamanho e o arquivo, e um
    aviso de que os detalhes nao deu para ler.
O arquivo vai ao topico por file_id (o Telegram reenvia o que ja tem, sem limite
de tamanho). Se o zip ja foi mandado no proprio topico Files, o robo responde a
ele com os dados, sem repetir o arquivo.

Variaveis: TELEGRAM_BOT_TOKEN (o bot do grupo), TELEGRAM_CHAT_ID (o grupo, se
quiser conferir; @fliperos15khz sem ela), TELEGRAM_FILES_TOPIC (o numero no fim
do link do topico, t.me/fliperos15khz/NUMERO; 578), TELEGRAM_API_ID,
TELEGRAM_API_HASH. Toda mensagem vai em portugues e em ingles."""
import argparse
import base64
import collections
import html
import importlib.util
import inspect
import io
import json
import os
import re
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / 'config' / 'fliperos-customgame'
SUFFIX = '.fliperos-customgame.zip'
DEFAULT_CHAT = '@fliperos15khz'
FILES_TOPIC = 578
API = 'https://api.telegram.org/bot%s/%s'
FILE_API = 'https://api.telegram.org/file/bot%s/%s'
BOT_DOWNLOAD_MAX = 20 << 20      # o que a Bot API entrega (getFile)
PHOTO_MAX = 10 << 20             # o que o sendPhoto aceita
VIDEO_MAX = 50 << 20             # o que o sendVideo aceita
TEXT_FILE_MAX = 1 << 20
CAPTION_MAX = 1024
TEXT_MAX = 4096
DESCRIPTION_MAX = 1800
PT, EN = '\U0001F1E7\U0001F1F7', '\U0001F1FA\U0001F1F8'
BLOCK = 512 * 1024               # o pedaco que o MTProto entrega de cada vez (multiplo de 4096, divide 1 MB)


class PostError(Exception):
    pass


def load_tool():
    """O fliperos-customgame (config/fliperos-customgame): quem confere um pacote."""
    loader = SourceFileLoader('fliperos_customgame_tool', str(TOOL))
    spec = importlib.util.spec_from_loader('fliperos_customgame_tool', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# ── Ler um zip por pedacos ──

class RangeFile(io.RawIOBase):
    """Um arquivo que so se le por pedacos (fetch(offset, length) devolve os bytes
    de um intervalo): o suficiente para o zipfile abrir um zip de 2 GB lendo o fim
    dele (a lista de arquivos) e os poucos arquivos pequenos que o robo quer. Os
    pedacos lidos ficam guardados (os ultimos `keep`); fetched conta os bytes que
    vieram da rede."""

    def __init__(self, size, fetch, block=BLOCK, keep=48):
        super().__init__()
        self.size, self.fetch, self.block, self.keep = size, fetch, block, keep
        self.pos = 0
        self.cache = collections.OrderedDict()
        self.fetched = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = max(0, base + offset)
        return self.pos

    def _block(self, number):
        data = self.cache.get(number)
        if data is None:
            start = number * self.block
            data = self.fetch(start, min(self.block, self.size - start))
            self.fetched += len(data)
            self.cache[number] = data
            while len(self.cache) > self.keep:
                self.cache.popitem(last=False)
        else:
            self.cache.move_to_end(number)
        return data

    def read(self, n=-1):
        end = self.size if n is None or n < 0 else min(self.size, self.pos + n)
        out = []
        while self.pos < end:
            number, inside = divmod(self.pos, self.block)
            data = self._block(number)
            take = data[inside:inside + (end - self.pos)]
            if not take:
                break
            out.append(take)
            self.pos += len(take)
        return b''.join(out)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)


# ── O que o pacote diz ──

def mode_label(tool, mode):
    """240p, 240p hack (Mugen), 480i, ou o proprio modo."""
    names = {v: k for k, v in tool.MODES.items()}
    label = names.get(mode, mode)
    return '240p hack (Mugen)' if label == '240p-hack' else label


def read_info(tool, package):
    """Tudo o que o post conta de um tool.Package: o cfg, o mapa do controle, o
    .ppdb, o texto e os arquivos de arte (os dados da imagem, do logotipo e do
    video, se cabem no que o Telegram aceita)."""
    cfg = package.cfg
    info = {'name': cfg['name'], 'platform': cfg['platform'], 'mode': mode_label(tool, cfg.get('mode', '')),
            'category': cfg.get('category', ''), 'year': cfg.get('year', ''), 'developer': cfg.get('developer', ''),
            'players': cfg.get('players', ''), 'buttons': cfg.get('buttons', ''), 'controls': cfg.get('controls', ''),
            'runner': cfg.get('runner') or tool.DEFAULT_RUNNER, 'game_bytes': package.bytes, 'files': len(package.files),
            'key': None, 'ppdb': 'ppdb' in package.extra, 'text': '', 'art': {}, 'skipped': []}
    if 'key' in package.extra:
        info['key'] = tool.key_lines(package.read('key').decode('utf-8', 'replace'))
    if 'texto' in package.extra and package.extra['texto'][0].file_size <= TEXT_FILE_MAX:
        info['text'] = package.read('texto').decode('utf-8', 'replace').strip()
    for kind, limit in (('snap', PHOTO_MAX), ('logo', PHOTO_MAX), ('preview', VIDEO_MAX)):
        if kind not in package.extra:
            continue
        member, ext = package.extra[kind]
        if member.file_size > limit * (3 if kind != 'preview' else 1):
            info['skipped'].append(kind)
            continue
        info['art'][kind] = (ext, package.zf.read(member))
    return info


def photo_bytes(data, ext):
    """A imagem como o sendPhoto a quer (ate 10 MB, lados somando ate 10000): com
    o Pillow, uma que passa disso volta menor, e uma com transparencia sai em PNG;
    sem ele, a de ate 10 MB vai como veio. None: nao deu."""
    try:
        from PIL import Image
    except ImportError:
        return data if len(data) <= PHOTO_MAX and ext in ('png', 'jpg', 'jpeg') else None
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:
        return None
    if len(data) <= PHOTO_MAX and ext in ('png', 'jpg', 'jpeg') and sum(image.size) <= 9000:
        return data
    image.thumbnail((2560, 2560))
    out = io.BytesIO()
    if image.mode in ('RGBA', 'LA', 'P'):
        image.convert('RGBA').save(out, 'PNG')
    else:
        image.convert('RGB').save(out, 'JPEG', quality=90)
    return out.getvalue() if out.tell() <= PHOTO_MAX else None


# ── O texto do post (portugues e ingles) ──

PLATFORMS = {'windows': ('Windows', 'Windows'), 'native': ('Linux', 'Linux')}
LABELS = {
    'pt': {'kind': 'Pacote de jogo custom do FliperOS', 'mode': 'Modo de vídeo', 'category': 'Categoria', 'year': 'Ano',
           'developer': 'Desenvolvedora', 'players': 'Jogadores', 'buttons': 'Botões', 'controls': 'Controles',
           'key': 'Mapa do controle (.key)', 'key_yes': 'sim, %d teclas', 'key_joystick': 'o jogo já aceita o joystick (mapa vazio)',
           'key_no': 'não (o menu na tela pede ao abrir)', 'ppdb': 'PortProton (.ppdb)', 'yes': 'sim', 'no': 'não',
           'runner': 'Abre com', 'size': 'Tamanho do jogo', 'size_files': '%s em %d arquivos', 'art': 'Arte', 'art_none': 'nenhuma (ganha de exemplo)',
           'snap': 'imagem', 'logo': 'logotipo', 'preview': 'vídeo', 'text': 'texto', 'description': 'Descrição',
           'by': 'Enviado por', 'install': 'Para instalar: painel web > Jogos custom > Jogos, solte o .zip (ele se instala sozinho), '
                                           'ou ponha na pasta ~/roms/custom-packages do gabinete.',
           'unreadable': 'Não deu para ler os detalhes: o arquivo é grande demais para o robô abrir. O arquivo está aqui.',
           'bad': 'Este arquivo não é um pacote que o FliperOS aceita', 'skipped': 'grande demais para o Telegram',
           'see': 'Os dados e o arquivo estão no tópico Arquivos'},
    'en': {'kind': 'FliperOS custom game package', 'mode': 'Video mode', 'category': 'Category', 'year': 'Year',
           'developer': 'Developer', 'players': 'Players', 'buttons': 'Buttons', 'controls': 'Controls',
           'key': 'Controller key map (.key)', 'key_yes': 'yes, %d keys', 'key_joystick': 'the game already works with the joystick (empty map)',
           'key_no': 'no (the on-screen menu asks when it opens)', 'ppdb': 'PortProton (.ppdb)', 'yes': 'yes', 'no': 'no',
           'runner': 'Runs with', 'size': 'Game size', 'size_files': '%s in %d files', 'art': 'Art', 'art_none': 'none (samples are made)',
           'snap': 'picture', 'logo': 'logo', 'preview': 'video', 'text': 'text', 'description': 'Description',
           'by': 'Sent by', 'install': 'To install: web panel > Custom games > Games, drop the .zip (it installs by itself), '
                                       'or put it in ~/roms/custom-packages on the cabinet.',
           'unreadable': 'The details could not be read: the file is too big for the bot to open. The file is here.',
           'bad': 'This file is not a package FliperOS accepts', 'skipped': 'too big for Telegram',
           'see': 'The details and the file are in the Files topic'},
}
RUNNERS = {'portproton': 'PortProton', 'wine': 'Wine', 'wine-staging': 'Wine Staging'}


def size_text(n):
    n = float(n)
    for unit in ('B', 'KB', 'MB'):
        if n < 1024:
            return ('%d %s' % (n, unit)) if unit == 'B' else '%.1f %s' % (n, unit)
        n /= 1024
    return '%.2f GB' % n


def e(text):
    return html.escape(str(text), quote=False)


def facts(info, lang):
    """As linhas "rotulo: valor" do pacote, num idioma."""
    t = LABELS[lang]
    out = [(t['mode'], e(info['mode'])), (t['runner'], e(RUNNERS.get(info['runner'], info['runner'])) if info['platform'] == 'windows'
                                           else 'Linux')]
    if info['category']:
        out.append((t['category'], e(info['category'])))
    if info['year'] or info['developer']:
        out.append((t['year'], e(info['year'] or '-')))
        out.append((t['developer'], e(info['developer'] or '-')))
    for key in ('players', 'buttons'):
        if info[key]:
            out.append((t[key], e(info[key])))
    if info['controls']:
        out.append((t['controls'], e(info['controls'].replace(',', ', '))))
    if info['key'] is None:
        out.append((t['key'], t['key_no']))
    elif not info['key']:
        out.append((t['key'], t['key_joystick']))
    else:
        out.append((t['key'], t['key_yes'] % len(info['key'])))
    if info['platform'] == 'windows':
        out.append((t['ppdb'], t['yes'] if info['ppdb'] else t['no']))
    out.append((t['size'], t['size_files'] % (size_text(info['game_bytes']), info['files'])))
    art = [t[k] for k in ('snap', 'logo', 'preview') if k in info['art']] + ([t['text']] if info['text'] else [])
    art += ['%s (%s)' % (t[k], t['skipped']) for k in info['skipped']]
    out.append((t['art'], e(', '.join(art)) if art else t['art_none']))
    return out


def caption(info, sender):
    """A legenda do album (ate 1024): o nome e uma linha por idioma."""
    plat = PLATFORMS.get(info['platform'], ('', ''))
    lines = ['\U0001F4E6 <b>%s</b>' % e(info['name'])]
    for flag, lang, platform in ((PT, 'pt', plat[0]), (EN, 'en', plat[1])):
        bits = [platform, info['mode'], info['category'], ' '.join(x for x in (info['year'], info['developer']) if x)]
        lines.append('%s %s · %s' % (flag, LABELS[lang]['kind'], e(' · '.join(b for b in bits if b))))
    if sender:
        lines.append('%s / %s: %s' % (LABELS['pt']['by'], LABELS['en']['by'], e(sender)))
    return '\n'.join(lines)[:CAPTION_MAX]


def details(info, sender):
    """A mensagem com todos os dados, em portugues e em ingles, e a descricao."""
    out = ['\U0001F4E6 <b>%s</b>' % e(info['name'])]
    for flag, lang in ((PT, 'pt'), (EN, 'en')):
        out.append('')
        out.append('%s <b>%s</b>' % (flag, LABELS[lang]['kind']))
        out += ['• %s: %s' % (label, value) for label, value in facts(info, lang)]
    if info['text']:
        text = info['text']
        text = text if len(text) <= DESCRIPTION_MAX else text[:DESCRIPTION_MAX].rsplit(' ', 1)[0] + '…'
        out += ['', '<b>%s / %s</b>' % (LABELS['pt']['description'], LABELS['en']['description']), e(text)]
    out += ['', '%s %s' % (PT, LABELS['pt']['install']), '%s %s' % (EN, LABELS['en']['install'])]
    if sender:
        out += ['', '%s / %s: %s' % (LABELS['pt']['by'], LABELS['en']['by'], e(sender))]
    return '\n'.join(out)[:TEXT_MAX]


def file_caption(file_name, size, note=''):
    """A legenda do arquivo (ate 1024)."""
    lines = ['\U0001F4E6 <code>%s</code> · %s' % (e(file_name), size_text(size))]
    if note:
        lines += ['%s %s' % (PT, LABELS['pt'][note]), '%s %s' % (EN, LABELS['en'][note])]
    lines += ['%s %s' % (PT, LABELS['pt']['install']), '%s %s' % (EN, LABELS['en']['install'])]
    return '\n'.join(lines)[:CAPTION_MAX]


def problems_text(file_name, problems, sender):
    out = ['⚠️ <code>%s</code>' % e(file_name), '%s %s:' % (PT, LABELS['pt']['bad']), '%s %s:' % (EN, LABELS['en']['bad'])]
    out += ['• %s' % e(text) for _, _, text in problems[:12]]
    return '\n'.join(out)[:TEXT_MAX]


# ── O Telegram ──

def multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode())
    for name, (filename, data) in files.items():
        body.write(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
                    'Content-Type: application/octet-stream\r\n\r\n' % (boundary, name, filename)).encode())
        body.write(data)
        body.write(b'\r\n')
    body.write(('--%s--\r\n' % boundary).encode())
    return body.getvalue(), 'multipart/form-data; boundary=' + boundary


class Telegram:
    """A Bot API do bot do grupo (so o que o robo usa)."""

    def __init__(self, token):
        self.token = token

    def call(self, method, fields, files=None):
        body, content_type = multipart(fields, files or {})
        for attempt in range(5):
            request = urllib.request.Request(API % (self.token, method), body, {'Content-Type': content_type})
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    return json.load(response)['result']
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

    def download(self, file_id):
        """Os bytes de um arquivo de ate 20 MB (a Bot API); PostError se for maior."""
        path = self.call('getFile', {'file_id': file_id})['file_path']
        with urllib.request.urlopen(FILE_API % (self.token, path), timeout=300) as response:
            return response.read()

    def where(self, chat, thread, reply):
        fields = {'chat_id': chat}
        if thread:
            fields['message_thread_id'] = str(thread)
        if reply:
            fields['reply_parameters'] = json.dumps({'message_id': reply, 'allow_sending_without_reply': True})
        return fields

    def message(self, chat, text, thread=None, reply=None):
        return self.call('sendMessage', dict(self.where(chat, thread, reply), text=text, parse_mode='HTML',
                                             link_preview_options=json.dumps({'is_disabled': True})))

    def album(self, chat, items, caption_text, thread=None, reply=None):
        """items: [(tipo, nome do arquivo, bytes)], photo ou video; a legenda no primeiro."""
        if len(items) == 1:
            kind, name, data = items[0]
            method = 'sendPhoto' if kind == 'photo' else 'sendVideo'
            fields = dict(self.where(chat, thread, reply), caption=caption_text, parse_mode='HTML')
            if kind == 'video':
                fields['supports_streaming'] = 'true'
            return self.call(method, fields, {kind: (name, data)})
        media, files = [], {}
        for n, (kind, name, data) in enumerate(items):
            entry = {'type': kind, 'media': 'attach://f%d' % n}
            if n == 0:
                entry.update(caption=caption_text, parse_mode='HTML')
            if kind == 'video':
                entry['supports_streaming'] = True
            media.append(entry)
            files['f%d' % n] = (name, data)
        return self.call('sendMediaGroup', dict(self.where(chat, thread, reply), media=json.dumps(media)), files)

    def document(self, chat, file_id, caption_text, thread=None):
        """O arquivo que ja esta no Telegram, de novo, por file_id."""
        return self.call('sendDocument', dict(self.where(chat, thread, None), document=file_id, caption=caption_text,
                                              parse_mode='HTML'))


class PrintOnly(Telegram):
    """O --no-post: ler o pacote e de verdade (a Bot API e o MTProto), mas nada vai ao grupo; o post sai no log."""

    def message(self, chat, text, thread=None, reply=None):
        print('[mensagem] topico=%s resposta=%s\n%s\n' % (thread, reply, text))

    def album(self, chat, items, caption_text, thread=None, reply=None):
        print('[album] topico=%s resposta=%s: %s\n%s\n' % (
            thread, reply, ', '.join('%s %s (%d bytes)' % (kind, name, len(data)) for kind, name, data in items), caption_text))

    def document(self, chat, file_id, caption_text, thread=None):
        print('[arquivo] topico=%s file_id=%s...\n%s\n' % (thread, file_id[:12], caption_text))


# ── O MTProto (so quando o pacote e grande demais para a Bot API) ──

def decode_file_id(file_id):
    """O file_id da Bot API (o formato persistente 4 do tdlib) de um documento: (dc, id, access_hash,
    file_reference). Eles sao do bot (a mesma conta no MTProto), e abrem o arquivo sem a mensagem. O
    resolve_bot_file_id do Telethon so le o formato velho e devolve None para os de agora. ValueError: nao
    e o file_id de um documento."""
    try:
        raw = base64.urlsafe_b64decode(file_id + '=' * (-len(file_id) % 4))
    except (ValueError, TypeError) as exc:
        raise ValueError('not a file_id: %s' % exc) from None
    data = bytearray()
    i = 0
    while i < len(raw):                       # zeros comprimidos: um 0x00 e a quantidade deles
        if raw[i] == 0 and i + 1 < len(raw):
            data += b'\0' * raw[i + 1]
            i += 2
        else:
            data.append(raw[i])
            i += 1
    data = bytes(data)
    if len(data) < 26 or data[-1] != 4:
        raise ValueError('not a persistent file_id of version 4')
    kind, dc = struct.unpack('<ii', data[:8])
    if kind & 0xFFFFFF != 5 or not kind & (1 << 25):
        raise ValueError('not a document with a file reference')
    pos = 8
    size = data[pos]
    pos += 1
    if size == 254:                           # os bytes do TL: 1 de tamanho, ou 254 e 3 de tamanho
        size = int.from_bytes(data[pos:pos + 3], 'little')
        pos += 3
        pad = -size % 4
    else:
        pad = -(1 + size) % 4
    reference = data[pos:pos + size]
    pos += size + pad
    if len(data) < pos + 16:
        raise ValueError('the file_id is cut short')
    media_id, access_hash = struct.unpack('<qq', data[pos:pos + 16])
    return dc, media_id, access_hash, reference


class TelethonSource:
    """O arquivo de uma mensagem do grupo lido por pedacos, como bot pelo MTProto
    (Telethon): iter_download entrega a partir de um deslocamento, sem baixar o
    arquivo inteiro. Precisa do pacote telethon e de TELEGRAM_API_ID e
    TELEGRAM_API_HASH."""

    def __init__(self, token, api_id, api_hash, chat, message_id, file_id='', file_size=0):
        import asyncio
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.client = TelegramClient(StringSession(), int(api_id), api_hash, loop=loop)
        # O laco que o proprio cliente usa: e nele que o start() e o disconnect() rodam.
        self.loop = getattr(self.client, 'loop', None) or loop
        self.run(self.client.start(bot_token=token))
        # O arquivo da mensagem do grupo; um bot nem sempre consegue buscar uma mensagem por id (o teste real
        # voltou sem a mensagem), e entao o arquivo vem do file_id da Bot API, que e do mesmo bot.
        self.document, self.size, self.dc_id = None, 0, None
        try:
            message = self.run(self.client.get_messages(chat, ids=message_id))
        except Exception as exc:    # RPCError do Telethon
            print('get_messages(%s, %s) failed: %s' % (chat, message_id, exc))
            message = None
        found = getattr(message, 'document', None) if message else None
        if found is not None:
            self.document, self.size = found, found.size
            print('MTProto: the file came from the message %s' % message_id)
        elif file_id:
            from telethon import types
            try:
                dc, media_id, access_hash, reference = decode_file_id(file_id)
            except ValueError as exc:
                raise PostError('the file_id cannot be opened by MTProto: %s' % exc) from None
            self.document = types.InputDocumentFileLocation(id=media_id, access_hash=access_hash, file_reference=reference,
                                                            thumb_size='')
            self.size, self.dc_id = int(file_size or 0), dc
            print('MTProto: the message %s was not readable (%s); the file came from its file_id (dc %d)'
                  % (message_id, type(message).__name__, dc))
        if self.document is None or not self.size:
            raise PostError('the message %s has no file the bot can read' % message_id)

    def run(self, value):
        """O resultado de uma chamada do Telethon. O start() e o disconnect() rodam o laco sozinhos quando ele
        nao esta rodando (e devolvem o resultado, nao uma corrotina); as outras chamadas sao corrotinas."""
        return self.loop.run_until_complete(value) if inspect.isawaitable(value) else value

    def fetch(self, offset, length):
        async def read():
            out = b''
            async for chunk in self.client.iter_download(self.document, offset=offset, request_size=BLOCK, limit=1,
                                                         file_size=self.size, dc_id=self.dc_id):
                out += chunk
            return out[:length]
        return self.loop.run_until_complete(read())

    def close(self):
        try:
            self.run(self.client.disconnect())
        finally:
            if not self.loop.is_closed():
                self.loop.close()


def telethon_source(env, chat, message_id, file_id='', file_size=0):
    """Uma fonte MTProto, ou None sem as chaves (ou sem o telethon)."""
    if not (env.get('TELEGRAM_API_ID') and env.get('TELEGRAM_API_HASH')):
        return None
    try:
        return TelethonSource(env['TELEGRAM_BOT_TOKEN'], env['TELEGRAM_API_ID'], env['TELEGRAM_API_HASH'], chat, message_id,
                              file_id, file_size)
    except ImportError:
        print('telethon is not installed: big packages cannot be read', file=sys.stderr)
        return None


# ── O post ──

def post_package(tg, payload, env, tool, mtproto=telethon_source, out=print):
    """Trata um zip mandado ao grupo. payload: chat_id, message_id, thread_id,
    file_id, file_name, file_size, from (o nome de quem mandou), username e
    chat_username. Devolve o que fez (para o log e para os testes)."""
    name = str(payload.get('file_name') or '')
    if not name.lower().endswith(SUFFIX):
        return 'skipped: not a custom game package'
    chat_id = str(payload.get('chat_id', ''))
    wanted = env.get('TELEGRAM_CHAT_ID') or ''
    if re.fullmatch(r'-?\d+', wanted) and wanted != chat_id:
        return 'skipped: another chat'
    chat = chat_id or wanted or DEFAULT_CHAT
    topic = int(env.get('TELEGRAM_FILES_TOPIC') or FILES_TOPIC)
    message_id = int(payload.get('message_id') or 0)
    origin = int(payload.get('thread_id') or 0)
    size = int(payload.get('file_size') or 0)
    file_id = payload.get('file_id') or ''
    sender = ' '.join(x for x in (str(payload.get('from') or ''), ('(@%s)' % payload['username']) if payload.get('username') else '') if x)
    # O zip: ate 20 MB pela Bot API; acima, pelo MTProto; sem ele, so o arquivo.
    info, problems, note, source = None, None, '', None
    try:
        if size and size <= BOT_DOWNLOAD_MAX:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / name
                path.write_bytes(tg.download(file_id))
                info = read_info(tool, tool.Package(str(path)))
        else:
            ref = payload.get('chat_username')
            ref = '@' + ref if ref and not ref.startswith('@') else ref or (wanted if wanted.startswith('@') else None) or \
                (int(chat_id) if chat_id else None)
            try:
                source = mtproto(env, ref, message_id, file_id, size)
            except Exception as exc:    # o Telethon: sem rede, mensagem que o bot nao acha, chaves erradas...
                out('could not open the file by MTProto: %s' % exc)
                source = None
            if source is None:
                note = 'unreadable'
            else:
                ranged = RangeFile(source.size, source.fetch)
                info = read_info(tool, tool.Package(name, fileobj=ranged))
                out('read %s: %d of %d bytes fetched' % (name, ranged.fetched, source.size))
    except tool.Bad as exc:
        problems = exc.problems
    except PostError as exc:
        note = 'unreadable'
        out('could not read %s: %s' % (name, exc))
    finally:
        if source is not None:
            source.close()
    in_files = origin == topic
    if problems:
        # Um pacote que nao serve: a resposta no lugar onde ele foi mandado, com os problemas.
        tg.message(chat, problems_text(name, problems, sender), origin or None, message_id)
        return 'refused: %d problems' % len(problems)
    reply = message_id if in_files else None
    where = origin if in_files else topic
    if info:
        items = []
        for kind in ('snap', 'logo'):
            if kind in info['art']:
                ext, data = info['art'][kind]
                data = photo_bytes(data, ext)
                if data:
                    items.append(('photo', '%s.%s' % (kind, 'png' if data[:4] == b'\x89PNG' else 'jpg'), data))
        if 'preview' in info['art']:
            ext, data = info['art']['preview']
            items.append(('video', 'preview.%s' % ext, data))
        if items:
            tg.album(chat, items, caption(info, sender), where, reply)
            tg.message(chat, details(info, sender), where, reply)
        else:
            tg.message(chat, caption(info, sender) + '\n\n' + details(info, '').split('\n', 1)[1], where, reply)
    else:
        text = '\U0001F4E6 <b>%s</b>' % e(name[:-len(SUFFIX)])
        text += '\n%s %s\n%s %s' % (PT, LABELS['pt']['unreadable'], EN, LABELS['en']['unreadable'])
        if sender:
            text += '\n%s / %s: %s' % (LABELS['pt']['by'], LABELS['en']['by'], e(sender))
        tg.message(chat, text, where, reply)
    if not in_files and file_id:
        tg.document(chat, file_id, file_caption(name, size, note if not info else ''), topic)
        # Onde o zip foi mandado: um aviso curto de onde estao os dados.
        tg.message(chat, '\U0001F4E6 <b>%s</b>\n%s %s\n%s %s' % (e(name[:-len(SUFFIX)]), PT, LABELS['pt']['see'], EN, LABELS['en']['see']),
                   origin or None, message_id)
    return 'posted: %s%s' % (info['name'] if info else name, ' (details unreadable)' if not info else '')


def preview(path, folder=None):
    """O post de um zip do disco, sem rede: o texto e as imagens (em folder)."""
    tool = load_tool()
    try:
        package = tool.Package(str(path))
    except tool.Bad as exc:
        print('%s is not a package FliperOS accepts: %s' % (path, exc), file=sys.stderr)
        raise SystemExit(1)
    info = read_info(tool, package)
    print(caption(info, 'Someone (@someone)'))
    print()
    print(details(info, 'Someone (@someone)'))
    print()
    print(file_caption(Path(path).name, Path(path).stat().st_size))
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        for kind, (ext, data) in info['art'].items():
            if kind == 'preview':
                (Path(folder) / ('preview.' + ext)).write_bytes(data)
            else:
                shown = photo_bytes(data, ext)
                if shown:
                    (Path(folder) / ('%s.%s' % (kind, 'png' if shown[:4] == b'\x89PNG' else 'jpg'))).write_bytes(shown)
    return info


def main():
    parser = argparse.ArgumentParser(description='Posta um pacote de jogo custom no topico Files do grupo do Telegram.')
    parser.add_argument('--zip', help='so mostra o post de um zip do disco')
    parser.add_argument('--out', help='com --zip: onde salvar as imagens')
    parser.add_argument('--payload-env', help='a variavel de ambiente com o JSON do pacote mandado ao grupo')
    parser.add_argument('--payload-file', help='o mesmo, num arquivo')
    parser.add_argument('--dry-run', action='store_true', help='confere o pedido e nao fala com o Telegram')
    parser.add_argument('--no-post', action='store_true', help='le o pacote de verdade, mas so mostra o post no log (nada vai ao grupo)')
    args = parser.parse_args()
    if args.zip:
        preview(args.zip, args.out)
        return 0
    raw = os.environ.get(args.payload_env or '', '') if args.payload_env else Path(args.payload_file).read_text(encoding='utf-8') \
        if args.payload_file else ''
    if not raw.strip():
        parser.error('give --zip, --payload-env or --payload-file')
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError('not an object')
    except ValueError as exc:
        print('the payload is not JSON: %s' % exc, file=sys.stderr)
        return 1
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if args.dry_run or not token:
        print('dry run: would post %s from message %s' % (payload.get('file_name'), payload.get('message_id')))
        if not args.dry_run:
            print('::warning::no TELEGRAM_BOT_TOKEN: nothing was posted')
        return 0
    try:
        result = post_package((PrintOnly if args.no_post else Telegram)(token), payload, dict(os.environ), load_tool())
    except PostError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
