"""Spec 013: app do painel no computador (janela nativa com pywebview + WebView2 e servidor local).

Nenhuma janela abre: nos testes da janela, o pywebview é trocado por um falso. Só usa a biblioteca padrão (o PyInstaller,
se estiver instalado, confere o formato das propriedades do .exe):
    python tests/test_painel_desktop.py
"""
import http.client
import importlib.util
import json
import os
import platform
import socket
import sys
import tempfile
import urllib.error
import urllib.request
from importlib import metadata
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[1]
# A ponte do js_api e o script local ligado a ela usam a pasta de dados do painel: nos testes, pasta temporária.
PASTA_DADOS_TESTE = tempfile.TemporaryDirectory(prefix="rotaguard-painel-teste-", ignore_cleanup_errors=True)
os.environ["ROTAGUARD_PAINEL_DADOS"] = PASTA_DADOS_TESTE.name
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import rotaguard_painel as rp  # noqa: E402

checks = 0
# Sem proxy do sistema: 127.0.0.1 precisa ir direto para o servidor do app.
abrir = urllib.request.build_opener(urllib.request.ProxyHandler({})).open


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def carregar(caminho, nome):
    especificacao = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def escrever(caminho, texto):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")
    return caminho


def interface_de_teste(base):
    """Exportação mínima com a forma de painel/app/out: trailingSlash, RSC em .txt, _next/static e 404.html."""
    raiz = base / "out"
    escrever(raiz / "index.html", '<!DOCTYPE html><html lang="pt-BR"><body>Chegadas · dados fictícios</body></html>')
    escrever(raiz / "index.txt", "0:rsc-da-home")
    escrever(raiz / "404.html", '<html lang="pt-BR"><body>Página não encontrada</body></html>')
    escrever(raiz / "veiculos" / "index.html", "<html><body>Veículos</body></html>")
    escrever(raiz / "viagens" / "v-2240" / "index.html", "<html><body>Viagem v-2240</body></html>")
    escrever(raiz / "viagens" / "v-2240" / "__next.viagens" / "$d$id" / "__PAGE__.txt", "0:rsc-da-viagem")
    escrever(raiz / "_next" / "static" / "chunks" / "app.js", "console.log('ok')")
    escrever(raiz / "_next" / "static" / "chunks" / "estilo.css", "body{}")
    escrever(raiz / "_next" / "static" / "media" / "fonte.woff2", "woff2")
    escrever(raiz / "sobre.html", "<html><body>Sobre</body></html>")
    escrever(raiz / "pasta com espaço" / "dados.json", "{}")
    escrever(base / "segredo.txt", "fora da interface")
    return raiz


# PAC-01 · URL → arquivo da exportação estática
with tempfile.TemporaryDirectory() as tmp:
    raiz = interface_de_teste(Path(tmp))
    real = raiz.resolve()

    def arquivo(alvo):
        resposta = rp.resolver(raiz, alvo)
        assert resposta.status == 200 and resposta.arquivo is not None, (alvo, resposta)
        return resposta.arquivo.relative_to(real).as_posix()

    assert arquivo("/") == "index.html"
    assert arquivo("/veiculos/") == "veiculos/index.html"
    assert arquivo("/veiculos") == "veiculos/index.html"
    assert arquivo("/viagens/v-2240/") == "viagens/v-2240/index.html"
    assert arquivo("/_next/static/chunks/app.js") == "_next/static/chunks/app.js"
    assert arquivo("/viagens/v-2240/__next.viagens/%24d%24id/__PAGE__.txt") == \
        "viagens/v-2240/__next.viagens/$d$id/__PAGE__.txt"
    assert arquivo("/?_rsc=abc") == "index.html"
    assert arquivo("/veiculos/?aba=pendentes#topo") == "veiculos/index.html"
    assert arquivo("/index.txt?_rsc=1x2y") == "index.txt"
    assert arquivo("/pasta%20com%20espa%C3%A7o/dados.json") == "pasta com espaço/dados.json"
    assert arquivo("/sobre") == "sobre.html"
ok("PAC-01 URL de pasta vira index.html, ?consulta ignorada, %20 decodificado e <caminho>.html como alternativa")

# PAC-02 · travessia bloqueada e arquivo faltando → 404 com a página 404
with tempfile.TemporaryDirectory() as tmp:
    raiz = interface_de_teste(Path(tmp))
    real = raiz.resolve()
    for ataque in ("/../segredo.txt", "/%2e%2e/segredo.txt", "/%2E%2E/segredo.txt", "/veiculos/..%2f..%2fsegredo.txt",
                   "/..%5csegredo.txt", "/veiculos/%5c..%5c..%5csegredo.txt", "/C:/Windows/win.ini",
                   "/index.html%00.png", "/./index.html", "/nao-existe/", "/nao-existe.js", "/viagens/v-9999/"):
        resposta = rp.resolver(raiz, ataque)
        assert resposta.status == 404 and resposta.arquivo == real / "404.html", (ataque, resposta)
    (raiz / "404.html").unlink()
    sem_pagina = rp.resolver(raiz, "/nao-existe/")
    assert sem_pagina.status == 404 and sem_pagina.arquivo is None, sem_pagina
ok("PAC-02 travessia (.., %2e%2e, ..%2f, %5c, C:, byte nulo) e arquivo faltando respondem 404 com a 404.html")

# PAC-03 · tipos MIME explícitos
for nome, tipo in {"a.html": "text/html", "A.HTML": "text/html", "a.js": "text/javascript", "a.css": "text/css",
                   "a.json": "application/json", "__PAGE__.txt": "text/plain", "a.woff2": "font/woff2",
                   "a.svg": "image/svg+xml", "a.png": "image/png", "favicon.ico": "image/x-icon",
                   "a.xyz": "application/octet-stream", "sem-extensao": "application/octet-stream"}.items():
    assert rp.tipo_mime(Path(nome)).split(";")[0] == tipo, (nome, rp.tipo_mime(Path(nome)))
assert "charset=utf-8" in rp.tipo_mime(Path("a.html")) and "charset=utf-8" in rp.tipo_mime(Path("a.txt"))
ok("PAC-03 tipos MIME: html, js, css, json, txt (RSC como text/plain), woff2, svg, png, ico e octet-stream")

# PAC-04 · servidor real na porta 0, só em 127.0.0.1, parado de forma limpa
with tempfile.TemporaryDirectory() as tmp:
    raiz = interface_de_teste(Path(tmp))
    servidor = rp.iniciar_servidor(raiz, porta=0)
    host, porta = servidor.server_address[:2]
    try:
        assert host == "127.0.0.1" and porta > 0, servidor.server_address
        url = rp.url_da_janela(porta)
        with abrir(url, timeout=5) as resposta:
            corpo = resposta.read().decode("utf-8")
            assert resposta.status == 200 and resposta.headers["Content-Type"].startswith("text/html")
            assert "dados fictícios" in corpo
            politica = resposta.headers["Content-Security-Policy"]
            assert "default-src 'self'" in politica and "connect-src 'self'" in politica, politica
            assert "http" not in politica, "a política não pode liberar origem externa"
            assert resposta.headers["X-Content-Type-Options"] == "nosniff"
        with abrir(urllib.request.Request(url + "index.txt?_rsc=1", headers={"RSC": "1"}), timeout=5) as resposta:
            assert resposta.headers["Content-Type"].startswith("text/plain") and resposta.read() == b"0:rsc-da-home"
        try:
            abrir(url + "nao-existe/", timeout=5)
        except urllib.error.HTTPError as erro:
            assert erro.code == 404 and "Página não encontrada" in erro.read().decode("utf-8")
            erro.close()
        else:
            raise AssertionError("caminho faltando deveria responder 404")
        conexao = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
        conexao.request("HEAD", "/veiculos/")
        cabeca = conexao.getresponse()
        assert cabeca.status == 200 and int(cabeca.getheader("Content-Length")) > 0 and cabeca.read() == b""
        conexao.close()
    finally:
        rp.parar_servidor(servidor)
    assert not servidor.linha.is_alive(), "a thread do servidor continuou rodando"
    try:
        socket.create_connection(("127.0.0.1", porta), timeout=1).close()
    except OSError:
        pass
    else:
        raise AssertionError("a porta continuou aberta depois de parar o servidor")
ok("PAC-04 servidor em 127.0.0.1:0 responde 200 text/html, RSC text/plain, 404 e HEAD; para e libera a porta")

# PAC-05 · pasta da interface e ícone, fora do pacote e no pacote
assert rp.pasta_interface() == RAIZ / "painel" / "app" / "out"
assert rp.pasta_interface(congelado=False) == RAIZ / "painel" / "app" / "out"
assert rp.pasta_interface(congelado=True, meipass=r"C:\Programas\RotaGuard Painel\_internal") == \
    Path(r"C:\Programas\RotaGuard Painel\_internal") / "interface"
ICONE = RAIZ / "implantacao" / "app-teste" / "rotaguard.ico"
assert rp.caminho_icone(congelado=False) == ICONE and ICONE.is_file()
assert rp.caminho_icone(congelado=True, meipass="/pacote/_internal") == Path("/pacote/_internal") / "rotaguard.ico"
ok("PAC-05 pasta_interface: painel/app/out fora do pacote e _MEIPASS/interface no pacote; ícone idem")

# PAC-06 · a janela só aponta para o servidor local
for porta in (1, 8080, 54321, 65535):
    url = rp.url_da_janela(porta)
    assert url.startswith("http://127.0.0.1:") and url == f"http://127.0.0.1:{porta}/", url
assert rp.opcoes_da_janela("http://127.0.0.1:9/", oculta=False)["url"] == "http://127.0.0.1:9/"
ok("PAC-06 URL da janela sempre http://127.0.0.1:<porta>/")


# Falsos do pywebview: registram o que o app pede e nunca abrem janela.
class EventoFalso:
    def __init__(self, disparado=True):
        self.disparado, self.funcoes = disparado, []

    def __iadd__(self, funcao):
        self.funcoes.append(funcao)
        return self

    def set(self, *args):
        """Igual ao pywebview: devolve True (abortar) se alguma função devolver False."""
        return any([funcao(*args) is False for funcao in self.funcoes])

    def wait(self, timeout=None):
        return self.disparado


class JanelaFalsa:
    def __init__(self, respostas, carrega):
        self.events = SimpleNamespace(initialized=EventoFalso(), loaded=EventoFalso(carrega))
        self.respostas, self.scripts, self.destruida = respostas, [], False

    def evaluate_js(self, script):
        self.scripts.append(script)
        return self.respostas.get(script)

    def destroy(self):
        self.destruida = True


class WebviewFalso:
    def __init__(self, respostas=None, carrega=True, motor="edgechromium"):
        self.janela = JanelaFalsa(respostas or {}, carrega)
        self.motor, self.criacoes, self.inicios, self.status_durante = motor, [], [], None

    def create_window(self, title, url=None, **opcoes):
        self.criacoes.append(dict(title=title, url=url, **opcoes))
        return self.janela

    def start(self, func=None, args=None, **opcoes):
        self.inicios.append(opcoes)
        with abrir(self.criacoes[-1]["url"], timeout=5) as resposta:  # com a janela aberta, o servidor responde
            self.status_durante = resposta.status
        if self.janela.events.initialized.set(self.motor):
            return
        if func:
            func(*(args or ()))


RESPOSTAS_OK = {rp.SCRIPT_IDIOMA: "pt-BR", rp.SCRIPT_TEXTO: "Chegadas\nDADOS FICTÍCIOS · não é diagnóstico",
                rp.SCRIPT_SCRIPTS: True}

with tempfile.TemporaryDirectory() as tmp:
    raiz = interface_de_teste(Path(tmp))

    # PAC-07 · janela: título, tamanhos, oculta só na verificação, sem devtools no pacote, servidor ligado à janela
    linhas, avisos = [], []
    pacote = WebviewFalso()
    assert rp.main(["--depurar"], webview_mod=pacote, raiz=raiz, congelado=True, imprimir=linhas.append,
                   avisar=avisos.append) == 0
    janela = pacote.criacoes[0]
    assert janela["title"] == "RotaGuard" and janela["width"] == 1440 and janela["height"] == 900, janela
    assert tuple(janela["min_size"]) == (1200, 760) and janela["hidden"] is False, janela
    assert janela["url"].startswith("http://127.0.0.1:"), janela
    assert pacote.inicios[0]["debug"] is False, "o pacote nunca liga as ferramentas de desenvolvedor"
    assert pacote.status_durante == 200 and linhas == [] and avisos == []
    try:
        abrir(janela["url"], timeout=1)
    except OSError:
        pass
    else:
        raise AssertionError("o servidor continuou respondendo depois de a janela fechar")
    dev = WebviewFalso()
    assert rp.main(["--depurar"], webview_mod=dev, raiz=raiz, congelado=False, imprimir=linhas.append,
                   avisar=avisos.append) == 0
    assert dev.inicios[0]["debug"] is True and Path(dev.inicios[0]["icon"]) == ICONE
    sem_depurar = WebviewFalso()
    rp.main([], webview_mod=sem_depurar, raiz=raiz, congelado=False, imprimir=linhas.append, avisar=avisos.append)
    assert sem_depurar.inicios[0]["debug"] is False
    assert rp.opcoes_de_inicio(congelado=True, depurar=True, icone=ICONE) == \
        {"debug": False, "private_mode": True, "icon": str(ICONE)}
    assert "icon" not in rp.opcoes_de_inicio(congelado=False, depurar=False, icone=Path(tmp) / "nao-existe.ico")
    ok("PAC-07 janela RotaGuard 1440x900 (mínimo 1200x760), sem devtools no pacote e servidor só com a janela aberta")

    # PAC-08 · --verificar: uma linha JSON, código 0 só com pt-BR e "dados fictícios"
    def verificar(falso, raiz_usada=raiz):
        saidas, alertas = [], []
        codigo = rp.main(["--verificar"], webview_mod=falso, raiz=raiz_usada, congelado=True, imprimir=saidas.append,
                         avisar=alertas.append)
        assert len(saidas) == 1 and "\n" not in saidas[0] and alertas == [], (saidas, alertas)
        return codigo, json.loads(saidas[0])

    certo = WebviewFalso(RESPOSTAS_OK)
    codigo, resultado = verificar(certo)
    assert codigo == 0 and resultado["ok"] is True, resultado
    assert resultado["lang"] == "pt-BR" and resultado["aviso_dados_ficticios"] is True and resultado["scripts"] is True
    assert resultado["url"].startswith("http://127.0.0.1:") and resultado["motor"] == "edgechromium", resultado
    assert certo.criacoes[0]["hidden"] is True and certo.inicios[0]["debug"] is False and certo.janela.destruida
    for respostas, motivo in (({**RESPOSTAS_OK, rp.SCRIPT_IDIOMA: "en"}, "lang"),
                              ({**RESPOSTAS_OK, rp.SCRIPT_TEXTO: "Chegadas sem o aviso"}, "dados fictícios"),
                              ({}, "lang")):
        falso = WebviewFalso(respostas)
        codigo, resultado = verificar(falso)
        assert codigo == 1 and resultado["ok"] is False and motivo in resultado["erro"], resultado
        assert falso.janela.destruida
    parada = WebviewFalso(RESPOSTAS_OK, carrega=False)
    codigo, resultado = verificar(parada)
    assert codigo == 1 and resultado["ok"] is False and "carreg" in resultado["erro"], resultado
    assert parada.janela.scripts == [] and parada.janela.destruida
    vazia = Path(tmp) / "vazia"
    vazia.mkdir()
    sem_interface = WebviewFalso(RESPOSTAS_OK)
    codigo, resultado = verificar(sem_interface, vazia)
    assert codigo == 1 and "interface" in resultado["erro"] and sem_interface.criacoes == [], resultado
    assert rp.resultado_verificacao("pt-BR", "Painel · Dados fictícios")["ok"] is True
    assert rp.resultado_verificacao("pt-BR", None)["ok"] is False and rp.resultado_verificacao(None, None)["ok"] is False
    ok("PAC-08 --verificar: uma linha JSON, código 0 só com lang pt-BR e 'dados fictícios'; falhas saem com 1")

    # PAC-09 · sem WebView2 o pywebview cairia no MSHTML: o app recusa
    sem_webview2 = WebviewFalso(RESPOSTAS_OK, motor="mshtml")
    codigo, resultado = verificar(sem_webview2)
    assert codigo == 1 and "WebView2" in resultado["erro"] and resultado["motor"] == "mshtml", resultado
    assert sem_webview2.janela.scripts == []
    avisos = []
    assert rp.main([], webview_mod=WebviewFalso(motor="mshtml"), raiz=raiz, congelado=True, imprimir=linhas.append,
                   avisar=avisos.append) == 1
    assert len(avisos) == 1 and "WebView2" in avisos[0], avisos
    assert rp.aceitar_motor("edgechromium") is True
    assert rp.aceitar_motor("mshtml") is False and rp.aceitar_motor("cef") is False
    ok("PAC-09 motor diferente de edgechromium (sem WebView2) é recusado com aviso e código 1")

# PAC-10 · vigia de 60 s: estoura uma vez só e encerra com 1; cancelado não faz nada
assert rp.TEMPO_LIMITE_VERIFICACAO_S == 60
linhas, codigos = [], []
saida = rp.SaidaUnica(linhas.append)
vigia = rp.iniciar_vigia(0.05, saida, encerrar=codigos.append)
vigia.join(5)
assert codigos == [1] and len(linhas) == 1, (codigos, linhas)
resultado = json.loads(linhas[0])
assert resultado["ok"] is False and "tempo" in resultado["erro"], resultado
assert saida.enviar({"ok": True}) is False and len(linhas) == 1
linhas_cancelado, codigos_cancelado = [], []
cancelado = rp.iniciar_vigia(0.2, rp.SaidaUnica(linhas_cancelado.append), encerrar=codigos_cancelado.append)
cancelado.cancel()
cancelado.join(5)
assert linhas_cancelado == [] and codigos_cancelado == []
ok("PAC-10 vigia de 60 s imprime o erro uma vez e encerra com 1; cancelado não faz nada")

# PAC-11 · propriedades do .exe: RotaGuard Painel, sem o nome do computador; o RotaGuard Teste continua igual
build_painel = carregar(RAIZ / "implantacao" / "painel" / "build.py", "build_painel")
propriedades = build_painel.propriedades_windows("0.1.0")
for esperado in ("StringStruct('CompanyName', 'RotaGuard')", "StringStruct('ProductName', 'RotaGuard Painel')",
                 "StringStruct('FileDescription', 'RotaGuard Painel')", "StringStruct('InternalName', 'RotaGuardPainel')",
                 "StringStruct('OriginalFilename', 'RotaGuardPainel.exe')", "filevers=(0, 1, 0, 0)"):
    assert esperado in propriedades, esperado
assert socket.gethostname() not in propriedades
teste = carregar(RAIZ / "implantacao" / "app-teste" / "build.py", "build_app_teste_013").texto_versao_windows("0.3.0")
assert "StringStruct('ProductName', 'RotaGuard Teste')" in teste
assert "StringStruct('OriginalFilename', 'RotaGuardTeste.exe')" in teste
try:
    from PyInstaller.utils.win32 import versioninfo
except ImportError:
    print("-- PyInstaller ausente: formato das propriedades não conferido")
else:
    with tempfile.TemporaryDirectory() as tmp:
        arquivo_propriedades = Path(tmp) / "propriedades.txt"
        arquivo_propriedades.write_text(propriedades, encoding="utf-8")
        assert "RotaGuard Painel" in str(versioninfo.load_version_info_from_text_file(str(arquivo_propriedades)))
ok("PAC-11 propriedades do .exe com RotaGuard Painel no formato do PyInstaller; RotaGuard Teste inalterado")

# PAC-12 · build.py, .spec e .iss
escuta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
escuta.bind(("127.0.0.1", 0))
escuta.listen(1)
porta_escuta = escuta.getsockname()[1]
try:
    assert build_painel.porta_ocupada(porta_escuta) is True
finally:
    escuta.close()
assert build_painel.porta_ocupada(porta_escuta) is False
assert build_painel.PORTA_DEV == 3001
versao_antes = os.environ.pop("ROTAGUARD_VERSAO", None)
try:
    pacote_json = json.loads((RAIZ / "painel" / "app" / "package.json").read_text(encoding="utf-8"))
    assert build_painel.versao() == pacote_json["version"]
    os.environ["ROTAGUARD_VERSAO"] = "painel-v0.2.0"
    assert build_painel.versao() == "0.2.0"
finally:
    os.environ.pop("ROTAGUARD_VERSAO", None)
    if versao_antes is not None:
        os.environ["ROTAGUARD_VERSAO"] = versao_antes
if sys.platform.startswith("win") and platform.machine().lower() in ("amd64", "x86_64"):
    assert build_painel.nome_zip() == "RotaGuard-Painel-windows-x64.zip", build_painel.nome_zip()
especificacao = (RAIZ / "implantacao" / "painel" / "rotaguard-painel.spec").read_text(encoding="utf-8")
for esperado in ('"interface"', 'name="RotaGuardPainel"', "console=False", "rotaguard_painel.py", "rotaguard.ico",
                 "copy_metadata", "ROTAGUARD_VERSAO_WINDOWS"):
    assert esperado in especificacao, esperado
assert "debug=True" not in especificacao
instalador = (RAIZ / "implantacao" / "painel" / "rotaguard-painel.iss").read_text(encoding="utf-8")
for esperado in ("PrivilegesRequired=lowest", f"OutputBaseFilename={build_painel.NOME}-windows-x64-setup",
                 "{autoprograms}\\RotaGuard Painel", 'Name: "desktopicon"', "Tasks: desktopicon",
                 "RotaGuardPainel.exe", "{localappdata}\\Programs\\RotaGuard Painel"):
    assert esperado in instalador, esperado
assert "4F0C8B7E-9A61-4D3B-8E57-2C1B6A9D0F31" not in instalador, "o painel precisa de AppId próprio"
ok("PAC-12 build.py confere a porta 3001 e a versão; .spec com interface e sem console; .iss por usuário")

# PAC-13 · versões travadas e iguais às do .venv
travadas = {}
for linha in (RAIZ / "painel" / "desktop" / "requirements.txt").read_text(encoding="utf-8").splitlines():
    linha = linha.split("#", 1)[0].strip()
    if not linha:
        continue
    requisito, _, marcador = linha.partition(";")
    nome, separador, versao = requisito.strip().partition("==")
    assert separador == "==" and versao.strip(), f"versão não travada: {linha}"
    travadas[nome.strip().lower().replace("_", "-")] = (versao.strip(), marcador.strip())
for nome in ("pywebview", "pythonnet", "clr-loader", "cffi", "proxy-tools", "bottle", "pyinstaller",
             "pyinstaller-hooks-contrib"):
    assert nome in travadas, nome
for nome, (versao, marcador) in travadas.items():
    if "win32" in marcador and sys.platform != "win32":
        continue
    try:
        instalada = metadata.version(nome)
    except metadata.PackageNotFoundError:
        print(f"-- {nome} não instalado: versão não conferida")
        continue
    assert instalada == versao, (nome, instalada, versao)
ok("PAC-13 requirements.txt com versões travadas (==) e iguais às instaladas")

print(f"\n{checks} verificações OK")
