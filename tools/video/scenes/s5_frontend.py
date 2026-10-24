# Cena 5: o frontend do FliperOS, com a biblioteca de amostra do gabinete.
# O tempo e o real (os videos dos jogos tocam no ritmo deles).
MODE = "list"
GAME = "garou"
OVERLAY = "guide"
PLAY_SECONDS = 6.0

T = []


def at(t, *keys, gap=0.45):
    for i, k in enumerate(keys):
        T.append((t + i * gap, k))


# O guia dos botoes e a lista, com o video do jogo a direita.
at(3.5, "b1")
at(6.0, "down", "down", gap=1.6)
at(10.0, "up", "up", gap=0.8)
# Os clones: o [+] abre o galho, e um clone abre como qualquer jogo.
at(13.0, "b1")
at(15.0, "down", "down", gap=1.0)
at(18.0, "b1")             # o cartao do clone
at(19.8, "b1")             # Jogar (6 s do jogo)
at(27.0, "b2")             # fecha o galho
# O cartao, a pagina + e a pagina 2.
at(28.5, "down", gap=0.4)
at(30.0, "b1")
at(31.3, "right", "right", gap=0.5)
at(32.6, "b1")             # a pagina do jogo
at(38.6, "right")          # a pagina 2 (fotos e mais dados)
at(43.0, "down", "down", gap=0.5)
at(45.0, "b2", "b2", gap=0.6)   # a pagina volta ao cartao, e o cartao fecha
# Os filtros e o menu do Tab.
at(46.5, "b5")
at(47.6, "down", "down", "down", gap=0.5)
at(50.0, "b1")             # filtra
at(52.5, "b5")
at(53.4, "up", "up", "up", gap=0.4)
at(55.0, "b1")             # All games de volta
at(56.5, "tab")
at(58.0, "b1")             # Classify
at(59.0, "down", "down", gap=0.6)
at(61.5, "b2")
at(62.3, "b2")
# A tela cheia, com o video de cada jogo ao fundo e os clones com o selo.
at(63.5, "start")
at(66.0, "down", "down", "down", gap=2.4)
at(74.0, "right")          # a proxima game list
at(77.0, "down", "down", gap=2.2)
# A grade, cada miniatura com o seu video.
at(82.5, "start")
at(85.0, "right", "down", "right", "down", gap=1.6)
at(92.0, "b1")             # o cartao na grade
at(93.5, "b1")             # Jogar
at(101.0, "b4")            # favorito
at(103.0, "start")         # de volta a lista
TIMELINE = T
DURATION = 106.0
