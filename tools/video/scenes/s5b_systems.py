# Cena 5b: as outras game lists (Naomi, Atomiswave, Model 2, Model 3, MAME
# 2010), na tela cheia e na grade, abrindo jogos.
MODE = "full"
GAME = "mvsc2"
OVERLAY = None
PLAY_SECONDS = 5.5
T = []


def at(t, *keys, gap=0.45):
    for i, k in enumerate(keys):
        T.append((t + i * gap, k))


at(1.5, "down", "down", gap=2.2)
at(6.5, "b1")
at(7.6, "b1")              # Jogar
at(14.5, "right")          # a proxima game list
at(17.0, "down", "down", gap=2.0)
at(22.0, "right")
at(24.5, "down", gap=2.0)
at(27.0, "start")          # a grade
at(29.0, "right", "right", "down", gap=1.4)
at(33.5, "b1")
at(34.6, "b1")             # Jogar
at(41.0, "start", "start", gap=0.8)   # de volta a lista
at(43.0, "down", "down", gap=1.2)
TIMELINE = T
DURATION = 46.0
