# O video do jogo no frontend do FliperOS (~/media/preview/<pasta>/<set>.mp4):
# o ffmpeg decodifica em quadros RGB do tamanho do quadro da tela, num pipe,
# no ritmo do proprio video (-re), em loop, e manda o som para o ALSA
# (default, o mesmo dmix dos jogos). O frontend pega o ultimo quadro a cada
# desenho. Sem o ffmpeg, nada: fica a imagem.

import os
import shutil
import subprocess
import threading

FFMPEG = os.environ.get("FLIPEROS_FFMPEG", "ffmpeg")
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv")


def available():
    return bool(shutil.which(FFMPEG))


class Video:
    """Um video tocando em w x h (cortado para encher, como a imagem)."""

    def __init__(self, path, w, h, sound=True):
        self.path, self.w, self.h = path, w, h
        self.frame = None          # o ultimo quadro (bytes RGB)
        self.count = 0             # quantos quadros ja chegaram
        self.alive = True
        vf = ("scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,fps=30" % (w, h, w, h))
        cmd = [FFMPEG, "-nostdin", "-loglevel", "quiet", "-re", "-stream_loop", "-1", "-i", path,
               "-map", "0:v:0", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
        if sound:
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
        while self.alive:
            data = out.read(size)
            if not data or len(data) < size:
                break
            self.frame = data
            self.count += 1
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
