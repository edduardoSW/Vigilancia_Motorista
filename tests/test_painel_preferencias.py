"""Spec 019: preferências por pessoa (tema e lista ou cards) e o tema antes de entrar (núcleo Python).

Sem janela e sem pywebview: a Ponte é chamada direto, com relógio falso, scrypt barato, pasta temporária e script local
falso. Só biblioteca padrão:
    python tests/test_painel_preferencias.py
"""
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
from dados import iso_utc  # noqa: E402
from ponte import Ponte  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc).timestamp()
# Senhas descartáveis, só deste teste.
SENHA_ADM = "frase comprida de teste um"
SENHA_SUP = "frase comprida de teste dois"
SENHA_CON = "frase comprida de teste tres"
SENHA_NOVA = "frase comprida de teste quatro"
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}
TELAS = ["viagens", "momentos", "motoristas", "veiculos", "caixas", "equipe"]
PADRAO = {"tema": "claro", "visao": {tela: "cards" for tela in TELAS}}
ORDEM_ESTADO = ["ativado", "modo", "empresa", "sessao", "bloqueado", "versao", "bloqueio_min", "texto_maior", "tema",
                "preferencias", "videos_dias"]


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


def nova_ponte(tmp, relogio):
    return Ponte(Path(tmp) / "dados", relogio=lambda: relogio[0], custo_scrypt=CUSTO_TESTE,
                 escolher_destino=lambda nome: Path(tmp) / nome, script_local=ScriptFalso())


def dados(resposta, contexto=""):
    assert resposta["ok"] is True, (contexto, resposta)
    return resposta["dados"]


def erro(resposta, codigo, contexto=""):
    assert resposta["ok"] is False and resposta.get("codigo") == codigo, (contexto, resposta)
    return resposta


def linhas(ponte):
    return ponte._n().banco.todos("SELECT * FROM atividades ORDER BY id")


def contar(ponte, tabela):
    return ponte._n().banco.um(f"SELECT COUNT(*) AS n FROM {tabela}")["n"]


def fechar(*pontes):
    for ponte in pontes:
        if ponte._nucleo is not None:
            ponte._n().banco.fechar()


def entrar_como(ponte, usuario, senha):
    ponte.sair()
    return dados(ponte.entrar(usuario, senha), usuario)


def pronta(tmp, relogio):
    """Demonstração ativada, com supervisor e consulta criados; volta com a administradora na sessão."""
    ponte = nova_ponte(tmp, relogio)
    dados(ponte.ativar_demonstracao(ADMIN), "ativar demonstração")
    for nome, usuario, funcao, senha in (("Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP),
                                         ("Ana Souza", "ana.souza", "consulta", SENHA_CON)):
        entrar_como(ponte, "marina.lopes", SENHA_ADM)
        novo = dados(ponte.equipe_adicionar({"nome": nome, "usuario": usuario, "funcao": funcao}), usuario)
        entrar_como(ponte, usuario, novo["senha_temporaria"])
        dados(ponte.trocar_senha(novo["senha_temporaria"], senha), usuario)
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    return ponte


def visao(**mudar):
    return {**PADRAO["visao"], **mudar}


# PRF-01 · preferencias_salvar aceita só os valores do contrato, vale para qualquer função e não aparece para outra pessoa
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    vazia = nova_ponte(Path(tmp) / "vazia", t)
    erro(vazia.preferencias_salvar({"tema": "escuro"}), "sem_sessao", "PRF-01 sem ativação")
    fechar(vazia)
    ponte = pronta(tmp, t)
    banco = ponte._n().banco
    registro_antes = len(linhas(ponte))
    ruins = [({"tema": "azul"}, "tema"), ({"tema": None}, "tema"), ({"tema": 1}, "tema"), ({"tema": "Escuro"}, "tema"),
             ({"tema": ["escuro"]}, "tema"), ({"visao": "cards"}, "visao"), ({"visao": None}, "visao"),
             ({"visao": ["lista"]}, "visao"), ({"visao": {"mapa": "lista"}}, "visao.mapa"),
             ({"visao": {"atividades": "cards"}}, "visao.atividades"),
             ({"visao": {"motoristas": "grade"}}, "visao.motoristas"),
             ({"visao": {"motoristas": None}}, "visao.motoristas"), ({"visao": {"equipe": True}}, "visao.equipe"),
             ({"cor": "verde"}, "cor"), ({"tema": "escuro", "texto_maior": True}, "texto_maior"),
             ({"tema": "escuro", "visao": {"viagens": "lista", "caixas": "tabela"}}, "visao.caixas")]
    for valores, campo in ruins:
        resposta = erro(ponte.preferencias_salvar(valores), "invalido", f"PRF-01 {valores!r}")
        assert resposta.get("campo") == campo, f"PRF-01 campo de {valores!r}: {resposta}"
    for valores in ("escuro", None, ["tema"], 3):
        erro(ponte.preferencias_salvar(valores), "invalido", f"PRF-01 valores que não são objeto: {valores!r}")
    assert dados(ponte.estado())["preferencias"] == PADRAO, "PRF-01 recusado não muda nada, nem em parte"
    assert banco.meta_ler("tema_ultimo") is None and contar(ponte, "preferencias") == 0, "PRF-01 recusado não grava"
    escuro = dados(ponte.preferencias_salvar({"tema": "escuro"}), "PRF-01 tema escuro")
    assert escuro == {"tema": "escuro", "visao": PADRAO["visao"]}, f"PRF-01 devolve as preferências completas: {escuro}"
    assert list(escuro) == ["tema", "visao"] and list(escuro["visao"]) == TELAS, f"PRF-01 ordem do contrato: {escuro}"
    parcial = dados(ponte.preferencias_salvar({"visao": {"motoristas": "lista", "equipe": "lista"}}))
    assert parcial == {"tema": "escuro", "visao": visao(motoristas="lista", equipe="lista")}, \
        f"PRF-01 visão parcial mantém o resto: {parcial}"
    for tema in ("claro", "sistema", "escuro"):
        assert dados(ponte.preferencias_salvar({"tema": tema}))["tema"] == tema, f"PRF-01 tema {tema}"
    for tela in TELAS:
        for escolha in ("lista", "cards", "lista"):
            salvo = dados(ponte.preferencias_salvar({"visao": {tela: escolha}}), f"PRF-01 {tela} {escolha}")
            assert salvo["visao"][tela] == escolha, f"PRF-01 {tela} {escolha}: {salvo}"
    da_marina = {"tema": "escuro", "visao": {tela: "lista" for tela in TELAS}}
    assert dados(ponte.preferencias_salvar({})) == da_marina, "PRF-01 objeto vazio devolve as preferências sem mudar"
    for usuario, senha, funcao in (("paulo.reis", SENHA_SUP, "supervisor"), ("ana.souza", SENHA_CON, "consulta")):
        entrar_como(ponte, usuario, senha)
        assert dados(ponte.estado())["preferencias"] == PADRAO, f"PRF-01 {funcao} não vê a preferência da Marina"
        salvo = dados(ponte.preferencias_salvar({"tema": "sistema", "visao": {"viagens": "lista"}}), f"PRF-01 {funcao}")
        assert salvo == {"tema": "sistema", "visao": visao(viagens="lista")}, f"PRF-01 {funcao} salva: {salvo}"
    dados(ponte.bloquear())
    erro(ponte.preferencias_salvar({"tema": "claro"}), "bloqueado", "PRF-01 tela bloqueada")
    dados(ponte.desbloquear(SENHA_CON))
    assert dados(ponte.estado())["preferencias"]["tema"] == "sistema", "PRF-01 bloqueada não salvou"
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    assert dados(ponte.estado())["preferencias"] == da_marina, "PRF-01 as outras pessoas não mexeram na da Marina"
    temporaria = dados(ponte.equipe_adicionar({"nome": "Rita Alves", "usuario": "rita.alves", "funcao": "consulta"}))
    entrar_como(ponte, "rita.alves", temporaria["senha_temporaria"])
    pendente = erro(ponte.preferencias_salvar({"tema": "escuro"}), "sem_permissao", "PRF-01 senha temporária")
    assert pendente["campo"] == "nova", f"PRF-01 senha temporária pede a troca antes: {pendente}"
    dados(ponte.trocar_senha(temporaria["senha_temporaria"], SENHA_NOVA))
    assert dados(ponte.preferencias_salvar({"tema": "escuro"}))["tema"] == "escuro", "PRF-01 depois de trocar a senha"
    acoes = {l["acao"] for l in linhas(ponte)[registro_antes:]}
    assert acoes <= {"entrou", "saiu", "bloqueou a tela", "desbloqueou a tela", "adicionou pessoa à equipe",
                     "trocou a senha"}, f"PRF-01 preferência não vai para o registro de atividades: {acoes}"
    assert not ponte._falhas, f"PRF-01 falha interna: {ponte._falhas}"
    fechar(ponte)
ok("PRF-01 recusa tema, visão, tela e chave fora do contrato com campo (tema, visao, visao.<tela>) sem gravar nada; "
   "aceita parcial e devolve tudo; administrador, supervisor e consulta salvam; bloqueada recusa; sem linha no registro; "
   "uma pessoa não vê a preferência da outra")

# VIS-02 · visão e tema guardados por pessoa, pela ponte, no banco do painel (sobrevivem a fechar e abrir)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    banco = ponte._n().banco
    marina_id = dados(ponte.estado())["sessao"]["id"]
    t[0] += 60
    dados(ponte.preferencias_salvar({"tema": "escuro", "visao": {"motoristas": "lista"}}))
    primeira = banco.um("SELECT * FROM preferencias WHERE usuario_id = ?", (marina_id,))
    assert len(primeira["uid"]) == 32 and primeira["criado_em"] == primeira["alterado_em"] == iso_utc(t[0]), \
        f"VIS-02 registro com uid, criado_em e alterado_em: {dict(primeira)}"
    assert json.loads(primeira["valores"]) == {"tema": "escuro", "visao": visao(motoristas="lista")}, \
        f"VIS-02 valores guardados: {primeira['valores']}"
    t[0] += 60
    dados(ponte.preferencias_salvar({"visao": {"viagens": "lista"}}))
    segunda = banco.um("SELECT * FROM preferencias WHERE usuario_id = ?", (marina_id,))
    assert (segunda["uid"], segunda["criado_em"], segunda["alterado_em"]) == \
        (primeira["uid"], primeira["criado_em"], iso_utc(t[0])), f"VIS-02 salvar de novo altera o mesmo: {dict(segunda)}"
    assert contar(ponte, "preferencias") == 1, "VIS-02 uma linha por pessoa"
    entrar_como(ponte, "paulo.reis", SENHA_SUP)
    dados(ponte.preferencias_salvar({"visao": {"caixas": "lista"}}))
    fechar(ponte)
    reaberta = nova_ponte(tmp, t)
    assert dados(reaberta.estado())["preferencias"] is None, "VIS-02 sem sessão não há preferências de pessoa"
    dados(reaberta.entrar("marina.lopes", SENHA_ADM))
    assert dados(reaberta.estado())["preferencias"] == {"tema": "escuro", "visao": visao(motoristas="lista",
                                                                                         viagens="lista")}, \
        "VIS-02 a escolha da Marina continua depois de fechar e abrir"
    entrar_como(reaberta, "paulo.reis", SENHA_SUP)
    assert dados(reaberta.estado())["preferencias"] == {"tema": "claro", "visao": visao(caixas="lista")}, \
        "VIS-02 a do Paulo continua e é só dele"
    entrar_como(reaberta, "ana.souza", SENHA_CON)
    assert dados(reaberta.estado())["preferencias"] == PADRAO, "VIS-02 quem nunca escolheu fica no padrão"
    rbanco = reaberta._n().banco
    paulo_id = rbanco.um("SELECT id FROM usuarios WHERE usuario = 'paulo.reis'")["id"]
    for guardado, esperado in (("não é json", PADRAO), ("[1, 2]", PADRAO),
                               ('{"tema": "roxo", "visao": {"motoristas": "grade", "viagens": "lista", "mapa": 1}}',
                                {"tema": "claro", "visao": visao(viagens="lista")})):
        rbanco.executar("UPDATE preferencias SET valores = ? WHERE usuario_id = ?", (guardado, paulo_id))
        entrar_como(reaberta, "paulo.reis", SENHA_SUP)
        assert dados(reaberta.estado())["preferencias"] == esperado, \
            f"VIS-02 valor estragado no banco não derruba o estado: {guardado!r}"
    assert dados(reaberta.preferencias_salvar({"tema": "escuro"})) == {"tema": "escuro", "visao": visao(viagens="lista")}, \
        "VIS-02 salvar por cima de valor com parte estragada mantém a parte boa"

    def guardado_do_paulo():
        return rbanco.um("SELECT valores FROM preferencias WHERE usuario_id = ?", (paulo_id,))["valores"]

    assert json.loads(guardado_do_paulo()) == {"tema": "escuro", "visao": visao(viagens="lista")}, "VIS-02 regravado"
    rbanco.executar("UPDATE preferencias SET valores = 'não é json' WHERE usuario_id = ?", (paulo_id,))
    assert dados(reaberta.preferencias_salvar({"visao": {"viagens": "cards"}})) == PADRAO, "VIS-02 salvar o padrão"
    assert json.loads(guardado_do_paulo()) == PADRAO, \
        "VIS-02 salvar valor igual ao padrão por cima de JSON estragado regrava a linha"
    fechar(reaberta)
    assert sorted(c.name for c in (Path(tmp) / "dados").iterdir()) == ["painel.db"], \
        "VIS-02 nada fora do banco do painel (sem arquivo de preferência)"
ok("VIS-02 preferências numa linha por pessoa (uid, criado_em, alterado_em), só no banco; continuam depois de fechar e "
   "abrir; quem nunca escolheu fica no padrão; valor estragado no banco volta ao padrão sem derrubar o estado")

# ESC-01 (ponte) · tema claro, escuro ou do sistema por pessoa; sem sessão, o último salvo neste computador
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    antes = nova_ponte(tmp, t)
    estado = dados(antes.estado())
    assert list(estado) == ORDEM_ESTADO, f"ESC-01 ordem do estado sem ativação: {list(estado)}"
    assert (estado["tema"], estado["preferencias"], estado["videos_dias"]) == ("claro", None, 30), \
        f"ESC-01 sem ativação: claro, sem preferências e 30 dias: {estado}"
    fechar(antes)
    ponte = pronta(tmp, t)
    banco = ponte._n().banco
    estado = dados(ponte.estado())
    assert list(estado) == ORDEM_ESTADO and estado["tema"] == "claro" and estado["preferencias"] == PADRAO, \
        f"ESC-01 padrão com sessão: {estado}"
    dados(ponte.preferencias_salvar({"tema": "escuro"}))
    assert dados(ponte.estado())["tema"] == "escuro" and banco.meta_ler("tema_ultimo") == "escuro", \
        "ESC-01 tema da pessoa no estado e na meta tema_ultimo"
    dados(ponte.sair())
    estado = dados(ponte.estado())
    assert (estado["sessao"], estado["tema"], estado["preferencias"]) == (None, "escuro", None), \
        f"ESC-01 sem sessão vale o último tema salvo neste computador: {estado}"
    dados(ponte.entrar("paulo.reis", SENHA_SUP))
    assert dados(ponte.estado())["tema"] == "claro", "ESC-01 com sessão vale o tema da pessoa, não o do computador"
    dados(ponte.preferencias_salvar({"visao": {"viagens": "lista"}}))
    assert banco.meta_ler("tema_ultimo") == "escuro", "ESC-01 salvar só a visão não muda o último tema"
    dados(ponte.preferencias_salvar({"tema": "sistema"}))
    dados(ponte.sair())
    assert dados(ponte.estado())["tema"] == "sistema", "ESC-01 igual ao Windows fica como último tema"
    dados(ponte.entrar("marina.lopes", SENHA_ADM))
    dados(ponte.bloquear())
    estado = dados(ponte.estado())
    assert estado["bloqueado"] is True and estado["tema"] == "escuro" and estado["preferencias"]["tema"] == "escuro", \
        f"ESC-01 tela bloqueada continua no tema de quem entrou: {estado}"
    dados(ponte.desbloquear(SENHA_ADM))
    dados(ponte.config_salvar("guarda", {"videos_dias": 60}))
    entrar_como(ponte, "ana.souza", SENHA_CON)
    assert dados(ponte.estado())["videos_dias"] == 60, "ESC-01 videos_dias das configurações também para a consulta"
    dados(ponte.sair())
    fechar(ponte)
    reaberta = nova_ponte(tmp, t)
    estado = dados(reaberta.estado())
    assert (estado["tema"], estado["preferencias"], estado["videos_dias"]) == ("sistema", None, 60), \
        f"ESC-01 ao abrir de novo, antes de entrar: {estado}"
    reaberta._n().banco.meta_gravar("tema_ultimo", "roxo")
    assert dados(reaberta.estado())["tema"] == "claro", "ESC-01 valor estranho na meta volta ao claro"
    fechar(reaberta)
ok("ESC-01 (ponte) estado() termina com tema, preferencias e videos_dias; sem ativação claro/None/30; com sessão o tema "
   "da pessoa (também bloqueada); sem sessão o último salvo neste computador, também depois de abrir de novo")

print(f"\n{checks} verificações OK")
