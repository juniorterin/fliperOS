# O video do jogo no frontend do FliperOS (~/media/preview/<pasta>/<set>.mp4):
# o ffmpeg decodifica em quadros RGB do tamanho do quadro da tela, num pipe,
# no ritmo do proprio video (-re), em loop, e manda o som para o ALSA
# (default, o mesmo dmix dos jogos). O frontend pega o ultimo quadro a cada
# desenho. Sem o ffmpeg, nada: fica a imagem.

import os
import shutil
import subprocess
import threading
import time

FFMPEG = os.environ.get("FLIPEROS_FFMPEG", "ffmpeg")
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv")


def available():
    return bool(shutil.which(FFMPEG))


class Video:
    """Um video tocando em w x h (cortado para encher, como a imagem)."""

    def __init__(self, path, w, h, sound=True, paced=False):
        """paced: sem som e sem o -re; quem da o ritmo e a leitura (30
        quadros por segundo), e parado (paused) o ffmpeg trava no pipe cheio,
        sem gastar nada: a miniatura da grade pronta para continuar na hora."""
        self.path, self.w, self.h = path, w, h
        self.frame = None          # o ultimo quadro (bytes RGB)
        self.count = 0             # quantos quadros ja chegaram
        self.alive = True
        self.paced = paced
        self.paused = False
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=30" % (w, h, w, h))
        cmd = [FFMPEG, "-nostdin", "-loglevel", "quiet", "-threads", "1"] + ([] if paced else ["-re"]) + [
               "-stream_loop", "-1", "-i", path, "-map", "0:v:0", "-filter_threads", "1", "-vf", vf,
               "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
        if sound and not paced:
            cmd += ["-map", "0:a:0?", "-f", "alsa", os.environ.get("FLIPEROS_VIDEO_AUDIO", "default")]
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                         stdin=subprocess.DEVNULL)
        except OSError:
            self.proc = None
            self.alive = False
            return
        threading.Thread(target=self.read, daemon=True).start()

    def read(self):
        size = self.w * self.h * 3
        out = self.proc.stdout
        due = time.monotonic()
        while self.alive:
            if self.paused and self.frame:
                time.sleep(0.05)
                due = time.monotonic()
                continue
            data = out.read(size)
            if not data or len(data) < size:
                break
            self.frame = data
            self.count += 1
            if self.paced:
                due += 1 / 30
                wait = due - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                else:
                    due = time.monotonic()
        self.alive = False

    def stop(self):
        self.alive = False
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None


class Player:
    """O video da tela: troca quando o jogo (ou o tamanho) muda, depois de o
    cursor parar um instante (andando pela lista nao abre um ffmpeg por
    jogo)."""

    DELAY = 0.45

    def __init__(self):
        self.video = None
        self.want = None           # (caminho, w, h) pedido agora
        self.since = 0.0
        self.ok = available()

    def request(self, path, w, h, now):
        """O video que a tela quer agora (None: nenhum). Devolve o quadro
        atual (bytes) ou None enquanto ele nao chega."""
        key = (path, w, h) if path and self.ok else None
        if key != self.want:
            self.want, self.since = key, now
            if self.video:
                # Fechar o ffmpeg espera por ele: fora do desenho, para a
                # troca de jogo nao travar.
                threading.Thread(target=self.video.stop, daemon=True).start()
                self.video = None
        if key and self.video is None and now - self.since >= self.DELAY:
            self.video = Video(path, w, h)
        if self.video and self.video.frame:
            return self.video.frame
        return None

    def stop(self):
        self.want = None
        if self.video:
            self.video.stop()
            self.video = None


class Grid:
    """Os videos da grade: um ffmpeg mudo por miniatura visivel e, parados
    no primeiro quadro, os das fileiras de antes e de depois (PRELOAD), que
    continuam na hora quando a fileira aparece. O som e so o do jogo
    escolhido (o Player)."""

    MAX = 30                   # ffmpeg de uma vez, no maximo
    STARTS = 2                 # comecados por quadro (sem engasgar o desenho)

    def __init__(self):
        self.videos = {}           # (caminho, w, h) -> Video
        self.ok = available()

    def frame(self, path, w, h):
        v = self.videos.get((path, w, h)) if path else None
        return v.frame if v else None

    def update(self, visible, preload, w, h):
        """visible e preload: os caminhos dos videos (sem None). Os que nao
        estao em nenhum dos dois param."""
        if not self.ok:
            return
        want = {}
        for path in preload:
            want[(path, w, h)] = True
        for path in visible:
            want[(path, w, h)] = False      # visivel: tocando
        for key in [k for k in self.videos if k not in want]:
            threading.Thread(target=self.videos.pop(key).stop, daemon=True).start()
        starts = 0
        # Os visiveis primeiro, depois os de perto.
        for key, paused in sorted(want.items(), key=lambda kv: kv[1]):
            v = self.videos.get(key)
            if v is None:          # (um que falhou fica parado, sem recomecar)
                if starts >= self.STARTS or len(self.videos) >= self.MAX:
                    continue
                v = self.videos[key] = Video(key[0], w, h, sound=False, paced=True)
                starts += 1
            v.paused = paused

    def stop(self):
        for v in self.videos.values():
            threading.Thread(target=v.stop, daemon=True).start()
        self.videos = {}
