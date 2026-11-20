#!/usr/bin/env python3
# Os sons do FliperOS: os seis eventos (o cursor andando, entrar, voltar,
# abrir o jogo, fechar o jogo e o dialogo de alerta) e a trilha do frontend.
# O mesmo codigo serve o Setup (Audio > Menu sounds) e o frontend (Tab >
# Frontend options > Frontend sounds): cada um tem o seu conjunto de arquivos
# e de volumes, e eles tem de ser espelho um do outro.
#
# Os arquivos ficam em ~/media/fliperos-sounds (a trilha, em music/); os
# padrao (gui/sounds/*.wav, feitos por tools/make-default-sounds.py) sao
# copiados para la na primeira vez (seed), para a pessoa ver e trocar. Um
# evento sem arquivo escolhido toca o padrao; "off" fica mudo.
#
# Como programa (o shell do Setup usa):
#   fesound.py seed                  copia os sons padrao para a pasta
#   fesound.py status menu           uma linha por evento: id, rotulo, arquivo, volume
#   fesound.py menu-env              as GUM_SOUND_MOVE/SELECT, no volume de cada um
#   fesound.py play menu EVENTO      toca um evento do menu (aplay, em segundo plano)
#   fesound.py play-file ARQ [VOL]   toca um arquivo qualquer
#   fesound.py music-list [PASTA]    as faixas da pasta (ou da trilha padrao)
#   fesound.py alsa-latency [PCM]    o atraso do som no ALSA (o do video de preview)

import array
import hashlib
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import time
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.environ.get("FLIPEROS_SOUNDS_BUNDLED") or os.path.join(HERE, "sounds")
CONF = os.environ.get("FLIPEROS_CONF", "/etc/fliperos/fliperos.conf")
# Os sons que a pessoa punha em /opt/fliperos/sounds/menu antes dos eventos
# (move.wav e select.wav): enquanto nada foi escolhido, eles ainda valem.
LEGACY = os.environ.get("FLIPEROS_MENU_SOUNDS", "/opt/fliperos/sounds/menu")
LEGACY_NAMES = {"move": "move.wav", "enter": "select.wav"}
FFMPEG = os.environ.get("FLIPEROS_FFMPEG", "ffmpeg")

# Os eventos, na ordem das telas: id, rotulo e o que cada um e.
EVENTS = ("move", "enter", "back", "open", "close", "alert")
LABELS = {"move": "Browse", "enter": "Enter", "back": "Back", "open": "Open game", "close": "Close game",
          "alert": "Alert dialog"}
HINTS = {"move": "Plays when the cursor moves through a list.",
         "enter": "Plays when you go into something: Enter, a menu, a choice.",
         "back": "Plays when you go back: Esc, Return, a closed menu.",
         "open": "Plays when a game is opened.",
         "close": "Plays when the game closes and you come back.",
         "alert": "Plays when an alert or a question opens."}
DEFAULT_FILE = {"move": "browse.wav", "enter": "enter.wav", "back": "back.wav", "open": "open-game.wav",
                "close": "close-game.wav", "alert": "alert.wav"}
DEFAULT_VOLUME = {"move": 60, "enter": 80, "back": 80, "open": 90, "close": 90, "alert": 90}
MUSIC_VOLUME, PREVIEW_VOLUME = 40, 100
# O que se escolhe como som (e como musica).
EXTS = (".wav", ".ogg", ".mp3", ".flac")
# A primeira musica da trilha: a de BurtySounds, que a pessoa baixou do
# Pixabay (Pixabay Content License) e pos em music/. Nao vem no repositorio.
DEFAULT_TRACK = "BurtySounds - Retrowave.mp3"
# Um som de evento maior que isso (ou que nao e WAV) e decodificado pelo ffmpeg
# antes, so os primeiros EVENT_SECONDS: o mixer guarda o som todo na memoria.
EVENT_MAX_BYTES, EVENT_SECONDS = 2 * 1024 * 1024, 10


# ── As pastas ─────────────────────────────────────────────────────

def sounds_dir():
    return os.environ.get("FLIPEROS_SOUNDS_DIR") or os.path.join(os.path.expanduser("~"), "media", "fliperos-sounds")


def music_dir():
    return os.path.join(sounds_dir(), "music")


def cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "fliperos", "sounds")


def _own(path, ref):
    """Com o root (o Setup), o que ele cria fica do dono da pasta de cima: no
    ~ do gabinete, o usuario, nao o root. Num disco que nao tem dono, nada."""
    if os.geteuid() != 0:
        return
    try:
        st = os.stat(ref)
        os.chown(path, st.st_uid, st.st_gid)
    except OSError:
        pass


def make_dirs(path):
    """makedirs, com cada pasta nova do dono da primeira que ja existia."""
    missing = []
    here = path
    while here and not os.path.isdir(here):
        missing.append(here)
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    for folder in reversed(missing):
        os.mkdir(folder)
        _own(folder, here)


def seed():
    """Copia os sons padrao para ~/media/fliperos-sounds (so os que faltam) e
    cria a pasta music. Um disco so de leitura ou cheio: o padrao segue
    tocando do gui/sounds. Devolve quantos arquivos copiou."""
    copied = 0
    try:
        make_dirs(music_dir())
    except OSError:
        return 0
    for name in DEFAULT_FILE.values():
        src, dst = os.path.join(BUNDLED, name), os.path.join(sounds_dir(), name)
        if os.path.exists(dst) or not os.path.isfile(src):
            continue
        try:
            shutil.copyfile(src, dst)
            _own(dst, sounds_dir())
            copied += 1
        except OSError:
            break
    return copied


# ── Quais arquivos ────────────────────────────────────────────────

def default_file(event, menu=False):
    """O som padrao do evento: (no menu) o move.wav/select.wav de antes, o da
    pasta fliperos-sounds, o que vem no sistema."""
    names = []
    if menu and event in LEGACY_NAMES:
        names.append(os.path.join(LEGACY, LEGACY_NAMES[event]))
    names += [os.path.join(sounds_dir(), DEFAULT_FILE[event]), os.path.join(BUNDLED, DEFAULT_FILE[event])]
    return next((n for n in names if os.path.isfile(n)), None)


def resolve(event, value, menu=False):
    """O arquivo que o evento toca: value vazio e o padrao, "off" nenhum, e
    um arquivo que sumiu (o disco saiu) cai no padrao."""
    if value == "off":
        return None
    if value and os.path.isfile(value):
        return value
    return default_file(event, menu)


def describe(value):
    """O arquivo, para a tela: DEFAULT, OFF ou o nome."""
    if value == "off":
        return "OFF"
    return os.path.basename(value) if value else "DEFAULT"


def clamp(value, default):
    try:
        return max(0, min(100, int(float(value))))
    except (TypeError, ValueError):
        return default


# ── Onde ficam as escolhas ────────────────────────────────────────

def read_conf(path=None):
    values = {}
    try:
        with open(path or CONF, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip()
    except OSError:
        pass
    return values


class Menu:
    """Os sons do menu do Setup: menu_sound_EVENTO (o arquivo, "off" ou vazio)
    e menu_sound_EVENTO_volume no fliperos.conf; menu_sounds=off desliga tudo."""

    scope = "menu"
    menu = True

    def __init__(self, values=None):
        self.values = read_conf() if values is None else values

    def enabled(self):
        return self.values.get("menu_sounds") != "off"

    def file(self, event):
        return self.values.get("menu_sound_" + event, "")

    def volume(self, event):
        return clamp(self.values.get("menu_sound_%s_volume" % event), DEFAULT_VOLUME[event])


class Frontend:
    """Os sons do frontend: o "sounds" do frontend.json, {"move": {"file": "",
    "volume": 60}, ..., "music": {"source": "", "volume": 40}, "preview":
    100}. Guarda o proprio dicionario: quem muda (o frontend) grava depois."""

    scope = "frontend"
    menu = False

    def __init__(self, data=None):
        self.data = data if isinstance(data, dict) else {}

    def enabled(self):
        return True

    def entry(self, event):
        """O dicionario do evento (so para ler: um evento sem nada fica fora)."""
        item = self.data.get(event)
        return item if isinstance(item, dict) else {}

    def writable(self, event):
        """O dicionario do evento, criado se faltava (para gravar)."""
        item = self.data.get(event)
        if not isinstance(item, dict):
            item = self.data[event] = {}
        return item

    def file(self, event):
        value = self.entry(event).get("file", "")
        return value if isinstance(value, str) else ""

    def volume(self, event):
        return clamp(self.entry(event).get("volume"), DEFAULT_VOLUME[event])

    def set_file(self, event, value):
        self.writable(event)["file"] = value

    def set_volume(self, event, value):
        self.writable(event)["volume"] = clamp(value, DEFAULT_VOLUME[event])

    def music_source(self):
        value = self.entry("music").get("source", "")
        return value if isinstance(value, str) else ""

    def music_volume(self):
        return clamp(self.entry("music").get("volume"), MUSIC_VOLUME)

    def music_pause(self):
        """A trilha para enquanto um video de preview com som toca? Desligado
        por padrao: a trilha e o som do video tocam juntos."""
        return self.entry("music").get("pause") is True

    def set_music_pause(self, value):
        self.writable("music")["pause"] = bool(value)

    def preview_volume(self):
        return clamp(self.data.get("preview"), PREVIEW_VOLUME)

    def set_music_source(self, value):
        self.writable("music")["source"] = value

    def set_music_volume(self, value):
        self.writable("music")["volume"] = clamp(value, MUSIC_VOLUME)

    def set_preview_volume(self, value):
        self.data["preview"] = clamp(value, PREVIEW_VOLUME)



# ── Decodificar e mudar o volume (gum e aplay) ────────────────────

def _signature(path, extra):
    st = os.stat(path)
    return hashlib.sha1(("%s|%d|%d|%s" % (path, st.st_mtime_ns, st.st_size, extra)).encode()).hexdigest()[:16]


def decoded(path):
    """Um WAV de 16 bits do arquivo, no cache: o proprio arquivo se ja e um
    WAV pequeno, senao o ffmpeg decodifica (so os primeiros EVENT_SECONDS).
    None se nao deu."""
    try:
        if path.lower().endswith(".wav") and os.path.getsize(path) <= EVENT_MAX_BYTES:
            try:
                with wave.open(path, "rb") as w:
                    if w.getsampwidth() == 2 and w.getcomptype() == "NONE":
                        return path
            except (EOFError, wave.Error):
                pass         # 8 ou 24 bits, ou um formato que o wave nao le: o ffmpeg decodifica
        out = os.path.join(cache_dir(), _signature(path, "dec") + ".wav")
        if os.path.isfile(out):
            return out
        if not shutil.which(FFMPEG):
            return None
        os.makedirs(cache_dir(), exist_ok=True)
        tmp = out + ".%d.tmp.wav" % os.getpid()
        subprocess.run([FFMPEG, "-nostdin", "-loglevel", "error", "-y", "-i", path, "-t", str(EVENT_SECONDS),
                        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", tmp], stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=True)
        os.replace(tmp, out)
        return out
    except (OSError, EOFError, wave.Error, subprocess.SubprocessError):
        return None


def prepared(path, volume):
    """Um WAV do arquivo no volume pedido (0 a 100), para o gum e o aplay, que
    so tocam o arquivo como esta. 100: o proprio arquivo (ou o decodificado).
    None: mudo ou nao deu."""
    if volume <= 0 or not path:
        return None
    source = decoded(path)
    if not source or volume >= 100:
        return source
    out = os.path.join(cache_dir(), _signature(source, "vol%d" % volume) + ".wav")
    if os.path.isfile(out):
        return out
    try:
        with wave.open(source, "rb") as w:
            params = w.getparams()
            samples = array.array("h")
            samples.frombytes(w.readframes(w.getnframes()))
        if sys.byteorder == "big":
            samples.byteswap()
        gain = volume / 100.0
        scaled = array.array("h", (max(-32768, min(32767, int(v * gain))) for v in samples))
        if sys.byteorder == "big":
            scaled.byteswap()
        os.makedirs(cache_dir(), exist_ok=True)
        tmp = out + ".%d.tmp" % os.getpid()
        with wave.open(tmp, "wb") as w:
            w.setparams(params)
            w.writeframes(scaled.tobytes())
        os.replace(tmp, out)
        return out
    except (OSError, EOFError, wave.Error):
        return None


def play_file(path, volume=100):
    """Toca um arquivo no volume pedido (aplay, em segundo plano: nao espera).
    False se nao ha o que tocar."""
    out = prepared(path, volume)
    if not out or not shutil.which("aplay"):
        return False
    try:
        subprocess.Popen(["aplay", "-q", out], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError:
        return False
    return True


def gum_env(settings=None):
    """As variaveis do gum (GUM_SOUND_MOVE e GUM_SOUND_SELECT, o "enter"),
    uma "NOME=arquivo" por linha: o gum toca o arquivo como esta, entao ja vai
    no volume do evento."""
    settings = settings or Menu()
    lines = []
    if settings.enabled():
        for event, name in (("move", "GUM_SOUND_MOVE"), ("enter", "GUM_SOUND_SELECT")):
            out = prepared(resolve(event, settings.file(event), True), settings.volume(event))
            if out:
                lines.append("%s=%s" % (name, out))
    return lines


# ── O titulo de uma faixa ─────────────────────────────────────────

def _id3_text(body):
    codec = {0: "latin-1", 1: "utf-16", 2: "utf-16-be", 3: "utf-8"}.get(body[:1][0] if body else 0, "latin-1")
    return body[1:].decode(codec, "replace").replace("\x00", " ").strip()


def id3_tags(path):
    """O titulo e o artista da tag ID3v2 de um MP3 ({} sem tag)."""
    tags = {}
    try:
        with open(path, "rb") as f:
            head = f.read(10)
            if head[:3] != b"ID3" or len(head) < 10:
                return tags
            version = head[3]
            size = (head[6] << 21) | (head[7] << 14) | (head[8] << 7) | head[9]
            data = f.read(min(size, 4 * 1024 * 1024))
    except OSError:
        return tags
    ids = {"TIT2": "title", "TPE1": "artist", "TT2": "title", "TP1": "artist"}
    pos = 0
    width = 6 if version == 2 else 10
    while pos + width <= len(data):
        fid = data[pos:pos + (3 if version == 2 else 4)]
        if not fid.strip(b"\x00"):
            break
        if version == 2:
            n = (data[pos + 3] << 16) | (data[pos + 4] << 8) | data[pos + 5]
        elif version == 4:
            n = (data[pos + 4] << 21) | (data[pos + 5] << 14) | (data[pos + 6] << 7) | data[pos + 7]
        else:
            n = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        key = ids.get(fid.decode("latin-1", "replace"))
        if key and n:
            text = _id3_text(data[pos + width:pos + width + n])
            if text:
                tags[key] = text
        pos += width + n
    return tags


def title_of(path):
    """O nome da faixa para o aviso: "Artista - Titulo" da tag ID3 quando ha;
    senao o nome do arquivo sem a extensao (um nome todo em minusculas com
    tracos, "artista-titulo-181955" do Pixabay, vira "Artista Titulo")."""
    tags = id3_tags(path) if path.lower().endswith(".mp3") else {}
    if tags.get("title"):
        return "%s - %s" % (tags["artist"], tags["title"]) if tags.get("artist") else tags["title"]
    stem = os.path.splitext(os.path.basename(path))[0]
    stem = re.sub(r"[-_ ]\d{4,}$", "", stem)
    if stem == stem.lower() and re.search(r"[-_]", stem):
        stem = " ".join(w.capitalize() for w in re.split(r"[-_ ]+", stem) if w)
    return stem.replace("_", " ").strip() or os.path.basename(path)


# ── A trilha ──────────────────────────────────────────────────────

def music_files(folder):
    """As faixas de uma pasta (sem entrar nas outras), em ordem de nome."""
    try:
        names = sorted(os.listdir(folder), key=str.lower)
    except OSError:
        return []
    return [os.path.join(folder, n) for n in names
            if n.lower().endswith(EXTS) and not n.startswith(".") and os.path.isfile(os.path.join(folder, n))]


def music_plan(source):
    """O que tocar: (as faixas, a primeira ou None). source: "" = a pasta
    music, com a BurtySounds primeiro; "off" nada; um arquivo, so ele; uma
    pasta, as faixas dela sorteadas."""
    if source == "off":
        return [], None
    if source and os.path.isfile(source):
        return [source], source
    folder = source if source and os.path.isdir(source) else music_dir()
    files = music_files(folder)
    first = None
    if not source or folder == music_dir():
        first = next((f for f in files if os.path.basename(f) == DEFAULT_TRACK), None)
    return files, first


def pick_next(files, last, first=None, rng=random):
    """A proxima faixa: a primeira pedida (so na abertura) e, depois, uma
    sorteada que nao e a que acabou de tocar."""
    if first:
        return first
    if not files:
        return None
    pool = [f for f in files if f != last] or files
    return rng.choice(pool)


def alsa_latency(device="default", rate=48000, chunk=1024, blocks=30):
    """Quantos segundos o som leva do instante em que e escrito ate soar no
    ALSA `device`, como o ffmpeg do video de preview o escreve (em tempo real,
    blocos de 1024 quadros). Escreve silencio por uns 0,65 s e le o
    snd_pcm_delay: com o dmix do "Live screen sound" (o fliperos_tee, buffer de
    16384) o som so comeca com a fila cheia e fica uns 320 ms atras da imagem.
    None se nao deu (sem libasound, o ALSA nao abre)."""
    try:
        import ctypes
        lib = ctypes.CDLL("libasound.so.2")
        pcm = ctypes.c_void_p()
        if lib.snd_pcm_open(ctypes.byref(pcm), device.encode(), 0, 0) < 0:
            return None
        try:
            # S16_LE, intercalado, estereo, com reamostragem, 500 ms pedidos (o que o ffmpeg pede).
            if lib.snd_pcm_set_params(pcm, 2, 3, 2, rate, 1, 500000) < 0:
                return None
            silence_block = (ctypes.c_short * (chunk * 2))()
            delay = ctypes.c_long()
            start, step, seen = time.monotonic(), chunk / rate, []
            for i in range(blocks):
                wait = start + i * step - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                lib.snd_pcm_delay(pcm, ctypes.byref(delay))
                before = delay.value
                written = lib.snd_pcm_writei(pcm, silence_block, chunk)
                if written < 0:
                    lib.snd_pcm_recover(pcm, written, 1)
                    continue
                if i >= blocks - 8:
                    seen.append(before)
            lib.snd_pcm_drop(pcm)
        finally:
            lib.snd_pcm_close(pcm)
        if not seen:
            return None
        seen.sort()
        return max(0.0, seen[len(seen) // 2] / rate)
    except (OSError, AttributeError, ValueError, TypeError):
        return None


def audio_opens(pygame):
    """O som abre num processo filho antes de abrir aqui: um asound.conf
    quebrado faz o ALSA abortar o processo (um assert, nao uma excecao).
    Assim o menu ou o frontend fica, so sem som. Com o mixer ja aberto neste
    processo (o pygame.init() do frontend o abre), nao ha o que testar: o filho
    fecharia o PCM que o pai esta usando."""
    try:
        if pygame.mixer.get_init():
            return True
    except pygame.error:
        pass
    try:
        pid = os.fork()
    except (OSError, AttributeError):
        return True
    if pid == 0:
        code = 1
        try:
            pygame.mixer.init()
            pygame.mixer.quit()
            code = 0
        finally:
            os._exit(code)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            ok = os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
            if not ok:
                print("fesound: o som nao abriu (status %d): sem som" % status, file=sys.stderr)
            return ok
        time.sleep(0.02)
    os.kill(pid, 9)
    os.waitpid(pid, 0)
    print("fesound: o som nao respondeu: sem som", file=sys.stderr)
    return False


def ensure_mixer(pygame):
    """O mixer aberto (o frontend o fecha antes de cada jogo). False: sem som."""
    try:
        if pygame.mixer.get_init():
            return True
        pygame.mixer.init(44100, -16, 2, 512)
        pygame.mixer.set_num_channels(16)
        return True
    except pygame.error:
        return False


class Bank:
    """Os seis sons de um conjunto (Menu ou Frontend) carregados no mixer do
    pygame, cada um no volume dele."""

    GAP = 0.03                  # nao toca o mesmo som duas vezes em menos que isso

    def __init__(self, pygame, settings):
        self.pg, self.settings = pygame, settings
        self.sounds = {}
        self.last = {}
        self.usable = True      # False: o som nao abriu (audio_opens); fica mudo

    def reload(self):
        """Le de novo o arquivo e o volume de cada evento (o Setup mudou)."""
        pg = self.pg
        self.sounds = {}
        if not self.usable or not self.settings.enabled() or not ensure_mixer(pg):
            return
        for event in EVENTS:
            sound = self.load(resolve(event, self.settings.file(event), self.settings.menu),
                              self.settings.volume(event))
            if sound:
                self.sounds[event] = sound

    def reload_one(self, event):
        """So o arquivo e o volume de um evento (a pessoa mexeu nele)."""
        self.sounds.pop(event, None)
        if not self.usable or not self.settings.enabled() or not ensure_mixer(self.pg):
            return
        sound = self.load(resolve(event, self.settings.file(event), self.settings.menu), self.settings.volume(event))
        if sound:
            self.sounds[event] = sound

    def play_outside(self, event):
        """Toca o evento num aplay a parte: o som segue depois de o mixer
        fechar (o frontend o fecha antes de abrir um jogo)."""
        if self.usable and self.settings.enabled():
            play_file(resolve(event, self.settings.file(event), self.settings.menu), self.settings.volume(event))

    def load(self, path, volume):
        if not path or volume <= 0:
            return None
        source = decoded(path)
        if not source:
            return None
        try:
            sound = self.pg.mixer.Sound(source)
        except self.pg.error:
            return None
        sound.set_volume(volume / 100.0)
        return sound

    def play(self, event):
        sound = self.sounds.get(event)
        now = time.monotonic()
        if sound and now - self.last.get(event, 0.0) >= self.GAP:
            self.last[event] = now
            try:
                sound.play()
            except self.pg.error:
                pass

    def play_file(self, path, volume):
        """Um arquivo avulso (a escolha na tela: ouvir antes de ficar)."""
        if self.usable and ensure_mixer(self.pg):
            sound = self.load(path, volume)
            if sound:
                sound.play()


class Music:
    """A trilha do frontend (pygame.mixer.music): toca a fonte (uma faixa, uma
    pasta sorteada ou a pasta padrao), passa para a proxima sozinha e conta o
    nome de cada uma que comeca (tick)."""

    def __init__(self, pygame, source="", volume=MUSIC_VOLUME):
        self.pg = pygame
        self.source, self.volume = source, volume
        self.files, self.first = [], None
        self.current, self.last = None, None
        self.held = False        # parada de proposito (um video com som, um jogo)
        self.failed = set()
        self.usable = True
        self.rng = random.Random()
        self.plan()

    def plan(self):
        self.files, self.first = music_plan(self.source)

    def configure(self, source, volume):
        """Fonte ou volume novos: o volume vale na hora; a fonte, desde o
        comeco dela."""
        if volume != self.volume:
            self.volume = volume
            self.apply_volume()
        if source != self.source:
            self.source = source
            self.stop()
            self.failed.clear()
            self.plan()

    def apply_volume(self):
        try:
            if self.pg.mixer.get_init():
                self.pg.mixer.music.set_volume(self.volume / 100.0)
        except self.pg.error:
            pass

    def stop(self):
        self.current = None
        try:
            if self.pg.mixer.get_init():
                self.pg.mixer.music.stop()
        except self.pg.error:
            pass

    def hold(self, on):
        """Para a trilha onde esta (on) ou continua. Um video com som e o jogo."""
        if on == self.held:
            return
        self.held = on
        try:
            if self.pg.mixer.get_init() and self.current:
                (self.pg.mixer.music.pause if on else self.pg.mixer.music.unpause)()
        except self.pg.error:
            pass

    def playing(self):
        try:
            return bool(self.current) and self.pg.mixer.get_init() and self.pg.mixer.music.get_busy()
        except self.pg.error:
            return False

    def start_track(self, path):
        """Abre a faixa. True se tocou; senao (nao abre, formato que o mixer
        nao le) tenta pelo ffmpeg e, se nao der, marca como falha."""
        pg = self.pg
        for candidate in (path, None):
            if candidate is None:
                candidate = self.convert(path)
                if not candidate:
                    break
            try:
                pg.mixer.music.load(candidate)
                pg.mixer.music.set_volume(self.volume / 100.0)
                pg.mixer.music.play()
                return True
            except pg.error:
                continue
        self.failed.add(path)
        return False

    def convert(self, path):
        """A faixa em WAV pelo ffmpeg (no cache), quando o mixer nao le o
        formato dela. Demora o tamanho dela: so em caso de falha."""
        out = os.path.join(cache_dir(), _signature(path, "music") + ".wav")
        if os.path.isfile(out):
            return out
        if not shutil.which(FFMPEG):
            return None
        try:
            os.makedirs(cache_dir(), exist_ok=True)
            tmp = out + ".%d.tmp.wav" % os.getpid()
            subprocess.run([FFMPEG, "-nostdin", "-loglevel", "error", "-y", "-i", path, "-vn", "-acodec", "pcm_s16le",
                            tmp], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=300, check=True)
            os.replace(tmp, out)
            return out
        except (OSError, subprocess.SubprocessError):
            return None

    def tick(self):
        """Chamado a cada quadro: quando a faixa acaba (ou ainda nao comecou),
        poe a proxima. Devolve o titulo da faixa que comecou agora, senao None."""
        if self.held or not self.usable or not self.files or self.source == "off":
            return None
        if self.playing():
            return None
        if not ensure_mixer(self.pg):
            return None
        pool = [f for f in self.files if f not in self.failed]
        for _ in range(len(pool)):
            if self.current is None and self.first and self.first not in self.failed:
                path = pick_next(pool, self.last, self.first)
                self.first = None
            else:
                path = pick_next(pool, self.last, None, self.rng)
            if not path:
                return None
            self.last = path
            if self.start_track(path):
                self.current = path
                return title_of(path)
            pool = [f for f in pool if f != path]
        self.files = []     # nenhuma tocou: nao tenta a cada quadro
        return None


# ── O programa (o shell do Setup) ─────────────────────────────────

def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "seed":
        seed()
        return 0
    if cmd == "status" and len(argv) >= 2 and argv[1] == "menu":
        settings = Menu()
        for event in EVENTS:
            print("%s\t%s\t%s\t%d" % (event, LABELS[event], describe(settings.file(event)), settings.volume(event)))
        return 0
    if cmd == "menu-env":
        for line in gum_env():
            print(line)
        return 0
    if cmd == "play" and len(argv) >= 3 and argv[1] == "menu" and argv[2] in EVENTS:
        settings = Menu()
        if settings.enabled():
            play_file(resolve(argv[2], settings.file(argv[2]), True), settings.volume(argv[2]))
        return 0
    if cmd == "play-file" and len(argv) >= 2:
        return 0 if play_file(argv[1], clamp(argv[2] if len(argv) > 2 else 100, 100)) else 1
    if cmd == "alsa-latency":
        seconds = alsa_latency(argv[1] if len(argv) > 1 else "default")
        print("unknown" if seconds is None else "%d ms" % round(seconds * 1000))
        return 0 if seconds is not None else 1
    if cmd == "music-list":
        files, first = music_plan(argv[1] if len(argv) > 1 else "")
        for path in ([first] if first else []) + [f for f in files if f != first]:
            print("%s\t%s" % (path, title_of(path)))
        return 0
    print(__doc__ or "", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
