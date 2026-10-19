"""Interface exportada (out/) com a Ponte de verdade num navegador comum, para conferir e capturar as telas (spec 030).

Fora da janela do app a interface usa o transporte vazio (nenhum dado). Para conferir as telas com o núcleo Python de
verdade, este servidor entrega a pasta out/ e acrescenta no HTML um `window.pywebview.api` que manda cada chamada para
`POST /__ponte/<método>`, atendida pela mesma `Ponte` da janela do app (painel/desktop/ponte.py), numa pasta de dados
de teste. Os trechos baixados da central saem por /__trechos/, como na janela.

Com --simular, a pasta ganha o que os testes usam (tests/test_painel_central.py e tests/test_painel_script_local.py):
uma central já conectada, com computadores, sessões e eventos de hoje, e o RotaGuard Script "aberto" neste computador,
com eventos na fila dele. Nada sai para a rede.

Uso (na raiz do repositório):
  python painel/app/scripts/servir-com-ponte.py --pasta <pasta de teste> [--porta 3107] [--simular]

Nunca aponte para a pasta de dados do painel instalado: o servidor recusa %LOCALAPPDATA%\\RotaGuard\\Painel.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import rotaguard_painel as rp  # noqa: E402
from central import Central, servir_trecho  # noqa: E402
from dados import pasta_dados  # noqa: E402
from ponte import Ponte  # noqa: E402
from script_local import ScriptLocal  # noqa: E402

CUSTO_BARATO = (2**14, 8, 1)  # senha de teste: entrar rápido nas capturas
_NOME = re.compile(r"^[a-z][a-z_]{1,40}$")
# O pywebview expõe a Ponte em window.pywebview.api; aqui cada método vira um POST. "then" fica de fora: senão a
# Promise do bridge.ts trataria o objeto como uma promessa.
PONTE_NO_NAVEGADOR = (
    "<script>window.pywebview={api:new Proxy({},{get:function(_,nome){"
    "if(typeof nome!=='string'||nome==='then'||!/^[a-z][a-z_]+$/.test(nome))return undefined;"
    "return function(){return fetch('/__ponte/'+nome,{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify(Array.prototype.slice.call(arguments))}).then(function(r){return r.json()})}}})};</script>"
)


def carregar(caminho: Path, nome: str):
    especificacao = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def conferir_pasta(pasta: Path) -> Path:
    pasta = pasta.resolve()
    real = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "RotaGuard"
    for proibida in (pasta_dados(), real):
        try:
            if pasta == Path(proibida).resolve() or pasta.is_relative_to(Path(proibida).resolve()):
                raise SystemExit(f"Recusado: {pasta} é a pasta de dados de verdade. Use uma pasta de teste.")
        except OSError:
            continue
    return pasta


def iso(instante: datetime) -> str:
    return instante.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def simular_central(pasta: Path, empresa: str) -> threading.Event:
    """Central já conectada: 2 computadores (1 testando agora), sessões e eventos de hoje e de ontem."""
    central = Central(pasta)
    agora = datetime.now(timezone.utc)
    escopo = "central-simulada#1"
    central._gravar_meta({"endereco": "https://rotaguard.acexpartners.com.br", "usuario_nome": "Gestor de teste",  # noqa: SLF001
                          "usuario_funcao": "gestor", "empresa_nome": empresa, "empresa": escopo,
                          "ultima_busca": iso(agora), "ultima_tentativa": iso(agora), "situacao": "ok"})
    protegido = central._token_trocar("token-simulado-so-para-capturas")  # noqa: SLF001
    central._gravar_meta({"token_protegido": "1" if protegido else "0"})  # noqa: SLF001
    banco = central._banco()  # noqa: SLF001
    uid = lambda n: f"{n:032x}"  # noqa: E731
    aparelhos = ((1, "Computador da portaria", "PORTARIA-01", agora - timedelta(seconds=10), 1, uid(11)),
                 (2, "Notebook do pátio", "PATIO-NB", agora - timedelta(hours=2), 0, None))
    for n, nome, computador, sinal, testando, sessao in aparelhos:
        banco.inserir("central_aparelhos", {"uid": uid(n), "empresa": escopo, "nome": nome, "computador": computador,
                                            "programa": "RotaGuard Script 0.5", "pareado_em": iso(agora - timedelta(days=1)),
                                            "ultimo_sinal": iso(sinal), "testando_agora": testando,
                                            "risco_atual": 2 if testando else None, "sessao_atual_uid": sessao})
    sessoes = ((11, 1, agora - timedelta(minutes=25), None, {"microssono": 1, "celular_na_mao": 1, "atencao": 1}),
               (12, 2, agora - timedelta(hours=3), agora - timedelta(hours=2, minutes=20), {"olhando_celular": 2}),
               (13, 2, agora - timedelta(days=1, hours=1), agora - timedelta(days=1), {"sono": 1}))
    for n, aparelho, inicio, fim, tipos in sessoes:
        duracao = ((fim or agora) - inicio).total_seconds()
        resumo = {"duracao_s": duracao, "eventos_por_tipo": tipos, "perclos_medio": 0.06, "piscadas_por_minuto": 16.1,
                  "trechos": 0, "fps_medio": 24.0}
        banco.inserir("central_sessoes", {"uid": uid(n), "empresa": escopo, "aparelho_uid": uid(aparelho),
                                          "iniciada_em": iso(inicio), "encerrada_em": iso(fim) if fim else None,
                                          "programa": "RotaGuard Script 0.5", "camera": "Câmera USB",
                                          "resumo": json.dumps(resumo)})
        passo = duracao / (sum(tipos.values()) + 1)
        momento = inicio
        for tipo, quantidade in tipos.items():
            for _ in range(quantidade):
                momento += timedelta(seconds=passo)
                risco = {"microssono": 3, "sono": 3, "celular_na_mao": 2, "olhando_celular": 2}.get(tipo, 1)
                banco.inserir("central_eventos", {"empresa": escopo, "aparelho_uid": uid(aparelho), "sessao_uid": uid(n),
                                                  "tipo": tipo, "nivel_risco": risco, "duracao_s": 2.4,
                                                  "ocorrido_em": iso(momento), "detalhes": "{}"})
    parar = threading.Event()

    def manter_sinal():  # o computador da portaria continua "testando agora" enquanto o servidor estiver de pé
        while not parar.wait(20):
            agora_ = datetime.now(timezone.utc)
            banco.executar("UPDATE central_aparelhos SET ultimo_sinal = ? WHERE uid = ?", (iso(agora_), uid(1)))
            central._gravar_meta({"ultima_busca": iso(agora_), "ultima_tentativa": iso(agora_)})  # noqa: SLF001

    threading.Thread(target=manter_sinal, name="central-simulada", daemon=True).start()
    return parar


def simular_script(pasta_script: Path):
    """RotaGuard Script "aberto": o anúncio do próprio script (caixa/vision/em_execucao.py, pid deste processo) e
    eventos de verdade na fila dele (caixa/vision/event_queue.py)."""
    anuncio_mod = carregar(RAIZ / "caixa" / "vision" / "em_execucao.py", "em_execucao_simulado")
    fila_mod = carregar(RAIZ / "caixa" / "vision" / "event_queue.py", "event_queue_simulado")
    anuncio = anuncio_mod.AnuncioExecucao(pasta_script, "RotaGuard Script", intervalo_s=3)
    anuncio.definir_camera("Câmera do computador")
    anuncio.iniciar()
    fila = fila_mod.EventStore(pasta_script / "eventos.db")
    for tipo, risco, duracao in (("atencao", 1, 0.0), ("olhando_celular", 2, 3.1), ("microssono", 3, 1.4)):
        fila.add(tipo, risco, duracao)
    return anuncio, fila


def criar_servidor(raiz: Path, ponte: Ponte, porta: int) -> ThreadingHTTPServer:
    raiz = raiz.resolve()
    rota_trechos = ponte._rota_trechos()  # noqa: SLF001

    class Manipulador(BaseHTTPRequestHandler):
        server_version = "RotaGuardCapturas"

        def _enviar(self, status: int, tipo: str, corpo: bytes, extras: dict | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.send_header("Cache-Control", "no-store")
            for chave, valor in (extras or {}).items():
                self.send_header(chave, valor)
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/__trechos/"):
                status, cabecalhos, corpo = servir_trecho(rota_trechos, self.path, self.headers.get("Range"))
                self._enviar(status, cabecalhos.pop("Content-Type", "application/octet-stream"), corpo, cabecalhos)
                return
            resposta = rp.resolver(raiz, self.path)
            if resposta.arquivo is None:
                self._enviar(404, "text/plain; charset=utf-8", "Não encontrado".encode("utf-8"))
                return
            corpo = resposta.arquivo.read_bytes()
            tipo = rp.tipo_mime(resposta.arquivo)
            if resposta.arquivo.suffix == ".html":
                corpo = corpo.replace(b"<head>", b"<head>" + PONTE_NO_NAVEGADOR.encode("utf-8"), 1)
            self._enviar(resposta.status, tipo, corpo)

        def do_POST(self) -> None:  # noqa: N802
            nome = self.path.removeprefix("/__ponte/")
            metodo = getattr(ponte, nome, None) if self.path.startswith("/__ponte/") and _NOME.match(nome) else None
            if not callable(metodo):
                self._enviar(404, "application/json", b'{"ok": false, "erro": "N\\u00e3o encontrado"}')
                return
            tamanho = int(self.headers.get("Content-Length") or 0)
            try:
                argumentos = json.loads(self.rfile.read(tamanho) or b"[]")
            except ValueError:
                argumentos = None
            if not isinstance(argumentos, list):
                self._enviar(400, "application/json", b'{"ok": false, "erro": "Pedido inv\\u00e1lido"}')
                return
            resposta = metodo(*argumentos)
            self._enviar(200, "application/json", json.dumps(resposta, ensure_ascii=False).encode("utf-8"))

        def log_message(self, format, *args) -> None:  # noqa: A002
            pass

    return ThreadingHTTPServer(("127.0.0.1", porta), Manipulador)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pasta", required=True, help="pasta de dados de teste (nunca a do painel instalado)")
    parser.add_argument("--porta", type=int, default=3107)
    parser.add_argument("--interface", default=str(RAIZ / "painel" / "app" / "out"))
    parser.add_argument("--simular", action="store_true", help="central conectada e RotaGuard Script aberto, simulados")
    parser.add_argument("--empresa", default="Transportes Lima", help="nome da empresa na central simulada")
    args = parser.parse_args(argv)
    pasta = conferir_pasta(Path(args.pasta))
    pasta.mkdir(parents=True, exist_ok=True)
    interface = Path(args.interface)
    if not (interface / "index.html").is_file():
        raise SystemExit(f"Interface não encontrada em {interface} (rode npm run build em painel/app).")
    script, extras = None, []
    if args.simular:
        extras.append(simular_central(pasta, args.empresa))
        pasta_script = pasta / "script-simulado"
        anuncio, fila = simular_script(pasta_script)
        extras += [anuncio, fila]
        script = ScriptLocal(pasta, [pasta_script])
    else:
        script = ScriptLocal(pasta, [pasta / "script-vazio"])
    ponte = Ponte(pasta, custo_scrypt=CUSTO_BARATO, script_local=script, escolher_destino=lambda nome: pasta / nome,
                  abrir_arquivo=lambda caminho: None)
    ponte._iniciar_script()  # noqa: SLF001 - captura os eventos do script, como a janela do app
    servidor = criar_servidor(interface, ponte, args.porta)
    print(f"Painel com a Ponte de verdade em http://127.0.0.1:{servidor.server_address[1]}/ (dados em {pasta})", flush=True)
    try:
        servidor.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        ponte._parar_script()  # noqa: SLF001
        for item in extras:
            if isinstance(item, threading.Event):
                item.set()
            elif hasattr(item, "parar"):
                item.parar()
            elif hasattr(item, "close"):
                item.close()
        time.sleep(0.1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
