"""Servidor de mentira da central (spec 026) em http.server, para os testes do app de teste. Não é teste."""
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = "dsk_" + "x" * 40


class Central:
    def __init__(self):
        self.pedidos = []
        self.sessoes = {}
        self.trechos = {}
        self.eventos = {}
        self.porta = None
        self.httpd = None
        # Resposta forçada por rota: {"/api/trechos": (429, {"Retry-After": "1"})}; vale até ser removida.
        self.forcar = {}

    def subir(self, porta=0):
        central = self

        class Manipulador(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _corpo(self):
                tamanho = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(tamanho) if tamanho else b""

            def _json(self, status, dados):
                corpo = json.dumps(dados).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def _forcado(self):
                for prefixo, (status, extras) in central.forcar.items():
                    if self.path.startswith(prefixo):
                        corpo = json.dumps({"detail": f"Forçado {status}."}).encode()
                        self.send_response(status)
                        for chave, valor in extras.items():
                            self.send_header(chave, valor)
                        self.send_header("Content-Type", "application/json")
                        self.send_header("Content-Length", str(len(corpo)))
                        self.end_headers()
                        self.wfile.write(corpo)
                        return True
                return False

            def do_POST(self):
                corpo = self._corpo()
                central.pedidos.append(("POST", self.path, dict(self.headers), corpo))
                if self._forcado():
                    return
                if self.path == "/api/pareamento/trocar":
                    dados = json.loads(corpo)
                    if dados["codigo"].replace("-", "").upper() != "ABCD2345":
                        return self._json(404, {"detail": "Código inválido ou expirado."})
                    return self._json(200, {"token": "dsk_" + "x" * 40, "aparelho_uid": "d" * 32,
                                            "empresa": {"uid": "e" * 32, "nome": "Transportes Exemplo"}})
                if self.headers.get("Authorization") != "Bearer dsk_" + "x" * 40:
                    return self._json(401, {"detail": "Token inválido."})
                if self.path == "/api/events":
                    for evento in json.loads(corpo)["events"]:
                        central.eventos[evento["event_uid"]] = evento
                    return self._json(200, {"accepted": 1, "duplicates": 0})
                if self.path == "/api/devices/heartbeat":
                    return self._json(200, {"policy": {}})
                return self._json(404, {"detail": "Nada aqui."})

            def do_PUT(self):
                corpo = self._corpo()
                central.pedidos.append(("PUT", self.path, dict(self.headers), corpo))
                if self._forcado():
                    return
                if self.headers.get("Authorization") != "Bearer dsk_" + "x" * 40:
                    return self._json(401, {"detail": "Token inválido."})
                partes = self.path.strip("/").split("/")
                if partes[:2] == ["api", "sessoes"]:
                    central.sessoes[partes[2]] = json.loads(corpo)
                    return self._json(200, {"uid": partes[2]})
                if partes[:2] == ["api", "trechos"]:
                    if hashlib.sha256(corpo).hexdigest() != self.headers.get("X-RotaGuard-Sha256"):
                        return self._json(422, {"detail": "SHA-256 não confere."})
                    central.trechos[partes[2]] = ({k.lower(): v for k, v in self.headers.items()}, corpo)
                    return self._json(201, {"uid": partes[2], "tamanho": len(corpo)})
                return self._json(404, {"detail": "Nada aqui."})

        self.httpd = ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)
        self.porta = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def descer(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.porta}"
