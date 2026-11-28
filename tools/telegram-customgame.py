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
    video, texto), nunca a pasta do jogo (RangeFile). A sessao do bot fica guardada em
    TELEGRAM_SESSION_FILE (o workflow a poe no cache) e o login tenta de novo com espera:
    entrar como bot a cada pacote fazia o Telegram responder 500 (ImportBotAuthorization);
  - sem isso, o post sai assim mesmo, com o nome e o tamanho e o arquivo, e um
    aviso de que os detalhes nao deu para ler.
O arquivo vai ao topico por file_id (o Telegram reenvia o que ja tem, sem limite
de tamanho). Se o zip ja foi mandado no proprio topico Files, o robo responde a
ele com os dados, sem repetir o arquivo.

Um pacote maior que o arquivo do plano gratuito do Telegram (2 GB) chega em partes
(GAME.fliperos-customgame.zip.001, .002..., que o painel web faz): o Worker espera
as partes, junta e chama o workflow uma vez so, com todas em "parts". O robo le as
partes como se fossem o zip inteiro (pelo MTProto), faz UM card com os dados e
responde uma vez a cada parte (post_split_package).

    python3 tools/telegram-customgame.py --messages-env MESSAGES [--no-post]
        partes que chegaram ao grupo sem o Worker as tratar: MESSAGES e a lista das
        mensagens delas (numeros, uma faixa 1708-1719 ou links t.me); o robo as le pelo
        MTProto, refaz o pedido e posta o card (workflow Telegram custom game, campo messages)

    python3 tools/telegram-customgame.py --check-names-env CHECK [--no-post]
        os pacotes ja postados com o nome errado (COTTOn_fliperos_customgame_zip.002: algum
        programa trocou os pontos e hifens por "_"; o gabinete nao os reconhece): CHECK e
        "all" (o grupo inteiro) ou as mensagens; cada pacote ganha a resposta que o Worker
        da hoje, com o nome certo (campo check_names do workflow)

Variaveis: TELEGRAM_BOT_TOKEN (o bot do grupo), TELEGRAM_CHAT_ID (o grupo, se
quiser conferir; @fliperos15khz sem ela), TELEGRAM_FILES_TOPIC (o numero no fim
do link do topico, t.me/fliperos15khz/NUMERO; 578), TELEGRAM_API_ID,
TELEGRAM_API_HASH. Toda mensagem vai em portugues e em ingles."""
import argparse
import base64
import bisect
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
MIB = 1 << 20
# Um pacote maior que o arquivo do plano gratuito do Telegram (2 GB) chega em partes, GAME.fliperos-customgame.zip.001,
# .002... (o painel web as faz: config/fliperos-web, package_parts). O Worker junta as partes e chama o workflow uma vez
# so, com todas em "parts".
PART_RE = re.compile(r'^(.+' + re.escape(SUFFIX) + r')\.(\d{3})$', re.I)
# O nome que o cliente do Telegram de quem mandou trocou: JoJo_s_Game_fliperos_customgame_zip.001 (todos os pontos, hifens e
# espacos do nome viraram "_", menos o ultimo ponto, o da numeracao ou da extensao).
MANGLED_RE = re.compile(r'^(.+?)_fliperos[_-]customgame[_.]zip(\.\d{3})?$', re.I)


def package_file_name(name):
    """O nome do arquivo como o painel o faz (GAME.fliperos-customgame.zip, com .001... nas partes), tambem quando o
    Telegram de quem o mandou trocou os pontos por "_"; qualquer outro nome volta como esta."""
    name = str(name or '')
    match = MANGLED_RE.match(name)
    return match.group(1) + SUFFIX + (match.group(2) or '') if match else name


# Um nome quase certo, como o Worker o ve (tools/telegram-translate/worker.js, LOOSE_NAME): os pontos, hifens ou espacos
# trocados por "_" (COTTOn_fliperos_customgame_zip.002) ou uma parte sem os tres digitos (.zip.2). O gabinete nao reconhece
# esse arquivo; o Worker responde com o nome certo e nao faz o card (warnBadName), e o --check-names faz o mesmo com o que
# ja foi postado antes dele.
LOOSE_NAME_RE = re.compile(r'(.+?)[._ -]+fliperos[._ -]*customgame[._ -]*zip(?:[._ -]*(\d{1,3}))?', re.I)
GOOD_NAME_RE = re.compile(r'.+' + re.escape(SUFFIX) + r'(?:\.\d{3})?', re.I)
BAD_NAME_TITLE = 'Nome de arquivo inválido.'


def loose_package_name(name):
    """(nome do pacote sem o sufixo, numero da parte ou None) de um nome quase certo; None para um nome certo ou para um
    arquivo que nao e pacote."""
    name = str(name or '')
    match = None if GOOD_NAME_RE.fullmatch(name) else LOOSE_NAME_RE.fullmatch(name)
    if not match:
        return None
    return match.group(1), None if match.group(2) is None else int(match.group(2))


def right_package_name(stem, number=None):
    return stem + SUFFIX + ('' if number is None else '.%03d' % number)


# O nome mais comprido que chega inteiro, em bytes: alguns apps trocam os pontos e hifens de um nome maior por "_" (no grupo,
# os 24 pacotes que chegaram certos tinham ate 57 caracteres e os 4 trocados, de 65 a 71). O mesmo do Worker (NAME_MAX) e
# do painel (config/fliperos-web, PACKAGE_NAME_MAX).
NAME_MAX = 57
SEPARATORS = '._ -'


def name_too_long(name):
    return len(name.encode('utf-8')) > NAME_MAX


def short_package_name(stem, number=None):
    """O nome certo com o nome do jogo cortado no fim de uma palavra (se der) ate caber em NAME_MAX, igual ao shortName do
    Worker. No gabinete o jogo continua com o nome dele (o do .cfg de dentro do zip)."""
    if not name_too_long(right_package_name(stem, number)):
        return right_package_name(stem, number)
    k = len(stem)
    while k > 1 and name_too_long(right_package_name(stem[:k], number)):
        k -= 1
    cut = stem[:k]
    if stem[k] not in SEPARATORS:
        last = max(cut.rfind(c) for c in SEPARATORS)
        if last > 0:
            cut = cut[:last]
    return right_package_name(cut.rstrip(SEPARATORS) or stem[:k], number)


def bad_name_text(names, shortened=False):
    """O aviso do nome invalido, igual ao do Worker (badNameText): names = [(nome errado, nome a usar)]; shortened: o nome
    certo passava de NAME_MAX e o sugerido e mais curto."""
    many = len(names) > 1
    lines = [
        PT + ' ⚠️ <b>' + BAD_NAME_TITLE + '</b> O FliperOS só reconhece ' + ('as partes do pacote' if many else 'o pacote') +
        ' com o nome assim: renomeie e mande de novo.' + (
            (' Use nomes curtos como estes' if many else ' Use um nome curto como este') + ': alguns apps trocam os pontos e '
            'hífens de um nome com mais de %d caracteres por "_". No gabinete o jogo continua com o nome dele.' % NAME_MAX
            if shortened else ''),
        EN + ' ⚠️ <b>Invalid file name.</b> FliperOS only recognises ' + ('the parts of the package' if many else 'the package') +
        ' named like this: rename ' + ('them' if many else 'it') + ' and send ' + ('them' if many else 'it') + ' again.' + (
            (' Keep the names short like these' if many else ' Keep the name short like this one') + ': some apps turn the dots '
            'and hyphens of a name longer than %d characters into "_". On the cabinet the game keeps its own name.' % NAME_MAX
            if shortened else ''),
    ]
    shown = names[:10]
    for wrong, right in shown:
        lines += ['', '❌ <code>' + html.escape(wrong, quote=False) + '</code>', '✅ <code>' + html.escape(right, quote=False) + '</code>']
    if len(names) > len(shown):
        lines += ['', '… +%d' % (len(names) - len(shown))]
    return '\n'.join(lines)


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


class PartsSource:
    """As partes de um zip lidas como o zip inteiro: fetch(offset, length) do zip vira o fetch de cada parte que o
    intervalo toca (fetch_part(numero da parte, deslocamento dentro dela, tamanho)). E o que o RangeFile precisa
    (size, fetch, close). sizes: o tamanho de cada parte, na ordem."""

    def __init__(self, sizes, fetch_part, closer=None):
        self.sizes, self.fetch_part, self.closer = list(sizes), fetch_part, closer
        self.starts = [sum(self.sizes[:i]) for i in range(len(self.sizes))]
        self.size = sum(self.sizes)

    def fetch(self, offset, length):
        end = min(offset + length, self.size)
        out = []
        while offset < end:
            number = bisect.bisect_right(self.starts, offset) - 1
            inside = offset - self.starts[number]
            take = min(end - offset, self.sizes[number] - inside)
            data = self.fetch_part(number, inside, take)
            if len(data) != take:
                raise PostError('part %d came short: %d of %d bytes' % (number + 1, len(data), take))
            out.append(data)
            offset += take
        return b''.join(out)

    def close(self):
        if self.closer:
            self.closer()


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
           'see': 'Os dados e o arquivo estão no tópico Arquivos',
           # O pacote que veio em partes (GAME.fliperos-customgame.zip.001, .002...): um card só e uma resposta por parte.
           'parts': 'Arquivo dividido', 'parts_value': '%d partes, %s no total',
           'install_split': 'Para instalar: baixe todas as partes na mesma pasta e dê dois cliques em qualquer uma delas no desktop do '
                            'gabinete (ele junta e instala), ou solte todas juntas no painel web > Jogos custom > Jogos. Para juntar à mão: '
                            'Linux e macOS: cat "%s".0* > "%s"; Windows: copy /b com as partes em ordem; ou abra a .001 no 7-Zip.',
           'part_of': 'Parte %d de %d', 'part_note': 'Parte do pacote %s: os dados e como juntar as partes estão no card.',
           'split_bad': 'Estas partes não formam um pacote',
           'split_missing': 'faltam as partes: %s', 'split_sizes': 'as partes, menos a última, têm de ter o mesmo tamanho',
           'split_extra': 'a numeração tem de ir de 001 a %03d sem repetir'},
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
           'see': 'The details and the file are in the Files topic',
           'parts': 'Split file', 'parts_value': '%d parts, %s in total',
           'install_split': 'To install: download all the parts into the same folder and double-click any one of them on the cabinet\'s '
                            'desktop (it joins them and installs), or drop all of them together in the web panel > Custom games > Games. To '
                            'join them by hand: Linux and macOS: cat "%s".0* > "%s"; Windows: copy /b with the parts in order; or open the '
                            '.001 in 7-Zip.',
           'part_of': 'Part %d of %d', 'part_note': 'Part of the package %s: the details and how to join the parts are in the card.',
           'split_bad': 'These parts do not make a package',
           'split_missing': 'parts missing: %s', 'split_sizes': 'the parts, except the last one, must have the same size',
           'split_extra': 'the numbering must run from 001 to %03d without repeating'},
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
    if info.get('split'):
        out.append((t['parts'], t['parts_value'] % (info['split']['count'], size_text(info['split']['total']))))
    art =[t[k] for k in ('snap', 'logo', 'preview') if k in info['art']] + ([t['text']] if info['text'] else [])
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


def details(info, sender, install=False):
    """A mensagem com todos os dados, em portugues e em ingles, e a descricao. install: com a dica de como
    instalar, para quando o arquivo nao vai junto (o zip ja foi mandado no topico Files); senao a dica vai na
    legenda do arquivo (file_caption), uma vez so."""
    out = ['\U0001F4E6 <b>%s</b>' % e(info['name'])]
    for flag, lang in ((PT, 'pt'), (EN, 'en')):
        out.append('')
        out.append('%s <b>%s</b>' % (flag, LABELS[lang]['kind']))
        out += ['• %s: %s' % (label, value) for label, value in facts(info, lang)]
    if info['text']:
        text = info['text']
        text = text if len(text) <= DESCRIPTION_MAX else text[:DESCRIPTION_MAX].rsplit(' ', 1)[0] + '…'
        out += ['', '<b>%s / %s</b>' % (LABELS['pt']['description'], LABELS['en']['description']), e(text)]
    if install:
        out += ['', '%s %s' % (PT, install_hint(info, 'pt')), '%s %s' % (EN, install_hint(info, 'en'))]
    if sender:
        out += ['', '%s / %s: %s' % (LABELS['pt']['by'], LABELS['en']['by'], e(sender))]
    return '\n'.join(out)[:TEXT_MAX]


def install_hint(info, lang):
    """Como instalar: o pacote inteiro (solta o .zip no painel) ou, vindo em partes, juntar as partes antes."""
    t = LABELS[lang]
    if info.get('split'):
        return t['install_split'] % (e(info['split'].get('source') or info['split']['base']), e(info['split']['base']))
    return t['install']


def file_caption(file_name, size):
    """A legenda do arquivo (ate 1024): o nome, o tamanho e como instalar. So aqui: a mensagem dos dados (ou o
    aviso de que nao deu para le-los) nao repete."""
    lines = ['\U0001F4E6 <code>%s</code> · %s' % (e(file_name), size_text(size)),
             '%s %s' % (PT, LABELS['pt']['install']), '%s %s' % (EN, LABELS['en']['install'])]
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

    def edit(self, chat, message_id, text):
        """Troca o texto de uma mensagem que o bot ja mandou."""
        return self.call('editMessageText', {'chat_id': chat, 'message_id': str(message_id), 'text': text, 'parse_mode': 'HTML',
                                             'link_preview_options': json.dumps({'is_disabled': True})})

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

    def document(self, chat, file_id, caption_text, thread=None, reply=None):
        """O arquivo que ja esta no Telegram, de novo, por file_id (reply: respondendo a uma mensagem)."""
        return self.call('sendDocument', dict(self.where(chat, thread, reply), document=file_id, caption=caption_text,
                                              parse_mode='HTML'))


class PrintOnly(Telegram):
    """O --no-post: ler o pacote e de verdade (a Bot API e o MTProto), mas nada vai ao grupo; o post sai no log."""

    def message(self, chat, text, thread=None, reply=None):
        print('[mensagem] topico=%s resposta=%s\n%s\n' % (thread, reply, text))

    def edit(self, chat, message_id, text):
        print('[editar] mensagem=%s\n%s\n' % (message_id, text))

    def album(self, chat, items, caption_text, thread=None, reply=None):
        print('[album] topico=%s resposta=%s: %s\n%s\n' % (
            thread, reply, ', '.join('%s %s (%d bytes)' % (kind, name, len(data)) for kind, name, data in items), caption_text))

    def document(self, chat, file_id, caption_text, thread=None, reply=None):
        print('[arquivo] topico=%s resposta=%s file_id=%s...\n%s\n' % (thread, reply, file_id[:12], caption_text))


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

    # Quanto esperar entre uma tentativa de entrar como bot e a seguinte (segundos). O Telegram responde 500
    # ("internal issues") ao ImportBotAuthorization quando o mesmo bot entra muito, e as tentativas do Telethon
    # (1 a 2 s entre elas) acabam antes de ele deixar; esperar mais resolve.
    LOGIN_WAITS = (10, 20, 40, 60, 90)

    def __init__(self, token, api_id, api_hash, chat, message_id, file_id='', file_size=0, session_file=''):
        self.connect(token, api_id, api_hash, session_file)
        self.document, self.size, self.dc_id = self.resolve(chat, message_id, file_id, file_size)

    def connect(self, token, api_id, api_hash, session_file):
        """O cliente do Telethon, ja entrado como bot (ou com a sessao guardada)."""
        import asyncio
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # A sessao da execucao anterior (o workflow a guarda no cache): com ela o bot nao precisa entrar de novo,
        # que e o que o Telegram recusa quando as execucoes se repetem.
        self.session_file = session_file
        saved = ''
        if session_file:
            try:
                saved = Path(session_file).read_text(encoding='utf-8').strip()
            except OSError:
                saved = ''
        self.client = TelegramClient(StringSession(saved) if saved else StringSession(), int(api_id), api_hash, loop=loop)
        # O laco que o proprio cliente usa: e nele que o start() e o disconnect() rodam.
        self.loop = getattr(self.client, 'loop', None) or loop
        self.login(token, bool(saved))

    def resolve(self, chat, message_id, file_id='', file_size=0):
        """O arquivo da mensagem do grupo: (documento, tamanho, data center). Um bot nem sempre consegue buscar uma
        mensagem por id (o teste real voltou sem a mensagem), e entao o arquivo vem do file_id da Bot API, que e do
        mesmo bot."""
        document, size, dc_id = None, 0, None
        try:
            message = self.run(self.client.get_messages(chat, ids=message_id))
        except Exception as exc:    # RPCError do Telethon
            print('get_messages(%s, %s) failed: %s' % (chat, message_id, exc))
            message = None
        found = getattr(message, 'document', None) if message else None
        if found is not None:
            document, size = found, found.size
            print('MTProto: the file came from the message %s' % message_id)
        elif file_id:
            from telethon import types
            try:
                dc, media_id, access_hash, reference = decode_file_id(file_id)
            except ValueError as exc:
                raise PostError('the file_id cannot be opened by MTProto: %s' % exc) from None
            document = types.InputDocumentFileLocation(id=media_id, access_hash=access_hash, file_reference=reference,
                                                       thumb_size='')
            size, dc_id = int(file_size or 0), dc
            print('MTProto: the message %s was not readable (%s); the file came from its file_id (dc %d)'
                  % (message_id, type(message).__name__, dc))
        if document is None or not size:
            raise PostError('the message %s has no file the bot can read' % message_id)
        return document, size, dc_id

    def login(self, token, resumed):
        """Entra como bot (ou retoma a sessao guardada), tentando de novo com espera quando o Telegram falha; a
        sessao que funcionou fica guardada para a proxima execucao."""
        waits = list(self.LOGIN_WAITS)
        while True:
            try:
                self.run(self.client.start(bot_token=token))
                break
            except Exception as exc:    # RpcCallFailError, ValueError("Request was unsuccessful"), rede
                if not waits:
                    raise
                wait = waits.pop(0)
                print('the MTProto login failed (%s: %s); trying again in %d s' % (type(exc).__name__, exc, wait))
                time.sleep(wait)
        print('MTProto: %s' % ('session resumed' if resumed else 'logged in as the bot'))
        if self.session_file:
            try:
                string = self.client.session.save()
                if string:
                    Path(self.session_file).parent.mkdir(parents=True, exist_ok=True)
                    Path(self.session_file).write_text(string, encoding='utf-8')
            except Exception as exc:    # sem a sessao guardada so a proxima execucao entra de novo
                print('the MTProto session was not saved: %s' % exc)

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


class TelethonParts(TelethonSource):
    """As partes de um pacote dividido, lidas como o zip inteiro (PartsSource) por um cliente so: o bot entra uma vez e
    abre uma mensagem por parte. size e fetch(offset, length) sao os do zip inteiro."""

    def __init__(self, token, api_id, api_hash, chat, parts, session_file=''):
        self.connect(token, api_id, api_hash, session_file)
        self.documents = [self.resolve(chat, int(p.get('message_id') or 0), p.get('file_id') or '', int(p.get('file_size') or 0))
                          for p in parts]
        self.source = PartsSource([size for _, size, _ in self.documents], self.read_part)
        self.size = self.source.size

    def fetch(self, offset, length):
        return self.source.fetch(offset, length)

    def read_part(self, number, offset, length):
        """LENGTH bytes a partir de OFFSET dentro da parte NUMBER (a partir de 0). O Telegram so entrega pedidos que
        comecam num multiplo de 4096 e nao cruzam um limite de 1 MiB: o intervalo vai em pedidos assim."""
        document, size, dc_id = self.documents[number]
        first = offset - offset % 4096
        pos, chunks = first, []

        async def read(at, request):
            out = b''
            async for chunk in self.client.iter_download(document, offset=at, request_size=request, limit=1, file_size=size,
                                                         dc_id=dc_id):
                out += chunk
            return out

        while pos < offset + length:
            request = min(BLOCK, MIB - pos % MIB)
            data = self.loop.run_until_complete(read(pos, request))
            if not data:
                break
            chunks.append(data)
            pos += len(data)
        return b''.join(chunks)[offset - first:offset - first + length]


def telethon_parts_source(env, chat, parts):
    """Uma fonte MTProto das partes de um pacote dividido, ou None sem as chaves (ou sem o telethon)."""
    if not (env.get('TELEGRAM_API_ID') and env.get('TELEGRAM_API_HASH')):
        return None
    try:
        return TelethonParts(env['TELEGRAM_BOT_TOKEN'], env['TELEGRAM_API_ID'], env['TELEGRAM_API_HASH'], chat, parts,
                             env.get('TELEGRAM_SESSION_FILE') or '')
    except ImportError:
        print('telethon is not installed: big packages cannot be read', file=sys.stderr)
        return None


def telethon_source(env, chat, message_id, file_id='', file_size=0):
    """Uma fonte MTProto, ou None sem as chaves (ou sem o telethon)."""
    if not (env.get('TELEGRAM_API_ID') and env.get('TELEGRAM_API_HASH')):
        return None
    try:
        return TelethonSource(env['TELEGRAM_BOT_TOKEN'], env['TELEGRAM_API_ID'], env['TELEGRAM_API_HASH'], chat, message_id,
                              file_id, file_size, env.get('TELEGRAM_SESSION_FILE') or '')
    except ImportError:
        print('telethon is not installed: big packages cannot be read', file=sys.stderr)
        return None


# ── O post ──

def post_card(tg, chat, info, sender, where, reply, in_files):
    """O card de um pacote: o album (imagem, logotipo e video, com a legenda) e a mensagem com os dados. Sem arte, so o
    texto. Devolve o que o Telegram respondeu a ultima mensagem."""
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
        return tg.message(chat, details(info, sender, install=in_files), where, reply)
    return tg.message(chat, caption(info, sender) + '\n\n' + details(info, '', install=in_files).split('\n', 1)[1], where, reply)


def post_package(tg, payload, env, tool, mtproto=telethon_source, out=print, mtproto_parts=telethon_parts_source):
    """Trata um zip mandado ao grupo. payload: chat_id, message_id, thread_id,
    file_id, file_name, file_size, from (o nome de quem mandou), username e
    chat_username. Um pacote que veio em partes traz tambem "parts" (as partes, que o Worker juntou): post_split_package.
    Devolve o que fez (para o log e para os testes)."""
    if payload.get('parts'):
        return post_split_package(tg, payload, env, tool, mtproto_parts, out)
    name = package_file_name(payload.get('file_name'))
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
    info, problems, source = None, None, None
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
            if source is not None:
                ranged = RangeFile(source.size, source.fetch)
                info = read_info(tool, tool.Package(name, fileobj=ranged))
                out('read %s: %d of %d bytes fetched' % (name, ranged.fetched, source.size))
    except tool.Bad as exc:
        problems = exc.problems
    except PostError as exc:
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
        post_card(tg, chat, info, sender, where, reply, in_files)
    else:
        text = '\U0001F4E6 <b>%s</b>' % e(name[:-len(SUFFIX)])
        text += '\n%s %s\n%s %s' % (PT, LABELS['pt']['unreadable'], EN, LABELS['en']['unreadable'])
        if sender:
            text += '\n%s / %s: %s' % (LABELS['pt']['by'], LABELS['en']['by'], e(sender))
        tg.message(chat, text, where, reply)
    if not in_files and file_id:
        tg.document(chat, file_id, file_caption(name, size), topic)
        # Onde o zip foi mandado: um aviso curto de onde estao os dados.
        tg.message(chat, '\U0001F4E6 <b>%s</b>\n%s %s\n%s %s' % (e(name[:-len(SUFFIX)]), PT, LABELS['pt']['see'], EN, LABELS['en']['see']),
                   origin or None, message_id)
    return 'posted: %s%s' % (info['name'] if info else name, ' (details unreadable)' if not info else '')


# ── O pacote que veio em partes ──
# Um pacote maior que o arquivo do plano gratuito do Telegram (2 GB) chega em partes, GAME.fliperos-customgame.zip.001,
# .002..., que o painel web faz e a pessoa manda ao grupo. O Worker junta as partes e chama o workflow uma vez so. O robo
# le as partes como o zip inteiro (PartsSource), faz UM card com os dados e responde uma vez a cada parte.

def check_parts(parts):
    """As partes que o Worker juntou (cada uma com message_id, file_id, file_name e file_size): (nome do pacote, as partes
    em ordem, problemas). Cada problema e (portugues, ingles): numeracao com furo ou repetida, ou partes de tamanhos
    diferentes (todas, menos a ultima, tem o mesmo tamanho, e a ultima nao e maior)."""
    found, base, matched = {}, '', 0
    for part in parts:
        match = PART_RE.match(package_file_name(part.get('file_name')))
        if not match:
            continue
        base = base or match.group(1)
        if match.group(1).lower() == base.lower():
            found[int(match.group(2))] = part
            matched += 1
    if not found:
        return '', [], []
    count = max(found)
    problems = []
    missing = ', '.join('%03d' % n for n in range(1, count + 1) if n not in found)
    if missing:
        problems.append((LABELS['pt']['split_missing'] % missing, LABELS['en']['split_missing'] % missing))
    elif matched != len(found):
        problems.append((LABELS['pt']['split_extra'] % count, LABELS['en']['split_extra'] % count))
    else:
        sizes = [int(found[n].get('file_size') or 0) for n in range(1, count + 1)]
        if any(size != sizes[0] for size in sizes[:-1]) or sizes[-1] > sizes[0]:
            problems.append((LABELS['pt']['split_sizes'], LABELS['en']['split_sizes']))
    return base, [found[n] for n in sorted(found)], problems


def part_caption(file_name, size, number, count):
    """A legenda de uma parte: o nome, o tamanho e que parte ela e, nos dois idiomas."""
    return '\U0001F4CE <code>%s</code> · %s\n%s %s · %s %s' % (
        e(file_name), size_text(size), PT, LABELS['pt']['part_of'] % (number, count), EN, LABELS['en']['part_of'] % (number, count))


def part_note(title, file_name, size, number, count, link=''):
    """A resposta a uma parte mandada no topico Files: que parte e, e que os dados estao no card (o nome do pacote leva
    ao card quando ha o link dele)."""
    named = '<a href="%s">%s</a>' % (html.escape(link, quote=True), e(title)) if link else '<b>%s</b>' % e(title)
    return '%s\n%s %s\n%s %s' % (part_caption(file_name, size, number, count), PT, LABELS['pt']['part_note'] % named,
                                 EN, LABELS['en']['part_note'] % named)


def message_link(payload, message_id):
    """O endereco de uma mensagem do grupo (t.me/NOME/ID, ou t.me/c/ID-DO-CHAT/ID num grupo sem nome); vazio se nao da."""
    if not message_id:
        return ''
    username = str(payload.get('chat_username') or '').lstrip('@')
    if username:
        return 'https://t.me/%s/%d' % (username, message_id)
    chat_id = str(payload.get('chat_id') or '')
    return 'https://t.me/c/%s/%d' % (chat_id[4:], message_id) if chat_id.startswith('-100') else ''


def split_problems_text(base, problems):
    out = ['⚠️ <code>%s</code>' % e(base), '%s %s:' % (PT, LABELS['pt']['split_bad'])]
    out += ['• %s' % e(pt) for pt, _ in problems]
    out += ['%s %s:' % (EN, LABELS['en']['split_bad'])]
    out += ['• %s' % e(en) for _, en in problems]
    return '\n'.join(out)[:TEXT_MAX]


def message_id_of(result):
    """O numero da mensagem que o Telegram devolveu (uma mensagem, ou a lista de um album); None se nao veio."""
    if isinstance(result, list):
        result = result[0] if result else None
    return result.get('message_id') if isinstance(result, dict) else None


def post_split_package(tg, payload, env, tool, mtproto_parts=None, out=print):
    """Um pacote que veio em partes: UM card com os dados (o zip das partes juntas, lido pelo MTProto) e uma resposta a
    cada parte. payload: o de um arquivo (chat_id, thread_id, from, username, chat_username) mais parts, a lista de
    {message_id, file_id, file_name, file_size} de cada parte, em qualquer ordem. Mandadas no topico Files, o card responde
    a primeira parte e cada parte ganha a sua resposta; mandadas em outro lugar, o card e as partes (por file_id,
    respondendo ao card) vao para o Files e a primeira parte ganha o aviso de onde estao."""
    chat_id = str(payload.get('chat_id', ''))
    wanted = env.get('TELEGRAM_CHAT_ID') or ''
    if re.fullmatch(r'-?\d+', wanted) and wanted != chat_id:
        return 'skipped: another chat'
    chat = chat_id or wanted or DEFAULT_CHAT
    base, parts, problems = check_parts(payload.get('parts') or [])
    if not base:
        return 'skipped: not a custom game package'
    topic = int(env.get('TELEGRAM_FILES_TOPIC') or FILES_TOPIC)
    origin = int(payload.get('thread_id') or 0)
    first = int(parts[0].get('message_id') or payload.get('message_id') or 0)
    sender = ' '.join(x for x in (str(payload.get('from') or ''), ('(@%s)' % payload['username']) if payload.get('username') else '') if x)
    if problems:
        tg.message(chat, split_problems_text(base, problems), origin or None, first)
        return 'refused: %d problems' % len(problems)
    count = len(parts)
    sizes = [int(p.get('file_size') or 0) for p in parts]
    title = base[:-len(SUFFIX)]
    info, bad, source = None, None, None
    try:
        if mtproto_parts is not None and all(sizes):
            ref = payload.get('chat_username')
            ref = '@' + ref if ref and not ref.startswith('@') else ref or (wanted if wanted.startswith('@') else None) or \
                (int(chat_id) if chat_id else None)
            try:
                source = mtproto_parts(env, ref, parts)
            except Exception as exc:    # o Telethon: sem rede, mensagem que o bot nao acha, chaves erradas...
                out('could not open the parts by MTProto: %s' % exc)
                source = None
        if source is not None:
            ranged = RangeFile(source.size, source.fetch)
            info = read_info(tool, tool.Package(base, fileobj=ranged))
            out('read %s (%d parts): %d of %d bytes fetched' % (base, count, ranged.fetched, source.size))
    except tool.Bad as exc:
        bad = exc.problems
    except PostError as exc:
        out('could not read %s: %s' % (base, exc))
    finally:
        if source is not None:
            source.close()
    if bad:
        tg.message(chat, problems_text(base, bad, sender), origin or None, first)
        return 'refused: %d problems' % len(bad)
    in_files = origin == topic
    where, reply = (origin, first) if in_files else (topic, None)
    if info:
        # base: o nome do zip depois de juntar; source: o das partes como chegaram (o de um cliente que trocou os pontos
        # por "_" e outro).
        info['split'] = {'count': count, 'total': sum(sizes), 'base': base,
                         'source': re.sub(r'\.\d{3}$', '', str(parts[0].get('file_name') or base))}
        title = info['name']
        card = message_id_of(post_card(tg, chat, info, sender, where, reply, in_files))
    else:
        text = '\U0001F4E6 <b>%s</b>\n%s %s\n%s %s' % (e(title), PT, LABELS['pt']['unreadable'], EN, LABELS['en']['unreadable'])
        if sender:
            text += '\n%s / %s: %s' % (LABELS['pt']['by'], LABELS['en']['by'], e(sender))
        card = message_id_of(tg.message(chat, text, where, reply))
    link = message_link(payload, card)
    for number, part in enumerate(parts, 1):
        name, size = str(part['file_name']), int(part.get('file_size') or 0)
        if in_files:
            tg.message(chat, part_note(title, name, size, number, count, link), origin, int(part.get('message_id') or 0) or None)
        elif part.get('file_id'):
            tg.document(chat, part['file_id'], part_caption(name, size, number, count), topic, reply=card)
    if not in_files:
        tg.message(chat, '\U0001F4E6 <b>%s</b>\n%s %s\n%s %s' % (e(title), PT, LABELS['pt']['see'], EN, LABELS['en']['see']),
                   origin or None, first)
    return 'posted: %s (%d parts)%s' % (title, count, '' if info else ' (details unreadable)')


# ── Repostar pelas mensagens ──
# Partes que chegaram ao grupo sem o Worker as tratar (o Worker no ar ainda era o de antes das partes) nao deixam nada
# para repetir: o pedido (message_id, file_name, file_size de cada parte) so existia no Worker. O robo o refaz lendo as
# mensagens pelo MTProto (get_messages por id), e o resto e o caminho de sempre (post_package).

MESSAGES_MAX = 300


def parse_message_ids(text, limit=MESSAGES_MAX):
    """Os numeros das mensagens de um texto: "1708-1719", "1708, 1719" ou links (t.me/grupo/578/1719: vale o ultimo
    numero de cada um). ValueError com algo que nao e nenhum dos tres, ou com mais de LIMIT mensagens."""
    ids = set()
    for token in re.split(r'[\s,;]+', str(text or '').strip()):
        if not token:
            continue
        link = re.search(r'/(\d+)/?(?:\?.*)?$', token) if '/' in token else None
        span = re.fullmatch(r'(\d+)-(\d+)', token)
        if link:
            ids.add(int(link.group(1)))
        elif span:
            low, high = int(span.group(1)), int(span.group(2))
            if high < low or high - low >= limit:
                raise ValueError('a range of up to %d messages, please: %s' % (limit, token))
            ids.update(range(low, high + 1))
        elif token.isdigit():
            ids.add(int(token))
        else:
            raise ValueError('not a message number or link: %s' % token)
        if len(ids) > limit:
            raise ValueError('up to %d messages, please' % limit)
    return sorted(ids)


def part_of_message(message):
    """O que o Worker diria de uma mensagem com arquivo (message_id, file_name, file_size, thread_id, from, username);
    None se ela nao tem arquivo."""
    document = getattr(message, 'document', None)
    if document is None:
        return None
    name = ''
    for attribute in getattr(document, 'attributes', None) or []:
        name = getattr(attribute, 'file_name', None) or name
    reply = getattr(message, 'reply_to', None)
    # Num topico, a mensagem responde ao topico (reply_to_msg_id) ou a outra mensagem dele (reply_to_top_id).
    thread = int(getattr(reply, 'reply_to_top_id', None) or getattr(reply, 'reply_to_msg_id', None) or 0) if reply else 0
    sender = getattr(message, 'sender', None)
    who = ' '.join(x for x in (getattr(sender, 'first_name', None), getattr(sender, 'last_name', None)) if x) or \
        str(getattr(sender, 'title', None) or '')
    return {'message_id': int(message.id), 'file_name': name, 'file_size': int(getattr(document, 'size', 0) or 0),
            'thread_id': thread, 'from': who, 'username': str(getattr(sender, 'username', None) or '')}


def split_requests(found, chat_id='', chat_username=''):
    """Os pedidos de pacotes em partes das mensagens lidas, found = [(id, mensagem ou None)]: (pedidos, avisos). Um pedido
    por pacote, como o do Worker. Uma parte mandada duas vezes vale a mensagem mais nova; o que nao e parte de um
    pacote fica de fora, com um aviso."""
    groups, notes = {}, []
    for number, message in found:
        part = part_of_message(message) if message is not None else None
        if message is None:
            notes.append('message %d: not found (deleted, or the bot cannot see it)' % number)
            continue
        if part is None:
            notes.append('message %d: no file' % number)
            continue
        match = PART_RE.match(package_file_name(part['file_name']))
        if not match:
            notes.append('message %d: %s is not a part of a package, left alone' % (number, part['file_name'] or 'a file'))
            continue
        group = groups.setdefault(match.group(1).lower(), {})
        if int(match.group(2)) not in group or group[int(match.group(2))]['message_id'] < part['message_id']:
            group[int(match.group(2))] = part
    requests = []
    for key, group in groups.items():
        parts = [group[n] for n in sorted(group)]
        # Como o Worker: so um conjunto inteiro (partes de 1 a k sem furo, k >= 2, a ultima menor que a primeira). Um que
        # ainda nao e (as mensagens dadas nao chegam ate a ultima parte) nao vira um card de um zip que nao abre.
        if sorted(group) != list(range(1, len(parts) + 1)) or len(parts) < 2 or parts[-1]['file_size'] >= parts[0]['file_size']:
            notes.append('%s: the parts found (%s) are not a whole package, left alone (give the messages up to its last part)'
                         % (key, ', '.join('%03d' % n for n in sorted(group))))
            continue
        first = min(parts, key=lambda p: p['message_id'])
        requests.append({'chat_id': chat_id, 'chat_username': chat_username, 'thread_id': first['thread_id'],
                         'message_id': first['message_id'], 'from': first['from'], 'username': first['username'],
                         'parts': [{k: p[k] for k in ('message_id', 'file_name', 'file_size')} for p in parts]})
    return requests, notes


class TelethonReader(TelethonSource):
    """So le mensagens por id (o cliente do MTProto, ja entrado como bot)."""

    def __init__(self, token, api_id, api_hash, session_file=''):
        self.connect(token, api_id, api_hash, session_file)

    def messages(self, chat, ids):
        """[(id, mensagem ou None)] de cada id, em lotes de 100."""
        found = []
        for start in range(0, len(ids), 100):
            batch = ids[start:start + 100]
            try:
                got = self.run(self.client.get_messages(chat, ids=batch))
            except Exception as exc:    # RPCError do Telethon
                print('get_messages(%s, %d..%d) failed: %s' % (chat, batch[0], batch[-1], exc))
                got = [None] * len(batch)
            found += list(zip(batch, got if isinstance(got, list) else [got]))
        return found


def recover(spec, env, reader, tg, tool, out=print, mtproto_parts=telethon_parts_source):
    """Refaz o pedido dos pacotes em partes das mensagens de SPEC (numeros, faixas ou links) e os posta como o Worker
    faria. reader.messages(chat, ids) le as mensagens. Devolve o que fez, um item por pacote."""
    ids = parse_message_ids(spec)
    wanted = env.get('TELEGRAM_CHAT_ID') or ''
    chat_id = wanted if re.fullmatch(r'-?\d+', wanted) else ''
    username = (wanted if wanted.startswith('@') else DEFAULT_CHAT).lstrip('@')
    ref = '@' + username
    out('reading %d messages of %s: %s' % (len(ids), ref, ', '.join(str(i) for i in ids[:30]) + (' ...' if len(ids) > 30 else '')))
    found = reader.messages(ref, ids)
    # Um cliente de cada vez com a mesma sessao: o que le as mensagens sai antes de o das partes entrar.
    getattr(reader, 'close', lambda: None)()
    requests, notes = split_requests(found, chat_id, username)
    for note in notes:
        out(note)
    results = []
    for request in requests:
        out('package in parts: %s' % ', '.join('%s (message %d, %d bytes)' % (p['file_name'], p['message_id'], p['file_size'])
                                               for p in request['parts']))
        results.append(post_package(tg, request, env, tool, out=out, mtproto_parts=mtproto_parts))
    return results


# ── Nomes errados no que ja foi postado ──
# O Worker so ve o que chega depois do deploy dele. O --check-names le as mensagens do grupo pelo MTProto (get_messages por
# id: um bot nao pode pedir o historico) e responde a cada pacote com o nome errado como o Worker: um aviso por pacote, com
# todas as partes de quem mandou, na mensagem da primeira. Fica de fora o pacote ja avisado (o bot ja respondeu a uma das
# mensagens dele com o aviso) e o que ja veio de novo com o nome certo.

CHECK_MAX = 50000
CHECK_EMPTY_BATCHES = 3     # "all" para depois de tantos lotes de 100 ids sem nenhuma mensagem (o fim do grupo)
CHECK_LEAD_BATCHES = 20     # ... e desiste se os primeiros tantos lotes vierem vazios (o bot nao ve o grupo)


def read_whole_group(reader, ref, out=print):
    """[(id, mensagem ou None)] do grupo inteiro, do id 1 ate passar do fim."""
    found, start, empty, seen = [], 1, 0, False
    while start <= CHECK_MAX:
        batch = reader.messages(ref, list(range(start, start + 100)))
        found += batch
        start += 100
        if any(message is not None for _, message in batch):
            seen, empty = True, 0
        else:
            empty += 1
        if (seen and empty >= CHECK_EMPTY_BATCHES) or (not seen and empty >= CHECK_LEAD_BATCHES):
            break
    out('read the messages 1..%d of %s' % (start - 1, ref))
    return found


def same_package_key(stem, number):
    """O que sobra de um nome de pacote quando se tiram os separadores que um programa troca por "_" (e as maiusculas):
    "JoJo's Battle R" e "JoJo_s_Battle_R" dao o mesmo."""
    return re.sub(r'[\W_]+', '', stem).lower(), number


def bad_name_sets(found):
    """Os pacotes com o nome errado nas mensagens lidas, found = [(id, mensagem ou None)]: [(partes, aviso, ja veio certo)],
    cada parte um dict de part_of_message com stem e n (o numero da parte; None num zip inteiro). aviso: (id, texto sem a
    formatacao) da resposta que o bot ja deu a uma das partes, ou None. "Ja veio certo": cada arquivo voltou com o nome
    certo, ou com o mesmo nome a menos de pontuacao e maiusculas."""
    sets, warned, good = {}, {}, set()
    for _, message in found:
        if message is None:
            continue
        reply = getattr(message, 'reply_to', None)
        if getattr(message, 'out', False):
            # Um aviso que o bot ja deu: a resposta a mensagem de uma das partes.
            text = str(getattr(message, 'message', None) or '')
            if reply is not None and BAD_NAME_TITLE in text:
                warned[int(getattr(reply, 'reply_to_msg_id', None) or 0)] = (int(message.id), text)
            continue
        if getattr(getattr(message, 'sender', None), 'bot', False):
            continue
        part = part_of_message(message)
        if part is None:
            continue
        good_part = PART_RE.fullmatch(part['file_name'])
        if good_part:
            good.add(same_package_key(good_part.group(1)[:-len(SUFFIX)], int(good_part.group(2))))
            continue
        if part['file_name'].lower().endswith(SUFFIX):
            good.add(same_package_key(part['file_name'][:-len(SUFFIX)], None))
            continue
        loose = loose_package_name(part['file_name'])
        if loose is None:
            continue
        stem, number = loose
        group = sets.setdefault((getattr(message, 'sender_id', None), stem.lower(), number is None), {})
        # A mesma parte mandada duas vezes: vale a primeira (e a ela que o aviso responde).
        if number not in group or group[number]['message_id'] > part['message_id']:
            group[number] = dict(part, stem=stem, n=number)
    result = []
    for group in sets.values():
        parts = [group[n] for n in sorted(group, key=lambda n: -1 if n is None else n)]
        warning = next((warned[p['message_id']] for p in parts if p['message_id'] in warned), None)
        result.append((parts, warning, all(same_package_key(p['stem'], p['n']) in good for p in parts)))
    return sorted(result, key=lambda item: min(p['message_id'] for p in item[0]))


def check_names(spec, env, reader, tg, out=print):
    """Responde a cada pacote com o nome errado nas mensagens de SPEC ("all": o grupo inteiro; ou numeros, faixas, links).
    Devolve uma linha por pacote achado."""
    wanted = env.get('TELEGRAM_CHAT_ID') or ''
    ref = '@' + (wanted if wanted.startswith('@') else DEFAULT_CHAT).lstrip('@')
    chat = wanted or DEFAULT_CHAT
    if str(spec or '').strip().lower() == 'all':
        found = read_whole_group(reader, ref, out)
    else:
        ids = parse_message_ids(spec, CHECK_MAX)
        out('reading %d messages of %s' % (len(ids), ref))
        found = reader.messages(ref, ids)
    getattr(reader, 'close', lambda: None)()
    results = []
    for parts, warning, resent in bad_name_sets(found):
        label = ', '.join('%s (message %d)' % (p['file_name'], p['message_id']) for p in parts)
        text = bad_name_text([(p['file_name'], short_package_name(p['stem'], p['n'])) for p in parts],
                             any(name_too_long(right_package_name(p['stem'], p['n'])) for p in parts))
        if warning and plain_text(text) == warning[1]:
            results.append('already warned: ' + label)
        elif warning:
            # O aviso de antes, com um texto que mudou (o nome curto, por exemplo): o bot o edita, nada novo no grupo.
            tg.edit(chat, warning[0], text)
            results.append('updated the warning %d: %s' % (warning[0], label))
        elif resent:
            results.append('sent again with the right name: ' + label)
        else:
            first = min(parts, key=lambda p: p['message_id'])
            tg.message(chat, text, first['thread_id'] or None, first['message_id'])
            results.append('warned: ' + label)
        out(results[-1])
    return results


def plain_text(text):
    """O texto de uma mensagem HTML como o MTProto o devolve (message.message): sem as marcas."""
    return html.unescape(re.sub(r'<[^>]+>', '', text))


def check_main(spec, no_post=False, dry_run=False):
    """--check-names-env: procura os pacotes postados com o nome errado e responde a cada um com o nome certo."""
    env = dict(os.environ)
    try:
        if str(spec or '').strip().lower() != 'all' and not parse_message_ids(spec, CHECK_MAX):
            raise ValueError('give "all" or the messages to check')
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if dry_run:
        print('dry run: would check the file names of the messages %s' % str(spec).strip())
        return 0
    if not (env.get('TELEGRAM_BOT_TOKEN') and env.get('TELEGRAM_API_ID') and env.get('TELEGRAM_API_HASH')):
        print('reading old messages needs TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID and TELEGRAM_API_HASH', file=sys.stderr)
        return 1
    try:
        reader = TelethonReader(env['TELEGRAM_BOT_TOKEN'], env['TELEGRAM_API_ID'], env['TELEGRAM_API_HASH'],
                                env.get('TELEGRAM_SESSION_FILE') or '')
    except ImportError:
        print('telethon is not installed', file=sys.stderr)
        return 1
    try:
        results = check_names(spec, env, reader, (PrintOnly if no_post else Telegram)(env['TELEGRAM_BOT_TOKEN']))
    except PostError as exc:
        print(exc, file=sys.stderr)
        return 1
    print('%d package(s) with a wrong file name, %d warned now, %d warnings updated' % (
        len(results), sum(r.startswith('warned') for r in results), sum(r.startswith('updated') for r in results)))
    return 0


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


def recover_main(spec, no_post=False, dry_run=False):
    """--messages-env: refaz e posta os pacotes em partes das mensagens dadas (precisa do MTProto: as partes sao grandes)."""
    env = dict(os.environ)
    try:
        ids = parse_message_ids(spec)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not ids:
        print('no messages given', file=sys.stderr)
        return 1
    if dry_run:
        print('dry run: would read the messages %s' % ', '.join(str(i) for i in ids))
        return 0
    if not (env.get('TELEGRAM_BOT_TOKEN') and env.get('TELEGRAM_API_ID') and env.get('TELEGRAM_API_HASH')):
        print('reading old messages needs TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID and TELEGRAM_API_HASH', file=sys.stderr)
        return 1
    try:
        reader = TelethonReader(env['TELEGRAM_BOT_TOKEN'], env['TELEGRAM_API_ID'], env['TELEGRAM_API_HASH'],
                                env.get('TELEGRAM_SESSION_FILE') or '')
    except ImportError:
        print('telethon is not installed', file=sys.stderr)
        return 1
    try:
        results = recover(spec, env, reader, (PrintOnly if no_post else Telegram)(env['TELEGRAM_BOT_TOKEN']), load_tool())
    except PostError as exc:
        print(exc, file=sys.stderr)
        return 1
    for result in results:
        print(result)
    if not results:
        print('no package in parts found in those messages', file=sys.stderr)
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description='Posta um pacote de jogo custom no topico Files do grupo do Telegram.')
    parser.add_argument('--zip', help='so mostra o post de um zip do disco')
    parser.add_argument('--out', help='com --zip: onde salvar as imagens')
    parser.add_argument('--payload-env', help='a variavel de ambiente com o JSON do pacote mandado ao grupo')
    parser.add_argument('--payload-file', help='o mesmo, num arquivo')
    parser.add_argument('--dry-run', action='store_true', help='confere o pedido e nao fala com o Telegram')
    parser.add_argument('--no-post', action='store_true', help='le o pacote de verdade, mas so mostra o post no log (nada vai ao grupo)')
    parser.add_argument('--messages-env', help='a variavel de ambiente com as mensagens das partes de um pacote que o Worker nao tratou '
                                               '(numeros, faixas como 1708-1719 ou links): o robo as le e posta o card')
    parser.add_argument('--check-names-env', help='a variavel de ambiente com as mensagens a conferir ("all" ou numeros, faixas, '
                                                  'links): cada pacote postado com o nome errado ganha uma resposta com o certo')
    args = parser.parse_args()
    if args.zip:
        preview(args.zip, args.out)
        return 0
    if args.check_names_env:
        return check_main(os.environ.get(args.check_names_env, ''), args.no_post, args.dry_run)
    if args.messages_env:
        return recover_main(os.environ.get(args.messages_env, ''), args.no_post, args.dry_run)
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
