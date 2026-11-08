"""Roda um comando no terminal de root do modo lab do FliperOS (Setup >
System > Lab mode: o link https://X.trycloudflare.com/lab?key=K que a pessoa
manda).

    python3 tools/labsh.py URL_DO_LAB "comando"   (ou um script pela entrada padrao)

Neste Windows nao ha Python: roda pelo WSL, com a URL entre aspas simples (o
shell de login do WSL e o zsh, e o "?" vira glob):

    MSYS_NO_PATHCONV=1 wsl -d Ubuntu-22.04 -e python3 /mnt/c/.../tools/labsh.py 'URL' 'comando'
    MSYS_NO_PATHCONV=1 wsl -d Ubuntu-22.04 -e sh -c 'python3 .../labsh.py "URL" < script.sh'

Como funciona: GET /lab?key= da o cookie fliperos_session (guardado em
labsh.cookie ao lado deste script, ou em LABSH_COOKIE); o WebSocket de
/api/terminal exige Origin igual ao Host; quadros binarios sao teclas, o texto
{"resize": [c, l]} o tamanho. O comando vai num bash sem eco nem prompt, sem a
expansao de "!" (set +H), e um marcador da o fim e o codigo de saida.

Cuidados: uma linha maior que 4096 bytes trava no pty (mande scripts longos
pela entrada padrao, linha a linha, ou em pedacos de base64); um comando calado
por ~100 s cai no tunel (LABSH_TIMEOUT, padrao 120): rode o longo com
setsid nohup ... & e consulte depois. O lab nao volta sozinho depois de um
reboot: a pessoa liga de novo e manda o link novo.
"""
import base64, json, os, re, socket, ssl, struct, sys, time, uuid
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
COOKIE = os.environ.get("LABSH_COOKIE") or os.path.join(HERE, "labsh.cookie")


def conn(host):
    ctx = ssl.create_default_context()
    s = socket.create_connection((host, 443), timeout=30)
    return ctx.wrap_socket(s, server_hostname=host)


def read_head(s):
    buf = b""
    while b"\r\n\r\n" not in buf:
        c = s.recv(4096)
        if not c:
            break
        buf += c
    head, _, rest = buf.partition(b"\r\n\r\n")
    return head.decode("latin-1"), rest


def login(url):
    u = urlparse(url)
    s = conn(u.hostname)
    s.sendall(("GET %s?%s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n" % (u.path, u.query, u.hostname)).encode())
    head, _ = read_head(s)
    s.close()
    m = re.search(r"fliperos_session=([^;\s]+)", head)
    if not m or m.group(1) == "":
        sys.exit("login falhou:\n" + head)
    with open(COOKIE, "w") as f:
        f.write(m.group(1))
    return m.group(1)


def frame(opcode, data):
    mask = os.urandom(4)
    n = len(data)
    head = bytes([0x80 | opcode])
    if n < 126:
        head += bytes([0x80 | n])
    elif n < 1 << 16:
        head += bytes([0x80 | 126]) + struct.pack(">H", n)
    else:
        head += bytes([0x80 | 127]) + struct.pack(">Q", n)
    return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data))


class Reader:
    def __init__(self, s, rest):
        self.s, self.buf = s, rest

    def need(self, n):
        while len(self.buf) < n:
            c = self.s.recv(65536)
            if not c:
                raise EOFError
            self.buf += c
        d, self.buf = self.buf[:n], self.buf[n:]
        return d

    def frame(self):
        b0, b1 = self.need(2)
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack(">H", self.need(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", self.need(8))[0]
        return b0 & 0x0F, self.need(n)


def run(url, cmd, timeout):
    u = urlparse(url)
    token = open(COOKIE).read().strip() if os.path.exists(COOKIE) else login(url)
    for attempt in (0, 1):
        s = conn(u.hostname)
        key = base64.b64encode(os.urandom(16)).decode()
        s.sendall(("GET /api/terminal HTTP/1.1\r\nHost: {h}\r\nOrigin: https://{h}\r\n"
                   "Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {k}\r\n"
                   "Sec-WebSocket-Version: 13\r\nCookie: fliperos_session={t}\r\n\r\n")
                  .format(h=u.hostname, k=key, t=token).encode())
        head, rest = read_head(s)
        if " 101 " in head.split("\r\n")[0]:
            break
        s.close()
        if attempt:
            sys.exit("terminal recusado:\n" + head)
        token = login(url)
    r = Reader(s, rest)
    s.sendall(frame(1, json.dumps({"resize": [250, 50]}).encode()))
    mark = uuid.uuid4().hex
    # bash sem eco nem prompt; o marcador diz o fim e o codigo de saida.
    script = ("exec bash --norc --noprofile\n")
    s.sendall(frame(2, script.encode()))
    time.sleep(0.5)
    body = "stty -echo; PS1=''; PS2=''; set +H\n{c}\necho; echo __END_{m}__ $?\n".format(c=cmd, m=mark)
    s.sendall(frame(2, body.encode()))
    out, end = b"", time.time() + timeout
    s.settimeout(5)
    while time.time() < end:
        try:
            op, data = r.frame()
        except socket.timeout:
            continue
        except EOFError:
            break
        if op == 8:
            break
        out += data
        if ("__END_%s__" % mark).encode() in out.split(b"stty -echo", 1)[-1].split(b"__END_" + mark.encode() + b"__ $?", 1)[-1]:
            break
    try:
        s.sendall(frame(8, struct.pack(">H", 1000)))
    except OSError:
        pass
    s.close()
    text = out.decode("utf-8", "replace").replace("\r\n", "\n")
    text = text.split("__END_%s__ $?" % mark, 1)[-1]
    text = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]|\x1b\][^\x07]*\x07", "", text)
    m = re.search(r"__END_%s__ (\d+)" % mark, text)
    code = int(m.group(1)) if m else -1
    text = text[:m.start()] if m else text + "\n[timeout]"
    return text.strip("\n"), code


if __name__ == "__main__":
    cmd = sys.argv[2] if len(sys.argv) > 2 else sys.stdin.read()
    t = int(os.environ.get("LABSH_TIMEOUT", "120"))
    text, code = run(sys.argv[1], cmd, t)
    print(text)
    print("[exit %d]" % code)
    sys.exit(0 if code == 0 else 1)
