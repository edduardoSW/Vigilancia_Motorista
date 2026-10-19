"""Spec 030: painel sem dados fictícios (SDF-05 a SDF-10, lado do Python).

Sem janela e sem rede: a Ponte é chamada direto, com relógio falso, scrypt barato e pastas temporárias. O banco "antigo"
em demonstração é montado pelo fixture `tests/demonstracao_antiga.py`, igual ao que a ativação gravava até 19/10/2026.
Nunca abre o banco de verdade de quem roda o teste. Só biblioteca padrão:
    python tests/test_painel_sem_demonstracao.py
"""
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import cadastros  # noqa: E402
import central as modulo_central  # noqa: E402
import demonstracao  # noqa: E402
import ponte as modulo_ponte  # noqa: E402
import script_local as sl  # noqa: E402
from atividades import Atividades  # noqa: E402
from cadastros import Cadastros, Decisoes  # noqa: E402
from configuracoes import Configuracoes  # noqa: E402
from dados import Banco  # noqa: E402
from ponte import Ponte  # noqa: E402

import demonstracao_antiga as antiga  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
T0 = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc).timestamp()
SENHA_ADM = "frase comprida de teste um"
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}
TABELAS_DA_DEMONSTRACAO = ("motoristas", "termos", "veiculos", "caixas", "caixa_vinculos", "decisoes")


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


class ScriptFalso:
    def estado(self):
        return dict(modulo_ponte.ESTADO_SCRIPT_FECHADO)

    def eventos(self, desde_id):
        return []

    def iniciar(self):
        pass

    def parar(self):
        pass


def nova_ponte(pasta, relogio, central=None, script=None):
    return Ponte(pasta, relogio=lambda: relogio[0], custo_scrypt=CUSTO_TESTE, script_local=script or ScriptFalso(),
                 central=central or modulo_central.Central(pasta, relogio=lambda: relogio[0]))


def dados(resposta, contexto=""):
    assert resposta.get("ok") is True, f"{contexto}: {resposta}"
    return resposta["dados"]


def erro(resposta, codigo, contexto=""):
    assert resposta.get("ok") is False and resposta.get("codigo") == codigo, f"{contexto}: esperava {codigo}, veio {resposta}"
    return resposta


def contar(banco, tabela):
    return banco.um(f"SELECT COUNT(*) AS n FROM {tabela}")["n"]


def fechar(*pontes):
    for item in pontes:
        if item._nucleo is not None:
            item._n().banco.fechar()


def iso(instante: datetime) -> str:
    return instante.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# SDF-06 · ativar sem demonstração: cria a empresa (nome digitado) e o administrador, sem carregar nada ---------------
assert not hasattr(Ponte, "ativar_demonstracao"), "SDF-06 a Ponte não oferece mais a demonstração"
assert not hasattr(cadastros, "carregar_demonstracao") and not hasattr(cadastros, "DEMO_EMPRESA"), \
    "SDF-06 cadastros.py sem a carga da demonstração"
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(Path(tmp) / "dados", t)
    for ruim in ("", "   ", "A", "x" * 121, None, 42, ["Transportes Lima"]):
        resposta = erro(ponte.ativar_local(ruim, ADMIN), "invalido", f"SDF-06 nome {ruim!r}")
        assert resposta["campo"] == "empresa", f"SDF-06 o erro marca o campo da empresa: {resposta}"
    assert erro(ponte.ativar_local("Transportes Lima", {**ADMIN, "senha": "curta"}), "invalido")["campo"] == "senha"
    banco = ponte._n().banco
    for tabela in ("usuarios", "configuracoes", "atividades", "meta", *TABELAS_DA_DEMONSTRACAO):
        assert contar(banco, tabela) == 0, f"SDF-06 recusado não grava nada em {tabela}"
    codigo = dados(ponte.ativar_local("  Transportes   Lima  ", ADMIN), "SDF-06 ativar")["codigo_recuperacao"]
    assert codigo, "SDF-06 código de recuperação"
    estado = dados(ponte.estado())
    assert (estado["ativado"], estado["modo"], estado["empresa"], estado["sessao"]["usuario"]) == \
        (True, "local", {"nome": "Transportes Lima"}, "marina.lopes"), f"SDF-06 estado: {estado}"
    for tabela in TABELAS_DA_DEMONSTRACAO:
        assert contar(banco, tabela) == 0, f"SDF-06 ativar não carrega {tabela}"
    assert dados(ponte.motoristas_listar()) == [] and dados(ponte.veiculos_listar()) == [] and \
        dados(ponte.caixas_listar()) == [] and dados(ponte.decisoes_listar()) == [], "SDF-06 listas vazias"
    atividades = banco.todos("SELECT usuario, acao, alvo, detalhe FROM atividades ORDER BY id")
    assert [tuple(l) for l in atividades] == [("Marina Lopes", "ativou o painel", None, "sem o arquivo da empresa"),
                                              ("Marina Lopes", "entrou", None, None)], \
        f"SDF-06 registro da ativação: {[tuple(l) for l in atividades]}"
    assert dados(ponte.config_ler())["empresa"]["nome"] == "Transportes Lima"
    erro(ponte.ativar_local("Outra", ADMIN), "conflito", "SDF-06 ativar de novo")
    texto = json.dumps([dict(l) for l in banco.todos("SELECT * FROM configuracoes")], ensure_ascii=False)
    assert demonstracao.DEMO_EMPRESA not in texto, "SDF-06 nada da empresa fictícia"
    fechar(ponte)
ok("SDF-06 ativar_local confere o nome da empresa (campo 'empresa') e o administrador antes de gravar; cria a empresa e "
   "o administrador sem motoristas, veículos, caixas, termos nem decisões; modo 'local'; uma vez só")


# SDF-07 · migração do painel ativado em demonstração --------------------------------------------------------------------
def banco_antigo(pasta, t):
    """Demonstração ativada como antes + o que a pessoa fez depois. Devolve o que deve sobrar."""
    banco = Banco(pasta, relogio=lambda: t[0])
    marina = antiga.ativar_como_antes(banco, lambda: t[0], CUSTO_TESTE, ADMIN)
    atividades = Atividades(banco)
    cad = Cadastros(banco, atividades, lambda: datetime.fromtimestamp(t[0]).date())
    t[0] += 3600
    pedro = cad.motorista_salvar({"nome": "Pedro Santos", "matricula": "0999", "cnh_numero": "12345678900",
                                  "cnh_categoria": "D", "cnh_validade": "2030-01-01",
                                  "termo": {"assinado": True, "data": "2026-09-20", "versao": "1"}}, marina)
    van = cad.veiculo_salvar({"numero": "4001", "placa": "ABC1D23", "tipo": "van", "transporta": "passageiros"}, marina)
    livre = banco.um("SELECT id FROM caixas WHERE codigo = ?", (antiga.CAIXA_LIVRE,))["id"]
    cad.caixa_vincular(livre, van["id"], marina)  # caixa fictícia na van da pessoa: a caixa sai, a van fica
    carlos = banco.um("SELECT id FROM motoristas WHERE ref = 'm-01'")["id"]
    cad.motorista_salvar({"id": carlos, "nome": "Carlos Menezes", "matricula": "0412", "cnh_numero": antiga.cnh(1),
                          "cnh_categoria": "D", "cnh_validade": "2028-03-31", "telefone": "(11) 99999-0000"}, marina)
    decisoes = Decisoes(banco, atividades)
    decisoes.registrar("v-2240-e-102", "confirmado", marina)  # momento de viagem fictícia
    decisoes.registrar("v-9000-e-1", "alarme_falso", marina)  # momento que não é da demonstração
    from contas import Contas  # noqa: PLC0415
    Contas(banco, atividades, lambda: t[0], CUSTO_TESTE).equipe_adicionar(
        {"nome": "Paulo Reis", "usuario": "paulo.reis", "funcao": "supervisor"}, marina)
    Configuracoes(banco, atividades).salvar("aparencia", {"texto_maior": True}, marina)
    banco.inserir("preferencias", {"usuario_id": marina["id"], "valores": json.dumps({"tema": "escuro"})})
    guardado = {
        "usuarios": [tuple(l) for l in banco.todos("SELECT * FROM usuarios ORDER BY id")],
        "atividades": [tuple(l) for l in banco.todos("SELECT * FROM atividades ORDER BY id")],
        "preferencias": [tuple(l) for l in banco.todos("SELECT * FROM preferencias ORDER BY usuario_id")],
        "pedro": pedro["id"], "van": van["id"],
        "termos_pedro": [tuple(l) for l in banco.todos("SELECT * FROM termos WHERE motorista_id = ?", (pedro["id"],))],
        "contagem": {tabela: contar(banco, tabela) for tabela in TABELAS_DA_DEMONSTRACAO},
    }
    banco.fechar()
    return guardado


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    pasta = Path(tmp) / "dados"
    antes = banco_antigo(pasta, t)
    assert antes["contagem"] == {"motoristas": 6, "termos": 5, "veiculos": 8, "caixas": 8, "caixa_vinculos": 8,
                                 "decisoes": 4}, f"SDF-07 banco antigo montado: {antes['contagem']}"
    leitura = sqlite3.connect(f"{(pasta / 'painel.db').resolve().as_uri()}?mode=ro", uri=True)  # como no banco real
    previa = demonstracao.contar_demonstracao(lambda sql, p=(): leitura.execute(sql, p).fetchall())
    leitura.close()
    assert previa == {"motoristas": 5, "termos": 4, "veiculos": 7, "caixas": 8, "caixa_vinculos": 8, "decisoes": 3,
                      "empresa": True}, f"SDF-07 contagem só lendo: {previa}"
    t[0] += 60
    ponte = nova_ponte(pasta, t)
    estado = dados(ponte.estado(), "SDF-07 abrir o painel antigo")
    assert estado["modo"] == "local" and estado["ativado"] is True, f"SDF-07 modo passa para local: {estado}"
    assert estado["empresa"] == {"nome": ""}, f"SDF-07 sem central, o nome fictício da empresa sai: {estado}"
    banco = ponte._n().banco
    assert [l["id"] for l in banco.todos("SELECT id FROM motoristas")] == [antes["pedro"]], "SDF-07 só o Pedro fica"
    assert [tuple(l) for l in banco.todos("SELECT * FROM termos ORDER BY id")] == antes["termos_pedro"], \
        "SDF-07 só o termo do Pedro fica, sem mudar"
    veiculos = banco.todos("SELECT * FROM veiculos")
    assert [l["id"] for l in veiculos] == [antes["van"]], "SDF-07 só a van da pessoa fica"
    assert contar(banco, "caixas") == 0 and contar(banco, "caixa_vinculos") == 0, "SDF-07 caixas fictícias saem"
    assert [d["momento_id"] for d in banco.todos("SELECT momento_id FROM decisoes")] == ["v-9000-e-1"], \
        "SDF-07 decisões de momentos fictícios saem; as outras ficam"
    assert [tuple(l) for l in banco.todos("SELECT * FROM usuarios ORDER BY id")] == antes["usuarios"], "SDF-07 contas"
    assert [tuple(l) for l in banco.todos("SELECT * FROM preferencias ORDER BY usuario_id")] == antes["preferencias"]
    depois = [tuple(l) for l in banco.todos("SELECT * FROM atividades ORDER BY id")]
    assert depois[:len(antes["atividades"])] == antes["atividades"], "SDF-07 atividades antigas intactas"
    novas = banco.todos("SELECT * FROM atividades WHERE id > ? ORDER BY id", (len(antes["atividades"]),))
    assert [(l["usuario"], l["acao"]) for l in novas] == [("RotaGuard Painel", demonstracao.ACAO)], \
        f"SDF-07 uma linha nova no registro: {[tuple(l) for l in novas]}"
    assert novas[0]["detalhe"] == ("5 motoristas, 4 termos, 7 veículos, 8 caixas, 8 vínculos de caixa e 3 decisões; "
                                   "nome da empresa apagado; cópia em painel.db.antes-de-remover-demonstracao"), \
        f"SDF-07 detalhe: {novas[0]['detalhe']}"
    assert Atividades(banco).verificar() is True, "SDF-07 registro de atividades íntegro"
    gatilhos = {l["name"] for l in banco.todos("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
    assert {"termos_sem_apagar", "termos_sem_alterar", "atividades_sem_apagar", "atividades_sem_alterar"} <= gatilhos, \
        f"SDF-07 os gatilhos voltam: {gatilhos}"
    try:
        banco.executar("DELETE FROM termos")
    except sqlite3.DatabaseError as falha:
        assert "nunca" in str(falha)
    else:
        raise AssertionError("SDF-07 termo voltou a poder ser apagado")
    copia = pasta / demonstracao.NOME_COPIA
    assert copia.is_file(), "SDF-07 cópia de segurança antes de apagar"
    antiga_con = sqlite3.connect(f"{copia.resolve().as_uri()}?mode=ro", uri=True)
    assert antiga_con.execute("SELECT COUNT(*) FROM motoristas").fetchone()[0] == 6, "SDF-07 a cópia tem o banco de antes"
    assert antiga_con.execute("SELECT valor FROM meta WHERE chave = 'modo'").fetchone()[0] == "demonstracao"
    antiga_con.close()
    dados(ponte.entrar("marina.lopes", SENHA_ADM), "SDF-07 a senha continua")
    assert [m["nome"] for m in dados(ponte.motoristas_listar())] == ["Pedro Santos"], "SDF-07 lista do Pedro"
    assert dados(ponte.motoristas_listar())[0]["termo"]["assinado"] is True, "SDF-07 termo do Pedro continua"
    assert [(v["numero"], v["caixa_id"]) for v in dados(ponte.veiculos_listar())] == [("4001", None)]
    assert not ponte._falhas, ponte._falhas
    tamanho_copia = copia.stat().st_size
    fechar(ponte)

    # SDF-08 · roda uma vez só
    t[0] += 60
    de_novo = nova_ponte(pasta, t)
    dados(de_novo.estado(), "SDF-08 abrir de novo")
    banco = de_novo._n().banco
    assert len(banco.todos("SELECT 1 FROM atividades WHERE acao = ?", (demonstracao.ACAO,))) == 1, \
        "SDF-08 a remoção fica uma vez só no registro"
    assert sorted(p.name for p in pasta.iterdir() if p.name.startswith("painel.db.")) == [demonstracao.NOME_COPIA], \
        "SDF-08 nenhuma cópia nova"
    assert copia.stat().st_size == tamanho_copia, "SDF-08 a cópia de antes não é trocada"
    assert banco.meta_ler("modo") == "local"
    fechar(de_novo)
ok("SDF-07 banco em demonstração + motorista, van, decisão, pessoa e preferência da pessoa: ao abrir, faz a cópia "
   "painel.db.antes-de-remover-demonstracao e apaga só os registros fictícios (motoristas, termos, veículos, caixas, "
   "vínculos e decisões dos momentos fictícios), mesmo o motorista fictício editado; contas, preferências e "
   "atividades intactas; gatilhos de volta; modo local")
ok("SDF-08 a remoção roda uma vez só: reabrir não registra de novo nem troca a cópia")

# SDF-07 · nome da empresa: o da central, se o painel está ligado a ela; nome que a pessoa trocou fica ----------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    pasta = Path(tmp) / "dados"
    banco_antigo(pasta, t)
    central = modulo_central.Central(pasta, relogio=lambda: t[0])
    central._gravar_meta({"empresa": "central-teste#1", "empresa_nome": "RotaGuard"})  # noqa: SLF001
    ponte = nova_ponte(pasta, t, central=central)
    assert dados(ponte.estado())["empresa"] == {"nome": "RotaGuard"}, "SDF-07 nome da empresa vem da central"
    linha = ponte._n().banco.um("SELECT detalhe FROM atividades WHERE acao = ?", (demonstracao.ACAO,))
    assert "nome da empresa trocado pelo da central (RotaGuard)" in linha["detalhe"], linha["detalhe"]
    fechar(ponte)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    pasta = Path(tmp) / "dados"
    banco = Banco(pasta, relogio=lambda: t[0])
    marina = antiga.ativar_como_antes(banco, lambda: t[0], CUSTO_TESTE, ADMIN)
    Configuracoes(banco, Atividades(banco)).salvar("empresa", {"nome": "Expresso Real"}, marina)
    banco.fechar()
    ponte = nova_ponte(pasta, t)
    assert dados(ponte.estado())["empresa"] == {"nome": "Expresso Real"}, "SDF-07 nome trocado pela pessoa fica"
    banco = ponte._n().banco
    assert all(contar(banco, tabela) == 0 for tabela in TABELAS_DA_DEMONSTRACAO), "SDF-07 cadastros fictícios saem"
    fechar(ponte)
ok("SDF-07 o nome fictício da empresa vira o da central (quando o painel está ligado a ela) ou fica em branco; nome "
   "trocado pela pessoa continua")

# SDF-07 · painel ativado sem demonstração não é tocado, mesmo com cadastro parecido ------------------------------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    pasta = Path(tmp) / "dados"
    ponte = nova_ponte(pasta, t)
    dados(ponte.ativar_local("Transportes Lima", ADMIN))
    antiga.carregar_na_ponte(ponte)
    fechar(ponte)
    reaberta = nova_ponte(pasta, t)
    dados(reaberta.estado())
    banco = reaberta._n().banco
    assert contar(banco, "motoristas") == 5 and contar(banco, "caixas") == 8, "SDF-07 modo local não é migrado"
    assert not (pasta / demonstracao.NOME_COPIA).exists(), "SDF-07 sem cópia quando não há o que remover"
    assert not banco.todos("SELECT 1 FROM atividades WHERE acao = ?", (demonstracao.ACAO,))
    fechar(reaberta)
ok("SDF-07 só o painel com modo 'demonstracao' é migrado; ativado sem a demonstração nunca perde cadastro")

# SDF-07 · identificação pelo conjunto conhecido: os identificadores do fixture são os da migração ----------------------
assert [(r, m) for r, _n, _c, m, *_ in antiga.MOTORISTAS] == list(demonstracao.MOTORISTAS)
assert [(n, p) for n, _t, _tr, p, _c, _m in antiga.VEICULOS] == list(demonstracao.VEICULOS)
assert sorted([c for *_x, c, _m in antiga.VEICULOS] + [antiga.CAIXA_LIVRE]) == sorted(demonstracao.CAIXAS)
assert {m for m, _r, _o in antiga.DECISOES} <= set(demonstracao.MOMENTOS) and len(demonstracao.MOMENTOS) == 8
nomes_no_desktop = "\n".join(p.read_text(encoding="utf-8") for p in (RAIZ / "painel" / "desktop").glob("*.py"))
for nome in ("Carlos Menezes", "Juliana Prado", "Rogério Lima", "Aline Costa", "Marcos Teixeira", "Marina (gestora)",
             "Cavalo mecânico", "Rodoviário"):
    assert nome not in nomes_no_desktop, f"SDF-01 nome fictício no núcleo do painel: {nome}"
ok("SDF-07 a migração reconhece a demonstração pelos identificadores (ref, matrícula, CNH, número, placa, código e "
   "momentos), os mesmos do fixture; os nomes fictícios só existem nos testes")


# SDF-05 · Início com números reais: testes de hoje, alertas, testando agora; zero quando não há -------------------------
def resumo_de_hoje(ponte):
    return dados(ponte.inicio_resumo(), "inicio_resumo")["hoje"]


ZERO = {"testes": 0, "testes_central": 0, "testes_locais": 0, "eventos": 0, "alertas": 0, "alertas_por_tipo": {},
        "testando_agora": 0, "computadores": 0, "script_aberto": False, "central_conectada": False}
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    pasta = Path(tmp) / "dados"
    processos = []
    local = sl.ScriptLocal(pasta, [Path(tmp) / "script"], relogio=lambda: datetime.fromtimestamp(t[0], timezone.utc),
                           listar_processos=lambda: list(processos), pid_vivo=lambda pid: False, cache_processos_s=0)
    central = modulo_central.Central(pasta, relogio=lambda: t[0])
    ponte = nova_ponte(pasta, t, central=central, script=local)
    dados(ponte.ativar_local("Transportes Lima", ADMIN))
    assert resumo_de_hoje(ponte) == ZERO, f"SDF-05 painel novo: tudo zero {resumo_de_hoje(ponte)}"
    assert not (pasta / modulo_central.NOME_BANCO).exists(), "SDF-05 contar não cria o banco da central"

    meia_noite = datetime.fromtimestamp(T0).astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
    hoje_cedo, ontem_tarde = meia_noite + timedelta(minutes=10), meia_noite - timedelta(minutes=10)
    agora = datetime.fromtimestamp(T0, timezone.utc)
    central._gravar_meta({"empresa": "central-teste#1", "empresa_nome": "RotaGuard"})  # noqa: SLF001
    banco_central = central._banco()  # noqa: SLF001
    for n, (nome, testando, sinal, revogado) in enumerate((("Notebook 1", 1, agora - timedelta(seconds=20), None),
                                                           ("Notebook 2", 0, agora - timedelta(hours=3), None),
                                                           ("Antigo", 1, agora - timedelta(seconds=5), iso(ontem_tarde)))):
        banco_central.inserir("central_aparelhos", {"uid": f"{n + 1:032x}", "empresa": "central-teste#1", "nome": nome,
                                                    "testando_agora": testando, "ultimo_sinal": iso(sinal),
                                                    "revogado_em": revogado})
    for n, inicio in enumerate((hoje_cedo, agora - timedelta(hours=1), ontem_tarde)):
        banco_central.inserir("central_sessoes", {"uid": f"{n + 11:032x}", "empresa": "central-teste#1",
                                                  "aparelho_uid": f"{1:032x}", "iniciada_em": iso(inicio)})
    for n, (tipo, risco, quando) in enumerate((("microssono", 3, hoje_cedo), ("celular_na_mao", 2, agora),
                                                ("atencao", 1, agora), ("sono", 3, ontem_tarde),
                                                ("olhando_celular", None, agora))):
        banco_central.inserir("central_eventos", {"uid": f"{n + 21:032x}", "empresa": "central-teste#1",
                                                  "sessao_uid": f"{11:032x}", "tipo": tipo, "nivel_risco": risco,
                                                  "ocorrido_em": iso(quando)})
    banco_central.inserir("central_eventos", {"uid": f"{99:032x}", "empresa": "outra-central#9", "tipo": "sono",
                                              "nivel_risco": 3, "ocorrido_em": iso(agora)})
    db = local._db()  # noqa: SLF001
    for n, (inicio, fim) in enumerate(((hoje_cedo, hoje_cedo + timedelta(minutes=30)), (ontem_tarde, hoje_cedo))):
        db.execute("INSERT INTO sessoes (uid, chave, origem, iniciado_em, encerrado_em, criado_em, alterado_em) "
                   "VALUES (?, ?, 'processo', ?, ?, ?, ?)", (f"{n + 31:032x}", f"processo:{n}", sl._iso(inicio),  # noqa: SLF001
                                                             sl._iso(fim), sl._iso(agora), sl._iso(agora)))  # noqa: SLF001
    for n, (tipo, risco, quando) in enumerate((("sono", 3, hoje_cedo), ("atencao", 1, hoje_cedo),
                                                ("celular_no_ouvido", 2, ontem_tarde))):
        db.execute("INSERT INTO eventos (uid, evento_uid, sessao_uid, tipo, risco, ocorrido_em, origem, criado_em, "
                   "alterado_em) VALUES (?, ?, NULL, ?, ?, ?, 'teste', ?, ?)",
                   (f"{n + 41:032x}", f"ev-{n}", tipo, risco, sl._iso(quando), sl._iso(agora), sl._iso(agora)))  # noqa: SLF001
    hoje = resumo_de_hoje(ponte)
    assert hoje == {"testes": 3, "testes_central": 2, "testes_locais": 1, "eventos": 6, "alertas": 3,
                    "alertas_por_tipo": {"celular_na_mao": 1, "microssono": 1, "sono": 1}, "testando_agora": 1,
                    "computadores": 2, "script_aberto": False, "central_conectada": False}, f"SDF-05 números: {hoje}"
    processos.append(sl.Processo(812, "RotaGuardTeste.exe"))
    hoje = resumo_de_hoje(ponte)
    assert (hoje["script_aberto"], hoje["testando_agora"], hoje["testes_locais"], hoje["testes"]) == (True, 2, 2, 4), \
        f"SDF-05 o script aberto neste computador conta como testando agora e como teste de hoje: {hoje}"
    t[0] += 24 * 3600
    processos.clear()
    dados(ponte.desbloquear(SENHA_ADM), "um dia depois a tela bloqueou")
    hoje = resumo_de_hoje(ponte)
    assert (hoje["testes"], hoje["eventos"], hoje["alertas"]) == (0, 0, 0), f"SDF-05 no dia seguinte zera: {hoje}"
    assert hoje["computadores"] == 2 and hoje["testando_agora"] == 0, f"SDF-05 sinal velho não testa: {hoje}"
    local.parar()
    fechar(ponte)
ok("SDF-05 inicio_resumo().hoje: testes de hoje (central + este computador, pelo dia local), eventos e alertas de risco "
   "2 ou mais por tipo, computadores testando agora (central + script aberto) e conectados; zero sem dados; outra "
   "empresa da central não conta")

# SDF-10 · cadastrar motorista, veículo e equipe continua e aparece nas listas ------------------------------------------
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(Path(tmp) / "dados", t)
    dados(ponte.ativar_local("Transportes Lima", ADMIN))
    motorista = dados(ponte.motorista_salvar({"nome": "Pedro Santos", "matricula": "0999", "cnh_numero": "12345678900",
                                              "cnh_categoria": "D", "cnh_validade": "2030-01-01"}), "SDF-10 motorista")
    veiculo = dados(ponte.veiculo_salvar({"numero": "4001", "placa": "ABC1D23", "tipo": "van",
                                          "transporta": "passageiros"}), "SDF-10 veículo")
    pessoa = dados(ponte.equipe_adicionar({"nome": "Paulo Reis", "usuario": "paulo.reis", "funcao": "supervisor"}))
    assert [m["id"] for m in dados(ponte.motoristas_listar())] == [motorista["id"]] and motorista["ref"] == "m-01"
    assert [v["id"] for v in dados(ponte.veiculos_listar())] == [veiculo["id"]]
    assert pessoa["usuario"]["id"] in [p["id"] for p in dados(ponte.equipe_listar())]
    fechar(ponte)
ok("SDF-10 painel ativado do zero: cadastrar motorista, veículo e pessoa da equipe aparece nas listas")

print(f"\n{checks} verificações OK")
