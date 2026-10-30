# GIF do site: o modo comercial do frontend (Tab > Frontend options >
# Commercial mode). Sem credito o cliente ve os jogos mas o botao 1 mostra
# INSERT COIN; duas fichas, uma a cada 2 segundos, somam o tempo e o relogio
# aparece; ai o jogo abre. Gravado em tempo real por fe_rec.py, com a
# biblioteca de amostra (render.sh gifs commercial).
MODE = "list"
GAME = "garou"
OVERLAY = None
PLAY_SECONDS = 3.0
# Modo comercial ligado e sem tempo, como o gabinete recem-ligado.
START = {"commercial": True, "credit_until": 0.0, "coin_minutes": 5}

T = []


def at(t, *keys, gap=0.45):
    for i, k in enumerate(keys):
        T.append((t + i * gap, k))


# O indicador piscando INSERT COIN, e o botao 1 sem credito: recusado.
at(1.6, "b1")
# As fichas: uma a cada 2 segundos.
at(3.6, "coin")
at(5.6, "coin")
# Com tempo, escolhe e joga.
at(8.6, "down", "down", gap=0.9)
at(11.0, "b1")             # o cartao do jogo
at(12.4, "b1")             # Jogar (o video do jogo em tela cheia)
TIMELINE = T
DURATION = 17.5
