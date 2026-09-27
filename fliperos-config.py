#!/usr/bin/env python3
"""FliperOS — menu de configuracao, em whiptail.

Equivalente ao `mainmenu` do gasetup: fica no sistema depois da instalacao e
concentra video, rede, compartilhamento e diagnostico, em vez de congelar tudo
no momento do build da ISO.

Sao dois menus. A midia de instalacao abre num menu de setup (Wi-Fi primeiro,
depois video, e instalar como um item), porque numa maquina sem cabo de rede e
preciso configurar a rede antes de qualquer coisa. O sistema instalado abre no
menu completo.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# O modulo de interface fica ao lado do script no repositorio e em
# /usr/local/lib/fliperos na imagem instalada.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "/usr/local/lib/fliperos")
import fliperos_tui as tui  # noqa: E402

ETC = Path("/etc/fliperos")
PROFILES = ETC / "profiles"
GRUB_CFG = Path("/etc/default/grub.d/99-fliperos.cfg")
EDID_LIVE = Path("/lib/firmware/edid/crt15.bin")
VIDEO_CHECK = Path("/etc/systemd/system/fliperos-video-check.service")
PROFILE_KHZ = {"15khz": (15.0, 16.0), "25khz": (24.5, 25.5), "31khz": (31.0, 32.0)}
REPO_CONF = ETC / "repo.conf"
APT_SOURCE = Path("/etc/apt/sources.list.d/fliperos.list")


def run(*args, check=True, capture=False, env=None):
    merged = dict(os.environ, **env) if env else None
    return subprocess.run(args, check=check, text=True, env=merged,
                          stdout=subprocess.PIPE if capture else None).stdout


def quiet(*args):
    """Roda sem falhar e sem poluir a tela; devolve True no exit 0."""
    return subprocess.run(args, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def active_profile():
    path = ETC / "profile"
    return path.read_text().strip() if path.is_file() else "15khz"


def active_session():
    path = ETC / "session"
    return path.read_text().strip() if path.is_file() else "launcher"


def installed():
    return (ETC / "installed").is_file()


def connector():
    path = ETC / "connector"
    return path.read_text().strip() if path.is_file() else "VGA-1"


# ════════════════════════════════════════════════════════════
#  Parametros de boot (GRUB da instalacao)
# ════════════════════════════════════════════════════════════
def read_cmdline():
    if not GRUB_CFG.is_file():
        return ""
    match = re.search(r'GRUB_CMDLINE_LINUX_DEFAULT="([^"]*)"', GRUB_CFG.read_text())
    return match.group(1) if match else ""


def write_cmdline(cmdline):
    if not GRUB_CFG.is_file():
        # Live boot: o GRUB da ISO nao e editavel e nada persiste mesmo.
        raise ValueError("Sem GRUB instalado; parametros de boot so no sistema em disco")
    text = GRUB_CFG.read_text()
    GRUB_CFG.write_text(re.sub(r'(GRUB_CMDLINE_LINUX_DEFAULT=")[^"]*(")',
                               lambda m: m.group(1) + cmdline + m.group(2), text))
    run("update-grub")


def set_param(cmdline, key, value):
    """Define key=value na cmdline; value None remove a chave."""
    parts = [p for p in cmdline.split() if not p.startswith(key + "=")]
    if value is not None:
        parts.append(key + "=" + value)
    return " ".join(parts)


def get_param(cmdline, key):
    for part in cmdline.split():
        if part.startswith(key + "="):
            return part[len(key) + 1:]
    return None


def set_video_subparam(cmdline, key, value):
    """O parametro video= carrega subvalores separados por virgula
    (video=VGA-1:e,panel_orientation=left_side_up)."""
    video = get_param(cmdline, "video")
    if not video:
        return cmdline
    keep = [v for v in video.split(",") if not v.startswith(key + "=")]
    if value is not None:
        keep.append(key + "=" + value)
    return set_param(cmdline, "video", ",".join(keep))


# ════════════════════════════════════════════════════════════
#  Escrita em arquivos de configuracao
# ════════════════════════════════════════════════════════════
def set_ini_value(path, key, value):
    """Grava `chave valor` em ini estilo MAME/switchres, inserindo se faltar.
    Inserir importa: os .ini que a imagem instala sao minimos e nao trazem as
    chaves de rotacao, geometria ou verbosidade — um sub puro nao faria nada."""
    if not path.is_file():
        return False
    text = path.read_text()
    pattern = r"^([ \t]*)" + re.escape(key) + r"[ \t]+\S+.*$"
    if re.search(pattern, text, flags=re.M):
        text = re.sub(pattern, lambda m: m.group(1) + key + " " + value, text, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + key + " " + value + "\n"
    path.write_text(text)
    return True


def set_cfg_value(path, key, value):
    """Mesmo upsert, no formato do RetroArch (chave = "valor")."""
    if not path.is_file():
        return False
    text = path.read_text()
    pattern = r"^" + re.escape(key) + r'[ \t]*=[ \t]*".*"$'
    line = key + ' = "' + value + '"'
    text = (re.sub(pattern, line, text, flags=re.M)
            if re.search(pattern, text, flags=re.M)
            else text.rstrip("\n") + "\n" + line + "\n")
    path.write_text(text)
    return True


def sync_switchres():
    """O switchres le /etc/switchres.ini; a copia canonica fica em /etc/fliperos."""
    source = ETC / "switchres.ini"
    if source.is_file():
        shutil.copyfile(source, "/etc/switchres.ini")


# ════════════════════════════════════════════════════════════
#  Sessao ao ligar
# ════════════════════════════════════════════════════════════
def sessions():
    """Le a tabela de sessoes instalaveis (nome|backend|binario|pacote|descricao)."""
    table = ETC / "sessions.conf"
    if not table.is_file():
        return []
    rows = []
    for line in table.read_text().splitlines():
        if line.strip().startswith("#") or not line.strip():
            continue
        fields = line.split("|")
        if len(fields) != 5:
            continue
        name, backend, binary, package, description = fields
        available = not binary or bool(shutil.which(binary)) or Path(binary).is_file()
        rows.append({"name": name, "backend": backend, "binary": binary,
                     "package": package, "description": description,
                     "available": available})
    return rows


def menu_session():
    """Sessao sem binario aparece marcada, em vez de escondida: e assim que o
    usuario descobre o que o wizard pode instalar."""
    current = active_session()
    rows = sessions()
    if not rows:
        tui.message("Tabela de sessoes ausente (/etc/fliperos/sessions.conf).")
        return
    backends = {"kms": "KMS", "x": "Xorg", "text": "texto", "none": "-"}
    options = []
    for row in rows:
        label = "[%s] %s" % (backends.get(row["backend"], row["backend"]),
                             row["description"])
        if row["name"] == current:
            label = "* " + label
        elif not row["available"]:
            label = "(falta " + (row["package"] or "?") + ") " + label
        options.append((row["name"], label))
    chosen = tui.menu("Sessao atual: %s\n\n* = atual" % current, options,
                      title="Sessao ao ligar", default=current)
    if chosen is None:
        return
    row = next(r for r in rows if r["name"] == chosen)
    if not row["available"]:
        tui.message("'%s' ainda nao esta instalado (pacote %s).\n\n"
                    "Instale pelo menu de componentes antes de escolher "
                    "essa sessao." % (row["name"], row["package"]))
        return
    (ETC / "session").write_text(row["name"] + "\n")
    tui.message("Sessao definida: %s.\nVale no proximo login da tty1." % row["name"])


# ════════════════════════════════════════════════════════════
#  Componentes (repositorio APT do FliperOS)
# ════════════════════════════════════════════════════════════
def repo_url():
    if REPO_CONF.is_file():
        for line in REPO_CONF.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return ""


def repo_source_line(url):
    """Monta a linha do sources.list pro repositorio plano do FliperOS.

    Exige HTTPS: o repositorio pode ainda nao estar assinado, e 'trusted=yes'
    sobre HTTP deixaria qualquer um no caminho entregar pacote que instala como
    root. O './' no fim e o que indica repositorio plano, sem dists/."""
    if not url.startswith("https://"):
        raise ValueError("URL do repositorio precisa ser HTTPS: " + url)
    if not url.endswith("/"):
        url += "/"
    return "deb [trusted=yes] " + url + " ./\n"


def configure_repo():
    current = repo_url()
    url = tui.inputbox("URL base do repositorio de componentes.\n\n"
                       "Precisa ser HTTPS: o repositorio e instalado sem\n"
                       "verificacao de assinatura, e por HTTP isso permitiria\n"
                       "injetar pacote que instala como root.",
                       default=current, title="Repositorio")
    if not url:
        return False
    try:
        line = repo_source_line(url)
    except ValueError as exc:
        tui.message("Recusado: " + str(exc))
        return False
    APT_SOURCE.write_text(line)
    if tui.run_visible(["apt-get", "update"], "Atualizando a lista de pacotes"):
        # Uma entrada invalida em sources.list.d faz TODO apt falhar depois,
        # nao so a instalacao de componentes — melhor desfazer do que deixar o
        # sistema sem conseguir instalar nada.
        APT_SOURCE.unlink(missing_ok=True)
        tui.message("apt-get update falhou; a URL foi descartada.\nConfira e tente de novo.")
        return False
    REPO_CONF.write_text(line.split()[2] + "\n")
    return True


def menu_components():
    while True:
        rows = [row for row in sessions() if row["package"]]
        if not rows:
            tui.message("Nenhum componente instalavel na tabela de sessoes.")
            return
        if not repo_url():
            if not tui.yesno("O repositorio de componentes ainda nao esta\n"
                             "configurado. Configurar agora?", default_no=False):
                return
            if not configure_repo():
                return
        options = [(row["name"],
                    ("[instalado] " if row["available"] else "") + row["description"])
                   for row in rows]
        options.append(("__repo__", "Trocar o repositorio (%s)" % (repo_url() or "-")))
        chosen = tui.menu("Instalar launchers e emuladores.", options,
                          title="Componentes")
        if chosen is None:
            return
        if chosen == "__repo__":
            configure_repo()
            continue
        row = next(r for r in rows if r["name"] == chosen)
        if row["available"]:
            if tui.yesno("%s ja esta instalado.\n\nUsar como sessao ao ligar?"
                         % row["name"], default_no=False):
                (ETC / "session").write_text(row["name"] + "\n")
                tui.message("Sessao definida: " + row["name"])
            continue
        if tui.run_visible(["apt-get", "install", "-y", row["package"]],
                           "Instalando " + row["package"]):
            tui.message("Instalacao de %s falhou." % row["package"])
            continue
        if tui.yesno("%s instalado.\n\nUsar como sessao ao ligar?" % row["name"],
                     default_no=False):
            (ETC / "session").write_text(row["name"] + "\n")
            tui.message("Sessao definida: %s.\nVale no proximo login." % row["name"])


# ════════════════════════════════════════════════════════════
#  Carta de teste (grid) — confirma um modo antes de gravar
# ════════════════════════════════════════════════════════════
def show_grid(width, height, refresh, note="", geometry=None):
    """Mostra a grade de teste no modo pedido. False se o switchres falhar."""
    if not shutil.which("grid"):
        tui.message("Binario 'grid' ausente; nao da pra testar o modo visualmente.")
        return False
    env = {"GRID_TEXT": note} if note else {}
    if not os.environ.get("DISPLAY"):
        env["SDL_VIDEODRIVER"] = "kmsdrm"
    args = ["switchres", str(width), str(height), str(refresh), "-s", "-l", "grid"]
    if geometry:
        args += ["--geometry", "%s:%d:%d" % geometry]
    subprocess.run(["clear"], check=False)
    return subprocess.run(args, env=dict(os.environ, **env)).returncode == 0


def confirm_mode(width, height, refresh, geometry=None):
    """Mostra a grade e exige confirmacao visual. Espelha o
    worker_custom_video_mode do gasetup: nada e gravado sem o usuario ver."""
    if not tui.yesno("A grade de teste vai aparecer no CRT em %sx%s@%s.\n\n"
                     "Feche com ENTER ou Q. Se a tela ficar preta ou fora de\n"
                     "sincronia, espere o retorno e responda NAO na pergunta\n"
                     "seguinte.\n\nMostrar a grade agora?"
                     % (width, height, refresh), default_no=False):
        return False
    if not show_grid(width, height, refresh,
                     "Teste %sx%s@%s" % (width, height, refresh), geometry):
        tui.message("O switchres nao conseguiu aplicar esse modo.")
        return False
    return tui.yesno("A grade apareceu inteira e estavel?", default_no=False)


# ════════════════════════════════════════════════════════════
#  Video
# ════════════════════════════════════════════════════════════
def apply_profile(profile):
    """Troca o perfil de monitor no sistema instalado: EDID, switchres, xorg,
    mame e a faixa de kHz do check de video. Tira a escolha de frequencia do
    build (era so --monitor-profile na mkiso)."""
    source = PROFILES / profile
    if not source.is_dir():
        raise ValueError("Perfil ausente na imagem: " + profile)
    shutil.copyfile(source / "edid.bin", EDID_LIVE)
    for name, targets in (("switchres.ini", [ETC / "switchres.ini", Path("/etc/switchres.ini")]),
                          ("mame.ini", [ETC / "mame/mame.ini"]),
                          ("xorg.conf", [ETC / "xorg.conf"])):
        for target in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / name, target)
    # O xorg.conf do perfil vem com o conector padrao; reaplica o real.
    xorg = ETC / "xorg.conf"
    xorg.write_text(re.sub(r'Option "Monitor-[^"]+" "CRT15"',
                           'Option "Monitor-' + connector() + '" "CRT15"', xorg.read_text()))
    if VIDEO_CHECK.is_file():
        low, high = PROFILE_KHZ[profile]
        text = re.sub(r"--min-khz \S+", "--min-khz " + str(low), VIDEO_CHECK.read_text())
        text = re.sub(r"--max-khz \S+", "--max-khz " + str(high), text)
        VIDEO_CHECK.write_text(text)
        quiet("systemctl", "daemon-reload")
    (ETC / "profile").write_text(profile + "\n")
    tui.run_visible(["update-initramfs", "-u", "-k", "all"],
                    "Regravando o initramfs com o EDID do perfil")


def menu_profile():
    current = active_profile()
    options = []
    for name, (low, high) in PROFILE_KHZ.items():
        label = "%.1f a %.1f kHz" % (low, high)
        options.append((name, ("* " if name == current else "") + label))
    chosen = tui.menu("Perfil ativo: %s\n\nCada perfil troca EDID, switchres.ini,\n"
                      "xorg.conf e mame.ini de uma vez." % current,
                      options, title="Perfil de monitor", default=current)
    if chosen is None:
        return
    if chosen == current:
        tui.message("Esse perfil ja esta ativo.")
        return
    if not tui.yesno("Trocar para %s?\n\nRegrava o EDID e o initramfs. O modo novo\n"
                     "so vale no proximo boot, e um CRT de 15 kHz nao\n"
                     "sincroniza um perfil de 31 kHz." % chosen):
        return
    apply_profile(chosen)
    tui.message("Perfil %s aplicado.\nReinicie pra validar o modo." % chosen)


def menu_custom_mode():
    """Gera o EDID em runtime com switchres -e, testando antes de gravar.
    E o que permite uma resolucao fora dos tres perfis sem rebuildar a ISO."""
    if not shutil.which("switchres"):
        tui.message("switchres ausente; rode sudo fliperos-postinstall primeiro.")
        return
    width = tui.inputbox("Largura", default="320", title="Resolucao customizada")
    if not width:
        return
    height = tui.inputbox("Altura", default="240", title="Resolucao customizada")
    if not height:
        return
    refresh = tui.inputbox("Refresh vertical (Hz)", default="60",
                           title="Resolucao customizada")
    if not refresh:
        return
    if not all(re.fullmatch(r"\d+(\.\d+)?", v) for v in (width, height, refresh)):
        tui.message("Valores invalidos.")
        return
    modeline = run("switchres", width, height, refresh, "-c", capture=True, check=False)
    if not tui.yesno("Modeline calculada:\n\n%s\n\nSeguir com ela?"
                     % (modeline or "(o switchres nao devolveu modeline)")):
        return
    if not confirm_mode(width, height, refresh):
        tui.message("Nada foi gravado.")
        return
    with tempfile.TemporaryDirectory() as tmp:
        # -e escreve o .bin no diretorio corrente, entao o switchres roda
        # dentro do tempdir: nada e procurado nem apagado fora dele.
        subprocess.run(["switchres", width, height, refresh, "-e"], cwd=tmp, check=True)
        produced = sorted(Path(tmp).glob("*.bin"))
        if not produced:
            tui.message("O switchres nao gerou o arquivo de EDID.")
            return
        shutil.copyfile(produced[0], EDID_LIVE)
    tui.run_visible(["update-initramfs", "-u", "-k", "all"],
                    "Regravando o initramfs com o EDID novo")
    (ETC / "custom-mode").write_text("%s %s %s\n" % (width, height, refresh))
    tui.message("EDID gravado e initramfs atualizado.\n\nA cmdline ja aponta pra esse "
                "arquivo, entao nao\nprecisa mexer no GRUB.")


def menu_orientation():
    """Gabinete vertical (tate). Ajusta MAME, fbcon e panel_orientation juntos,
    como o worker_select_monitor_orientation do gasetup."""
    modes = {"horizontal": ("horizontal", None, None, None),
             "direita": ("vertical (girado a direita)", "1", "ror", "right_side_up"),
             "esquerda": ("vertical (girado a esquerda)", "3", "rol", "left_side_up"),
             "invertido": ("invertido (180 graus)", "2", None, "upside_down")}
    chosen = tui.menu("Orientacao do monitor.", [(k, v[0]) for k, v in modes.items()],
                      title="Orientacao")
    if chosen is None:
        return
    label, fbcon, mame_key, panel = modes[chosen]
    mame = ETC / "mame/mame.ini"
    for key in ("ror", "rol", "autoror", "autorol"):
        set_ini_value(mame, key, "1" if key == mame_key else "0")
    cmdline = read_cmdline()
    cmdline = set_param(cmdline, "fbcon", "rotate:" + fbcon if fbcon else None)
    cmdline = set_video_subparam(cmdline, "panel_orientation", panel)
    write_cmdline(cmdline)
    live = Path("/sys/class/graphics/fbcon/rotate")
    if live.exists():
        try:
            live.write_text(fbcon or "0")
        except OSError:
            pass
    tui.message("Orientacao: %s\n\nMAME e console valem ja; o giro do KMS entra\n"
                "no proximo boot." % label)


def menu_connector():
    """Troca de GPU/cabo sem reinstalar: reaponta conector na cmdline e nos configs."""
    detected = []
    checker = "/usr/local/bin/fliperos-video-check"
    if Path(checker).is_file():
        report = subprocess.run([checker, "--json"], text=True, capture_output=True)
        try:
            for out in json.loads(report.stdout)["outputs"]:
                state = ("ativo %.4f kHz" % out["horizontal_khz"]
                         if out["active"] else "inativo")
                detected.append("  %s (%s)" % (out["connector"], state))
        except (json.JSONDecodeError, KeyError):
            pass
    new = tui.inputbox("Conector atual: %s\n\nDetectados:\n%s\n\nNovo conector:"
                       % (connector(), "\n".join(detected) or "  (nenhum)"),
                       title="Conector")
    if not new:
        return
    if not re.fullmatch(r"(?:VGA|DVI-I|DVI-A|DP|HDMI-A)-[1-9][0-9]*", new):
        tui.message("Nome de conector invalido.")
        return
    (ETC / "connector").write_text(new + "\n")
    xorg = ETC / "xorg.conf"
    if xorg.is_file():
        xorg.write_text(re.sub(r'Option "Monitor-[^"]+" "CRT15"',
                               'Option "Monitor-' + new + '" "CRT15"', xorg.read_text()))
    if VIDEO_CHECK.is_file():
        VIDEO_CHECK.write_text(re.sub(r"--connector \S+", "--connector " + new,
                                      VIDEO_CHECK.read_text()))
        quiet("systemctl", "daemon-reload")
    cmdline = set_param(read_cmdline(), "video", new + ":e")
    cmdline = set_param(cmdline, "drm.edid_firmware", new + ":edid/crt15.bin")
    write_cmdline(cmdline)
    tui.message("Conector trocado para %s.\nReinicie pra validar." % new)


def menu_geometry():
    """Centraliza/dimensiona a imagem no tubo e grava em switchres.ini.
    O grid do switchres so desenha a carta; o laco de ajuste e daqui."""
    ini = ETC / "switchres.ini"
    if not ini.is_file():
        tui.message("switchres.ini ausente.")
        return
    h_size, h_shift, v_shift = 1.0, 0, 0
    steps = [("grade", "Mostrar a grade com os valores atuais"),
             ("esquerda", "Mover para a esquerda"),
             ("direita", "Mover para a direita"),
             ("cima", "Mover para cima"),
             ("baixo", "Mover para baixo"),
             ("estreitar", "Estreitar a imagem"),
             ("alargar", "Alargar a imagem"),
             ("gravar", "Gravar em switchres.ini")]
    while True:
        note = "h_size %.2f  h_shift %d  v_shift %d" % (h_size, h_shift, v_shift)
        chosen = tui.menu("Atual: %s" % note, steps, title="Geometria",
                          cancel="Cancelar")
        if chosen is None:
            return
        if chosen == "grade":
            show_grid(640, 480, 60, note, (h_size, h_shift, v_shift))
        elif chosen == "esquerda":
            h_shift -= 1
        elif chosen == "direita":
            h_shift += 1
        elif chosen == "cima":
            v_shift -= 1
        elif chosen == "baixo":
            v_shift += 1
        elif chosen == "estreitar":
            h_size = round(h_size - 0.01, 2)
        elif chosen == "alargar":
            h_size = round(h_size + 0.01, 2)
        elif chosen == "gravar":
            set_ini_value(ini, "h_size", "%.3f" % h_size)
            set_ini_value(ini, "h_shift", str(h_shift))
            set_ini_value(ini, "v_shift", str(v_shift))
            sync_switchres()
            tui.message("Geometria gravada em switchres.ini.")
            return


def menu_video():
    options = [("perfil", "Perfil de monitor (15 / 25 / 31 kHz)"),
               ("custom", "Resolucao customizada (gera EDID novo)"),
               ("orientacao", "Orientacao do monitor"),
               ("conector", "Trocar conector (troquei de GPU ou cabo)"),
               ("geometria", "Calibrar geometria")]
    while True:
        chosen = tui.menu("Perfil: %s   Conector: %s" % (active_profile(), connector()),
                          options, title="Video")
        if chosen is None:
            return
        actions = {"perfil": menu_profile, "custom": menu_custom_mode,
                   "orientacao": menu_orientation, "conector": menu_connector,
                   "geometria": menu_geometry}
        actions[chosen]()


# ════════════════════════════════════════════════════════════
#  Rede
# ════════════════════════════════════════════════════════════
def nmcli_fields(line):
    """Separa os campos de uma linha do `nmcli -t`.

    No modo terse o nmcli escapa ':' dentro dos valores como '\\:' e '\\' como
    '\\\\'. Um split(':') cru quebraria um SSID que contenha dois-pontos: o
    nome sairia truncado na lista e a conexao falharia com o nome errado."""
    fields, current, escaped = [], "", False
    for char in line:
        if escaped:
            current += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append(current)
            current = ""
        else:
            current += char
    fields.append(current)
    return fields


def wifi_device():
    out = run("nmcli", "-t", "-f", "DEVICE,TYPE", "device", capture=True, check=False) or ""
    for line in out.splitlines():
        parts = nmcli_fields(line)
        if len(parts) >= 2 and parts[1] == "wifi":
            return parts[0]
    return None


def menu_wifi():
    """Wi-Fi via nmcli. O gasetup usa iwctl/iwd porque e Arch; aqui o
    NetworkManager ja persiste a conexao, sem editar arquivo de rede."""
    device = wifi_device()
    if not device:
        tui.message("Nenhuma interface Wi-Fi encontrada.\n\n"
                    "Pode faltar firmware do adaptador.")
        return
    quiet("nmcli", "device", "wifi", "rescan")
    out = run("nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list",
              capture=True, check=False) or ""
    networks, seen = [], set()
    for line in out.splitlines():
        fields = nmcli_fields(line)
        # SSID vazio e rede oculta: nao da pra listar pelo nome.
        if not fields or not fields[0] or fields[0] in seen:
            continue
        seen.add(fields[0])
        networks.append((fields[0], fields[1] if len(fields) > 1 else "?",
                         fields[2] if len(fields) > 2 else ""))
    if not networks:
        tui.message("Nenhuma rede encontrada.")
        return
    options = [(ssid, "sinal %s%%%s" % (signal, "" if security else "  (aberta)"))
               for ssid, signal, security in networks]
    chosen = tui.menu("Interface: %s" % device, options, title="Redes Wi-Fi")
    if chosen is None:
        return
    security = next(s for ssid, _, s in networks if ssid == chosen)
    args = ["nmcli", "device", "wifi", "connect", chosen]
    if security:
        secret = tui.password("Senha de " + chosen, title="Wi-Fi")
        if not secret:
            return
        args += ["password", secret]
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        tui.message("Falhou:\n\n" + (result.stderr or result.stdout).strip())
    else:
        tui.message("Conectado em %s.\n\nO NetworkManager reconecta sozinho no boot."
                    % chosen)


def menu_regdom():
    """Dominio regulatorio: pais errado derruba canais (copiado do gasetup)."""
    current = run("iw", "reg", "get", capture=True, check=False) or ""
    match = re.search(r"country (\S\S)", current)
    found = match.group(1) if match else "desconhecido"
    text = "Dominio atual: %s\n\n" % found
    if found == "00":
        text += "'00' e o padrao mundial restrito — define o pais\npra liberar os canais.\n\n"
    code = tui.inputbox(text + "Codigo do pais (ex: BR):", title="Dominio regulatorio")
    if not code:
        return
    code = code.upper()
    if not re.fullmatch(r"[A-Z]{2}", code):
        tui.message("Codigo invalido.")
        return
    if not quiet("iw", "reg", "set", code):
        tui.message("Nao foi possivel aplicar o dominio.")
        return
    Path("/etc/default/crda").write_text("REGDOMAIN=" + code + "\n")
    Path("/etc/modprobe.d/cfg80211.conf").write_text(
        "options cfg80211 ieee80211_regdom=" + code + "\n")
    tui.message("Dominio %s aplicado e persistido." % code)


def network_summary():
    addrs = run("ip", "-4", "-br", "addr", capture=True, check=False) or ""
    lines = [" ".join(line.split()) for line in addrs.splitlines()
             if not line.startswith("lo")]
    return "\n".join(lines) or "sem endereco IPv4"


def menu_network():
    options = [("wifi", "Conectar no Wi-Fi"),
               ("regdom", "Dominio regulatorio (pais)"),
               ("status", "Status detalhado")]
    while True:
        chosen = tui.menu("Enderecos:\n%s" % network_summary(), options, title="Rede")
        if chosen is None:
            return
        if chosen == "wifi":
            menu_wifi()
        elif chosen == "regdom":
            menu_regdom()
        elif chosen == "status":
            tui.run_visible(["nmcli", "device", "status"], "Status da rede")


# ════════════════════════════════════════════════════════════
#  Compartilhamento (Samba / SSH)
# ════════════════════════════════════════════════════════════
def service_state(unit):
    active = quiet("systemctl", "is-active", "--quiet", unit)
    enabled = quiet("systemctl", "is-enabled", "--quiet", unit)
    return ("ligado" if active else "parado") + (", inicia no boot" if enabled else "")


def toggle_service(units, label):
    on = all(quiet("systemctl", "is-enabled", "--quiet", u) for u in units)
    if on:
        if not tui.yesno("Desligar " + label + "?"):
            return
        for unit in units:
            quiet("systemctl", "disable", "--now", unit)
        tui.message(label + " desligado.")
    else:
        for unit in units:
            quiet("systemctl", "enable", "--now", unit)
        tui.message(label + " ligado.")


def menu_sharing():
    while True:
        ips = [part.split("/")[0] for line in
               (run("ip", "-4", "-br", "addr", capture=True, check=False) or "").splitlines()
               if not line.startswith("lo") for part in line.split() if "/" in part]
        host = (run("hostname", capture=True, check=False) or "fliperos").strip()
        text = "Samba: %s\nSSH/SFTP: %s\n" % (service_state("smbd"), service_state("ssh"))
        if ips:
            text += "\n\\\\%s\\FliperOS   sftp fliperos@%s\npor nome: \\\\%s  ou  %s.local" % (
                ips[0], ips[0], host, host)
        chosen = tui.menu(text, [("samba", "Ligar/desligar Samba"),
                                 ("ssh", "Ligar/desligar SSH"),
                                 ("senha", "Senha do Samba do usuario fliperos")],
                          title="Compartilhamento")
        if chosen is None:
            return
        if chosen == "samba":
            toggle_service(["smbd", "nmbd"], "Samba")
        elif chosen == "ssh":
            toggle_service(["ssh"], "SSH")
        elif chosen == "senha":
            tui.run_visible(["smbpasswd", "-a", "fliperos"], "Senha do Samba")


# ════════════════════════════════════════════════════════════
#  Sistema e diagnostico
# ════════════════════════════════════════════════════════════
def menu_password():
    if tui.run_visible(["passwd", "fliperos"], "Senha do usuario fliperos"):
        return
    if tui.yesno("Usar a mesma senha no Samba?", default_no=False):
        tui.run_visible(["smbpasswd", "-a", "fliperos"], "Senha do Samba")


def menu_usb():
    """Montar pendrive de ROMs. O gasetup usa udiskie no X; num console
    KMS um item de menu resolve melhor que um daemon de bandeja."""
    out = run("lsblk", "-rno", "NAME,SIZE,LABEL,MOUNTPOINT,TYPE,RM",
              capture=True, check=False) or ""
    removable = []
    for line in out.splitlines():
        fields = line.split(" ")
        if len(fields) >= 6 and fields[4] == "part" and fields[5] == "1":
            removable.append(fields)
    if not removable:
        tui.message("Nenhuma particao removivel encontrada.")
        return
    options = [(fields[0], "%s  %s  %s" % (fields[1], fields[2] or "sem rotulo",
                                           fields[3] or "nao montada"))
               for fields in removable]
    chosen = tui.menu("Particoes removiveis:", options, title="Pendrive")
    if chosen is None:
        return
    result = subprocess.run(["udisksctl", "mount", "-b", "/dev/" + chosen],
                            text=True, capture_output=True)
    tui.message((result.stdout or result.stderr).strip())


def menu_logging():
    """Liga verbose em switchres, MAME e RetroArch de uma vez (gasetup
    lib-troubleshoot faz o mesmo), pra nao cacar flag por flag."""
    on = tui.yesno("Ligar log detalhado?\n\nSIM liga; NAO volta ao nivel normal.",
                   default_no=False)
    set_ini_value(ETC / "switchres.ini", "verbosity", "3" if on else "2")
    sync_switchres()
    set_ini_value(ETC / "mame/mame.ini", "verbose", "1" if on else "0")
    retroarch = ETC / "retroarch/retroarch.cfg"
    set_cfg_value(retroarch, "log_verbosity", "true" if on else "false")
    set_cfg_value(retroarch, "libretro_log_level", "0" if on else "1")
    tui.message("Log detalhado " + ("ligado" if on else "desligado") + ".")


def menu_collect_logs():
    """Junta os logs num arquivo so, pra sair da maquina por SFTP/Samba.
    O gasetup sobe pra um pastebin; aqui nada sai da rede local sem o usuario."""
    dest = Path("/opt/fliperos/logs")
    dest.mkdir(parents=True, exist_ok=True)
    bundle = dest / "fliperos-diagnostico.txt"
    with bundle.open("w") as out:
        for label, path in (("cmdline", Path("/proc/cmdline")),
                            ("perfil", ETC / "profile")):
            out.write("\n===== " + label + " =====\n")
            out.write(path.read_text() if path.is_file() else "(ausente)\n")
        out.write("\n===== modos DRM =====\n")
        for modes in sorted(Path("/sys/class/drm").glob("*/modes")):
            out.write(modes.parent.name + ": " + " ".join(modes.read_text().split()) + "\n")
        for label, args in (("fliperos-video-check", ["/usr/local/bin/fliperos-video-check"]),
                            ("journal do video-check",
                             ["journalctl", "-u", "fliperos-video-check", "-n", "200"]),
                            ("dmesg drm", ["dmesg", "--level=err,warn"])):
            if not shutil.which(args[0]) and not Path(args[0]).exists():
                continue
            out.write("\n===== " + label + " =====\n")
            out.flush()
            subprocess.run(args, stdout=out, stderr=subprocess.STDOUT, check=False)
    tui.message("Logs reunidos em\n%s\n\nPegue pela rede:\n"
                "\\\\<ip>\\FliperOS\\logs  ou  sftp fliperos@<ip>" % bundle)


def menu_system():
    options = [("senha", "Trocar senha do fliperos"),
               ("usb", "Montar pendrive (copiar ROMs)"),
               ("log", "Nivel de log (diagnostico)"),
               ("coletar", "Reunir logs num arquivo"),
               ("shell", "Shell root")]
    while True:
        chosen = tui.menu("Sistema e diagnostico.", options, title="Sistema")
        if chosen is None:
            return
        if chosen == "senha":
            menu_password()
        elif chosen == "usb":
            menu_usb()
        elif chosen == "log":
            menu_logging()
        elif chosen == "coletar":
            menu_collect_logs()
        elif chosen == "shell":
            tui.run_visible(["/bin/bash"], "Shell root — digite exit pra voltar",
                            pause_after=False)


def menu_power():
    chosen = tui.menu("Encerrar a maquina.", [("reboot", "Reiniciar"),
                                              ("poweroff", "Desligar")],
                      title="Energia")
    if chosen == "reboot":
        run("reboot")
    elif chosen == "poweroff":
        run("poweroff")


# ════════════════════════════════════════════════════════════
def status_line():
    host = (run("hostname", capture=True, check=False) or "fliperos").strip()
    addrs = [part.split("/")[0] for line in
             (run("ip", "-4", "-br", "addr", capture=True, check=False) or "").splitlines()
             if not line.startswith("lo") for part in line.split() if "/" in part]
    usage = ""
    try:
        total, used, _ = shutil.disk_usage("/")
        usage = "   disco %d%%" % round(used * 100 / total)
    except OSError:
        pass
    return "%s (%s)%s" % (host, ", ".join(addrs) if addrs else "sem rede", usage)


def menu_setup_media():
    """Menu da midia de instalacao.

    A midia abre AQUI, nao no instalador: numa maquina sem cabo de rede e
    preciso configurar o Wi-Fi e conferir o video antes de instalar em disco.
    Os itens que dependem de GRUB instalado ficam de fora, em vez de estarem
    presentes e recusarem."""
    options = [("rede", "Rede (Wi-Fi) — necessario pra acessar por SSH"),
               ("video", "Verificar o modo de video ativo"),
               ("detectar", "Descobrir qual conector e o do CRT"),
               ("geometria", "Calibrar geometria da imagem"),
               ("instalar", "Instalar em disco (ou reparar existente)"),
               ("compartilhar", "Compartilhamento (Samba, SSH/SFTP)"),
               ("sistema", "Sistema e diagnostico"),
               ("energia", "Reiniciar / desligar"),
               ("shell", "Sair para o shell")]
    while True:
        chosen = tui.menu("%s\n\nMidia de instalacao — configure antes de instalar."
                          % status_line(), options, title="FliperOS — setup",
                          cancel="Sair")
        if chosen is None or chosen == "shell":
            return 0
        try:
            if chosen == "rede":
                menu_network()
            elif chosen == "video":
                tui.run_visible(["/usr/local/bin/fliperos-video-check"],
                                "Modo de video ativo")
            elif chosen == "detectar":
                tui.run_visible(["/usr/local/bin/fliperos-video-autodetect"],
                                "Descobrindo o conector do CRT")
            elif chosen == "geometria":
                menu_geometry()
            elif chosen == "instalar":
                tui.run_visible(["/usr/local/bin/fliperos-install"],
                                "Instalacao", pause_after=False)
            elif chosen == "compartilhar":
                menu_sharing()
            elif chosen == "sistema":
                menu_system()
            elif chosen == "energia":
                menu_power()
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            tui.message("Falhou:\n\n" + str(exc))


def menu_installed():
    options = [("componentes", "Instalar componentes (launchers, emuladores)"),
               ("sessao", "Sessao ao ligar (qual launcher abre)"),
               ("video", "Video (monitor, resolucao, orientacao, geometria)"),
               ("rede", "Rede (Wi-Fi)"),
               ("compartilhar", "Compartilhamento (Samba, SSH/SFTP)"),
               ("sistema", "Sistema e diagnostico"),
               ("abrir", "Abrir a sessao agora"),
               ("energia", "Reiniciar / desligar"),
               ("shell", "Sair para o shell")]
    while True:
        chosen = tui.menu("%s\nperfil %s   sessao %s"
                          % (status_line(), active_profile(), active_session()),
                          options, title="FliperOS — configuracao", cancel="Sair")
        if chosen is None or chosen == "shell":
            return 0
        try:
            if chosen == "componentes":
                menu_components()
            elif chosen == "sessao":
                menu_session()
            elif chosen == "video":
                menu_video()
            elif chosen == "rede":
                menu_network()
            elif chosen == "compartilhar":
                menu_sharing()
            elif chosen == "sistema":
                menu_system()
            elif chosen == "abrir":
                tui.run_visible(["/opt/fliperos/bin/fliperos-session"],
                                "Sessao", pause_after=False)
            elif chosen == "energia":
                menu_power()
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            tui.message("Falhou:\n\n" + str(exc))


def main():
    if os.geteuid() != 0:
        print("Execute com sudo: sudo fliperos-config")
        return 1
    tui.require()
    try:
        return menu_installed() if installed() else menu_setup_media()
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
