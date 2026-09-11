"""Sobe o servidor central (API + painel) e abre o painel no navegador."""
import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser


def wait_until_up(url, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except OSError:
            time.sleep(0.5)
    return False


def lan_addresses():
    try:
        return sorted({ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")})
    except OSError:
        return []


def main():
    parser = argparse.ArgumentParser(description="Inicia o servidor DriveSafe AI.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="use 0.0.0.0 para receber dados dos dispositivos pela rede")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="reinicia ao salvar arquivos (desenvolvimento)")
    parser.add_argument("--no-browser", action="store_true", help="não abre o navegador")
    args = parser.parse_args()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    command = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", args.host, "--port", str(args.port)]
    if args.reload:  # vigia servidor/ e caixa/ (o vision/ usado pelo modo teste)
        command += ["--reload", "--reload-dir", project_dir,
                    "--reload-dir", os.path.join(os.path.dirname(project_dir), "caixa")]

    print("Iniciando o servidor DriveSafe AI...")
    process = subprocess.Popen(command, cwd=project_dir)
    local_url = f"http://localhost:{args.port}"
    try:
        if wait_until_up(local_url + "/health", process):
            print(f"App: {local_url}")
            if args.host == "0.0.0.0":
                for ip in lan_addresses():
                    print(f"Dispositivos na rede usam: http://{ip}:{args.port}")
            if not args.no_browser:
                webbrowser.open(local_url)
        process.wait()
    except KeyboardInterrupt:
        print("\nParando o servidor...")
        process.terminate()
        process.wait(10)


if __name__ == "__main__":
    main()
