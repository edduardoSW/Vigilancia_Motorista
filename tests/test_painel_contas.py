"""Spec 014: entrar, equipe, permissões e registro de atividades do painel (núcleo Python).

Sem janela e sem pywebview: a Ponte é chamada direto, com relógio falso, scrypt barato, pasta temporária e script local
falso (não lista processos do Windows). Só biblioteca padrão; a cópia de segurança usa o cryptography do .venv:
    python tests/test_painel_contas.py
"""
import base64
import csv
import inspect
import io
import json
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import atividades as atv  # noqa: E402
import contas  # noqa: E402
from dados import Banco, iso_utc  # noqa: E402
from ponte import Ponte  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc).timestamp()
# Senhas descartáveis, só deste teste.
SENHA_ADM = "frase comprida de teste um"
SENHA_SUP = "frase comprida de teste dois"
SENHA_CON = "frase comprida de teste tres"
SENHA_ERRADA = "frase errada de teste"
SENHA_COPIA = "frase da copia de teste"
SENHA_NO_USUARIO = "frase secreta digitada no campo usuario"
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}
B64 = base64.b64encode(bytes(range(32))).decode()


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


class ScriptFalso:
    def estado(self):
        return {"aberto": False, "programa": None, "desde": None, "pid": None, "camera": None, "ultimo_sinal": None,
                "eventos": 0, "pasta": None}

    def eventos(self, desde_id):
        return []

    def iniciar(self):
        pass

    def parar(self):
        pass


def nova_ponte(tmp, relogio, destinos=None):
    def escolher(nome):
        if destinos is not None:
            destinos.append(nome)
        return Path(tmp) / nome

    return Ponte(Path(tmp) / "dados", relogio=lambda: relogio[0], custo_scrypt=CUSTO_TESTE, escolher_destino=escolher,
                 script_local=ScriptFalso())


def dados(resposta, contexto=""):
    assert resposta["ok"] is True, (contexto, resposta)
    return resposta["dados"]


def erro(resposta, codigo, contexto=""):
    assert resposta["ok"] is False and resposta.get("codigo") == codigo, (contexto, resposta)
    return resposta


def linhas(ponte, acao=None):
    banco = ponte._n().banco
    if acao is None:
        return banco.todos("SELECT * FROM atividades ORDER BY id")
    return banco.todos("SELECT * FROM atividades WHERE acao = ? ORDER BY id", (acao,))


def contar(ponte, tabela):
    return ponte._n().banco.um(f"SELECT COUNT(*) AS n FROM {tabela}")["n"]


def fechar(*pontes):
    for ponte in pontes:
        if ponte._nucleo is not None:
            ponte._n().banco.fechar()


def entrar_como(ponte, usuario, senha):
    ponte.sair()
    return dados(ponte.entrar(usuario, senha), usuario)


def criar_pessoa(ponte, nome, usuario, funcao, senha, admin=("marina.lopes", SENHA_ADM)):
    """Administrador adiciona; a pessoa entra com a senha temporária e troca. Volta com o administrador na sessão."""
    entrar_como(ponte, *admin)
    novo = dados(ponte.equipe_adicionar({"nome": nome, "usuario": usuario, "funcao": funcao}), usuario)
    entrar_como(ponte, usuario, novo["senha_temporaria"])
    dados(ponte.trocar_senha(novo["senha_temporaria"], senha), usuario)
    entrar_como(ponte, *admin)
    return novo["usuario"]["id"]


def chaveiro(**mudar):
    """Arquivo `rotaguard-chaveiro-coleta/1` (spec 003, §4.3) com duas caixas, a segunda revogada."""
    arquivo = {"formato": "rotaguard-chaveiro-coleta/1", "empresa_id": 7, "gerado_em": "2026-09-11T15:20:00.000Z",
               "caixas": [
                   {"id_caixa": "rg-abcdefghijkl", "dispositivo_id": 3, "nome": "Caminhão ABC-1234",
                    "geracao_atual": 1, "chaves_coleta": {"1": B64},
                    "chaves_publicas": [{"geracao": 1, "kid": "0123456789abcdef", "publica": B64}],
                    "revogada_em": None},
                   {"id_caixa": "rg-mnopqrstuvwx", "dispositivo_id": 4, "nome": "Ônibus 2240", "geracao_atual": 2,
                    "chaves_coleta": {"1": B64, "2": B64},
                    "chaves_publicas": [{"geracao": 2, "kid": "fedcba9876543210", "publica": B64}],
                    "revogada_em": "2026-09-12T10:00:00.000Z"}]}
    arquivo.update(mudar)
    return arquivo


def caixa_alterada(indice, **mudar):
    arquivo = chaveiro()
    arquivo["caixas"][indice].update(mudar)
    return json.dumps(arquivo)


# ENT-01 · sem banco: tela de ativação; sem arquivo da empresa, só a demonstração abre
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    assert not (Path(tmp) / "dados").exists(), "ENT-01 criar a ponte não pode gravar nada"
    estado = dados(ponte.estado())
    assert (estado["ativado"], estado["modo"], estado["empresa"], estado["sessao"]) == (False, None, None, None), \
        f"ENT-01 sem banco o painel pede ativação: {estado}"
    erro(ponte.entrar("marina.lopes", SENHA_ADM), "sem_sessao", "ENT-01 entrar antes de ativar")
    erro(ponte.motoristas_listar(), "sem_sessao", "ENT-01 cadastro antes de ativar")
    for vazio in ("", None, "{}"):
        resposta = erro(ponte.ativar_com_arquivo(vazio, ADMIN), "invalido", "ENT-01 sem arquivo da empresa")
        assert resposta["erro"] == contas.MENSAGEM_ARQUIVO_INVALIDO, f"ENT-01 mensagem do arquivo: {resposta}"
    assert dados(ponte.estado())["ativado"] is False, "ENT-01 arquivo vazio não ativa"
    codigo = dados(ponte.ativar_demonstracao(ADMIN))["codigo_recuperacao"]
    estado = dados(ponte.estado())
    assert estado["ativado"] is True and estado["modo"] == "demonstracao", f"ENT-01 demonstração ativa: {estado}"
    assert estado["empresa"] == {"nome": "Viação Demonstração"} and estado["sessao"]["usuario"] == "marina.lopes", \
        f"ENT-01 demonstração já entra com o administrador: {estado}"
    erro(ponte.ativar_demonstracao(ADMIN), "conflito", "ENT-01 ativar de novo")
    erro(ponte.ativar_com_arquivo(json.dumps(chaveiro()), ADMIN), "conflito", "ENT-01 arquivo depois de ativado")
    fechar(ponte)
ok("ENT-01 sem banco pede ativação; entrar e cadastros recusados; sem arquivo só a demonstração ativa (uma vez)")

# ENT-02 · arquivo inválido ou alterado é recusado e nada é gravado
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    valido = json.dumps(chaveiro())
    ruins = [
        valido[:-5], "não é json", json.dumps([chaveiro()]), json.dumps(chaveiro(formato="rotaguard-chaveiro-coleta/2")),
        json.dumps(chaveiro(empresa_id="7")), json.dumps(chaveiro(empresa_id=0)), json.dumps(chaveiro(gerado_em="ontem")),
        json.dumps(chaveiro(caixas=[])), json.dumps(chaveiro(caixas=[chaveiro()["caixas"][0]] * 2)),
        caixa_alterada(0, id_caixa="rg-ABCDEFGHIJKL"), caixa_alterada(0, id_caixa="rg-abc"),
        caixa_alterada(0, dispositivo_id=True), caixa_alterada(0, geracao_atual=2),
        caixa_alterada(0, chaves_coleta={"1": "@@@"}), caixa_alterada(0, chaves_publicas=[]),
        caixa_alterada(0, chaves_publicas=[{"geracao": 1, "kid": "xyz", "publica": B64}]),
        caixa_alterada(1, revogada_em="quando"), caixa_alterada(0, nome=None),
    ]
    for conteudo in ruins:
        resposta = erro(ponte.ativar_com_arquivo(conteudo, ADMIN), "invalido", f"ENT-02 arquivo ruim: {conteudo[:80]}")
        assert resposta["erro"] == contas.MENSAGEM_ARQUIVO_INVALIDO, f"ENT-02 mensagem simples: {resposta}"
    resposta = erro(ponte.ativar_com_arquivo(valido, {**ADMIN, "senha": "curta"}), "invalido", "ENT-02 admin ruim")
    assert resposta["campo"] == "senha", f"ENT-02 arquivo bom com senha ruim marca o campo: {resposta}"
    for tabela in ("usuarios", "caixas", "motoristas", "veiculos", "configuracoes", "atividades", "meta", "decisoes"):
        assert contar(ponte, tabela) == 0, f"ENT-02 arquivo recusado não grava nada em {tabela}"
    dados(ponte.ativar_com_arquivo(valido, ADMIN), "ENT-02 arquivo válido")
    estado = dados(ponte.estado())
    assert estado["modo"] == "empresa" and estado["empresa"] == {"nome": "Empresa 7"}, f"ENT-02 empresa: {estado}"
    assert ponte._n().banco.meta_ler("empresa_id") == "7" and contar(ponte, "caixas") == 2, "ENT-02 caixas do arquivo"
    assert dados(ponte.decisoes_listar()) == [] and contar(ponte, "motoristas") == 0, \
        "ENT-02 ativar com arquivo não traz dados de demonstração"
    fechar(ponte)
print("-- ENT-02 parcial: o formato rotaguard-chaveiro-coleta/1 (spec 003, §4.3) não tem assinatura da RotaGuard nem "
      "nome da empresa; arquivo alterado com estrutura válida ou de outra empresa não tem como ser detectado")
ok("ENT-02 arquivo quebrado, fora do formato ou com caixa inválida é recusado com frase simples e nada é gravado")

# ENT-03 · senha só como scrypt (N 2^17, r 8, p 1, sal 16 bytes); nenhuma senha em texto no banco, no log ou na ponte
guardado = contas.hash_senha(SENHA_ADM)  # custo de produção, uma vez só (≈130 MB e alguns décimos de segundo)
partes = contas.ler_hash(guardado)
assert (partes["n"], partes["r"], partes["p"], len(partes["sal"]), len(partes["chave"])) == (2**17, 8, 1, 16, 32), \
    f"ENT-03 parâmetros de produção: {partes}"
assert contas.conferir_senha(SENHA_ADM, guardado) and not contas.conferir_senha(SENHA_ERRADA, guardado), \
    "ENT-03 senha certa confere e errada não"
assert contas.hash_senha(SENHA_ADM) != guardado, "ENT-03 sal novo a cada hash"
assert "hmac.compare_digest" in inspect.getsource(contas.conferir_senha), "ENT-03 conferida com hmac.compare_digest"
assert Ponte()._custo == contas.CUSTO_PRODUCAO == (2**17, 8, 1), "ENT-03 a ponte de verdade usa o custo de produção"
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    respostas = [ponte.estado()]
    codigo = dados(ponte.ativar_demonstracao(ADMIN))["codigo_recuperacao"]
    novo = dados(ponte.equipe_adicionar({"nome": "Paulo Reis", "usuario": "paulo.reis", "funcao": "supervisor"}))
    temporaria = novo["senha_temporaria"]
    respostas += [ponte.sair(), ponte.entrar("paulo.reis", SENHA_ERRADA), ponte.entrar("paulo.reis", temporaria),
                  ponte.trocar_senha(temporaria, SENHA_SUP), ponte.estado(), ponte.sair(),
                  ponte.entrar("marina.lopes", SENHA_ADM), ponte.equipe_listar(), ponte.atividades_listar({}),
                  ponte.desbloquear(SENHA_ERRADA), ponte.copia_fazer(SENHA_COPIA), ponte.atividades_exportar(),
                  ponte.estado()]
    texto_ponte = json.dumps(respostas, ensure_ascii=False)
    for proibido in (SENHA_ADM, SENHA_SUP, SENHA_ERRADA, SENHA_COPIA, "senha_hash", "scrypt$"):
        assert proibido not in texto_ponte, f"ENT-03 a ponte devolveu {proibido!r}"
    assert all(l["senha_hash"].startswith("scrypt$16$8$1$") for l in ponte._n().banco.todos("SELECT * FROM usuarios")), \
        "ENT-03 banco guarda só o hash scrypt com os parâmetros"
    assert not ponte._falhas, f"ENT-03 nenhuma falha interna: {ponte._falhas}"
    fechar(ponte)
    arquivos = [caminho for caminho in Path(tmp).rglob("*") if caminho.is_file()]
    assert {c.suffix for c in arquivos} >= {".db", ".csv", ".rotaguard-copia"}, f"ENT-03 arquivos gerados: {arquivos}"
    segredos = (SENHA_ADM, SENHA_SUP, SENHA_ERRADA, SENHA_COPIA, temporaria, codigo, contas.normalizar_codigo(codigo))
    for caminho in arquivos:
        conteudo = caminho.read_bytes()
        for segredo in segredos:
            assert segredo.encode("utf-8") not in conteudo, f"ENT-03 segredo em texto em {caminho.name}"
ok("ENT-03 scrypt N 2^17 r 8 p 1 sal 16 bytes com compare_digest; senhas, senha temporária e código fora do banco, "
   "do CSV, da cópia e das respostas")

# ENT-04 · senha curta ou comum recusada com frase simples; senha temporária obriga a trocar no primeiro acesso
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    for senha, mensagem in ((None, contas.MENSAGEM_SENHA_CURTA), ("", contas.MENSAGEM_SENHA_CURTA),
                            ("curta1234", contas.MENSAGEM_SENHA_CURTA), ("1234567890", contas.MENSAGEM_SENHA_COMUM),
                            ("Password123", contas.MENSAGEM_SENHA_COMUM), ("SENHA123456", contas.MENSAGEM_SENHA_COMUM),
                            ("aaaaaaaaaaaa", contas.MENSAGEM_SENHA_COMUM),
                            ("marina.lopes-2026", contas.MENSAGEM_SENHA_COMUM)):
        resposta = erro(ponte.ativar_demonstracao({**ADMIN, "senha": senha}), "invalido", f"ENT-04 {senha!r}")
        assert resposta["erro"] == mensagem and resposta["campo"] == "senha", f"ENT-04 {senha!r}: {resposta}"
    longa = erro(ponte.ativar_demonstracao({**ADMIN, "senha": "x1" * 101}), "invalido", "ENT-04 senha enorme")
    assert "200" in longa["erro"], longa
    assert dados(ponte.estado())["ativado"] is False and contar(ponte, "usuarios") == 0, "ENT-04 nada gravado"
    dados(ponte.ativar_demonstracao(ADMIN))
    resposta = erro(ponte.trocar_senha(SENHA_ADM, "curta"), "invalido", "ENT-04 troca curta")
    assert resposta["campo"] == "nova" and resposta["erro"] == contas.MENSAGEM_SENHA_CURTA, resposta
    assert erro(ponte.trocar_senha(SENHA_ADM, SENHA_ADM), "invalido")["campo"] == "nova", "ENT-04 nova igual à atual"
    novo = dados(ponte.equipe_adicionar({"nome": "Ana Souza", "usuario": "ana.souza", "funcao": "consulta"}))
    assert novo["usuario"]["trocar_senha"] is True and re.fullmatch(r"[a-z2-9]{4}(-[a-z2-9]{4}){2}",
                                                                   novo["senha_temporaria"]), novo
    entrar_como(ponte, "ana.souza", novo["senha_temporaria"])
    resposta = erro(ponte.motoristas_listar(), "sem_permissao", "ENT-04 senha temporária sem trocar")
    assert resposta["campo"] == "nova", resposta
    dados(ponte.trocar_senha(novo["senha_temporaria"], SENHA_CON))
    assert dados(ponte.estado())["sessao"]["trocar_senha"] is False and dados(ponte.motoristas_listar()), \
        "ENT-04 depois de trocar a senha a pessoa usa o painel"
    ponte.sair()
    resposta = erro(ponte.recuperar_acesso("marina.lopes", "AAAAA", "curta"), "invalido", "ENT-04 recuperar curta")
    assert resposta["campo"] == "nova_senha", resposta
    fechar(ponte)
ok("ENT-04 senha curta, comum, repetida ou com o usuário é recusada com frase simples e nada grava; senha temporária "
   "obriga a trocar no primeiro acesso")

# ENT-05 · 5 erros seguidos → 30 s, dobrando até 15 min; cada erro no registro
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    ponte.sair()
    for numero in range(1, 5):
        resposta = erro(ponte.entrar("marina.lopes", SENHA_ERRADA), "invalido", f"ENT-05 {numero}º erro")
        assert resposta["erro"] == contas.MENSAGEM_CREDENCIAIS and "esperar_s" not in resposta, f"ENT-05 {resposta}"
    quinto = erro(ponte.entrar("marina.lopes", SENHA_ERRADA), "espera", "ENT-05 5º erro")
    assert quinto["esperar_s"] == 30 and "Espere 30 segundos" in quinto["erro"], f"ENT-05 5º erro: {quinto}"
    t[0] += 10
    durante = erro(ponte.entrar("marina.lopes", SENHA_ADM), "espera", "ENT-05 senha certa durante a espera")
    assert durante["esperar_s"] == 20, f"ENT-05 contagem regressiva: {durante}"
    esperas = []
    for _ in range(6):
        t[0] += contas.ESPERA_MAXIMA_S
        esperas.append(erro(ponte.entrar("marina.lopes", SENHA_ERRADA), "espera", "ENT-05")["esperar_s"])
    assert esperas == [60, 120, 240, 480, 900, 900], f"ENT-05 a espera dobra até 15 min: {esperas}"
    t[0] += contas.ESPERA_MAXIMA_S
    dados(ponte.entrar("marina.lopes", SENHA_ADM), "ENT-05 depois da espera a senha certa entra")
    ponte.sair()
    depois = erro(ponte.entrar("marina.lopes", SENHA_ERRADA), "invalido", "ENT-05 entrar zera a contagem")
    assert depois["erro"] == contas.MENSAGEM_CREDENCIAIS, f"ENT-05 {depois}"
    registro = linhas(ponte, "errou a senha")
    assert len(registro) == 12, f"ENT-05 cada erro (e só erro) vai para o registro: {len(registro)}"
    assert all(l["usuario"] == "Marina Lopes" and l["alvo"] == "marina.lopes" and "erro seguido" in l["detalhe"]
               for l in registro), "ENT-05 linha com quem e em quê"
    assert registro[-2]["detalhe"] == "11º erro seguido, espera de 900 s", f"ENT-05 {registro[-2]['detalhe']}"
    ninguem = ponte.entrar("ninguem.aqui", SENHA_ERRADA)
    assert ninguem == {"ok": False, "erro": contas.MENSAGEM_CREDENCIAIS, "codigo": "invalido", "campo": "senha"}, \
        f"ENT-05 usuário que não existe recebe a mesma resposta da senha errada: {ninguem}"
    assert linhas(ponte, "errou a senha")[-1]["usuario"] is None, "ENT-05 erro de usuário inexistente também registra"
    fechar(ponte)
assert [contas.espera_para(n) for n in (1, 4, 5, 6, 7, 9, 10, 40)] == [0, 0, 30, 60, 120, 480, 900, 900], \
    "ENT-05 tabela de espera"
ok("ENT-05 relógio falso: 4 erros sem espera, 5º com 30 s (nem a senha certa passa), 60/120/240/480/900/900; "
   "12 erros no registro; usuário inexistente com a mesma resposta")

# ENT-03 · senha digitada por engano no campo de usuário não vai para o registro de atividades nem para o banco
# (achado na revisão de 15/09/2026: o registro guardava o texto digitado como "em quê").
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    ponte.sair()
    erro(ponte.entrar(SENHA_NO_USUARIO, SENHA_ERRADA), "invalido", "ENT-03 senha no campo de usuário ao entrar")
    erro(ponte.recuperar_acesso(SENHA_NO_USUARIO, "AAAAA-BBBBB", "frase nova de teste cinco"), "invalido",
         "ENT-03 senha no campo de usuário ao recuperar o acesso")
    registro = [dict(l) for l in linhas(ponte) if l["acao"] in ("errou a senha", "errou o código de recuperação")]
    assert len(registro) == 2 and all(l["usuario"] is None and l["alvo"] is None for l in registro), \
        f"ENT-03 usuário que não existe fica sem 'em quê' no registro: {registro}"
    assert all("usuário não cadastrado" in (l["detalhe"] or "") for l in registro), f"ENT-03 detalhe: {registro}"
    fechar(ponte)
    for caminho in Path(tmp).rglob("*"):
        if caminho.is_file():
            assert SENHA_NO_USUARIO.encode("utf-8") not in caminho.read_bytes(), \
                f"ENT-03 senha digitada no campo de usuário ficou em {caminho.name}"
ok("ENT-03 senha digitada por engano no campo de usuário (entrar e recuperar acesso) fica fora do registro e do banco")

# ENT-06 · usuário desativado: mesma resposta com senha certa ou errada
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    supervisor_id = criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    dados(ponte.equipe_alterar(supervisor_id, {"ativo": False}))
    ponte.sair()
    certa = ponte.entrar("paulo.reis", SENHA_SUP)
    errada = ponte.entrar("paulo.reis", SENHA_ERRADA)
    assert certa == errada and certa["ok"] is False and certa["erro"] == contas.MENSAGEM_DESATIVADO, \
        f"ENT-06 respostas diferentes: {certa} × {errada}"
    for _ in range(6):
        assert ponte.entrar("paulo.reis", SENHA_ERRADA) == certa, "ENT-06 errar várias vezes não muda a resposta"
    assert ponte.entrar("paulo.reis", SENHA_SUP) == certa, "ENT-06 a senha certa continua com a mesma resposta"
    assert len(linhas(ponte, "tentou entrar com acesso desativado")) == 9, "ENT-06 cada tentativa no registro"
    assert not linhas(ponte, "errou a senha") and dados(ponte.estado())["sessao"] is None, "ENT-06 não entra"
    fechar(ponte)
ok("ENT-06 desativado recebe a mesma resposta com senha certa ou errada, sem espera que denuncie, e fica no registro")

# ENT-07 · sessão só na memória: reabrir o app pede login; nada de sessão em arquivo
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    primeira = nova_ponte(tmp, t)
    dados(primeira.ativar_demonstracao(ADMIN))
    assert dados(primeira.estado())["sessao"]["usuario"] == "marina.lopes", "ENT-07 entrou na ativação"
    fechar(primeira)
    reaberta = nova_ponte(tmp, t)
    estado = dados(reaberta.estado())
    assert estado["ativado"] is True and estado["sessao"] is None, f"ENT-07 reaberto pede login: {estado}"
    erro(reaberta.motoristas_listar(), "sem_sessao", "ENT-07 sem sessão depois de reabrir")
    erro(reaberta.tocar(), "sem_sessao", "ENT-07 tocar sem sessão")
    banco = reaberta._n().banco
    chaves = {linha["chave"] for linha in banco.todos("SELECT chave FROM meta")}
    assert chaves == {"ativado", "modo", "recuperacao_hash", "atividades_ultimo"}, f"ENT-07 meta sem sessão: {chaves}"
    tabelas = {linha["name"] for linha in banco.todos("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert not [n for n in tabelas if any(p in n for p in ("sess", "token", "cookie"))], f"ENT-07 {tabelas}"
    fechar(reaberta)
    assert sorted(c.name for c in (Path(tmp) / "dados").iterdir()) == ["painel.db"], "ENT-07 só o banco na pasta"
print("-- ENT-07 parcial: localStorage e cookie ficam para o teste da interface")
ok("ENT-07 reabrir a ponte na mesma pasta pede login; meta, tabelas e pasta sem sessão nem token")


def chamadas(ids):
    """Métodos da ponte que exigem ação (spec 014, decisão 3), com argumentos que não estragam os dados."""
    return [
        ("equipe_listar", "equipe", ()),
        ("equipe_adicionar", "equipe", ({"nome": "Pessoa da Matriz", "usuario": "matriz.teste", "funcao": "consulta"},)),
        ("equipe_alterar", "equipe", (ids["consulta"], {"funcao": "consulta"})),
        ("equipe_nova_senha", "equipe", (999999,)),
        ("atividades_listar", "atividades", ({},)),
        ("atividades_exportar", "atividades", ()),
        ("motoristas_listar", "ver_viagens", ()),
        ("veiculos_listar", "ver_viagens", ()),
        ("caixas_listar", "ver_viagens", ()),
        ("decisoes_listar", "ver_viagens", ()),
        ("script_estado", "ver_viagens", ()),
        ("script_eventos", "ver_viagens", (0,)),
        ("inicio_resumo", "ver_viagens", ()),
        ("motorista_salvar", "cadastrar", ({},)),
        ("motorista_exportar", "cadastrar", (1,)),
        # Spec 019 (TER-04): termo importado só para administrador e supervisor; motorista que não existe não grava.
        ("motorista_termos", "cadastrar", (999999,)),
        ("termo_importar", "cadastrar", (999999, {"nome": "termo.pdf", "conteudo_base64": "JVBERi0xLjQK"},
                                         {"data": "2026-09-14", "versao": None})),
        ("termo_ver", "cadastrar", (999999,)),
        ("veiculo_salvar", "cadastrar", ({},)),
        ("caixa_vincular", "cadastrar", (999999, None)),
        ("decisao_registrar", "decidir", ("v-2240-e-001", "confirmado")),
        ("decisao_orientado", "decidir", ("v-2240-e-001", False)),
        ("decisao_desfazer", "decidir", ("v-2240-e-001",)),
        ("video_abrir", "ver_video", ("v-1187-e-202", "m-01")),
        ("config_ler", "configuracoes", ()),
        ("config_salvar", "configuracoes", ("acesso", {"bloqueio_min": 15})),
        ("copia_fazer", "configuracoes", (SENHA_COPIA,)),
        ("primeiros_passos_esconder", "configuracoes", (False,)),
    ]


SEM_ACAO = {"estado", "ativar_demonstracao", "ativar_com_arquivo", "entrar", "sair", "bloquear", "tocar", "desbloquear",
            "trocar_senha", "recuperar_acesso", "preferencias_salvar"}  # preferências: qualquer sessão (spec 019, PRF-01)

# ENT-08 · bloqueio depois do tempo configurado; desbloquear exige a senha de quem entrou
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    t[0] += 15 * 60 - 1
    assert dados(ponte.estado())["bloqueado"] is False, "ENT-08 14 min 59 s ainda aberto"
    assert dados(ponte.tocar()) == {"bloqueado": False}, "ENT-08 tocar com uso"
    t[0] += 15 * 60 - 1
    assert dados(ponte.estado())["bloqueado"] is False, "ENT-08 tocar renova o tempo"
    t[0] += 1
    estado = dados(ponte.estado())
    assert estado["bloqueado"] is True and estado["sessao"]["usuario"] == "marina.lopes", f"ENT-08 bloqueou: {estado}"
    assert len(linhas(ponte, "bloqueou por tempo sem uso")) == 1, "ENT-08 bloqueio no registro"
    for nome, _acao, args in chamadas({"consulta": 1}) + [("trocar_senha", None, (SENHA_ADM, SENHA_SUP)),
                                                          ("preferencias_salvar", None, ({"tema": "escuro"},))]:
        erro(getattr(ponte, nome)(*args), "bloqueado", f"ENT-08 {nome} com a tela bloqueada")
    t[0] += 3600
    assert dados(ponte.tocar()) == {"bloqueado": True}, "ENT-08 tocar não desbloqueia"
    outra = erro(ponte.desbloquear(SENHA_SUP), "invalido", "ENT-08 senha de outra pessoa")
    assert outra["campo"] == "senha" and dados(ponte.estado())["bloqueado"] is True, f"ENT-08 {outra}"
    assert dados(ponte.desbloquear(SENHA_ADM))["usuario"] == "marina.lopes", "ENT-08 senha de quem entrou"
    assert dados(ponte.estado())["bloqueado"] is False and linhas(ponte, "desbloqueou a tela"), "ENT-08 desbloqueou"
    assert linhas(ponte, "errou a senha ao desbloquear"), "ENT-08 erro ao desbloquear no registro"
    dados(ponte.config_salvar("acesso", {"bloqueio_min": 5}))
    assert dados(ponte.estado())["bloqueio_min"] == 5, "ENT-08 estado leva o tempo configurado"
    t[0] += 5 * 60
    assert dados(ponte.estado())["bloqueado"] is True, "ENT-08 vale o tempo configurado (5 min)"
    dados(ponte.desbloquear(SENHA_ADM))
    dados(ponte.bloquear())
    assert dados(ponte.estado())["bloqueado"] is True and len(linhas(ponte, "bloqueou a tela")) == 1, "ENT-08 bloquear"
    dados(ponte.sair(), "ENT-08 sair funciona com a tela bloqueada")
    assert dados(ponte.estado())["sessao"] is None, "ENT-08 saiu"
    fechar(ponte)
ok("ENT-08 relógio falso: bloqueia com 15 min sem tocar (e com 5 min configurado); bloqueada, só estado, tocar, "
   "desbloquear e sair; desbloqueia só com a senha de quem entrou")

# ENT-09 · código de recuperação mostrado uma vez, guardado só como hash e usável uma vez
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    codigo = dados(ponte.ativar_demonstracao(ADMIN))["codigo_recuperacao"]
    assert re.fullmatch(r"[A-Z2-9]{5}(-[A-Z2-9]{5}){3}", codigo), f"ENT-09 formato do código: {codigo}"
    guardado = ponte._n().banco.meta_ler("recuperacao_hash")
    assert guardado.startswith("scrypt$") and contas.normalizar_codigo(codigo) not in guardado, "ENT-09 só hash"
    outras = json.dumps([ponte.estado(), ponte.equipe_listar(), ponte.atividades_listar({}), ponte.config_ler()])
    assert codigo not in outras and contas.normalizar_codigo(codigo) not in outras, "ENT-09 código aparece uma vez só"
    erro(ponte.ativar_demonstracao(ADMIN), "conflito", "ENT-09 não dá para pedir o código de novo")
    criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    ponte.sair()
    nova = "frase nova de recuperacao"
    errado = erro(ponte.recuperar_acesso("marina.lopes", "AAAAA-BBBBB-CCCCC-DDDDD", nova), "invalido", "ENT-09 errado")
    assert errado["campo"] == "codigo" and errado["erro"] == "Usuário ou código de recuperação incorretos.", errado
    erro(ponte.recuperar_acesso("paulo.reis", codigo, nova), "invalido", "ENT-09 só para administrador")
    assert dados(ponte.recuperar_acesso("marina.lopes", codigo.lower().replace("-", " "), nova)) == {}, \
        "ENT-09 código digitado em minúsculas e com espaços vale"
    erro(ponte.entrar("marina.lopes", SENHA_ADM), "invalido", "ENT-09 a senha antiga deixa de valer")
    dados(ponte.entrar("marina.lopes", nova), "ENT-09 entra com a senha nova")
    ponte.sair()
    de_novo = erro(ponte.recuperar_acesso("marina.lopes", codigo, "outra frase de recuperacao"), "invalido", "ENT-09")
    assert de_novo["campo"] == "codigo", f"ENT-09 código usado não vale de novo: {de_novo}"
    assert len(linhas(ponte, "usou o código de recuperação")) == 1, "ENT-09 uso no registro"
    assert ponte._n().banco.meta_ler("recuperacao_hash") == "", "ENT-09 hash apagado depois do uso"
    fechar(ponte)
    conteudo = (Path(tmp) / "dados" / "painel.db").read_bytes()
    assert codigo.encode() not in conteudo and contas.normalizar_codigo(codigo).encode() not in conteudo, \
        "ENT-09 código em texto no banco"
ok("ENT-09 código XXXXX-XXXXX-XXXXX-XXXXX só na ativação, guardado como scrypt, só para administrador e uso único")

# EQP-01 · matriz função × método da ponte (spec 014, decisão 3), conferida no Python
PODE = {
    "administrador": {"ver_viagens", "ver_video", "importar", "decidir", "cadastrar", "equipe", "configuracoes",
                      "atividades"},
    "supervisor": {"ver_viagens", "ver_video", "importar", "decidir", "cadastrar"},
    "consulta": {"ver_viagens"},
}
assert {funcao: set(acoes) for funcao, acoes in contas.PERMISSOES.items()} == PODE, "EQP-01 tabela da decisão 3"
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    destinos = []
    ponte = nova_ponte(tmp, t, destinos)
    dados(ponte.ativar_demonstracao(ADMIN))
    ids = {"supervisor": criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP),
           "consulta": criar_pessoa(ponte, "Ana Souza", "ana.souza", "consulta", SENHA_CON)}
    publicos = {nome for nome in dir(ponte) if not nome.startswith("_")}
    cobertos = {nome for nome, _, _ in chamadas(ids)} | SEM_ACAO
    assert publicos == cobertos, f"EQP-01 método público fora da matriz: {sorted(publicos ^ cobertos)}"
    assert not [nome for nome in vars(ponte) if not nome.startswith("_")], "EQP-01 atributo público exposto ao JavaScript"
    for funcao, usuario, senha, nome in (("administrador", "marina.lopes", SENHA_ADM, "Marina Lopes"),
                                         ("supervisor", "paulo.reis", SENHA_SUP, "Paulo Reis"),
                                         ("consulta", "ana.souza", SENHA_CON, "Ana Souza")):
        entrar_como(ponte, usuario, senha)
        for metodo, acao, args in chamadas(ids):
            antes, dialogos = len(linhas(ponte, "tentou sem permissão")), len(destinos)
            resposta = getattr(ponte, metodo)(*args)
            contexto = f"EQP-01 {funcao} × {metodo} ({acao})"
            if acao in PODE[funcao]:
                assert resposta.get("codigo") not in ("sem_permissao", "sem_sessao", "bloqueado"), f"{contexto}: {resposta}"
                continue
            assert resposta == {"ok": False, "erro": "Sua função não permite fazer isso.", "codigo": "sem_permissao"}, \
                f"{contexto} deveria recusar: {resposta}"
            novas = linhas(ponte, "tentou sem permissão")[antes:]
            assert len(novas) == 1 and novas[0]["alvo"] == acao and novas[0]["usuario"] == nome, \
                f"{contexto} sem a linha 'tentou sem permissão': {[dict(l) for l in novas]}"
            assert len(destinos) == dialogos, f"{contexto} abriu o diálogo de salvar sem permissão"
    assert not ponte._falhas, f"EQP-01 falha interna: {ponte._falhas}"
    fechar(ponte)
ok("EQP-01 administrador, supervisor e consulta × 28 métodos que exigem ação: permitido passa, sem permissão devolve "
   "sem_permissao e registra 'tentou sem permissão'; nenhum método público fora da matriz")

# EQP-03 · ninguém é apagado; desativar mantém o nome nas revisões; o último administrador ativo fica
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    admin_id = dados(ponte.estado())["sessao"]["id"]
    apagar = [nome for nome in dir(ponte) if any(p in nome for p in ("apagar", "excluir", "remover", "deletar"))]
    assert apagar == [], f"EQP-03 a ponte não tem como apagar: {apagar}"
    for mudanca, campo in (({"ativo": False}, "ativo"), ({"funcao": "supervisor"}, "funcao"),
                           ({"funcao": "consulta", "ativo": False}, "funcao")):
        resposta = erro(ponte.equipe_alterar(admin_id, mudanca), "conflito", f"EQP-03 último administrador {mudanca}")
        assert resposta["erro"] == contas.MENSAGEM_ULTIMO_ADMIN and resposta["campo"] == campo, f"EQP-03 {resposta}"
    supervisor_id = criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    entrar_como(ponte, "paulo.reis", SENHA_SUP)
    dados(ponte.decisao_registrar("v-2240-e-001", "confirmado"))
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    assert dados(ponte.equipe_alterar(supervisor_id, {"ativo": False}))["ativo"] is False, "EQP-03 desativou"
    equipe = {pessoa["usuario"]: pessoa for pessoa in dados(ponte.equipe_listar())}
    assert contar(ponte, "usuarios") == 2 and equipe["paulo.reis"]["ativo"] is False, "EQP-03 desativado continua"
    revisao = [d for d in dados(ponte.decisoes_listar()) if d["momento_id"] == "v-2240-e-001"]
    assert revisao and revisao[0]["por"] == "Paulo Reis" and revisao[0]["funcao"] == "supervisor", \
        f"EQP-03 o nome continua na revisão: {revisao}"
    desativou = linhas(ponte, "desativou acesso")
    assert len(desativou) == 1 and desativou[0]["alvo"] == "paulo.reis" and desativou[0]["usuario"] == "Marina Lopes"
    rita_id = criar_pessoa(ponte, "Rita Alves", "rita.alves", "administrador", "frase comprida de teste quatro")
    dados(ponte.equipe_alterar(admin_id, {"funcao": "supervisor"}), "EQP-03 com outro administrador dá para rebaixar")
    entrar_como(ponte, "rita.alves", "frase comprida de teste quatro")
    erro(ponte.equipe_alterar(rita_id, {"ativo": False}), "conflito", "EQP-03 a nova última administradora fica")
    assert dados(ponte.equipe_alterar(supervisor_id, {"ativo": True}))["ativo"] is True and \
        linhas(ponte, "reativou acesso"), "EQP-03 desativado pode voltar"
    fechar(ponte)
ok("EQP-03 ponte sem método de apagar; desativado continua na equipe e nas revisões; último administrador ativo não "
   "é desativado nem rebaixado")

# EQP-04 · decisão de momento grava nome e função de quem entrou
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    entrar_como(ponte, "paulo.reis", SENHA_SUP)
    t[0] += 60
    decisao = dados(ponte.decisao_registrar("v-2240-e-001", "confirmado"))
    assert decisao == {"momento_id": "v-2240-e-001", "resultado": "confirmado", "orientado": False, "por": "Paulo Reis",
                       "funcao": "supervisor", "em": iso_utc(t[0])}, f"EQP-04 decisão do supervisor: {decisao}"
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    t[0] += 60
    orientada = dados(ponte.decisao_orientado("v-2240-e-001", True))
    assert (orientada["por"], orientada["funcao"], orientada["orientado"], orientada["resultado"], orientada["em"]) == \
        ("Marina Lopes", "administrador", True, "confirmado", iso_utc(t[0])), f"EQP-04 orientação: {orientada}"
    historico = ponte._n().banco.todos("SELECT por, funcao, ativa FROM decisoes WHERE momento_id = ? ORDER BY id",
                                       ("v-2240-e-001",))
    assert [tuple(l) for l in historico] == [("Paulo Reis", "supervisor", 0), ("Marina Lopes", "administrador", 1)], \
        f"EQP-04 a decisão anterior fica no banco: {[tuple(l) for l in historico]}"
    assert erro(ponte.decisao_registrar("v-2240-e-001", "talvez"), "invalido")["campo"] == "resultado", "EQP-04"
    assert erro(ponte.decisao_registrar("../x y", "confirmado"), "invalido")["campo"] == "momento_id", "EQP-04"
    assert erro(ponte.decisao_orientado("v-2240-e-001", "sim"), "invalido")["campo"] == "orientado", "EQP-04"
    # Orientação só em momento confirmado (spec 012: "depois de confirmar, dá para registrar se o motorista foi orientado").
    falso = dados(ponte.decisao_registrar("v-2240-e-001", "alarme_falso"))
    assert falso["orientado"] is False, f"EQP-04 alarme falso não herda a orientação do confirmado: {falso}"
    recusa = erro(ponte.decisao_orientado("v-2240-e-001", True), "conflito", "EQP-04 orientação em alarme falso")
    assert "confirmado" in recusa["erro"], f"EQP-04 frase da recusa: {recusa}"
    dados(ponte.decisao_desfazer("v-2240-e-001"))
    assert "v-2240-e-001" not in [d["momento_id"] for d in dados(ponte.decisoes_listar())], "EQP-04 desfeita some"
    erro(ponte.decisao_desfazer("v-2240-e-001"), "nao_encontrado", "EQP-04 desfazer de novo")
    fechar(ponte)
ok("EQP-04 decisão e orientação com nome, função e hora de quem entrou; anterior fica inativa no banco; orientação só "
   "em momento confirmado; desfazer tira")


def ponte_na_pasta(pasta, relogio):
    return Ponte(pasta, relogio=lambda: relogio[0], custo_scrypt=CUSTO_TESTE, escolher_destino=lambda nome: None,
                 script_local=ScriptFalso())


# ATV-01 · registro só acrescenta, cada linha com o hash da anterior; alterar ou apagar é detectado
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    banco = ponte._n().banco
    for sql in ("UPDATE atividades SET acao = 'nada' WHERE id = 1", "DELETE FROM atividades WHERE id = 1"):
        try:
            banco.executar(sql)
        except sqlite3.DatabaseError as falha:
            assert "só acrescenta" in str(falha), f"ATV-01 mensagem do gatilho: {falha}"
        else:
            raise AssertionError(f"ATV-01 o gatilho deixou passar: {sql}")
    anterior = atv.GENESE
    for linha in linhas(ponte):
        assert linha["hash_anterior"] == anterior and re.fullmatch(r"[0-9a-f]{64}", linha["hash"]), \
            f"ATV-01 corrente quebrada na linha {linha['id']}"
        anterior = linha["hash"]
    assert dados(ponte.atividades_listar({}))["integro"] is True, "ATV-01 registro íntegro"
    fechar(ponte)
    original = Path(tmp) / "dados" / "painel.db"

    def copia_mexida(nome, *comandos):
        pasta = Path(tmp) / nome
        pasta.mkdir()
        shutil.copy(original, pasta / "painel.db")
        mexido = Banco(pasta)
        for comando in ("DROP TRIGGER atividades_sem_alterar", "DROP TRIGGER atividades_sem_apagar", *comandos):
            mexido.executar(comando)
        return mexido

    ultima = "DELETE FROM atividades WHERE id = (SELECT MAX(id) FROM atividades)"
    for nome, comando in (("alterar", "UPDATE atividades SET detalhe = 'outra coisa' WHERE id = 2"),
                          ("trocar-quem", "UPDATE atividades SET usuario = 'Outra Pessoa' WHERE id = 3"),
                          ("apagar-meio", "DELETE FROM atividades WHERE id = 2"),
                          ("apagar-ultima", ultima),
                          ("apagar-meta", "DELETE FROM meta WHERE chave = 'atividades_ultimo'")):
        mexido = copia_mexida(nome, comando)
        assert atv.Atividades(mexido).verificar() is False, f"ATV-01 '{nome}' com os gatilhos removidos não foi detectado"
        mexido.fechar()
    for nome, comando in (("apagar-ultima-e-entrar", ultima),
                          ("apagar-meta-e-entrar", "DELETE FROM meta WHERE chave = 'atividades_ultimo'")):
        copia_mexida(nome, comando).fechar()
        depois = ponte_na_pasta(Path(tmp) / nome, t)
        dados(depois.entrar("marina.lopes", SENHA_ADM), f"ATV-01 {nome}")
        dados(depois.sair())
        dados(depois.entrar("marina.lopes", SENHA_ADM), f"ATV-01 {nome}")
        assert dados(depois.atividades_listar({}))["integro"] is False, \
            f"ATV-01 '{nome}': a atividade seguinte escondeu a linha apagada"
        fechar(depois)
ok("ATV-01 gatilhos recusam UPDATE e DELETE; corrente de hash desde a gênese; sem os gatilhos, alterar, trocar quem, "
   "apagar do meio, apagar a última ou a meta é detectado, mesmo depois de novas atividades")


def conferir_linha(ponte, t, acao, usuario, alvo=None, detalhe=None):
    achadas = linhas(ponte, acao)
    assert achadas, f"ATV-02 falta a linha '{acao}'"
    linha = achadas[-1]
    assert linha["usuario"] == usuario and linha["em"] == iso_utc(t[0]), \
        f"ATV-02 '{acao}' sem quem ou quando: {dict(linha)}"
    assert alvo is None or linha["alvo"] == alvo, f"ATV-02 '{acao}' em quê: {linha['alvo']!r} × {alvo!r}"
    assert detalhe is None or linha["detalhe"] == detalhe, f"ATV-02 '{acao}' detalhe: {linha['detalhe']!r}"
    return linha


MOTORISTA_NOVO = {"nome": "Pedro Santos", "matricula": "0999", "cnh_numero": "12345678900", "cnh_categoria": "D",
                  "cnh_validade": "2030-01-01", "situacao": "ativo", "cpf": None, "telefone": None,
                  "observacoes": None, "termo": {"assinado": False, "data": None, "versao": None}}

# ATV-02 · as ações da decisão 11 geram linha com quem, quando, o quê e em quê
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    supervisor_id = criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    marina = "Marina Lopes"

    def passo():
        t[0] += 60

    passo(); dados(ponte.sair()); conferir_linha(ponte, t, "saiu", marina)
    passo(); ponte.entrar("marina.lopes", SENHA_ERRADA); conferir_linha(ponte, t, "errou a senha", marina, "marina.lopes")
    passo(); dados(ponte.entrar("marina.lopes", SENHA_ADM)); conferir_linha(ponte, t, "entrou", marina)
    passo(); dados(ponte.bloquear()); conferir_linha(ponte, t, "bloqueou a tela", marina)
    dados(ponte.desbloquear(SENHA_ADM))
    passo(); dados(ponte.video_abrir("v-1187-e-202", "m-01")); conferir_linha(ponte, t, "abriu vídeo", marina, "v-1187-e-202")
    passo(); dados(ponte.decisao_registrar("v-2240-e-001", "confirmado"))
    conferir_linha(ponte, t, "confirmou momento", marina, "v-2240-e-001")
    passo(); dados(ponte.decisao_registrar("v-2240-e-002", "alarme_falso"))
    conferir_linha(ponte, t, "marcou alarme falso", marina, "v-2240-e-002")
    passo(); dados(ponte.decisao_orientado("v-2240-e-001", True))
    conferir_linha(ponte, t, "registrou orientação", marina, "v-2240-e-001")
    passo(); dados(ponte.decisao_desfazer("v-2240-e-002"))
    conferir_linha(ponte, t, "desfez decisão", marina, "v-2240-e-002", "alarme_falso")
    passo(); motorista = dados(ponte.motorista_salvar(MOTORISTA_NOVO))
    conferir_linha(ponte, t, "cadastrou motorista", marina, "Pedro S. (matrícula 0999)")
    passo(); dados(ponte.motorista_salvar({**MOTORISTA_NOVO, "id": motorista["id"], "telefone": "(11) 90000-0000"}))
    conferir_linha(ponte, t, "editou motorista", marina, "Pedro S. (matrícula 0999)", "campos: telefone")
    veiculo_novo = {"numero": "4001", "placa": "ABC1D23", "tipo": "van", "transporta": "passageiros"}
    passo(); veiculo = dados(ponte.veiculo_salvar(veiculo_novo))
    conferir_linha(ponte, t, "cadastrou veículo", marina, "Veículo 4001")
    passo(); dados(ponte.veiculo_salvar({**veiculo_novo, "id": veiculo["id"], "situacao": "oficina"}))
    conferir_linha(ponte, t, "editou veículo", marina, "Veículo 4001", "campos: situacao")
    passo(); dados(ponte.equipe_alterar(supervisor_id, {"ativo": False}))
    conferir_linha(ponte, t, "desativou acesso", marina, "paulo.reis")
    passo(); dados(ponte.config_salvar("regras", {"direcao_continua_min": 300}))
    conferir_linha(ponte, t, "mudou configuração", marina, "regras.direcao_continua_min", "5 h 30 → 5 h")
    passo(); copia_feita = dados(ponte.copia_fazer(SENHA_COPIA))
    conferir_linha(ponte, t, "fez cópia de segurança", marina, Path(copia_feita["caminho"]).name)
    passo(); exportado = dados(ponte.atividades_exportar())
    conferir_linha(ponte, t, "exportou registro de atividades", marina, Path(exportado["caminho"]).name)
    passo(); dados(ponte.motorista_exportar(motorista["id"]))
    conferir_linha(ponte, t, "exportou dados do motorista", marina, "Pedro S.")
    itens = dados(ponte.atividades_listar({}))["itens"]
    assert all(set(item) == {"id", "em", "usuario", "acao", "alvo", "detalhe"} for item in itens), "ATV-02 formato"
    assert itens[0]["acao"] == "exportou dados do motorista", "ATV-02 lista do mais novo para o mais velho"
    do_paulo = dados(ponte.atividades_listar({"usuario_id": supervisor_id}))["itens"]
    assert do_paulo and {item["usuario"] for item in do_paulo} == {"Paulo Reis"}, "ATV-02 filtro por pessoa"
    assert len(dados(ponte.atividades_listar({"de": "2026-09-14", "ate": "2026-09-14"}))["itens"]) == len(itens)
    assert dados(ponte.atividades_listar({"de": "2026-09-15"}))["itens"] == [], "ATV-02 filtro por data"
    erro(ponte.atividades_listar({"usuario_id": "x"}), "invalido", "ATV-02 filtro inválido")
    fechar(ponte)
ok("ATV-02 entrou, errou a senha, saiu, bloqueou, abriu vídeo, confirmou, alarme falso, orientação, desfez, "
   "cadastrou, editou, desativou, mudou configuração, cópia e exportações com quem, quando e em quê; filtros")

# ATV-03 · exportação CSV do registro, só para o administrador, também registrada
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    destinos = []
    ponte = nova_ponte(tmp, t, destinos)
    dados(ponte.ativar_demonstracao(ADMIN))
    criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    entrar_como(ponte, "paulo.reis", SENHA_SUP)
    erro(ponte.atividades_exportar(), "sem_permissao", "ATV-03 supervisor não exporta")
    assert destinos == [], "ATV-03 sem permissão nem abre o diálogo"
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    caminho = Path(dados(ponte.atividades_exportar())["caminho"])
    assert caminho == Path(tmp) / "rotaguard-atividades-2026-09-14.csv" and destinos == [caminho.name], caminho
    bruto = caminho.read_bytes()
    assert bruto.startswith(b"\xef\xbb\xbf"), "ATV-03 CSV com BOM para abrir no Excel"
    tabela = list(csv.reader(io.StringIO(bruto.decode("utf-8-sig")), delimiter=";"))
    assert tabela[0] == ["id", "quando (UTC)", "quem", "o quê", "em quê", "detalhe", "hash"], tabela[0]
    assert len(tabela) - 1 == contar(ponte, "atividades"), "ATV-03 todas as linhas no CSV"
    assert tabela[-1][2:5] == ["Marina Lopes", "exportou registro de atividades", caminho.name], \
        f"ATV-03 a exportação entra no registro e no próprio CSV: {tabela[-1]}"
    antes = contar(ponte, "atividades")
    ponte._escolher_destino_injetado = lambda nome: None
    cancelada = erro(ponte.atividades_exportar(), "invalido", "ATV-03 diálogo cancelado")
    assert cancelada["erro"] == "Nada foi salvo." and contar(ponte, "atividades") == antes, "ATV-03 cancelar não grava"
    fechar(ponte)
ok("ATV-03 CSV com BOM, ';' e cabeçalho, com todas as linhas e a própria exportação; supervisor recusado sem diálogo; "
   "cancelar não grava")

# INI-01 · inicio_resumo: última cópia, dias desde a cópia e Primeiros passos escondidos (BKP-03, spec 017)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    erro(ponte.inicio_resumo(), "sem_sessao", "INI-01 sem sessão")
    dados(ponte.ativar_demonstracao(ADMIN))
    resumo = dados(ponte.inicio_resumo())
    assert list(resumo) == ["ultima_copia_em", "dias_desde_copia", "primeiros_passos_escondidos"], f"INI-01 {resumo}"
    assert resumo == {"ultima_copia_em": None, "dias_desde_copia": None, "primeiros_passos_escondidos": False}, \
        f"INI-01 sem cópia: {resumo}"
    t[0] += 60  # menos que o bloqueio de 15 min
    dados(ponte.copia_fazer(SENHA_COPIA))
    copia_em = iso_utc(t[0])
    assert dados(ponte.inicio_resumo())["ultima_copia_em"] == copia_em and \
        dados(ponte.inicio_resumo())["dias_desde_copia"] == 0, "INI-01 cópia de agora"
    criar_pessoa(ponte, "Ana Souza", "ana.souza", "consulta", SENHA_CON)
    for passado, dias in ((7 * 86400 + 23 * 3600, 7), (8 * 86400, 8), (40 * 86400, 40)):
        t[0] = T0 + 60 + passado
        entrar_como(ponte, "ana.souza", SENHA_CON)
        resumo = dados(ponte.inicio_resumo(), "INI-01 consulta vê o resumo")
        assert resumo["dias_desde_copia"] == dias and resumo["ultima_copia_em"] == copia_em, \
            f"INI-01 dias inteiros pelo relógio: {resumo} × {dias}"
    fechar(ponte)
ok("INI-01 inicio_resumo exige sessão; sem cópia nulos; depois da cópia conta dias inteiros pelo relógio (7 d 23 h = 7)")

# INI-02 · primeiros_passos_esconder: só administrador, bool, grava na meta e registra
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    criar_pessoa(ponte, "Ana Souza", "ana.souza", "consulta", SENHA_CON)
    for valor in ("sim", 1, None):
        assert erro(ponte.primeiros_passos_esconder(valor), "invalido", f"INI-02 {valor!r}")["campo"] == "esconder"
    assert not linhas(ponte, "escondeu primeiros passos"), "INI-02 valor inválido não registra"
    t[0] += 60
    assert dados(ponte.primeiros_passos_esconder(True)) == {"primeiros_passos_escondidos": True}, "INI-02 esconder"
    conferir_linha(ponte, t, "escondeu primeiros passos", "Marina Lopes")
    assert ponte._n().banco.meta_ler("primeiros_passos_escondidos") == "1", "INI-02 gravado na meta"
    entrar_como(ponte, "ana.souza", SENHA_CON)
    assert dados(ponte.inicio_resumo())["primeiros_passos_escondidos"] is True, "INI-02 vale para todos"
    erro(ponte.primeiros_passos_esconder(False), "sem_permissao", "INI-02 consulta não mexe")
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    t[0] += 60
    assert dados(ponte.primeiros_passos_esconder(False)) == {"primeiros_passos_escondidos": False}, "INI-02 mostrar"
    conferir_linha(ponte, t, "mostrou primeiros passos", "Marina Lopes")
    dados(ponte.primeiros_passos_esconder(True))
    fechar(ponte)
    reaberta = nova_ponte(tmp, t)
    dados(reaberta.entrar("marina.lopes", SENHA_ADM))
    assert dados(reaberta.inicio_resumo())["primeiros_passos_escondidos"] is True, "INI-02 continua depois de reabrir"
    fechar(reaberta)
ok("INI-02 primeiros_passos_esconder só com bool e só administrador; grava na meta, registra esconder e mostrar, "
   "e continua depois de reabrir")

# CFG-09 (ponte) · estado() leva texto_maior, na ordem do contrato, para qualquer função
ORDEM_ESTADO = ["ativado", "modo", "empresa", "sessao", "bloqueado", "versao", "bloqueio_min", "texto_maior", "tema",
                "preferencias", "videos_dias"]  # spec 019 acrescenta os três últimos, nesta ordem
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    estado = dados(ponte.estado())
    assert list(estado) == ORDEM_ESTADO and estado["texto_maior"] is False, f"CFG-09 sem ativação: {estado}"
    dados(ponte.ativar_demonstracao(ADMIN))
    estado = dados(ponte.estado())
    assert list(estado) == ORDEM_ESTADO and estado["texto_maior"] is False, f"CFG-09 padrão: {estado}"
    dados(ponte.config_salvar("aparencia", {"texto_maior": True}))
    criar_pessoa(ponte, "Ana Souza", "ana.souza", "consulta", SENHA_CON)
    entrar_como(ponte, "ana.souza", SENHA_CON)
    assert dados(ponte.estado())["texto_maior"] is True, "CFG-09 consulta recebe texto maior pelo estado"
    erro(ponte.config_ler(), "sem_permissao", "CFG-09 consulta não precisa ler as configurações")
    fechar(ponte)
ok("CFG-09 (ponte) estado() com texto_maior na ordem do contrato: false sem ativação, true depois de ligar, para todos")

print(f"\n{checks} verificações OK")
