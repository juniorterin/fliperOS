#!/usr/bin/env python3
"""FliperOS — menu de configuracao do sistema instalado.

Equivalente ao `mainmenu` do gasetup: fica no sistema depois da instalacao e
concentra video, rede, compartilhamento e diagnostico, em vez de congelar tudo
no momento do build da ISO.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ETC = Path("/etc/fliperos")
PROFILES = ETC / "profiles"
GRUB_CFG = Path("/etc/default/grub.d/99-fliperos.cfg")
EDID_LIVE = Path("/lib/firmware/edid/crt15.bin")
VIDEO_CHECK = Path("/etc/systemd/system/fliperos-video-check.service")
PROFILE_KHZ = {"15khz": (15.0, 16.0), "25khz": (24.5, 25.5), "31khz": (31.0, 32.0)}


def run(*args, check=True, capture=False, env=None):
    merged = dict(os.environ, **env) if env else None
    return subprocess.run(args, check=check, text=True, env=merged,
                          stdout=subprocess.PIPE if capture else None).stdout


def quiet(*args):
    """Roda sem falhar e sem poluir a tela; devolve True no exit 0."""
    return subprocess.run(args, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0


def ask(prompt, default=""):
    got = input(prompt + (" [" + default + "]" if default else "") + ": ").strip()
    return got or default


def confirm(prompt):
    return input(prompt + " (s/N): ").strip().lower() in ("s", "sim", "y")


def pause():
    input("\nENTER para voltar. ")


def active_profile():
    path = ETC / "profile"
    return path.read_text().strip() if path.is_file() else "15khz"


def installed():
    return (ETC / "installed").is_file()


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


def connector():
    path = ETC / "connector"
    return path.read_text().strip() if path.is_file() else "VGA-1"


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
#  Carta de teste (grid) — confirma um modo antes de gravar
# ════════════════════════════════════════════════════════════
def show_grid(width, height, refresh, note="", geometry=None):
    """Mostra a grade de teste no modo pedido. False se o switchres falhar."""
    if not shutil.which("grid"):
        print("Binario 'grid' ausente; nao da pra testar o modo visualmente.")
        return False
    env = {"GRID_TEXT": note} if note else {}
    if not os.environ.get("DISPLAY"):
        env["SDL_VIDEODRIVER"] = "kmsdrm"
    args = ["switchres", str(width), str(height), str(refresh), "-s", "-l", "grid"]
    if geometry:
        args += ["--geometry", "%s:%d:%d" % geometry]
    return subprocess.run(args, env=dict(os.environ, **env)).returncode == 0


def confirm_mode(width, height, refresh, geometry=None):
    """Mostra a grade e exige confirmacao visual. Espelha o
    worker_custom_video_mode do gasetup: nada e gravado sem o usuario ver."""
    print("\nA grade de teste vai aparecer no CRT. Feche com ENTER ou Q.")
    print("Se a tela ficar preta ou fora de sincronia, espere o retorno e responda NAO.")
    pause()
    if not show_grid(width, height, refresh,
                     "Teste %sx%s@%s" % (width, height, refresh), geometry):
        print("O switchres nao conseguiu aplicar esse modo.")
        return False
    return confirm("A grade apareceu inteira e estavel?")


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
    run("update-initramfs", "-u", "-k", "all")


def menu_profile():
    current = active_profile()
    print("\nPerfil de monitor ativo: " + current)
    print("Cada perfil troca EDID, switchres.ini, xorg.conf e mame.ini de uma vez.")
    options = list(PROFILE_KHZ)
    for i, name in enumerate(options, 1):
        low, high = PROFILE_KHZ[name]
        mark = " (atual)" if name == current else ""
        print("%d. %s — %.1f a %.1f kHz%s" % (i, name, low, high, mark))
    print("0. Voltar")
    choice = ask("Opcao")
    if choice == "0" or not choice.isdigit() or not 1 <= int(choice) <= len(options):
        return
    profile = options[int(choice) - 1]
    if profile == current:
        print("Esse perfil ja esta ativo.")
        return pause()
    print("\nTrocar de perfil regrava o EDID e o initramfs. O modo novo so vale no")
    print("proximo boot, e um CRT de 15 kHz nao sincroniza um perfil de 31 kHz.")
    if not confirm("Aplicar o perfil " + profile + "?"):
        return
    apply_profile(profile)
    print("Perfil " + profile + " aplicado. Reinicie pra validar o modo.")
    pause()


def menu_custom_mode():
    """Gera o EDID em runtime com switchres -e, testando antes de gravar.
    E o que permite uma resolucao fora dos tres perfis sem rebuildar a ISO."""
    if not shutil.which("switchres"):
        print("switchres ausente; rode sudo fliperos-postinstall primeiro.")
        return pause()
    print("\nResolucao customizada — gera um EDID novo pro CRT.")
    width = ask("Largura", "320")
    height = ask("Altura", "240")
    refresh = ask("Refresh vertical (Hz)", "60")
    if not all(re.fullmatch(r"\d+(\.\d+)?", v) for v in (width, height, refresh)):
        print("Valores invalidos.")
        return pause()
    modeline = run("switchres", width, height, refresh, "-c", capture=True, check=False)
    print("\nModeline calculada:\n" + (modeline or "(o switchres nao devolveu modeline)"))
    if not confirm("Seguir com essa modeline?"):
        return
    if not confirm_mode(width, height, refresh):
        print("Nada foi gravado.")
        return pause()
    with tempfile.TemporaryDirectory() as tmp:
        # -e escreve o .bin no diretorio corrente, entao o switchres roda
        # dentro do tempdir: nada e procurado nem apagado fora dele.
        subprocess.run(["switchres", width, height, refresh, "-e"], cwd=tmp, check=True)
        produced = sorted(Path(tmp).glob("*.bin"))
        if not produced:
            print("O switchres nao gerou o arquivo de EDID.")
            return pause()
        shutil.copyfile(produced[0], EDID_LIVE)
    run("update-initramfs", "-u", "-k", "all")
    (ETC / "custom-mode").write_text("%s %s %s\n" % (width, height, refresh))
    print("\nEDID gravado em " + str(EDID_LIVE) + " e initramfs atualizado.")
    print("A cmdline ja aponta pra esse arquivo, entao nao precisa mexer no GRUB.")
    pause()


def menu_orientation():
    """Gabinete vertical (tate). Ajusta MAME, fbcon e panel_orientation juntos,
    como o worker_select_monitor_orientation do gasetup."""
    modes = [("horizontal", None, None, None),
             ("vertical (girado a direita)", "1", "ror", "right_side_up"),
             ("vertical (girado a esquerda)", "3", "rol", "left_side_up"),
             ("invertido (180 graus)", "2", None, "upside_down")]
    print("\nOrientacao do monitor")
    for i, (label, _, _, _) in enumerate(modes, 1):
        print("%d. %s" % (i, label))
    print("0. Voltar")
    choice = ask("Opcao")
    if choice == "0" or not choice.isdigit() or not 1 <= int(choice) <= len(modes):
        return
    label, fbcon, mame_key, panel = modes[int(choice) - 1]
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
    print("Orientacao ajustada para: " + label)
    print("MAME e console valem ja; o giro do KMS entra no proximo boot.")
    pause()


def menu_connector():
    """Troca de GPU/cabo sem reinstalar: reaponta conector na cmdline e nos configs."""
    print("\nConector atual: " + connector())
    checker = "/usr/local/bin/fliperos-video-check"
    if Path(checker).is_file():
        report = subprocess.run([checker, "--json"], text=True, capture_output=True)
        try:
            outputs = json.loads(report.stdout)["outputs"]
        except (json.JSONDecodeError, KeyError):
            outputs = []
        for out in outputs:
            state = "ativo %.4f kHz" % out["horizontal_khz"] if out["active"] else "inativo"
            print("  - %s (%s)" % (out["connector"], state))
    new = ask("Novo conector (ENTER cancela)")
    if not new:
        return
    if not re.fullmatch(r"(?:VGA|DVI-I|DVI-A|DP|HDMI-A)-[1-9][0-9]*", new):
        print("Nome de conector invalido.")
        return pause()
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
    print("Conector trocado para " + new + ". Reinicie pra validar.")
    pause()


def menu_geometry():
    """Centraliza/dimensiona a imagem no tubo e grava em switchres.ini.
    O grid do switchres so desenha a carta; o laco de ajuste e daqui."""
    ini = ETC / "switchres.ini"
    if not ini.is_file():
        print("switchres.ini ausente.")
        return pause()
    h_size, h_shift, v_shift = 1.0, 0, 0
    print("\nCalibracao de geometria — a grade aparece, voce fecha com ENTER/Q e ajusta.")
    while True:
        note = "h_size %.2f  h_shift %d  v_shift %d" % (h_size, h_shift, v_shift)
        print("\nAtual: " + note)
        if confirm("Mostrar a grade com esses valores?"):
            show_grid(640, 480, 60, note, (h_size, h_shift, v_shift))
        print("a/d = esquerda/direita   w/s = cima/baixo   -/+ = largura")
        print("g = gravar   c = cancelar")
        key = ask("Tecla")
        if key == "a":
            h_shift -= 1
        elif key == "d":
            h_shift += 1
        elif key == "w":
            v_shift -= 1
        elif key == "s":
            v_shift += 1
        elif key == "-":
            h_size = round(h_size - 0.01, 2)
        elif key == "+":
            h_size = round(h_size + 0.01, 2)
        elif key == "g":
            set_ini_value(ini, "h_size", "%.3f" % h_size)
            set_ini_value(ini, "h_shift", str(h_shift))
            set_ini_value(ini, "v_shift", str(v_shift))
            sync_switchres()
            print("Geometria gravada em switchres.ini.")
            return pause()
        elif key == "c":
            return


def menu_video():
    while True:
        print("\n── Video ──  perfil: %s  conector: %s" % (active_profile(), connector()))
        print("1. Perfil de monitor (15 / 25 / 31 kHz)")
        print("2. Resolucao customizada (gera EDID novo)")
        print("3. Orientacao do monitor")
        print("4. Trocar conector (troquei de GPU ou cabo)")
        print("5. Calibrar geometria")
        print("0. Voltar")
        choice = ask("Opcao")
        if choice == "1":
            menu_profile()
        elif choice == "2":
            menu_custom_mode()
        elif choice == "3":
            menu_orientation()
        elif choice == "4":
            menu_connector()
        elif choice == "5":
            menu_geometry()
        else:
            return


# ════════════════════════════════════════════════════════════
#  Rede
# ════════════════════════════════════════════════════════════
def wifi_device():
    out = run("nmcli", "-t", "-f", "DEVICE,TYPE", "device", capture=True, check=False) or ""
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] == "wifi":
            return parts[0]
    return None


def menu_wifi():
    """Wi-Fi via nmcli. O gasetup usa iwctl/iwd porque e Arch; aqui o
    NetworkManager ja persiste a conexao, sem editar arquivo de rede."""
    device = wifi_device()
    if not device:
        print("Nenhuma interface Wi-Fi encontrada. Pode faltar firmware do adaptador.")
        return pause()
    print("\nInterface Wi-Fi: " + device)
    print("Procurando redes...")
    quiet("nmcli", "device", "wifi", "rescan")
    out = run("nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list",
              capture=True, check=False) or ""
    networks = []
    for line in out.splitlines():
        fields = line.split(":")
        if fields and fields[0] and fields[0] not in [n[0] for n in networks]:
            networks.append((fields[0], fields[1] if len(fields) > 1 else "?",
                             fields[2] if len(fields) > 2 else ""))
    if not networks:
        print("Nenhuma rede encontrada.")
        return pause()
    for i, (ssid, signal, security) in enumerate(networks, 1):
        print("%d. %s (sinal %s%%%s)" % (i, ssid, signal,
                                         ", aberta" if not security else ""))
    print("0. Voltar")
    choice = ask("Rede")
    if choice == "0" or not choice.isdigit() or not 1 <= int(choice) <= len(networks):
        return
    ssid, _, security = networks[int(choice) - 1]
    args = ["nmcli", "device", "wifi", "connect", ssid]
    if security:
        password = ask("Senha de " + ssid)
        if not password:
            return
        args += ["password", password]
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        print("Falhou: " + (result.stderr or result.stdout).strip())
    else:
        print("Conectado em " + ssid + ". O NetworkManager reconecta sozinho no boot.")
    pause()


def menu_regdom():
    """Dominio regulatorio: pais errado derruba canais (copiado do gasetup)."""
    current = run("iw", "reg", "get", capture=True, check=False) or ""
    match = re.search(r"country (\S\S)", current)
    print("\nDominio regulatorio atual: " + (match.group(1) if match else "desconhecido"))
    if match and match.group(1) == "00":
        print("'00' e o padrao mundial restrito — define o pais pra liberar os canais.")
    code = ask("Codigo do pais (ex: BR), ENTER cancela").upper()
    if not re.fullmatch(r"[A-Z]{2}", code or ""):
        return
    if not quiet("iw", "reg", "set", code):
        print("Nao foi possivel aplicar o dominio.")
        return pause()
    Path("/etc/default/crda").write_text("REGDOMAIN=" + code + "\n")
    conf = Path("/etc/modprobe.d/cfg80211.conf")
    conf.write_text("options cfg80211 ieee80211_regdom=" + code + "\n")
    print("Dominio " + code + " aplicado e persistido.")
    pause()


def menu_network():
    while True:
        addrs = run("ip", "-4", "-br", "addr", capture=True, check=False) or ""
        print("\n── Rede ──")
        for line in addrs.splitlines():
            if not line.startswith("lo"):
                print("  " + " ".join(line.split()))
        print("1. Conectar no Wi-Fi")
        print("2. Dominio regulatorio (pais)")
        print("3. Status detalhado")
        print("0. Voltar")
        choice = ask("Opcao")
        if choice == "1":
            menu_wifi()
        elif choice == "2":
            menu_regdom()
        elif choice == "3":
            run("nmcli", "device", "status", check=False)
            pause()
        else:
            return


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
        if not confirm("Desligar " + label + "?"):
            return
        for unit in units:
            quiet("systemctl", "disable", "--now", unit)
        print(label + " desligado.")
    else:
        for unit in units:
            quiet("systemctl", "enable", "--now", unit)
        print(label + " ligado.")
    pause()


def menu_sharing():
    while True:
        ips = [part.split("/")[0] for line in
               (run("ip", "-4", "-br", "addr", capture=True, check=False) or "").splitlines()
               if not line.startswith("lo") for part in line.split() if "/" in part]
        host = (run("hostname", capture=True, check=False) or "fliperos").strip()
        print("\n── Compartilhamento ──")
        print("  Samba (smbd/nmbd): " + service_state("smbd"))
        print("  SSH/SFTP (ssh):    " + service_state("ssh"))
        if ips:
            print("  Acesso: \\\\" + ips[0] + "\\FliperOS   ou   sftp fliperos@" + ips[0])
            print("  Por nome: \\\\" + host + "  (NetBIOS)   " + host + ".local (mDNS)")
        print("\n1. Ligar/desligar Samba")
        print("2. Ligar/desligar SSH")
        print("3. Senha do Samba do usuario fliperos")
        print("0. Voltar")
        choice = ask("Opcao")
        if choice == "1":
            toggle_service(["smbd", "nmbd"], "Samba")
        elif choice == "2":
            toggle_service(["ssh"], "SSH")
        elif choice == "3":
            subprocess.run(["smbpasswd", "-a", "fliperos"])
            pause()
        else:
            return


# ════════════════════════════════════════════════════════════
#  Sistema e diagnostico
# ════════════════════════════════════════════════════════════
def menu_password():
    print("\nSenha do usuario fliperos (login, sudo e SSH).")
    if subprocess.run(["passwd", "fliperos"]).returncode:
        return pause()
    if confirm("Usar a mesma senha no Samba?"):
        subprocess.run(["smbpasswd", "-a", "fliperos"])
    pause()


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
        print("Nenhuma particao removivel encontrada.")
        return pause()
    for i, fields in enumerate(removable, 1):
        mounted = fields[3] or "nao montada"
        print("%d. /dev/%s  %s  %s  (%s)" % (i, fields[0], fields[1],
                                             fields[2] or "sem rotulo", mounted))
    print("0. Voltar")
    choice = ask("Particao")
    if choice == "0" or not choice.isdigit() or not 1 <= int(choice) <= len(removable):
        return
    device = "/dev/" + removable[int(choice) - 1][0]
    result = subprocess.run(["udisksctl", "mount", "-b", device], text=True, capture_output=True)
    print((result.stdout or result.stderr).strip())
    pause()


def menu_logging():
    """Liga verbose em switchres, MAME e RetroArch de uma vez (gasetup
    lib-troubleshoot faz o mesmo), pra nao caçar flag por flag."""
    print("\nResponder SIM liga o log detalhado; NAO volta ao nivel normal.")
    on = confirm("Ligar log detalhado?")
    set_ini_value(ETC / "switchres.ini", "verbosity", "3" if on else "2")
    sync_switchres()
    set_ini_value(ETC / "mame/mame.ini", "verbose", "1" if on else "0")
    retroarch = ETC / "retroarch/retroarch.cfg"
    set_cfg_value(retroarch, "log_verbosity", "true" if on else "false")
    set_cfg_value(retroarch, "libretro_log_level", "0" if on else "1")
    print("Log detalhado " + ("ligado" if on else "desligado") + ".")
    pause()


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
    print("Logs reunidos em " + str(bundle))
    print("Pegue pela rede: \\\\<ip>\\FliperOS\\logs  ou  sftp fliperos@<ip>")
    pause()


def menu_rescue_shell():
    """Shell root no proprio sistema (o rescue_mode do gasetup entra por
    chroot a partir da ISO; aqui o sistema ja e o alvo)."""
    print("\nAbrindo um shell root. Digite exit pra voltar ao menu.")
    subprocess.run(["/bin/bash"])


def menu_system():
    while True:
        print("\n── Sistema ──")
        print("1. Trocar senha do fliperos")
        print("2. Montar pendrive (copiar ROMs)")
        print("3. Nivel de log (diagnostico)")
        print("4. Reunir logs num arquivo")
        print("5. Shell root")
        print("0. Voltar")
        choice = ask("Opcao")
        if choice == "1":
            menu_password()
        elif choice == "2":
            menu_usb()
        elif choice == "3":
            menu_logging()
        elif choice == "4":
            menu_collect_logs()
        elif choice == "5":
            menu_rescue_shell()
        else:
            return


def menu_power():
    print("\n1. Reiniciar")
    print("2. Desligar")
    print("0. Voltar")
    choice = ask("Opcao")
    if choice == "1":
        run("reboot")
    elif choice == "2":
        run("poweroff")


# ════════════════════════════════════════════════════════════
def header():
    host = (run("hostname", capture=True, check=False) or "fliperos").strip()
    addrs = [part.split("/")[0] for line in
             (run("ip", "-4", "-br", "addr", capture=True, check=False) or "").splitlines()
             if not line.startswith("lo") for part in line.split() if "/" in part]
    usage = ""
    try:
        total, used = shutil.disk_usage("/")[0], shutil.disk_usage("/")[1]
        usage = "  disco %d%%" % round(used * 100 / total)
    except OSError:
        pass
    ip = ", ".join(addrs) if addrs else "sem rede"
    print("\n" + "=" * 52)
    print("FliperOS — configuracao")
    print("%s (%s)%s  perfil %s" % (host, ip, usage, active_profile()))
    print("=" * 52)


def main():
    if os.geteuid() != 0:
        print("Execute com sudo: sudo fliperos-config")
        return 1
    if not installed():
        print("Este e o sistema live. Use sudo fliperos-install pra instalar em disco;")
        print("as opcoes de video aqui valem so ate reiniciar.")
    while True:
        header()
        print("1. Video (monitor, resolucao, orientacao, geometria)")
        print("2. Rede (Wi-Fi)")
        print("3. Compartilhamento (Samba, SSH/SFTP)")
        print("4. Sistema e diagnostico")
        print("5. Iniciar o launcher de emuladores")
        print("6. Reiniciar / desligar")
        print("0. Sair para o shell")
        try:
            choice = ask("Opcao")
        except (KeyboardInterrupt, EOFError):
            print()
            return 0
        try:
            if choice == "1":
                menu_video()
            elif choice == "2":
                menu_network()
            elif choice == "3":
                menu_sharing()
            elif choice == "4":
                menu_system()
            elif choice == "5":
                subprocess.run(["/opt/fliperos/bin/fliperos-launcher"])
            elif choice == "6":
                menu_power()
            elif choice == "0":
                return 0
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            print("Falhou: " + str(exc))
            pause()
        except KeyboardInterrupt:
            print()


if __name__ == "__main__":
    raise SystemExit(main())
