"""Abre o app DriveSafe no modo de teste local: sem o servidor da API e sem banco.

Serve a pasta webapp/ em http://localhost:8765 (só neste computador) e abre o navegador.
No navegador, dá para instalar o app (ícone de instalar na barra de endereço do Chrome/Edge).

    python servir_app_local.py            # porta 8765
    python servir_app_local.py 9000       # outra porta
"""
import functools
import http.server
import sys
import webbrowser
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
WEBAPP = Path(__file__).resolve().parent / "webapp"

# No Windows o registro às vezes diz que .js é text/plain, e o navegador recusa módulos: força os tipos certos.
TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json", ".webmanifest": "application/manifest+json",
    ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2", ".wasm": "application/wasm",
    ".task": "application/octet-stream", ".tflite": "application/octet-stream", ".txt": "text/plain; charset=utf-8",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **TYPES}

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        if self.path.startswith("/sw.js"):
            self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def log_message(self, format, *args):  # noqa: A002 - assinatura da biblioteca
        pass


def main():
    handler = functools.partial(Handler, directory=str(WEBAPP))
    with http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler) as server:
        url = f"http://localhost:{PORT}/"
        print(f"App DriveSafe (modo de teste local) em {url}")
        print("PIN de teste: o combinado com a equipe. Feche esta janela (ou Ctrl+C) para parar.")
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
