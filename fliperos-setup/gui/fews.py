# Um cliente WebSocket (RFC 6455) so com a biblioteca padrao do Python, para
# o Matchmaker falar com o servidor online (wss://, pelo tunel da
# Cloudflare). So o que o Matchmaker usa: mensagens de texto, ping e pong,
# fechamento; os quadros que saem vao mascarados, como a norma pede ao cliente.
#
# A Cloudflare recusa (403) o User-Agent padrao do Python: este manda o do
# FliperOS.

import base64
import hashlib
import os
import socket
import ssl
import struct
import threading
from urllib.parse import urlparse

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
USER_AGENT = "FliperOS-Matchmaker/1"
MAX_MESSAGE = 1 << 20


class Closed(Exception):
    """A conexao fechou (o servidor, a rede ou close())."""


class WebSocket:
    def __init__(self, url, timeout=10.0, headers=None):
        u = urlparse(url)
        if u.scheme not in ("ws", "wss"):
            raise ValueError("url")
        secure = u.scheme == "wss"
        host = u.hostname
        port = u.port or (443 if secure else 80)
        path = (u.path or "/") + ("?" + u.query if u.query else "")
        sock = socket.create_connection((host, port), timeout)
        try:
            if secure:
                sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
            key = base64.b64encode(os.urandom(16)).decode()
            hostport = host if port == (443 if secure else 80) else "%s:%d" % (host, port)
            lines = ["GET %s HTTP/1.1" % path, "Host: %s" % hostport, "Upgrade: websocket", "Connection: Upgrade",
                     "Sec-WebSocket-Key: %s" % key, "Sec-WebSocket-Version: 13", "User-Agent: %s" % USER_AGENT]
            lines += ["%s: %s" % kv for kv in (headers or {}).items()]
            sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = sock.recv(4096)
                if not chunk or len(data) > 16384:
                    raise Closed("handshake")
                data += chunk
            head, self.buf = data.split(b"\r\n\r\n", 1)
            status, *fields = head.decode("latin-1").split("\r\n")
            if " 101 " not in status + " ":
                raise Closed("status " + status)
            hdr = {k.strip().lower(): v.strip() for k, _, v in (f.partition(":") for f in fields)}
            want = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
            if hdr.get("sec-websocket-accept") != want:
                raise Closed("accept")
        except Exception:
            sock.close()
            raise
        self.sock = sock
        self.lock = threading.Lock()
        self.closed = False

    # -- saida
    def _frame(self, opcode, payload):
        n = len(payload)
        if n < 126:
            head = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        mask = os.urandom(4)
        body = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        with self.lock:
            try:
                self.sock.sendall(head + mask + body)
            except OSError as e:
                raise Closed(str(e))

    def send(self, text):
        self._frame(0x1, text.encode("utf-8"))

    # -- entrada
    def _frame_in(self):
        """O proximo quadro inteiro do buffer, (b1, payload), ou None se ainda
        falta chegar parte dele (o buffer fica como esta: um tempo esgotado no
        meio de um quadro nao perde nada)."""
        b = self.buf
        if len(b) < 2:
            return None
        b1, b2 = b[0], b[1]
        n, i = b2 & 0x7F, 2
        if n == 126:
            if len(b) < 4:
                return None
            n, i = struct.unpack("!H", b[2:4])[0], 4
        elif n == 127:
            if len(b) < 10:
                return None
            n, i = struct.unpack("!Q", b[2:10])[0], 10
        if n > MAX_MESSAGE:
            raise Closed("too big")
        mask = None
        if b2 & 0x80:
            if len(b) < i + 4:
                return None
            mask, i = b[i:i + 4], i + 4
        if len(b) < i + n:
            return None
        payload, self.buf = b[i:i + n], b[i + n:]
        if mask:
            payload = bytes(x ^ mask[k & 3] for k, x in enumerate(payload))
        return b1, payload

    def recv(self, timeout=None):
        """A proxima mensagem de texto; None se o tempo acabou. Responde os pings."""
        self.sock.settimeout(timeout)
        if not hasattr(self, "parts"):
            self.parts = []
        while True:
            fr = self._frame_in()
            if fr is None:
                try:
                    chunk = self.sock.recv(65536)
                except socket.timeout:
                    return None
                except OSError as e:
                    raise Closed(str(e))
                if not chunk:
                    raise Closed("eof")
                self.buf += chunk
                continue
            b1, payload = fr
            opcode = b1 & 0x0F
            if opcode == 0x8:
                self.close()
                raise Closed("closed by the server")
            if opcode == 0x9:
                self._frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            self.parts.append(payload)
            if b1 & 0x80:
                text = b"".join(self.parts).decode("utf-8", errors="replace")
                self.parts = []
                return text

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self._frame(0x8, struct.pack("!H", 1000))
        except Closed:
            pass
        try:
            self.sock.close()
        except OSError:
            pass
