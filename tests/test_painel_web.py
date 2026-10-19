"""Spec 024: painel da empresa no navegador (servidor HTTP da ponte, `painel/web/servidor_web.py`).

Sem rede de verdade: o TestClient do Starlette chama o app ASGI direto. Relógio falso, scrypt barato, pastas temporárias.
Senhas e código de ativação são descartáveis, só deste teste. Precisa de starlette e httpx2 (painel/web/requirements*.txt):
    python tests/test_painel_web.py
O WEB-14 roda de novo os testes antigos do painel (tests/test_painel_*.py) em processos separados.
"""
import base64
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
sys.path.insert(0, str(RAIZ / "painel" / "web"))
import copia  # noqa: E402
from ponte import Ponte  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

import servidor_web  # noqa: E402

import demonstracao_antiga  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
T0 = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc).timestamp()
ORIGEM = "https://painel.teste"
BASE = "/painel"
# Descartáveis, só deste teste.
CODIGO = "codigo-de-ativacao-de-teste-7Kq2"
SENHA_ADM = "frase comprida de teste um"
SENHA_SUP = "frase comprida de teste dois"
SENHA_COPIA = "frase da copia de teste web"
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}
EMPRESA = "Transportes Lima"  # spec 030: ativar sem arquivo cria a empresa com o nome digitado
SEGREDOS = (CODIGO, SENHA_ADM, SENHA_SUP, SENHA_COPIA)
PDF = b"%PDF-1.4\n% termo-web-de-teste\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + bytes(17) + b"png-web-de-teste"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(20) + b"\xff\xd9"
CABECALHOS = {"X-RotaGuard": "1", "Origin": ORIGEM}


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


class Registros(logging.Handler):
    """Guarda tudo o que o servidor registrar, para conferir que nenhum segredo vai para o log."""

    def __init__(self):
        super().__init__(logging.DEBUG)
        self.linhas = []

    def emit(self, record):
        self.linhas.append(record.getMessage())


REGISTROS = Registros()
logging.getLogger().addHandler(REGISTROS)
logging.getLogger().setLevel(logging.DEBUG)


class Ambiente:
    """Um servidor de teste: pasta de dados, interface mínima, pasta temporária e relógio falso."""

    def __init__(self, nome, **opcoes):
        self.tmp = Path(tempfile.mkdtemp(prefix=f"rg-web-{nome}-"))
        self.dados = self.tmp / "dados"
        self.temp = self.tmp / "temp"
        self.estatico = self.tmp / "out-web"
        for caminho, texto in {"index.html": "<!DOCTYPE html><html lang=\"pt-BR\"><body>Painel web</body></html>",
                               "404.html": "<html><body>Não encontrada</body></html>",
                               "motoristas/index.html": "<html><body>Motoristas</body></html>",
                               "_next/static/chunks/app.js": "console.log(1)"}.items():
            destino = self.estatico / caminho
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto, encoding="utf-8")
        self.relogio = [T0]
        parametros = {"pasta": self.dados, "estatico": self.estatico, "base": BASE, "codigo_ativacao": CODIGO,
                      "origem": ORIGEM, "cookie_seguro": True, "custo_scrypt": CUSTO_TESTE,
                      "relogio": lambda: self.relogio[0], "pasta_temp": self.temp}
        parametros.update(opcoes)
        self.app = servidor_web.criar_app(**parametros)
        self.servidor = self.app.state.painel

    def cliente(self):
        return TestClient(self.app, base_url=ORIGEM)

    def avancar(self, segundos):
        self.relogio[0] += segundos


def chamar(cliente, metodo, *args, cabecalhos=CABECALHOS, ativacao=None):
    corpo = {"args": list(args)}
    if ativacao is not None:
        corpo["ativacao"] = ativacao
    return cliente.post(f"{BASE}/api/ponte/{metodo}", json=corpo, headers=cabecalhos)


def dados(resposta, contexto=""):
    assert resposta.status_code == 200, f"{contexto}: HTTP {resposta.status_code} {resposta.text[:300]}"
    corpo = resposta.json()
    assert corpo.get("ok") is True, f"{contexto}: {corpo}"
    return corpo["dados"]


def erro(resposta, codigo, contexto=""):
    corpo = resposta.json()
    assert corpo.get("ok") is False and corpo.get("codigo") == codigo, f"{contexto}: esperava {codigo}, veio {corpo}"
    return corpo


def set_cookie(resposta):
    return [valor for chave, valor in resposta.headers.multi_items() if chave.lower() == "set-cookie"]


def sobras(ambiente):
    """O que ficou na pasta temporária do servidor (só a subpasta própria dele pode existir, vazia)."""
    return [p.relative_to(ambiente.temp).as_posix() for p in ambiente.temp.rglob("*")
            if p != ambiente.temp / servidor_web.PASTA_SAIDAS]


def ativar(ambiente):
    cliente = ambiente.cliente()
    resposta = chamar(cliente, "ativar_local", EMPRESA, ADMIN, ativacao=CODIGO)
    assert "codigo_recuperacao" in dados(resposta, "ativar")
    # Spec 030: ativar não traz cadastro nenhum; os fictícios do fixture entram só aqui, para os testes de listas.
    demonstracao_antiga.carregar(ambiente.servidor._anonima._n().banco)  # noqa: SLF001
    return cliente, resposta


# NOMES -----------------------------------------------------------------------------------------------------------------
texto_bridge = (RAIZ / "painel" / "app" / "src" / "lib" / "bridge.ts").read_text(encoding="utf-8")
bloco = texto_bridge[texto_bridge.index("const NOMES = ["):texto_bridge.index("] as const satisfies")]
nomes_ts = tuple(nome for nome in re.findall(r'"(\w+)"', bloco) if nome not in servidor_web.NOMES_SO_NO_APP)
assert nomes_ts == tuple(servidor_web.NOMES), f"lista de métodos diferente: {set(nomes_ts) ^ set(servidor_web.NOMES)}"
assert not set(servidor_web.NOMES) & set(servidor_web.NOMES_SO_NO_APP), "central só no app instalado (spec 026)"
assert all(not nome.startswith("_") and callable(getattr(Ponte, nome, None)) for nome in servidor_web.NOMES)
ok(f"NOMES do servidor iguais aos {len(nomes_ts)} de bridge.ts, todos métodos públicos da Ponte")

# WEB-01 ------------------------------------------------------------------------------------------------------------------
web = Ambiente("01")
cliente = web.cliente()
resposta = chamar(cliente, "estado")
estado_web = dados(resposta, "WEB-01")
direta = Ponte(web.tmp / "outra", relogio=lambda: T0, custo_scrypt=CUSTO_TESTE, script_local=None).estado()
assert direta["ok"] and set(estado_web) == set(direta["dados"]), f"WEB-01 chaves: {set(estado_web) ^ set(direta['dados'])}"
assert estado_web["ativado"] is False and estado_web["sessao"] is None
assert resposta.headers["cache-control"] == "no-store" and resposta.headers["x-content-type-options"] == "nosniff"
assert not set_cookie(resposta), "WEB-01 sem sessão não nasce cookie"
assert web.servidor.total_sessoes() == 0
ok("WEB-01 estado pelo HTTP no mesmo formato da ponte local, com no-store e nosniff, sem criar sessão")

saude = cliente.get(f"{BASE}/api/saude")
assert saude.status_code == 200 and saude.json() == {"ok": True}
pagina = cliente.get(f"{BASE}/")
assert pagina.status_code == 200 and "Painel web" in pagina.text
assert pagina.headers["x-content-type-options"] == "nosniff" and "frame-ancestors 'none'" in pagina.headers[
    "content-security-policy"]
assert cliente.get(f"{BASE}/motoristas/").text.count("Motoristas") == 1
assert cliente.get(f"{BASE}/_next/static/chunks/app.js").headers["cache-control"].endswith("immutable")
assert cliente.get(f"{BASE}/nao-existe/").status_code == 404
sem_barra = cliente.get(BASE, follow_redirects=False)
assert sem_barra.status_code in (307, 308) and sem_barra.headers["location"] == f"{BASE}/"
assert cliente.get(f"{BASE}/api/nada").status_code == 404
ok("saúde em /painel/api/saude; interface estática em /painel/ com CSP, nosniff, 404.html e cache longo só em _next/static")

# WEB-02 ------------------------------------------------------------------------------------------------------------------
for nome in ("_trava", "_n", "__init__", "_exigir", "nao_existe", "script_local", "Estado"):
    resposta = chamar(cliente, nome)
    assert resposta.status_code == 404 and resposta.json()["ok"] is False, f"WEB-02 {nome}: {resposta.status_code}"
assert cliente.get(f"{BASE}/api/ponte/estado", headers=CABECALHOS).status_code == 405
ok("WEB-02 método fora da lista, nome com _ e GET na ponte não passam (404/405)")

# WEB-03 ------------------------------------------------------------------------------------------------------------------
for contexto, cabecalhos in (("sem X-RotaGuard", {"Origin": ORIGEM}),
                             ("X-RotaGuard 0", {"X-RotaGuard": "0", "Origin": ORIGEM}),
                             ("sem Origin", {"X-RotaGuard": "1"}),
                             ("Origin de outro site", {"X-RotaGuard": "1", "Origin": "https://outro.site"}),
                             ("Origin com outra porta", {"X-RotaGuard": "1", "Origin": ORIGEM + ":8443"}),
                             ("Origin null", {"X-RotaGuard": "1", "Origin": "null"})):
    resposta = chamar(cliente, "estado", cabecalhos=cabecalhos)
    assert resposta.status_code == 403 and resposta.json()["ok"] is False, f"WEB-03 {contexto}: {resposta.status_code}"
ok("WEB-03 POST sem X-RotaGuard: 1 ou com Origin de outro endereço responde 403")

# WEB-06 ------------------------------------------------------------------------------------------------------------------
sem_codigo = erro(chamar(cliente, "ativar_local", EMPRESA, ADMIN), "sem_permissao", "WEB-06 sem código")
assert sem_codigo.get("campo") == "codigo_ativacao"
erro(chamar(cliente, "ativar_local", EMPRESA, ADMIN, ativacao="codigo-errado"), "sem_permissao", "WEB-06 errado")
erro(chamar(cliente, "ativar_com_arquivo", "{}", ADMIN, ativacao=CODIGO[:-1]), "sem_permissao", "WEB-06 arquivo errado")
assert dados(chamar(cliente, "estado"))["ativado"] is False, "WEB-06 código errado não ativa"
assert web.servidor.total_sessoes() == 0
admin, ativacao = ativar(web)
estado_admin = dados(chamar(admin, "estado"))
assert estado_admin["ativado"] and estado_admin["sessao"]["usuario"] == "marina.lopes"
segundo = web.cliente()
de_novo = erro(chamar(segundo, "ativar_local", EMPRESA, {**ADMIN, "usuario": "outro.adm"}, ativacao=CODIGO), "conflito")
assert "computador" not in de_novo["erro"], de_novo
assert [u["usuario"] for u in dados(chamar(admin, "equipe_listar"))] == ["marina.lopes"]
desligado = Ambiente("06b", codigo_ativacao=None)
recusa = erro(chamar(desligado.cliente(), "ativar_local", EMPRESA, ADMIN, ativacao=CODIGO), "sem_permissao", "sem env")
assert recusa.get("campo") == "codigo_ativacao" and not dados(chamar(desligado.cliente(), "estado"))["ativado"]
ok("WEB-06 ativar sem código ou com código errado: sem_permissao; com o certo ativa uma vez só; sem PAINEL_CODIGO_ATIVACAO nunca ativa")

# WEB-07 ------------------------------------------------------------------------------------------------------------------
cookies = set_cookie(ativacao)
assert len(cookies) == 1, cookies
partes = [parte.strip() for parte in cookies[0].split(";")]
nome_valor = partes[0].split("=", 1)
assert nome_valor[0] == "rg_painel" and len(nome_valor[1]) >= 40, "WEB-07 cookie aleatório e longo"
assert {"HttpOnly", "Secure", "SameSite=Strict", "Path=/painel"} <= set(partes), f"WEB-07 {partes}"
assert not any(parte.lower().startswith(("expires", "max-age")) for parte in partes), "cookie de sessão do navegador"
inseguro = Ambiente("07b", cookie_seguro=False)
cookies_http = set_cookie(chamar(inseguro.cliente(), "ativar_local", EMPRESA, ADMIN, ativacao=CODIGO))
assert cookies_http and "Secure" not in [p.strip() for p in cookies_http[0].split(";")]
ok("WEB-07 cookie rg_painel com HttpOnly, Secure, SameSite=Strict e Path=/painel (Secure só some com PAINEL_COOKIE_SEGURO=0)")

# WEB-04 ------------------------------------------------------------------------------------------------------------------
adicionado = dados(chamar(admin, "equipe_adicionar", {"nome": "Paulo Souza", "usuario": "paulo.souza",
                                                        "funcao": "supervisor"}))
temporaria = adicionado["senha_temporaria"]
supervisor = web.cliente()
entrou = chamar(supervisor, "entrar", "paulo.souza", temporaria)
assert dados(entrou)["funcao"] == "supervisor" and set_cookie(entrou)
dados(chamar(supervisor, "trocar_senha", temporaria, SENHA_SUP))
web.avancar(61)
assert dados(chamar(supervisor, "estado"))["sessao"]["usuario"] == "paulo.souza"
assert dados(chamar(admin, "estado"))["sessao"]["usuario"] == "marina.lopes"
erro(chamar(supervisor, "equipe_listar"), "sem_permissao", "WEB-04 supervisor não vê a equipe")
assert dados(chamar(admin, "equipe_listar")), "WEB-04 a recusa do supervisor não mexe no administrador"
assert web.servidor.total_sessoes() == 2
ok("WEB-04 duas sessões (dois cookies) com pessoas diferentes; cada uma vê só o próprio estado.usuario e as próprias permissões")

# Várias Pontes sobre a mesma pasta (o servidor abre uma por sessão): escritas ao mesmo tempo, sem "database is locked"
# e com a cadeia do registro de atividades íntegra no fim.
falhas = []


def trabalho(cliente_http, indice):
    for volta in range(12):
        tema = ("claro", "escuro", "sistema")[(indice + volta) % 3]
        for metodo, args in (("preferencias_salvar", ({"tema": tema},)), ("motoristas_listar", ()),
                             ("decisao_registrar", (f"v-1187-e-{300 + volta}", "confirmado")),
                             ("estado", ())):
            resposta = chamar(cliente_http, metodo, *args)
            corpo = resposta.json()
            if resposta.status_code != 200 or not corpo.get("ok"):
                falhas.append((indice, metodo, corpo))


linhas = [threading.Thread(target=trabalho, args=(c, i)) for i, c in enumerate((admin, supervisor, admin, supervisor))]
for linha in linhas:
    linha.start()
for linha in linhas:
    linha.join()
assert not falhas, f"WEB-04 concorrência: {falhas[:3]}"
lista = dados(chamar(admin, "atividades_listar", {"limite": 5000}))
assert lista["integro"] is True, "WEB-04 cadeia de atividades quebrou com escritas de várias conexões"
assert all(not p.ponte._falhas for p in web.servidor.sessoes_ativas()), "WEB-04 falha interna numa Ponte"
pontes = [Ponte(web.dados, relogio=lambda: web.relogio[0], custo_scrypt=CUSTO_TESTE, script_local=None) for _ in range(3)]
resultados = []


def direto(ponte, indice):
    resultados.append(ponte.entrar("marina.lopes", SENHA_ADM)["ok"])
    for volta in range(10):
        resultados.append(ponte.decisao_orientado(f"v-1187-e-{300 + volta}", (indice + volta) % 2 == 0)["ok"])


linhas = [threading.Thread(target=direto, args=(p, i)) for i, p in enumerate(pontes)]
for linha in linhas:
    linha.start()
for linha in linhas:
    linha.join()
assert all(resultados) and len(resultados) == 33, f"WEB-04 Pontes diretas: {resultados}"
assert pontes[0].atividades_listar({"limite": 5000})["dados"]["integro"] is True
for ponte in pontes:
    ponte._n().banco.fechar()
ok("WEB-04/05 várias Pontes na mesma pasta: 4 linhas HTTP + 3 Pontes diretas gravando juntas, tudo ok e registro íntegro")

# WEB-05 ------------------------------------------------------------------------------------------------------------------
web.avancar(61)
saiu = chamar(supervisor, "sair")
assert dados(saiu) == {} and any("Max-Age=0" in c for c in set_cookie(saiu)), "WEB-05 sair apaga o cookie"
assert dados(chamar(supervisor, "estado"))["sessao"] is None
erro(chamar(supervisor, "motoristas_listar"), "sem_sessao", "WEB-05 depois de sair")
assert dados(chamar(admin, "estado"))["sessao"]["usuario"] == "marina.lopes"
assert len(dados(chamar(admin, "motoristas_listar"))) == 5
assert web.servidor.total_sessoes() == 1
ok("WEB-05 sair numa sessão apaga só aquele cookie; a outra segue entrando e listando")

# Espera crescente das contas vale entre sessões (cada tentativa sem cookie usa uma Ponte nova).
web.avancar(61)
for tentativa in range(1, 6):
    resposta = chamar(web.cliente(), "entrar", "paulo.souza", "senha errada de proposito")
    corpo = resposta.json()
    if tentativa < 5:
        assert corpo["codigo"] == "invalido", f"tentativa {tentativa}: {corpo}"
    else:
        assert corpo["codigo"] == "espera" and corpo["esperar_s"] == 30, f"5ª tentativa: {corpo}"
erro(chamar(web.cliente(), "entrar", "paulo.souza", SENHA_SUP), "espera", "senha certa durante a espera")
assert web.servidor.total_sessoes() == 1, "tentativa errada não cria sessão"
web.avancar(31)
ok("espera crescente das contas (5 erros: 30 s) vale entre sessões do navegador; erro não cria sessão nem cookie")

# WEB-08 ------------------------------------------------------------------------------------------------------------------
web.avancar(61)
antes = sorted(p.relative_to(web.tmp).as_posix() for p in web.tmp.rglob("*") if p.is_file())
exportado = chamar(admin, "motorista_exportar", 1)
corpo = exportado.json()
assert corpo["ok"] and corpo["arquivo"]["nome"].startswith("rotaguard-motorista-") and corpo["arquivo"]["nome"].endswith(
    ".json"), corpo.get("arquivo", {}).get("nome")
assert corpo["arquivo"]["tipo"] == "application/json"
conteudo = json.loads(base64.b64decode(corpo["arquivo"]["base64"]))
assert conteudo["formato"] == "rotaguard-dados-motorista/1" and conteudo["motorista"]["id"] == 1
assert corpo["dados"]["caminho"] == corpo["arquivo"]["nome"], "WEB-08 sem caminho do servidor na resposta"
csv = chamar(admin, "atividades_exportar").json()
assert csv["ok"] and csv["arquivo"]["tipo"] == "text/csv" and csv["arquivo"]["nome"].endswith(".csv")
assert base64.b64decode(csv["arquivo"]["base64"]).startswith("﻿id;".encode("utf-8"))
feita = chamar(admin, "copia_fazer", SENHA_COPIA).json()
assert feita["ok"] and feita["arquivo"]["nome"].endswith(".rotaguard-copia"), feita.get("erro")
assert feita["dados"]["bytes"] == len(base64.b64decode(feita["arquivo"]["base64"]))
cabecalho, pacote = copia.decifrar(base64.b64decode(feita["arquivo"]["base64"]), SENHA_COPIA)
assert cabecalho["formato"] == copia.FORMATO and copia.conteudo_da_copia(cabecalho, pacote)["banco"]
depois = sorted(p.relative_to(web.tmp).as_posix() for p in web.tmp.rglob("*") if p.is_file())
assert depois == antes, f"WEB-08 arquivos sobrando: {set(depois) ^ set(antes)}"
assert sobras(web) == [], f"WEB-08 a pasta temporária fica vazia depois do download: {sobras(web)}"
erro(chamar(supervisor, "motorista_exportar", 1), "sem_sessao", "exportar sem sessão")
ok("WEB-08 exportar motorista, atividades e cópia devolvem o arquivo para baixar; nada fica gravado fora da pasta temporária")

# WEB-09 ------------------------------------------------------------------------------------------------------------------
for motorista_id, conteudo_termo, nome, mime in ((1, PDF, "termo-carlos.pdf", "application/pdf"),
                                                 (2, PNG, "termo-juliana.png", "image/png"),
                                                 (3, JPEG, "termo-rogerio.jpg", "image/jpeg")):
    arquivo = {"nome": nome, "conteudo_base64": base64.b64encode(conteudo_termo).decode("ascii")}
    dados(chamar(admin, "termo_importar", motorista_id, arquivo, {"data": "2026-10-01"}), f"WEB-09 importar {nome}")
    visto = chamar(admin, "termo_ver", motorista_id).json()
    assert visto["ok"], visto
    if mime == "application/pdf":
        assert visto["dados"] == {"tipo": "pdf", "nome": nome, "aberto": True}
        assert visto["arquivo"]["tipo"] == mime and visto["arquivo"]["nome"] == nome
        assert base64.b64decode(visto["arquivo"]["base64"]) == conteudo_termo
    else:
        assert "arquivo" not in visto and visto["dados"]["tipo"] == "imagem"
        assert visto["dados"]["conteudo"] == f"data:{mime};base64,{base64.b64encode(conteudo_termo).decode('ascii')}"
assert sobras(web) == []
ok("WEB-09 termo_ver devolve o PDF como arquivo (application/pdf) e a foto como data: image/png ou image/jpeg")

# Script local não existe na web: responde sem erro, com o aviso.
script = dados(chamar(admin, "script_estado"))
assert script["aberto"] is False and script.get("indisponivel"), script
assert dados(chamar(admin, "script_eventos", 0)) == []
erro(chamar(web.cliente(), "script_estado"), "sem_sessao", "script sem sessão")
ok("script_estado e script_eventos na web: indisponível, sem erro (Ao vivo usa a câmera do navegador)")

# WEB-10 ------------------------------------------------------------------------------------------------------------------
web.avancar(15 * 60 + 1)
expirou = chamar(admin, "motoristas_listar")
erro(expirou, "sem_sessao", "WEB-10 depois de 15 min sem uso")
assert any("Max-Age=0" in c for c in set_cookie(expirou)), "WEB-10 cookie vencido é apagado"
assert dados(chamar(admin, "estado"))["sessao"] is None
assert web.servidor.total_sessoes() == 0
admin = web.cliente()
dados(chamar(admin, "entrar", "marina.lopes", SENHA_ADM))
for _ in range(12 * 6 - 1):  # usa a cada 10 min, sem nunca passar do bloqueio, até perto de 12 h
    web.avancar(10 * 60)
    dados(chamar(admin, "tocar"), "WEB-10 uso dentro das 12 h")
web.avancar(10 * 60)
erro(chamar(admin, "tocar"), "sem_sessao", "WEB-10 passou de 12 h")
ok("WEB-10 sessão some depois do tempo de bloqueio sem uso (15 min) e, mesmo em uso, depois de 12 h: sem_sessao")

# Sessão nova a cada entrada (o id muda) e no máximo N sessões (a de uso mais antigo sai).
pequeno = Ambiente("cap", max_sessoes=2)
primeiro, _ = ativar(pequeno)
anterior = primeiro.cookies.get("rg_painel")
dados(chamar(primeiro, "entrar", "marina.lopes", SENHA_ADM))
assert primeiro.cookies.get("rg_painel") != anterior, "id da sessão troca ao entrar"
pequeno.avancar(5)
outros = [pequeno.cliente(), pequeno.cliente()]
for cliente_extra in outros:
    pequeno.avancar(5)
    dados(chamar(cliente_extra, "entrar", "marina.lopes", SENHA_ADM))
assert pequeno.servidor.total_sessoes() == 2
erro(chamar(primeiro, "motoristas_listar"), "sem_sessao", "a sessão de uso mais antigo saiu")
assert all(dados(chamar(c, "estado"))["sessao"] for c in outros)
ok("id da sessão troca ao entrar; com o máximo de sessões cheio, a de uso mais antigo sai")

# WEB-11 ------------------------------------------------------------------------------------------------------------------
grande = b'{"args": ["' + b"a" * (16 * 1024 * 1024) + b'"]}'
resposta = cliente.post(f"{BASE}/api/ponte/estado", content=grande,
                        headers={**CABECALHOS, "Content-Type": "application/json"})
assert resposta.status_code == 413 and resposta.json()["ok"] is False, resposta.status_code


def em_pedacos():
    for _ in range(17):
        yield b"a" * (1024 * 1024)


resposta = cliente.post(f"{BASE}/api/ponte/estado", content=em_pedacos(),
                        headers={**CABECALHOS, "Content-Type": "application/json"})
assert resposta.status_code == 413, f"WEB-11 sem Content-Length: {resposta.status_code}"
for corpo_ruim in (b"[1, 2]", b"{\"args\": 3}", b"nao e json", b"{\"args\": [NaN]}"):
    resposta = cliente.post(f"{BASE}/api/ponte/estado", content=corpo_ruim, headers=CABECALHOS)
    assert resposta.status_code == 400 and resposta.json()["ok"] is False, corpo_ruim
ok("WEB-11 corpo acima de 16 MB responde 413 (com e sem Content-Length); corpo fora do formato responde 400")

# WEB-12 ------------------------------------------------------------------------------------------------------------------
limite = Ambiente("12")
ativar(limite)
limite.avancar(61)
tentativas = [chamar(limite.cliente(), "entrar", "marina.lopes", "senha errada de proposito") for _ in range(10)]
assert all(r.status_code == 200 for r in tentativas)
bloqueada = chamar(limite.cliente(), "entrar", "marina.lopes", SENHA_ADM)
assert bloqueada.status_code == 429 and bloqueada.json()["codigo"] == "espera" and int(bloqueada.headers["retry-after"]) > 0
assert bloqueada.json()["esperar_s"] >= 1
for metodo, args in (("recuperar_acesso", ("marina.lopes", "AAAA", "frase nova e comprida")),
                     ("desbloquear", ("x",)), ("ativar_local", (EMPRESA, ADMIN))):
    assert chamar(limite.cliente(), metodo, *args).status_code == 429, f"WEB-12 {metodo}"
assert chamar(limite.cliente(), "estado").status_code == 200, "estado não entra no limite"
limite.avancar(61)
assert chamar(limite.cliente(), "entrar", "marina.lopes", "senha errada de proposito").status_code == 200
assert servidor_web.ip_do_cliente("172.18.0.5", "203.0.113.7, 10.0.0.2", servidor_web.PROXIES_PADRAO) == "203.0.113.7"
assert servidor_web.ip_do_cliente("203.0.113.9", "198.51.100.1", servidor_web.PROXIES_PADRAO) == "203.0.113.9"
assert servidor_web.ip_do_cliente("172.18.0.5", "isto nao e ip", servidor_web.PROXIES_PADRAO) == "172.18.0.5"
assert servidor_web.ip_do_cliente("172.18.0.5", "198.51.100.1", ()) == "172.18.0.5"
assert servidor_web.ip_do_cliente(None, None, servidor_web.PROXIES_PADRAO) == "desconhecido"
ok("WEB-12 mais de 10 tentativas por minuto do mesmo IP (entrar, recuperar, desbloquear, ativar) respondem 429; "
   "X-Forwarded-For só vale vindo do proxy")

# Configuração pelo ambiente --------------------------------------------------------------------------------------------
padrao = servidor_web.config_do_ambiente({})
assert padrao["pasta"] == Path("/dados") and padrao["base"] == "/painel" and padrao["cookie_seguro"] is True
assert padrao["codigo_ativacao"] is None and padrao["origem"] is None
lida = servidor_web.config_do_ambiente({"PAINEL_DADOS": str(web.dados), "PAINEL_BASE": "/painel/",
                                        "PAINEL_CODIGO_ATIVACAO": " " + CODIGO + " ",
                                        "PAINEL_ORIGEM": "https://rotaguard.acexpartners.com.br/",
                                        "PAINEL_COOKIE_SEGURO": "0", "PAINEL_ESTATICO": str(web.estatico)})
assert lida["base"] == "/painel" and lida["codigo_ativacao"] == CODIGO and lida["cookie_seguro"] is False
assert lida["origem"] == "https://rotaguard.acexpartners.com.br" and lida["estatico"] == web.estatico
curto = servidor_web.config_do_ambiente({"PAINEL_CODIGO_ATIVACAO": "curto"})
assert curto["codigo_ativacao"] is None, "código curto demais desliga a ativação pela web"
ok("variáveis: PAINEL_DADOS=/dados, PAINEL_BASE=/painel e cookie seguro por padrão; código curto desliga a ativação")

# Nenhum segredo no log ---------------------------------------------------------------------------------------------------
texto_log = "\n".join(REGISTROS.linhas)
assert REGISTROS.linhas, "o servidor registra ao menos o início"
for segredo in (*SEGREDOS, temporaria):
    assert segredo not in texto_log, "senha ou código apareceu no log"
ok(f"nenhuma senha, senha temporária ou código de ativação nos {len(REGISTROS.linhas)} registros do servidor")

# WEB-14 ------------------------------------------------------------------------------------------------------------------
antigos = sorted(p for p in (RAIZ / "tests").glob("test_painel_*.py") if p.name != Path(__file__).name)
for caminho in antigos:
    inicio = time.monotonic()
    feito = subprocess.run([sys.executable, str(caminho)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=RAIZ, timeout=600, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert feito.returncode == 0, f"WEB-14 {caminho.name} falhou:\n{feito.stdout[-1500:]}\n{feito.stderr[-1500:]}"
    print(f"   {caminho.name}: ok em {time.monotonic() - inicio:.0f} s")
ok(f"WEB-14 os {len(antigos)} testes antigos do painel continuam passando")

print(f"\n{checks} verificações OK")
