"""Spec 015: cadastro de motoristas, veículos e caixas do painel (núcleo Python).

Sem janela e sem pywebview: a Ponte é chamada direto, com relógio falso, scrypt barato, pasta temporária e script local
falso. Casos de CNH, CPF, placa e nome curto iguais aos da tela (painel/app/scripts/testes/cadastros.test.mjs). Só
biblioteca padrão:
    python tests/test_painel_cadastros.py
"""
import base64
import json
import sqlite3
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import cadastros  # noqa: E402
from dados import ErroPainel, iso_utc  # noqa: E402
from ponte import Ponte  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc).timestamp()
# Senhas descartáveis, só deste teste.
SENHA_ADM = "frase comprida de teste um"
SENHA_SUP = "frase comprida de teste dois"
SENHA_CON = "frase comprida de teste tres"
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}
B64 = base64.b64encode(bytes(range(32))).decode()
CHAVES_MOTORISTA = {"id", "ref", "nome", "nome_curto", "matricula", "cpf", "telefone", "cnh_numero", "cnh_categoria",
                    "cnh_validade", "situacao", "termo", "observacoes", "viagens_30d", "confirmados_30d"}
BASE = {"nome": "Pedro Santos", "matricula": "0999", "cnh_numero": "12345678900", "cnh_categoria": "D",
        "cnh_validade": "2030-01-01", "situacao": "ativo", "cpf": None, "telefone": None, "observacoes": None,
        "termo": {"assinado": False, "data": None, "versao": None}}
CNH_OK = ["12345678900", "10000000100", "00000008500"]
CNH_RUINS = ["12345678901", "10000000108", "00000009309", "00000009300", "11111111111"]


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


def linhas(ponte, acao):
    return ponte._n().banco.todos("SELECT * FROM atividades WHERE acao = ? ORDER BY id", (acao,))


def contar(ponte, tabela):
    return ponte._n().banco.um(f"SELECT COUNT(*) AS n FROM {tabela}")["n"]


def fechar(*pontes):
    for ponte in pontes:
        if ponte._nucleo is not None:
            ponte._n().banco.fechar()


def entrar_como(ponte, usuario, senha):
    ponte.sair()
    return dados(ponte.entrar(usuario, senha), usuario)


def criar_pessoa(ponte, nome, usuario, funcao, senha):
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    novo = dados(ponte.equipe_adicionar({"nome": nome, "usuario": usuario, "funcao": funcao}), usuario)
    entrar_como(ponte, usuario, novo["senha_temporaria"])
    dados(ponte.trocar_senha(novo["senha_temporaria"], senha), usuario)
    return novo["usuario"]["id"]


def pronta(tmp, relogio, destinos=None, arquivo=None):
    """Painel ativado (demonstração ou arquivo da empresa) com o supervisor Paulo Reis na sessão."""
    ponte = nova_ponte(tmp, relogio, destinos)
    if arquivo is None:
        dados(ponte.ativar_demonstracao(ADMIN), "ativar demonstração")
    else:
        dados(ponte.ativar_com_arquivo(json.dumps(arquivo), ADMIN), "ativar com arquivo")
    criar_pessoa(ponte, "Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)
    return ponte


def ultima_linha(ponte, acao, usuario="Paulo Reis"):
    achadas = linhas(ponte, acao)
    assert achadas and achadas[-1]["usuario"] == usuario, f"falta a linha '{acao}' de {usuario}"
    return achadas[-1]


def chaveiro():
    """Arquivo `rotaguard-chaveiro-coleta/1` (spec 003, §4.3): uma caixa normal e uma revogada."""
    return {"formato": "rotaguard-chaveiro-coleta/1", "empresa_id": 7, "gerado_em": "2026-09-11T15:20:00.000Z",
            "caixas": [
                {"id_caixa": "rg-abcdefghijkl", "dispositivo_id": 3, "nome": "Caminhão ABC-1234", "geracao_atual": 1,
                 "chaves_coleta": {"1": B64},
                 "chaves_publicas": [{"geracao": 1, "kid": "0123456789abcdef", "publica": B64}], "revogada_em": None},
                {"id_caixa": "rg-mnopqrstuvwx", "dispositivo_id": 4, "nome": "Ônibus 2240", "geracao_atual": 2,
                 "chaves_coleta": {"1": B64, "2": B64},
                 "chaves_publicas": [{"geracao": 2, "kid": "fedcba9876543210", "publica": B64}],
                 "revogada_em": "2026-09-12T10:00:00.000Z"}]}


def cnh_nova(indice):
    return cadastros.cnh_demo(100 + indice)


# MOT-01 · campos obrigatórios da decisão 1; matrícula e CNH únicas; erro com o nome da propriedade
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    antes = contar(ponte, "motoristas")
    ruins = (("nome", ""), ("nome", "Al"), ("nome", None), ("nome", 42), ("matricula", ""), ("matricula", "x" * 21),
             ("matricula", None), ("cnh_numero", ""), ("cnh_numero", None), ("cnh_categoria", "B"),
             ("cnh_categoria", None), ("cnh_validade", ""), ("cnh_validade", "31/12/2030"),
             ("cnh_validade", "2030-02-30"), ("situacao", "ferias"), ("termo", "sim"),
             ("termo", {"assinado": True, "data": None, "versao": None}), ("nome_curto", "x" * 41),
             ("telefone", 11999990000), ("observacoes", "x" * 501))
    for campo, valor in ruins:
        resposta = erro(ponte.motorista_salvar({**BASE, campo: valor}), "invalido", f"MOT-01 {campo}={valor!r}")
        assert resposta["campo"] == campo, f"MOT-01 campo com o nome da propriedade: {campo} × {resposta}"
    for campo in ("nome", "matricula", "cnh_numero", "cnh_categoria", "cnh_validade"):
        sem = {chave: valor for chave, valor in BASE.items() if chave != campo}
        assert erro(ponte.motorista_salvar(sem), "invalido", f"MOT-01 sem {campo}")["campo"] == campo, campo
    assert erro(ponte.motorista_salvar("tudo"), "invalido")["campo"] == "nome", "MOT-01 dados que não são objeto"
    assert contar(ponte, "motoristas") == antes and not linhas(ponte, "cadastrou motorista"), "MOT-01 nada gravado"
    novo = dados(ponte.motorista_salvar(BASE), "MOT-01 supervisor cadastra")
    assert set(novo) >= CHAVES_MOTORISTA and novo["ref"] == "m-06" and novo["situacao"] == "ativo", f"MOT-01 {novo}"
    assert novo["id"] in [m["id"] for m in dados(ponte.motoristas_listar())], "MOT-01 aparece na lista"
    assert ultima_linha(ponte, "cadastrou motorista")["alvo"] == "Pedro S. (matrícula 0999)", "MOT-01 registro"
    duplicada = erro(ponte.motorista_salvar({**BASE, "cnh_numero": cnh_nova(1)}), "conflito", "MOT-01 matrícula")
    assert duplicada["campo"] == "matricula" and duplicada["erro"] == "Já existe um motorista com esta matrícula.", \
        f"MOT-01 {duplicada}"
    assert erro(ponte.motorista_salvar({**BASE, "matricula": "0412", "cnh_numero": cnh_nova(2)}), "conflito",
                "MOT-01 matrícula da demonstração")["campo"] == "matricula"
    repetida = erro(ponte.motorista_salvar({**BASE, "matricula": "1000"}), "conflito", "MOT-01 CNH repetida")
    assert repetida["campo"] == "cnh_numero" and repetida["erro"] == "Já existe um motorista com esta CNH.", repetida
    assert contar(ponte, "motoristas") == antes + 1, "MOT-01 repetido não grava"
    dados(ponte.motorista_salvar({**BASE, "id": novo["id"], "observacoes": "Turno da noite"}),
          "MOT-01 editar mantendo a própria matrícula e CNH")
    erro(ponte.motorista_salvar({**BASE, "id": 9999}), "nao_encontrado", "MOT-01 editar quem não existe")
    fechar(ponte)
ok("MOT-01 nome, matrícula, CNH (número, categoria C/D/E, validade), situação e termo conferidos com campo igual à "
   "propriedade; matrícula e CNH únicas; supervisor cadastra e o registro ganha a linha")

# MOT-02 · CNH com dígito verificador (mesma variante da tela); CPF opcional com dígito verificador e mascarado
for numero in CNH_OK + [" 123.456.789-00 "]:
    assert cadastros.cnh_valida(numero), f"MOT-02 CNH válida recusada: {numero}"
for numero in CNH_RUINS + ["1234567890", "123456789001", "", None]:
    assert not cadastros.cnh_valida(numero), f"MOT-02 CNH inválida aceita: {numero}"
assert all(cadastros.cnh_valida(cadastros.cnh_demo(i)) for i in range(1, 6)), "MOT-02 CNHs de demonstração válidas"
assert len({cadastros.cnh_demo(i) for i in range(1, 6)}) == 5, "MOT-02 CNHs de demonstração diferentes"
for cpf in ("529.982.247-25", "52998224725"):
    assert cadastros.cpf_valido(cpf), f"MOT-02 CPF válido recusado: {cpf}"
for cpf in ("52998224724", "111.111.111-11", "5299822472", "", None):
    assert not cadastros.cpf_valido(cpf), f"MOT-02 CPF inválido aceito: {cpf}"
assert cadastros.mascarar_cpf("52998224725") == "•••.•••.247-••", \
    f"MOT-02 CPF mascarado igual ao da tela: {cadastros.mascarar_cpf('52998224725')}"
assert cadastros.mascarar_cpf("529.982.247-25") == "•••.•••.247-••" and cadastros.mascarar_cpf(None) is None
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    for indice, numero in enumerate(CNH_OK):
        salvo = dados(ponte.motorista_salvar({**BASE, "matricula": f"70{indice}", "cnh_numero": numero}), numero)
        assert salvo["cnh_numero"] == numero, f"MOT-02 {salvo['cnh_numero']}"
    for numero in CNH_RUINS:
        resposta = erro(ponte.motorista_salvar({**BASE, "matricula": "800", "cnh_numero": numero}), "invalido", numero)
        assert resposta["campo"] == "cnh_numero", f"MOT-02 CNH {numero}: {resposta}"
    assert erro(ponte.motorista_salvar({**BASE, "matricula": "800", "cnh_numero": cnh_nova(1), "cpf": "52998224724"}),
                "invalido")["campo"] == "cpf", "MOT-02 CPF com dígito errado"
    sem_cpf = dados(ponte.motorista_salvar({**BASE, "matricula": "801", "cnh_numero": cnh_nova(2), "cpf": ""}))
    assert sem_cpf["cpf"] is None, "MOT-02 CPF vazio é aceito"
    com_cpf = dados(ponte.motorista_salvar({**BASE, "matricula": "802", "cnh_numero": cnh_nova(3),
                                            "cpf": "529.982.247-25"}))
    assert com_cpf["cpf"] == "•••.•••.247-••", f"MOT-02 CPF mascarado na resposta: {com_cpf['cpf']}"
    na_lista = [m for m in dados(ponte.motoristas_listar()) if m["id"] == com_cpf["id"]][0]
    assert na_lista["cpf"] == "•••.•••.247-••", f"MOT-02 CPF mascarado na lista: {na_lista['cpf']}"

    def cpf_guardado():
        return ponte._n().banco.um("SELECT cpf FROM motoristas WHERE id = ?", (com_cpf["id"],))["cpf"]

    assert cpf_guardado() == "529.982.247-25", "MOT-02 banco guarda o CPF inteiro"
    # Bug: a lista devolvia ***.982.247-**; a tela não reconhece e editar motorista com CPF não salvava.
    editado = dados(ponte.motorista_salvar({**na_lista, "telefone": "(11) 95555-0000"}),
                    "MOT-02 editar com o CPF mascarado da lista")
    assert editado["telefone"] == "(11) 95555-0000" and cpf_guardado() == "529.982.247-25", "MOT-02 CPF mantido"
    dados(ponte.motorista_salvar({**na_lista, "cpf": "***.***.247-**", "telefone": None}), "MOT-02 máscara antiga")
    assert cpf_guardado() == "529.982.247-25", "MOT-02 máscara com * também mantém"
    erro(ponte.motorista_salvar({**BASE, "matricula": "803", "cnh_numero": cnh_nova(4), "cpf": "•••.•••.247-••"}),
         "invalido", "MOT-02 CPF mascarado ao cadastrar não vale")
    dados(ponte.motorista_salvar({**na_lista, "cpf": ""}), "MOT-02 apagar o CPF")
    assert cpf_guardado() is None, "MOT-02 CPF apagado quando a tela manda vazio"
    fechar(ponte)
ok("MOT-02 CNH 12345678900/10000000100/00000008500 válidas e 12345678901/10000000108/00000009309/00000009300/"
   "11111111111 recusadas (campo cnh_numero); CPF opcional com dígito; lista com •••.•••.247-••; editar com o CPF "
   "mascarado mantém o guardado")

# MOT-03 · nome nos relatórios sugerido igual ao nomeCurto da tela e editável
for nome, curto in {"Carlos Menezes": "Carlos M.", "  juliana   prado ": "Juliana P.", "Maria da Silva": "Maria S.",
                    "Ana Beatriz dos Santos e Souza": "Ana S.", "Rogério": "Rogério", "": "", None: "",
                    "JOÃO DE": "João", "élida  ÁVILA": "Élida Á."}.items():
    assert cadastros.nome_curto_sugerido(nome) == curto, \
        f"MOT-03 {nome!r} → {cadastros.nome_curto_sugerido(nome)!r}, esperado {curto!r}"
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    sugerido = dados(ponte.motorista_salvar({**BASE, "nome": "  juliana   prado "}))
    assert (sugerido["nome"], sugerido["nome_curto"]) == ("juliana prado", "Juliana P."), f"MOT-03 {sugerido}"
    proprio = dados(ponte.motorista_salvar({**BASE, "matricula": "1001", "cnh_numero": cnh_nova(1),
                                            "nome_curto": "Carlão"}))
    assert proprio["nome_curto"] == "Carlão", f"MOT-03 nome curto escolhido: {proprio}"
    editado = dados(ponte.motorista_salvar({**proprio, "nome_curto": "Pedro Santos"}))
    assert editado["nome_curto"] == "Pedro Santos", f"MOT-03 editável: {editado}"
    assert ultima_linha(ponte, "editou motorista")["detalhe"] == "campos: nome_curto", "MOT-03 edição registrada"
    fechar(ponte)
ok("MOT-03 nome curto como a tela (maiúscula, sem de/da/das/do/dos/e): Carlos M., Juliana P., Maria S., Ana S., "
   "Rogério; escolhido e editado pela pessoa")


def por_ref(ponte, ref):
    return [m for m in dados(ponte.motoristas_listar()) if m["ref"] == ref][0]


# MOT-04 · sem termo registrado a ponte não entrega o vídeo daquele motorista, nem com chamada direta
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    trancado = dados(ponte.video_abrir("v-1187-e-202", "m-05"))
    assert trancado == {"liberado": False, "motivo": cadastros.MENSAGEM_TERMO}, f"MOT-04 Marcos sem termo: {trancado}"
    linha = ultima_linha(ponte, "vídeo trancado")
    assert (linha["alvo"], linha["detalhe"]) == ("v-1187-e-202", cadastros.MENSAGEM_TERMO), f"MOT-04 {dict(linha)}"
    assert dados(ponte.video_abrir("v-1187-e-202", "m-01")) == {"liberado": True}, "MOT-04 Carlos com termo"
    assert ultima_linha(ponte, "abriu vídeo")["alvo"] == "v-1187-e-202", "MOT-04 abriu vídeo no registro"
    for ref in ("m-99", None, 5, ""):
        assert dados(ponte.video_abrir("v-1187-e-202", ref))["liberado"] is False, f"MOT-04 motorista {ref!r}"
    assert erro(ponte.video_abrir("../x", "m-01"), "invalido")["campo"] == "momento_id", "MOT-04 momento inválido"
    marcos = por_ref(ponte, "m-05")
    dados(ponte.motorista_salvar({**marcos, "termo": {"assinado": True, "data": "2026-09-14", "versao": None}}))
    assert dados(ponte.video_abrir("v-1187-e-202", "m-05"))["liberado"] is True, "MOT-04 termo registrado destranca"
    dados(ponte.motorista_salvar({**por_ref(ponte, "m-05"), "termo": {"assinado": False, "data": None, "versao": None}}))
    assert dados(ponte.video_abrir("v-1187-e-202", "m-05"))["liberado"] is False, "MOT-04 termo revogado tranca"
    criar_pessoa(ponte, "Ana Souza", "ana.souza", "consulta", SENHA_CON)
    erro(ponte.video_abrir("v-1187-e-202", "m-01"), "sem_permissao", "MOT-04 consulta não vê vídeo")
    fechar(ponte)
ok("MOT-04 video_abrir sem termo (ou motorista desconhecido) devolve liberado false com o motivo e registra; termo "
   "registrado libera, revogado tranca de novo; consulta recusada")

# MOT-05 · termo nunca apagado: registrar, revogar e reassinar criam registro novo com data, versão e quem registrou
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    banco = ponte._n().banco
    marcos = por_ref(ponte, "m-05")

    def termos():
        return [tuple(l) for l in banco.todos("SELECT assinado, data, versao, registrado_por FROM termos "
                                              "WHERE motorista_id = ? ORDER BY id", (marcos["id"],))]

    assert termos() == [], "MOT-05 Marcos começa sem termo"
    t[0] += 60
    assinado = dados(ponte.motorista_salvar({**marcos, "termo": {"assinado": True, "data": "2026-09-10",
                                                                 "versao": None}}))
    assert assinado["termo"] == {"assinado": True, "data": "2026-09-10", "versao": "1", "arquivo": None}, \
        f"MOT-05 termo.versao null grava a versão 1: {assinado['termo']}"
    assert ultima_linha(ponte, "registrou termo de ciência")["detalhe"] == "versão 1, assinado em 2026-09-10"
    dados(ponte.motorista_salvar({**assinado, "telefone": "(11) 90000-1111"}))
    assert len(termos()) == 1, "MOT-05 salvar sem mudar o termo não cria registro"
    t[0] += 60
    revogado = dados(ponte.motorista_salvar({**assinado, "termo": {"assinado": False, "data": None, "versao": None}}))
    assert revogado["termo"] == {"assinado": False, "data": None, "versao": None, "arquivo": None}, \
        f"MOT-05 {revogado['termo']} (spec 019: termo registrado pelo cadastro fica sem arquivo)"
    assert ultima_linha(ponte, "revogou termo de ciência")["alvo"] == "Marcos T. (matrícula 0467)", "MOT-05 revogou"
    t[0] += 60
    dados(ponte.motorista_salvar({**revogado, "termo": {"assinado": True, "data": "2026-09-14", "versao": "2"}}))
    assert termos() == [(1, "2026-09-10", "1", "Paulo Reis"), (0, None, None, "Paulo Reis"),
                        (1, "2026-09-14", "2", "Paulo Reis")], f"MOT-05 histórico: {termos()}"
    historico = ponte._n().cadastros.termos_historico(marcos["id"])
    assert [h["registrado_em"] for h in historico] == [iso_utc(T0 + 60), iso_utc(T0 + 120), iso_utc(T0 + 180)], \
        f"MOT-05 quando foi registrado: {historico}"
    for sql in ("UPDATE termos SET versao = '9'", "DELETE FROM termos"):
        try:
            banco.executar(sql)
        except sqlite3.DatabaseError as falha:
            assert "nunca" in str(falha), f"MOT-05 mensagem do gatilho: {falha}"
        else:
            raise AssertionError(f"MOT-05 o gatilho deixou passar: {sql}")
    fechar(ponte)
ok("MOT-05 registrar (versão null vira 1), revogar e reassinar geram 3 registros com data, versão, quem e quando; "
   "salvar sem mudar o termo não duplica; gatilhos recusam alterar e apagar")

# MOT-06 · aviso de CNH 30 dias antes e de CNH vencida, sem bloquear
HOJE = date(2026, 9, 14)
for validade, aviso in {"2028-03-31": None, "2026-10-15": None, "2026-10-14": "CNH vence em 30 dias",
                        "2026-09-26": "CNH vence em 12 dias", "2026-09-15": "CNH vence em 1 dia",
                        "2026-09-14": "CNH vence hoje", "2026-09-13": "CNH vencida em 13/09/2026",
                        "2026-09-10": "CNH vencida em 10/09/2026", "31/12/2026": None}.items():
    assert cadastros.aviso_cnh(validade, HOJE) == aviso, \
        f"MOT-06 {validade}: {cadastros.aviso_cnh(validade, HOJE)!r} × {aviso!r}"
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    lista = {m["ref"]: m for m in dados(ponte.motoristas_listar())}
    assert lista["m-03"]["aviso_cnh"] == "CNH vence em 12 dias" and lista["m-01"]["aviso_cnh"] is None, \
        f"MOT-06 aviso na lista pelo relógio: {lista['m-03']['aviso_cnh']}"
    vencida = dados(ponte.motorista_salvar({**BASE, "cnh_validade": "2026-09-10"}), "MOT-06 CNH vencida salva")
    assert vencida["aviso_cnh"] == "CNH vencida em 10/09/2026", f"MOT-06 {vencida['aviso_cnh']}"
    t[0] = T0 + 20 * 86400
    entrar_como(ponte, "paulo.reis", SENHA_SUP)
    assert por_ref(ponte, "m-03")["aviso_cnh"] == "CNH vencida em 26/09/2026", "MOT-06 relógio andou 20 dias"
    assert ponte._n().cadastros.caixa_pode_importar("RG-0139") is True, "MOT-06 CNH não entra na regra de importar"
    fechar(ponte)
print("-- MOT-06 parcial: a importação de viagem ainda não existe; conferido só que a regra da caixa não olha a CNH")
ok("MOT-06 aviso aos 30 dias, no dia e depois de vencida (relógio falso, 12 dias → vencida em 26/09/2026); CNH "
   "vencida é salva")

# MOT-07 · exportar dados do motorista gera arquivo com cadastro, termos, viagens e momentos, e registra
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    destinos = []
    ponte = pronta(tmp, t, destinos)
    pedro = dados(ponte.motorista_salvar({**BASE, "cpf": "529.982.247-25",
                                          "termo": {"assinado": True, "data": "2026-09-10", "versao": "1"}}))
    erro(ponte.motorista_exportar(9999), "nao_encontrado", "MOT-07 motorista que não existe")
    erro(ponte.motorista_exportar("1"), "nao_encontrado", "MOT-07 id que não é número")
    assert destinos == [], "MOT-07 sem motorista nem abre o diálogo"
    t[0] += 60
    caminho = Path(dados(ponte.motorista_exportar(pedro["id"]))["caminho"])
    assert caminho == Path(tmp) / "rotaguard-motorista-pedro-s.json" and destinos == [caminho.name], caminho
    conteudo = json.loads(caminho.read_text(encoding="utf-8"))
    assert set(conteudo) == {"formato", "gerado_em", "motorista", "termos", "viagens", "momentos_confirmados"}, conteudo
    assert conteudo["formato"] == "rotaguard-dados-motorista/1" and conteudo["gerado_em"] == iso_utc(t[0])
    assert conteudo["motorista"]["cpf"] == "529.982.247-25" and conteudo["motorista"]["cnh_numero"] == "12345678900", \
        "MOT-07 o próprio motorista recebe os dados sem máscara"
    assert [(x["assinado"], x["versao"]) for x in conteudo["termos"]] == [(True, "1")], conteudo["termos"]
    linha = ultima_linha(ponte, "exportou dados do motorista")
    assert (linha["alvo"], linha["detalhe"], linha["em"]) == ("Pedro S.", caminho.name, iso_utc(t[0])), dict(linha)
    antes = len(linhas(ponte, "exportou dados do motorista"))
    ponte._escolher_destino_injetado = lambda nome: None
    assert erro(ponte.motorista_exportar(pedro["id"]), "invalido")["erro"] == "Nada foi salvo.", "MOT-07 cancelar"
    assert len(linhas(ponte, "exportou dados do motorista")) == antes, "MOT-07 cancelar não registra"
    criar_pessoa(ponte, "Ana Souza", "ana.souza", "consulta", SENHA_CON)
    erro(ponte.motorista_exportar(pedro["id"]), "sem_permissao", "MOT-07 consulta não exporta")
    fechar(ponte)
print("-- MOT-07 parcial: viagens e momentos confirmados saem vazios; o banco do painel ainda não guarda viagens")
ok("MOT-07 arquivo rotaguard-dados-motorista/1 com cadastro sem máscara e termos, registro com quem, quando e arquivo; "
   "cancelar não grava; consulta recusada")

VEICULO = {"numero": "4001", "placa": "ABC1D23", "tipo": "van", "transporta": "passageiros", "modelo": None,
           "ano": None, "situacao": "em_uso"}


def por_numero(ponte, numero):
    return [v for v in dados(ponte.veiculos_listar()) if v["numero"] == numero][0]


def por_codigo(ponte, codigo):
    return [c for c in dados(ponte.caixas_listar()) if c["codigo"] == codigo][0]


# VEI-01 · número único; placa Mercosul ou antiga; tipo e "transporta" obrigatórios
for placa, normal in {"BRA2E19": "BRA2E19", " bra3f27 ": "BRA3F27", "ABC-1234": "ABC-1234", "abc1234": "ABC-1234",
                      " abc-1234 ": "ABC-1234"}.items():
    assert cadastros.placa_normalizada(placa) == normal, f"VEI-01 placa {placa!r}"
for placa in ("", None, "BR2E19", "BRA2E1", "1BC1234", "ABC-1D23", "ABCD123", "ABC12345"):
    assert cadastros.placa_normalizada(placa) is None, f"VEI-01 placa inválida aceita: {placa!r}"
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    antes = contar(ponte, "veiculos")
    for campo, valor in (("numero", ""), ("numero", None), ("numero", "12345678901"), ("numero", "40 01"),
                         ("placa", "BR2E19"), ("placa", "ABC-1D23"), ("placa", None), ("tipo", "moto"), ("tipo", None),
                         ("transporta", "gado"), ("transporta", None), ("ano", 1900), ("ano", "2019"), ("ano", True),
                         ("ano", 2028), ("situacao", "vendido"), ("modelo", "x" * 81)):
        resposta = erro(ponte.veiculo_salvar({**VEICULO, campo: valor}), "invalido", f"VEI-01 {campo}={valor!r}")
        assert resposta["campo"] == campo, f"VEI-01 campo com o nome da propriedade: {campo} × {resposta}"
    for campo in ("numero", "placa", "tipo", "transporta"):
        sem = {chave: valor for chave, valor in VEICULO.items() if chave != campo}
        assert erro(ponte.veiculo_salvar(sem), "invalido", f"VEI-01 sem {campo}")["campo"] == campo, campo
    assert contar(ponte, "veiculos") == antes, "VEI-01 nada gravado"
    novo = dados(ponte.veiculo_salvar({**VEICULO, "placa": " abc1234 ", "ano": 2027, "modelo": "Sprinter"}))
    assert novo == {"id": novo["id"], "numero": "4001", "placa": "ABC-1234", "tipo": "van", "transporta": "passageiros",
                    "modelo": "Sprinter", "ano": 2027, "situacao": "em_uso", "caixa_id": None}, f"VEI-01 {novo}"
    repetido = erro(ponte.veiculo_salvar({**VEICULO, "placa": "XYZ9A99"}), "conflito", "VEI-01 número repetido")
    assert repetido["campo"] == "numero" and repetido["erro"] == "Já existe um veículo com este número.", repetido
    erro(ponte.veiculo_salvar({**VEICULO, "numero": "2240"}), "conflito", "VEI-01 número da demonstração")
    editado = dados(ponte.veiculo_salvar({**novo, "situacao": "oficina", "ano": ""}), "VEI-01 editar o mesmo")
    assert editado["situacao"] == "oficina" and editado["ano"] is None, f"VEI-01 {editado}"
    erro(ponte.veiculo_salvar({**VEICULO, "id": 9999}), "nao_encontrado", "VEI-01 editar o que não existe")
    assert contar(ponte, "veiculos") == antes + 1, "VEI-01 só o válido entrou"
    fechar(ponte)
ok("VEI-01 placas iguais às da tela (ABC-1234 com hífen, maiúsculas); número único; tipo, transporta, ano e situação "
   "conferidos com campo igual à propriedade")

# VEI-02 · "transporta" define a regra de descanso (carga 30 min a cada 6 h; passageiros 30 min a cada 4 h)
assert cadastros.regra_descanso("carga") == {"descanso_min": 30, "a_cada_min": 360}, "VEI-02 carga"
assert cadastros.regra_descanso("passageiros") == {"descanso_min": 30, "a_cada_min": 240}, "VEI-02 passageiros"
regra = cadastros.regra_descanso("carga")
regra["a_cada_min"] = 1
assert cadastros.regra_descanso("carga")["a_cada_min"] == 360, "VEI-02 a regra devolvida é uma cópia"
try:
    cadastros.regra_descanso("gado")
except ErroPainel as falha:
    assert falha.campo == "transporta", falha.resposta()
else:
    raise AssertionError("VEI-02 transporte desconhecido sem regra")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    for numero, descanso in (("3302", 360), ("2240", 240)):
        veiculo = por_numero(ponte, numero)
        assert cadastros.regra_descanso(veiculo["transporta"])["a_cada_min"] == descanso, f"VEI-02 {numero}"
    fechar(ponte)
print("-- VEI-02 parcial: o relatório da viagem ainda não usa o cadastro; conferida só a regra por tipo de transporte")
ok("VEI-02 carga 30 min a cada 6 h e passageiros 30 min a cada 4 h, pelo 'transporta' do veículo")

# CXA-01 · caixas só vêm do arquivo da empresa; o painel não cria caixa
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t, arquivo=chaveiro())
    caixas = dados(ponte.caixas_listar())
    assert [(c["codigo"], c["veiculo_id"], c["situacao"]) for c in caixas] == \
        [("RG-ABCDEFGHIJKL", None, "ok"), ("RG-MNOPQRSTUVWX", None, "bloqueada")], f"CXA-01 {caixas}"
    assert set(caixas[0]) == {"id", "codigo", "veiculo_id", "situacao", "detalhe", "ultima_coleta", "versao"}
    guardadas = ponte._n().banco.todos("SELECT dispositivo_id, geracao, revogada_em FROM caixas ORDER BY codigo")
    assert [tuple(l) for l in guardadas] == [(3, 1, None), (4, 2, "2026-09-12T10:00:00.000Z")], "CXA-01 dados do arquivo"
    assert {nome for nome in dir(ponte) if "caixa" in nome} == {"caixas_listar", "caixa_vincular"}, \
        "CXA-01 a ponte não tem método para criar caixa"
    assert erro(ponte.caixa_vincular(9999, None), "nao_encontrado")["campo"] == "caixa_id", "CXA-01 caixa inexistente"
    veiculos_antes = contar(ponte, "veiculos")
    erro(ponte.veiculo_salvar({**VEICULO, "caixa_id": 9999}), "nao_encontrado", "CXA-01 veículo com caixa inexistente")
    assert contar(ponte, "veiculos") == veiculos_antes and not linhas(ponte, "cadastrou veículo"), \
        "CXA-01 nada fica gravado quando a caixa não existe"
    assert contar(ponte, "caixas") == 2, "CXA-01 nenhuma caixa nova"
    fechar(ponte)
    demo = pronta(Path(tmp) / "demo", t)
    codigos = {c["codigo"]: c for c in dados(demo.caixas_listar())}
    assert len(codigos) == 8 and codigos["RG-0155"]["veiculo_id"] is None, "CXA-01 caixas da demonstração"
    assert (codigos["RG-0129"]["situacao"], codigos["RG-0129"]["detalhe"]) == ("atencao", cadastros.DEMO_DETALHE_RG_0129)
    fechar(demo)
ok("CXA-01 ativar com arquivo traz só as caixas dele (código, geração, revogação); ponte sem criar caixa; caixa "
   "inexistente não grava veículo; demonstração com 8 caixas e RG-0155 livre")

# CXA-02 · uma caixa em um veículo por vez; trocar guarda o histórico e não muda viagens antigas
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    banco = ponte._n().banco
    livre, rg0142, onibus = por_codigo(ponte, "RG-0155"), por_codigo(ponte, "RG-0142"), por_numero(ponte, "2240")
    ocupado = erro(ponte.caixa_vincular(livre["id"], onibus["id"]), "conflito", "CXA-02 veículo já tem caixa")
    assert ocupado["campo"] == "caixa_id" and "RG-0142" in ocupado["erro"], f"CXA-02 {ocupado}"
    t[0] += 60
    van = dados(ponte.veiculo_salvar({**VEICULO, "caixa_id": livre["id"]}), "CXA-02 veiculo_salvar com caixa_id")
    assert van["caixa_id"] == livre["id"] and por_codigo(ponte, "RG-0155")["veiculo_id"] == van["id"], "CXA-02 vinculou"
    assert "RG-0155" not in [c["codigo"] for c in dados(ponte.caixas_listar()) if c["veiculo_id"] is None], \
        "CXA-02 a caixa sai da lista de livres"
    assert ultima_linha(ponte, "instalou caixa")["detalhe"] == "Veículo 4001", "CXA-02 instalação registrada"
    antes_da_troca = iso_utc(t[0])
    t[0] += 60
    caminhao = dados(ponte.veiculo_salvar({**VEICULO, "numero": "4002", "tipo": "caminhao", "transporta": "carga"}))
    t[0] += 60
    movida = dados(ponte.caixa_vincular(rg0142["id"], caminhao["id"]))
    assert movida["veiculo_id"] == caminhao["id"] and por_numero(ponte, "2240")["caixa_id"] is None, "CXA-02 trocou"
    assert ultima_linha(ponte, "trocou caixa de veículo")["detalhe"] == "Veículo 2240 → Veículo 4002", "CXA-02 registro"
    cad = ponte._n().cadastros
    assert cad.veiculo_da_caixa_em("RG-0142", antes_da_troca) == onibus["id"], "CXA-02 viagem antiga fica no 2240"
    assert cad.veiculo_da_caixa_em("RG-0142", iso_utc(t[0])) == caminhao["id"], "CXA-02 viagem nova vai para o 4002"
    vinculos = banco.todos("SELECT veiculo_id, ate FROM caixa_vinculos WHERE caixa_id = ? ORDER BY id", (rg0142["id"],))
    assert [tuple(l) for l in vinculos] == [(onibus["id"], iso_utc(t[0])), (caminhao["id"], None)], \
        f"CXA-02 histórico de vínculos: {[tuple(l) for l in vinculos]}"
    t[0] += 60
    dados(ponte.caixa_vincular(rg0142["id"], None))
    assert ultima_linha(ponte, "retirou caixa do veículo")["detalhe"] == "Veículo 4002", "CXA-02 retirada registrada"
    t[0] += 60
    dados(ponte.veiculo_salvar({**van, "caixa_id": rg0142["id"]}), "CXA-02 trocar a caixa pelo veículo")
    assert por_codigo(ponte, "RG-0155")["veiculo_id"] is None and por_codigo(ponte, "RG-0142")["veiculo_id"] == van["id"]
    dados(ponte.veiculo_salvar({**por_numero(ponte, "4001"), "caixa_id": None}), "CXA-02 tirar a caixa pelo veículo")
    assert por_numero(ponte, "4001")["caixa_id"] is None, "CXA-02 caixa_id null tira a caixa"
    try:
        banco.executar("UPDATE caixas SET veiculo_id = ? WHERE codigo IN ('RG-0139', 'RG-0155')", (van["id"],))
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("CXA-02 o banco aceitou duas caixas no mesmo veículo")
    fechar(ponte)
ok("CXA-02 veículo com caixa recusa outra; veiculo_salvar com caixa_id vincula e tira dos livres; trocar fecha o "
   "vínculo antigo e a viagem antiga continua no veículo de antes; retirar e trocar registrados")

# CXA-03 · caixa revogada não importa viagem e aparece bloqueada
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t, arquivo=chaveiro())
    bloqueada = por_codigo(ponte, "RG-MNOPQRSTUVWX")
    assert (bloqueada["situacao"], bloqueada["detalhe"]) == ("bloqueada", "Caixa bloqueada pela RotaGuard"), bloqueada
    cad = ponte._n().cadastros
    assert cad.caixa_pode_importar("RG-ABCDEFGHIJKL") is True, "CXA-03 caixa normal importa"
    assert cad.caixa_pode_importar("RG-MNOPQRSTUVWX") is False and cad.caixa_pode_importar("RG-0000") is False, \
        "CXA-03 revogada ou desconhecida não importa"
    veiculo = dados(ponte.veiculo_salvar(VEICULO))
    recusa = erro(ponte.caixa_vincular(bloqueada["id"], veiculo["id"]), "conflito", "CXA-03 instalar revogada")
    assert recusa["campo"] == "caixa_id" and "Caixa bloqueada pela RotaGuard" in recusa["erro"], recusa
    erro(ponte.veiculo_salvar({**veiculo, "caixa_id": bloqueada["id"]}), "conflito", "CXA-03 revogada pelo veículo")
    assert por_codigo(ponte, "RG-MNOPQRSTUVWX")["veiculo_id"] is None, "CXA-03 continua sem veículo"
    fechar(ponte)
print("-- CXA-03 parcial: a importação de viagem ainda não existe; conferida a regra caixa_pode_importar")
ok("CXA-03 revogada no arquivo aparece como 'Caixa bloqueada pela RotaGuard', não importa e não é instalada")

# CAD-01 · nada é apagado: desligado e fora de uso continuam no banco
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    apagar = [nome for nome in dir(ponte) if any(p in nome for p in ("apagar", "excluir", "remover", "deletar"))]
    assert apagar == [], f"CAD-01 a ponte não tem como apagar cadastro: {apagar}"
    dados(ponte.motorista_salvar({**por_ref(ponte, "m-01"), "situacao": "desligado"}))
    carlos = por_ref(ponte, "m-01")
    assert carlos["situacao"] == "desligado" and carlos["termo"]["assinado"] is True, f"CAD-01 {carlos}"
    dados(ponte.veiculo_salvar({**por_numero(ponte, "3302"), "situacao": "fora_de_uso"}))
    assert por_numero(ponte, "3302")["situacao"] == "fora_de_uso" and por_numero(ponte, "3302")["caixa_id"], "CAD-01"
    assert (contar(ponte, "motoristas"), contar(ponte, "veiculos")) == (5, 7), "CAD-01 nada saiu do banco"
    fechar(ponte)
print("-- CAD-01 parcial: sair das listas do dia a dia é filtro da tela (abas por situação); viagens antigas ainda "
      "não ficam no banco do painel")
ok("CAD-01 desligar motorista e tirar veículo de uso mantêm o cadastro, o termo e a caixa; ponte sem método de apagar")


def linha_agora(ponte, t, acao, alvo, detalhe=None):
    linha = ultima_linha(ponte, acao)
    assert linha["em"] == iso_utc(t[0]) and linha["alvo"] == alvo, f"CAD-02 '{acao}' quando ou em quê: {dict(linha)}"
    assert detalhe is None or linha["detalhe"] == detalhe, f"CAD-02 '{acao}' detalhe: {linha['detalhe']!r}"


# CAD-02 · criação, edição, troca de caixa e exportação geram linha no registro
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    t[0] += 60
    pedro = dados(ponte.motorista_salvar(BASE))
    linha_agora(ponte, t, "cadastrou motorista", "Pedro S. (matrícula 0999)")
    t[0] += 60
    pedro = dados(ponte.motorista_salvar({**pedro, "telefone": "(11) 91234-5678", "cnh_categoria": "E"}))
    linha_agora(ponte, t, "editou motorista", "Pedro S. (matrícula 0999)", "campos: telefone, cnh_categoria")
    edicoes = len(linhas(ponte, "editou motorista"))
    dados(ponte.motorista_salvar(pedro))
    assert len(linhas(ponte, "editou motorista")) == edicoes, "CAD-02 salvar sem mudar não registra"
    t[0] += 60
    van = dados(ponte.veiculo_salvar(VEICULO))
    linha_agora(ponte, t, "cadastrou veículo", "Veículo 4001")
    t[0] += 60
    van = dados(ponte.veiculo_salvar({**van, "placa": "XYZ9A99"}))
    linha_agora(ponte, t, "editou veículo", "Veículo 4001", "campos: placa")
    t[0] += 60
    dados(ponte.caixa_vincular(por_codigo(ponte, "RG-0155")["id"], van["id"]))
    linha_agora(ponte, t, "instalou caixa", "RG-0155", "Veículo 4001")
    t[0] += 60
    dados(ponte.caixa_vincular(por_codigo(ponte, "RG-0155")["id"], None))
    linha_agora(ponte, t, "retirou caixa do veículo", "RG-0155", "Veículo 4001")
    t[0] += 60
    dados(ponte.caixa_vincular(por_codigo(ponte, "RG-0142")["id"], van["id"]))
    linha_agora(ponte, t, "trocou caixa de veículo", "RG-0142", "Veículo 2240 → Veículo 4001")
    t[0] += 60
    dados(ponte.motorista_exportar(pedro["id"]))
    linha_agora(ponte, t, "exportou dados do motorista", "Pedro S.")
    fechar(ponte)
ok("CAD-02 cadastrou e editou motorista e veículo (com os campos), instalou, retirou e trocou caixa e exportou, "
   "com quem, quando e em quê; salvar sem mudança não registra")

# EQP-04 (demonstração) · decisões de demonstração iguais às da tela, sem linha no registro
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = nova_ponte(tmp, t)
    dados(ponte.ativar_demonstracao(ADMIN))
    decisoes = dados(ponte.decisoes_listar())
    assert decisoes == [
        {"momento_id": "v-1187-e-202", "resultado": "alarme_falso", "orientado": False, "por": "Marina (gestora)",
         "funcao": "administrador", "em": "2026-09-14T06:58"},
        {"momento_id": "v-1187-e-203", "resultado": "confirmado", "orientado": True, "por": "Marina (gestora)",
         "funcao": "administrador", "em": "2026-09-14T06:58"}], f"EQP-04 decisões de demonstração: {decisoes}"
    guardadas = ponte._n().banco.todos("SELECT uid, criado_em, alterado_em, ativa FROM decisoes ORDER BY id")
    assert all(len(l["uid"]) == 32 and l["criado_em"] and l["alterado_em"] and l["ativa"] == 1 for l in guardadas)
    acoes = [l["acao"] for l in ponte._n().banco.todos("SELECT acao FROM atividades ORDER BY id")]
    assert acoes == ["ativou o painel", "entrou"], f"EQP-04 demonstração sem linha de decisão no registro: {acoes}"
    dados(ponte.decisao_desfazer("v-1187-e-202"))
    assert [d["momento_id"] for d in dados(ponte.decisoes_listar())] == ["v-1187-e-203"], "EQP-04 desfazer vale"
    fechar(ponte)
ok("EQP-04 (demonstração) v-1187-e-202 alarme falso e v-1187-e-203 confirmado e orientado, por Marina (gestora) às "
   "06:58, com uid, sem linha no registro")

print(f"\n{checks} verificações OK")
