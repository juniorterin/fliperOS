#!/usr/bin/env python3
# Gera os sons padrao do FliperOS (fliperos-setup/gui/sounds/*.wav): os seis
# eventos do Menu sounds e do Frontend sounds. O jeito e o do retrowave:
# senoides (com um pouco de harmonico), pads de duas senoides levemente
# dessintonizadas, um sino de FM e um eco morno que some devagar. Sao
# sintetizados aqui, entao nao ha licenca de terceiros e os WAVs saem sempre
# iguais.
#
#   python3 tools/make-default-sounds.py [PASTA]
#
# Mono, 16 bits, 22050 Hz: cada som tem poucos KB. Mexeu aqui, rode de novo
# e commite os WAVs.

import math
import os
import struct
import sys
import wave

RATE = 22050
PEAK = 0.8                  # o pico depois de normalizar (0 a 1)
TAU = 2 * math.pi


def note(name):
    """A frequencia de uma nota como "C5" ou "F#4" (A4 = 440 Hz)."""
    steps = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    pitch = steps[name[0]]
    rest = name[1:]
    if rest.startswith("#"):
        pitch += 1
        rest = rest[1:]
    midi = 12 * (int(rest) + 1) + pitch
    return 440.0 * 2 ** ((midi - 69) / 12)


def envelope(t, seconds, attack, release, decay):
    """O volume no instante t: sobe em `attack`, cai em curva (decay: a
    constante de tempo, 0 = sustentado) e desce em `release` no fim."""
    env = min(1.0, t / attack) if attack > 0 else 1.0
    if decay > 0:
        env *= math.exp(-t / decay)
    if release > 0:
        env *= min(1.0, (seconds - t) / release)
    return max(0.0, env)


def tone(freq, seconds, level=1.0, attack=0.004, release=0.03, decay=0.0, slide=0.0,
         partials=((1, 1.0), (2, 0.14), (3, 0.05)), cents=0.0):
    """Uma nota de senoide: o fundamental e uns harmonicos baixos (o calor).
    slide: quanto a nota sobe ou desce em oitavas ate o fim; cents: a
    dessintonia (um pad usa duas, uma para cada lado)."""
    count = int(seconds * RATE)
    out, phase = [], 0.0
    detune = 2 ** (cents / 1200)
    norm = sum(a for _, a in partials)
    for i in range(count):
        t = i / RATE
        f = freq * detune * 2 ** (slide * i / max(1, count))
        phase += f / RATE
        value = sum(a * math.sin(TAU * phase * k) for k, a in partials) / norm
        out.append(value * level * envelope(t, seconds, attack, release, decay))
    return out


def pad(freq, seconds, level=1.0, attack=0.06, release=0.25):
    """Um pad: duas senoides dessintonizadas para os dois lados (o chorus do
    sintetizador) e a oitava de baixo bem de leve."""
    a = tone(freq, seconds, level, attack, release, 0.0, 0.0, ((1, 1.0), (2, 0.1)), +6)
    b = tone(freq, seconds, level, attack, release, 0.0, 0.0, ((1, 1.0), (2, 0.1)), -6)
    sub = tone(freq / 2, seconds, level * 0.35, attack, release, 0.0, 0.0, ((1, 1.0),))
    return mix(a, b, sub)


def bell(freq, seconds, level=1.0, index=1.7, ratio=2.0, decay=0.22):
    """Um sino de FM: a senoide modulada por outra, com a modulacao morrendo
    antes do som (o brilho do toque que vira senoide limpa)."""
    count = int(seconds * RATE)
    out = []
    for i in range(count):
        t = i / RATE
        mod = index * math.exp(-t / (decay * 0.6)) * math.sin(TAU * freq * ratio * t)
        out.append(math.sin(TAU * freq * t + mod) * level * envelope(t, seconds, 0.002, 0.04, decay))
    return out


def lowpass(samples, cutoff):
    """Um passa-baixas de um polo: tira o agudo (os ecos ficam mais escuros)."""
    k = 1 - math.exp(-TAU * cutoff / RATE)
    out, y = [], 0.0
    for v in samples:
        y += k * (v - y)
        out.append(y)
    return out


def silence(seconds):
    return [0.0] * int(seconds * RATE)


def mix(*tracks):
    size = max(len(t) for t in tracks)
    out = [0.0] * size
    for track in tracks:
        for i, v in enumerate(track):
            out[i] += v
    return out


def at(offset, samples):
    """O som comecando offset segundos depois."""
    return silence(offset) + list(samples)


def echo(samples, delay, gain, times=3, cutoff=2400):
    """O eco do retrowave: cada repeticao mais baixa e mais escura que a
    anterior."""
    out = list(samples) + [0.0] * int(delay * RATE * times)
    wet = list(samples)
    for n in range(1, times + 1):
        wet = lowpass([v * gain for v in wet], cutoff)
        offset = int(delay * RATE * n)
        for i, v in enumerate(wet):
            out[i + offset] += v
    return out


def sounds():
    """Nome do arquivo -> amostras."""
    out = {}
    # O cursor andando: um toque curtinho de senoide que cai de leve (tem de
    # agradar o ouvido 30 vezes por segundo ao segurar o botao): sem eco.
    out["browse.wav"] = tone(note("C6"), 0.06, 0.9, 0.003, 0.02, 0.016, -0.12, ((1, 1.0), (2, 0.12)))
    # Entrar: duas notas para cima, macias, com o eco.
    up = mix(tone(note("E5"), 0.12, 0.9, 0.006, 0.06, 0.07),
             at(0.09, tone(note("B5"), 0.22, 1.0, 0.006, 0.12, 0.09)))
    out["enter.wav"] = echo(up, 0.11, 0.38, 3)
    # Voltar: o contrario, descendo.
    down = mix(tone(note("B5"), 0.12, 0.9, 0.006, 0.06, 0.07),
               at(0.09, tone(note("E5"), 0.24, 1.0, 0.006, 0.14, 0.1)))
    out["back.wav"] = echo(down, 0.11, 0.38, 3)
    # Abrir o jogo: o arpejo de La menor subindo (A3 C4 E4 A4 C5 E5) por cima de
    # uma varredura grave que sobe, e o acorde (pad) que abre no fim, com eco.
    arp = [tone(note(n), 0.16, 0.8, 0.004, 0.08, 0.1) for n in ("A3", "C4", "E4", "A4", "C5", "E5")]
    notes = mix(*[at(0.075 * i, s) for i, s in enumerate(arp)])
    sweep = tone(note("A2"), 0.5, 0.28, 0.05, 0.2, 0.0, 1.5, ((1, 1.0), (2, 0.2)))
    chord = mix(*[at(0.42, pad(note(n), 0.7, 0.36, 0.12, 0.45)) for n in ("A3", "E4", "A4", "C5")])
    out["open-game.wav"] = echo(mix(notes, sweep, chord), 0.19, 0.42, 3, 2000)
    # Fechar o jogo: o arpejo descendo (E5 C5 A4 E4 C4 A3) e a nota grave que
    # cai e apaga, com o eco.
    arp = [tone(note(n), 0.16, 0.8, 0.004, 0.08, 0.1) for n in ("E5", "C5", "A4", "E4", "C4", "A3")]
    notes = mix(*[at(0.075 * i, s) for i, s in enumerate(arp)])
    tail = at(0.4, tone(note("A2"), 0.8, 0.5, 0.03, 0.5, 0.35, -0.6, ((1, 1.0), (2, 0.18))))
    low = at(0.4, pad(note("A3"), 0.7, 0.3, 0.05, 0.5))
    out["close-game.wav"] = echo(mix(notes, tail, low), 0.19, 0.4, 3, 1800)
    # O alerta: um "ding-dong" de sino de FM (La e depois Mi, mais grave), o
    # eco longo. So chama a atencao: nao e um som de erro.
    ding = mix(bell(note("A5"), 0.5, 0.9), at(0.2, bell(note("E5"), 0.6, 1.0)))
    out["alert.wav"] = echo(ding, 0.24, 0.4, 3, 2600)
    return out


def save(path, samples):
    peak = max(abs(v) for v in samples) or 1.0
    scale = PEAK / peak
    # Um fade de 4 ms no fim, para a cauda do eco nunca terminar num estalo.
    fade = int(0.004 * RATE)
    samples = list(samples)
    for i in range(min(fade, len(samples))):
        samples[-1 - i] *= i / fade
    frames = b"".join(struct.pack("<h", max(-32767, min(32767, int(round(v * scale * 32767))))) for v in samples)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(frames)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "fliperos-setup", "gui", "sounds")
    os.makedirs(target, exist_ok=True)
    for name, samples in sounds().items():
        save(os.path.join(target, name), samples)
        print("%-16s %5.2f s" % (name, len(samples) / RATE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
