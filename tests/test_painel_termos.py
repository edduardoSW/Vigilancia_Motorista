"""Spec 019: termo assinado importado como comprovante (núcleo Python).

Sem janela e sem pywebview: a Ponte é chamada direto, com relógio falso, scrypt barato, pasta temporária, script local
falso e abridor de arquivo falso (nenhum leitor de PDF abre). Arquivos de teste descartáveis, feitos aqui. Biblioteca
padrão e o cryptography do .venv (a cópia usa AES-GCM):
    python tests/test_painel_termos.py
"""
import base64
import hashlib
import io
import json
import os
import sqlite3
import stat
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import cadastros  # noqa: E402
import copia  # noqa: E402
import dados as modulo_dados  # noqa: E402
from atividades import Atividades  # noqa: E402
from configuracoes import Configuracoes  # noqa: E402
from contas import Contas  # noqa: E402
from dados import Banco, ErroPainel, iso_utc  # noqa: E402
from ponte import Ponte  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc).timestamp()
HOJE = "2026-09-14"
# Senhas descartáveis, só deste teste.
SENHA_ADM = "frase comprida de teste um"
SENHA_SUP = "frase comprida de teste dois"
SENHA_CON = "frase comprida de teste tres"
SENHA_COPIA = "frase da copia de teste"
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}
# Arquivos de teste: só a assinatura de cada tipo e alguns bytes.
MARCA = b"marca-unica-do-termo-de-teste"
PDF = b"%PDF-1.4\n% " + MARCA + b"\n1 0 obj <<>> endobj\ntrailer <<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + bytes(17) + b"png-de-teste"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(20) + b"\xff\xd9"
EXE = b"MZ\x90\x00\x03" + bytes(59) + b"This program cannot be run in DOS mode"
MSG_TIPO = "Use um PDF ou uma foto (PNG ou JPEG) do termo assinado."
MSG_TAMANHO = "O arquivo pode ter até 10 MB."
MSG_SEM_ARQUIVO = "Este motorista não tem o arquivo do termo."
MSG_ALTERADO = "O arquivo do termo foi alterado fora do painel."
LIMITE = 10 * 1024 * 1024


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


def nova_ponte(tmp, relogio, abertos, pasta=None):
    return Ponte(pasta if pasta is not None else Path(tmp) / "dados", relogio=lambda: relogio[0],
                 custo_scrypt=CUSTO_TESTE, escolher_destino=lambda nome: Path(tmp) / nome, script_local=ScriptFalso(),
                 abrir_arquivo=abertos.append)


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


def pronta(tmp, relogio, abertos):
    """Demonstração ativada, com o supervisor Paulo Reis e a consulta Ana Souza; volta com o Paulo na sessão."""
    ponte = nova_ponte(tmp, relogio, abertos)
    dados(ponte.ativar_demonstracao(ADMIN), "ativar demonstração")
    for nome, usuario, funcao, senha in (("Ana Souza", "ana.souza", "consulta", SENHA_CON),
                                         ("Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP)):
        entrar_como(ponte, "marina.lopes", SENHA_ADM)
        novo = dados(ponte.equipe_adicionar({"nome": nome, "usuario": usuario, "funcao": funcao}), usuario)
        entrar_como(ponte, usuario, novo["senha_temporaria"])
        dados(ponte.trocar_senha(novo["senha_temporaria"], senha), usuario)
    return ponte


def b64(conteudo):
    return base64.b64encode(conteudo).decode("ascii")


def arquivo(nome, conteudo):
    return {"nome": nome, "conteudo_base64": b64(conteudo)}


def sha(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


def por_ref(ponte, ref):
    return [m for m in dados(ponte.motoristas_listar()) if m["ref"] == ref][0]


def arquivos_termos(tmp):
    pasta = Path(tmp) / "dados" / "termos"
    return sorted(p.name for p in pasta.iterdir()) if pasta.exists() else []


def termo_mais_novo(ponte, motorista_id):
    return ponte._n().banco.um("SELECT * FROM termos WHERE motorista_id = ? ORDER BY id DESC LIMIT 1", (motorista_id,))


def liberar_escrita(caminho):
    os.chmod(caminho, stat.S_IREAD | stat.S_IWRITE)


# TER-01 · só PDF, PNG ou JPEG (primeiros bytes) até 10 MB, com data não futura; o resto é recusado e nada é gravado
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t, abertos = [T0], []
    ponte = pronta(tmp, t, abertos)
    marcos = por_ref(ponte, "m-05")
    termos_antes = contar(ponte, "termos")
    for nome, conteudo in (("termo-marcos.pdf", EXE), ("termo.pdf", b"ola, sou texto"), ("vazio.pdf", b""),
                           ("termo.gif", b"GIF89a" + bytes(10)), ("cortado.pdf", b"%PDF"), ("espaco.pdf", b" %PDF-1.4"),
                           ("quase.png", PNG[:7]), ("quase.jpg", b"\xff\xd8")):
        resposta = erro(ponte.termo_importar(marcos["id"], arquivo(nome, conteudo), {"data": HOJE}), "invalido",
                        f"TER-01 {nome}")
        assert (resposta["campo"], resposta["erro"]) == ("arquivo", MSG_TIPO), f"TER-01 {nome}: {resposta}"
    for ruim in ("não é base64!", "JVBERi0", "JVBERi0x\n", " JVBERi0x", "JVBERi0x====", "JVBE Ri0x", 123, None):
        resposta = erro(ponte.termo_importar(marcos["id"], {"nome": "t.pdf", "conteudo_base64": ruim}, {"data": HOJE}),
                        "invalido", f"TER-01 base64 {ruim!r}")
        assert resposta["campo"] == "arquivo", f"TER-01 base64 estrito {ruim!r}: {resposta}"
    for forma in (None, "termo.pdf", ["termo.pdf"], {"nome": "t.pdf"}, {"conteudo_base64": b64(PDF)},
                  {"nome": 5, "conteudo_base64": b64(PDF)}):
        resposta = erro(ponte.termo_importar(marcos["id"], forma, {"data": HOJE}), "invalido", f"TER-01 {forma!r}")
        assert resposta["campo"] == "arquivo", f"TER-01 arquivo sem nome ou conteúdo {forma!r}: {resposta}"
    grande = b"%PDF-1.4\n" + bytes(LIMITE + 1 - 9)
    for nome, conteudo_base64 in (("grande.pdf", b64(grande)), ("enorme.pdf", "A" * (4 * ((LIMITE + 2) // 3) + 4)),
                                  ("grande.exe", b64(EXE + bytes(LIMITE)))):
        resposta = erro(ponte.termo_importar(marcos["id"], {"nome": nome, "conteudo_base64": conteudo_base64},
                                             {"data": HOJE}), "invalido", f"TER-01 {nome}")
        assert (resposta["campo"], resposta["erro"]) == ("arquivo", MSG_TAMANHO), f"TER-01 {nome}: {resposta}"
    for data in ("2026-09-15", "2027-01-01", "14/09/2026", "2026-02-30", "", None, 20260914):
        resposta = erro(ponte.termo_importar(marcos["id"], arquivo("t.pdf", PDF), {"data": data}), "invalido",
                        f"TER-01 data {data!r}")
        assert resposta["campo"] == "data", f"TER-01 data {data!r}: {resposta}"
    assert "futur" in erro(ponte.termo_importar(marcos["id"], arquivo("t.pdf", PDF), {"data": "2026-09-15"}),
                           "invalido")["erro"], "TER-01 data futura com frase simples"
    for forma in ("2026-09-14", None, {}):
        assert erro(ponte.termo_importar(marcos["id"], arquivo("t.pdf", PDF), forma), "invalido")["campo"] == "data", \
            f"TER-01 dados sem data {forma!r}"
    for versao in (7, "x" * 21, ["1"]):
        resposta = erro(ponte.termo_importar(marcos["id"], arquivo("t.pdf", PDF), {"data": HOJE, "versao": versao}),
                        "invalido", f"TER-01 versão {versao!r}")
        assert resposta["campo"] == "versao", f"TER-01 versão {versao!r}: {resposta}"
    for motorista_id in (999999, "1", True, None):
        resposta = erro(ponte.termo_importar(motorista_id, arquivo("t.pdf", PDF), {"data": HOJE}), "nao_encontrado",
                        f"TER-01 motorista {motorista_id!r}")
        assert resposta["erro"] == "Motorista não encontrado.", f"TER-01 frase do motorista inexistente: {resposta}"
    assert contar(ponte, "termos") == termos_antes and arquivos_termos(tmp) == [], "TER-01 recusado não grava nada"
    assert not linhas(ponte, "importou termo assinado"), "TER-01 recusado não entra no registro"
    assert por_ref(ponte, "m-05")["termo"] == {"assinado": False, "data": None, "versao": None, "arquivo": None}, \
        "TER-01 Marcos continua sem termo depois das recusas"
    assert dados(ponte.video_abrir("v-1187-e-202", "m-05"))["liberado"] is False, "TER-01 continua trancado"
    no_limite = b"%PDF-1.4\n" + bytes(LIMITE - 9)
    aceito = dados(ponte.termo_importar(marcos["id"], arquivo("termo-10mb.pdf", no_limite), {"data": "2026-09-01"}),
                   "TER-01 exatamente 10 MB e data passada")
    assert aceito["termo"]["arquivo"]["bytes"] == LIMITE and aceito["termo"]["data"] == "2026-09-01", \
        f"TER-01 exatamente 10 MB aceito: {aceito['termo']}"
    dados(ponte.termo_importar(marcos["id"], arquivo("termo.jpg", JPEG), {"data": HOJE, "versao": "  "}), "TER-01 hoje")
    assert por_ref(ponte, "m-05")["termo"]["versao"] == "1", "TER-01 versão vazia vira 1"
    assert abertos == [] and not ponte._falhas, f"TER-01 {abertos} {ponte._falhas}"
    fechar(ponte)
ok("TER-01 .exe renomeado, texto, GIF, vazio e assinatura cortada → 'Use um PDF ou uma foto...'; base64 não estrito, "
   "arquivo sem nome ou conteúdo, mais de 10 MB, data futura ou inválida, versão ruim e motorista inexistente "
   "recusados com o campo; nada gravado; exatamente 10 MB e data de hoje aceitos")

# TER-02 · arquivo em termos/ com SHA-256; ver mostra a foto e abre o PDF; alterado fora do painel é detectado
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t, abertos = [T0], []
    ponte = pronta(tmp, t, abertos)
    banco = ponte._n().banco
    marcos, carlos, juliana, aline = (por_ref(ponte, ref) for ref in ("m-05", "m-01", "m-02", "m-04"))
    t[0] += 60
    devolvido = dados(ponte.termo_importar(marcos["id"], arquivo("termo-marcos.pdf", PDF), {"data": HOJE, "versao": None}))
    assert devolvido == por_ref(ponte, "m-05") and set(devolvido) == set(marcos), "TER-02 devolve o Motorista da lista"
    assert devolvido["termo"] == {"assinado": True, "data": HOJE, "versao": "1", "arquivo": {
        "nome": "termo-marcos.pdf", "tipo": "pdf", "bytes": len(PDF), "importado_em": iso_utc(t[0]),
        "importado_por": "Paulo Reis"}}, f"TER-02 termo com arquivo: {devolvido['termo']}"
    linha = termo_mais_novo(ponte, marcos["id"])
    assert (linha["arquivo_caminho"], linha["arquivo_sha256"], linha["arquivo_tipo"], linha["arquivo_mime"],
            linha["arquivo_bytes"], linha["arquivo_nome"], linha["registrado_por"], linha["assinado"]) == \
        (f"termos/{linha['uid']}.pdf", sha(PDF), "pdf", "application/pdf", len(PDF), "termo-marcos.pdf", "Paulo Reis", 1), \
        f"TER-02 registro no banco: {dict(linha)}"
    caminho = Path(tmp) / "dados" / linha["arquivo_caminho"]
    assert caminho.read_bytes() == PDF and arquivos_termos(tmp) == [caminho.name], "TER-02 um arquivo, sem .tmp"
    assert not os.access(caminho, os.W_OK), "TER-02 arquivo guardado só para leitura (o leitor de PDF não grava nele)"
    assert dados(ponte.video_abrir("v-1187-e-202", "m-05"))["liberado"] is True, "TER-02 vídeos do Marcos destrancam"
    assert dados(ponte.termo_ver(marcos["id"])) == {"tipo": "pdf", "nome": "termo-marcos.pdf", "aberto": True}, \
        "TER-02 ver o PDF devolve tipo, nome e aberto"
    assert abertos == [caminho], f"TER-02 o PDF abre no leitor do computador: {abertos}"
    dados(ponte.termo_importar(carlos["id"], arquivo("foto do termo.png", PNG), {"data": HOJE}))
    dados(ponte.termo_importar(juliana["id"], arquivo("termo.jpeg", JPEG), {"data": HOJE}))
    assert dados(ponte.termo_ver(carlos["id"])) == {"tipo": "imagem", "nome": "foto do termo.png",
                                                   "conteudo": "data:image/png;base64," + b64(PNG)}, "TER-02 PNG"
    assert dados(ponte.termo_ver(juliana["id"])) == {"tipo": "imagem", "nome": "termo.jpeg",
                                                    "conteudo": "data:image/jpeg;base64," + b64(JPEG)}, "TER-02 JPEG"
    assert abertos == [caminho], "TER-02 foto aparece no painel, sem chamar o leitor"
    assert termo_mais_novo(ponte, juliana["id"])["arquivo_caminho"].endswith(".jpg"), "TER-02 JPEG guardado como .jpg"
    for bruto, limpo in (("C:\\Users\\ana\\Documentos\\termo-aline.pdf", "termo-aline.pdf"),
                         ("../../etc/termo.pdf", "termo.pdf"), ("termo\x00\n\tassinado.pdf", "termoassinado.pdf"),
                         ("   termo    da   Aline .pdf  ", "termo da Aline .pdf"), ("..", "termo-assinado.pdf"),
                         ("", "termo-assinado.pdf"), ("a" * 200 + ".pdf", "a" * 116 + ".pdf")):
        nome = dados(ponte.termo_importar(aline["id"], arquivo(bruto, PDF), {"data": HOJE}))["termo"]["arquivo"]["nome"]
        assert nome == limpo, f"TER-02 nome limpo {bruto!r} → {nome!r}, esperado {limpo!r}"
    liberar_escrita(caminho)
    caminho.write_bytes(PDF.replace(b"1.4", b"1.7"))
    alterado = erro(ponte.termo_ver(marcos["id"]), "conflito", "TER-02 PDF alterado fora do painel")
    assert alterado["erro"] == MSG_ALTERADO and abertos == [caminho], f"TER-02 não abre o alterado: {alterado}"
    foto = Path(tmp) / "dados" / termo_mais_novo(ponte, carlos["id"])["arquivo_caminho"]
    liberar_escrita(foto)
    foto.unlink()
    sumiu = erro(ponte.termo_ver(carlos["id"]), "conflito", "TER-02 arquivo apagado fora do painel")
    assert "sumiu" in sumiu["erro"], f"TER-02 frase do arquivo que sumiu: {sumiu}"
    rogerio = por_ref(ponte, "m-03")
    assert erro(ponte.termo_ver(rogerio["id"]), "nao_encontrado")["erro"] == MSG_SEM_ARQUIVO, "TER-02 termo sem arquivo"
    assert erro(ponte.termo_ver(999999), "nao_encontrado")["erro"] == "Motorista não encontrado.", "TER-02 inexistente"
    mantido = dados(ponte.motorista_salvar({**por_ref(ponte, "m-02"), "telefone": "(11) 90000-2222"}))
    assert mantido["termo"]["arquivo"]["nome"] == "termo.jpeg", "TER-02 editar o motorista sem mexer no termo mantém o arquivo"
    # Bug de 15/09 (visto na revisão da tela): alteração sem as chaves "termo" e "situacao" revogava o termo e reativava.
    dados(ponte.motorista_salvar({**por_ref(ponte, "m-02"), "situacao": "afastado"}))
    parcial = {chave: valor for chave, valor in por_ref(ponte, "m-02").items() if chave not in ("termo", "situacao")}
    sem_chaves = dados(ponte.motorista_salvar({**parcial, "telefone": "(11) 90000-3333"}))
    assert sem_chaves["termo"]["assinado"] is True and (sem_chaves["termo"]["arquivo"] or {}).get("nome") == "termo.jpeg", \
        f"TER-02 alterar sem mandar o termo não revoga nem tira o arquivo: {sem_chaves['termo']}"
    assert sem_chaves["situacao"] == "afastado", f"TER-02 alterar sem mandar a situação mantém a situação: {sem_chaves['situacao']}"
    assert linhas(ponte, "revogou termo de ciência") == [], "TER-02 alteração sem o termo não registra revogação"
    revogado = dados(ponte.motorista_salvar({**por_ref(ponte, "m-05"), "termo": {"assinado": False}}))
    assert revogado["termo"]["arquivo"] is None, "TER-02 revogado fica sem arquivo"
    assert erro(ponte.termo_ver(marcos["id"]), "nao_encontrado")["erro"] == MSG_SEM_ARQUIVO, "TER-02 revogado"
    registrado = dados(ponte.motorista_salvar({**revogado, "termo": {"assinado": True, "data": HOJE, "versao": "2"}}))
    assert registrado["termo"] == {"assinado": True, "data": HOJE, "versao": "2", "arquivo": None}, \
        f"TER-02 termo registrado pelo cadastro fica sem arquivo: {registrado['termo']}"
    assert erro(ponte.termo_ver(marcos["id"]), "nao_encontrado")["erro"] == MSG_SEM_ARQUIVO, "TER-02 sem o arquivo"
    assert not ponte._falhas, f"TER-02 falha interna: {ponte._falhas}"
    fechar(ponte)
ok("TER-02 termos/<uid>.pdf|png|jpg só leitura com SHA-256, tipo, MIME, bytes e nome limpo; Motorista da lista com "
   "arquivo; foto volta em data:image, PDF chama o leitor; alterado ou apagado fora do painel → conflito; sem arquivo "
   "ou revogado → nao_encontrado; editar sem mexer no termo mantém o arquivo")

# TER-03 · nada é apagado: trocar cria registro novo; o histórico mostra quem importou e quando
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t, abertos = [T0], []
    ponte = pronta(tmp, t, abertos)
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    marcos = por_ref(ponte, "m-05")
    t[0] += 60
    dados(ponte.termo_importar(marcos["id"], arquivo("termo-v1.pdf", PDF), {"data": "2026-09-10", "versao": "1"}))
    t1 = iso_utc(t[0])
    t[0] += 60
    dados(ponte.termo_importar(marcos["id"], arquivo("termo-v2.png", PNG), {"data": HOJE, "versao": "2"}))
    t2 = iso_utc(t[0])
    t[0] += 60
    dados(ponte.motorista_salvar({**por_ref(ponte, "m-05"), "termo": {"assinado": False, "data": None, "versao": None}}))
    t3 = iso_utc(t[0])
    historico = dados(ponte.motorista_termos(marcos["id"]))
    assert [(h["assinado"], h["data"], h["versao"], h["registrado_por"], h["registrado_em"]) for h in historico] == \
        [(False, None, None, "Marina Lopes", t3), (True, HOJE, "2", "Marina Lopes", t2),
         (True, "2026-09-10", "1", "Marina Lopes", t1)], f"TER-03 histórico do mais novo para o mais velho: {historico}"
    assert all(set(h) == {"id", "assinado", "data", "versao", "registrado_por", "registrado_em", "arquivo"}
               for h in historico) and [h["id"] for h in historico] == sorted((h["id"] for h in historico), reverse=True), \
        f"TER-03 TermoRegistro com os campos do contrato, id do mais novo para o mais velho: {historico}"
    assert historico[0]["arquivo"] is None and historico[1]["arquivo"] == {
        "nome": "termo-v2.png", "tipo": "imagem", "bytes": len(PNG), "importado_em": t2, "importado_por": "Marina Lopes"} \
        and historico[2]["arquivo"]["nome"] == "termo-v1.pdf", f"TER-03 arquivos no histórico: {historico}"
    texto = json.dumps(historico, ensure_ascii=False)
    for proibido in ("termos/", "caminho", "sha256", sha(PDF), sha(PNG)):
        assert proibido not in texto, f"TER-03 o histórico não mostra caminho nem hash: {proibido}"
    assert len(arquivos_termos(tmp)) == 2, "TER-03 os dois arquivos continuam na pasta"
    entrar_como(ponte, "paulo.reis", SENHA_SUP)
    assert dados(ponte.motorista_termos(marcos["id"])) == historico, "TER-03 supervisor vê o mesmo histórico"
    demo = dados(ponte.motorista_termos(por_ref(ponte, "m-01")["id"]))
    assert [(h["assinado"], h["registrado_por"], h["arquivo"]) for h in demo] == [(True, "Demonstração", None)], \
        f"TER-03 termo de demonstração continua sem arquivo: {demo}"
    pedro = dados(ponte.motorista_salvar({"nome": "Pedro Santos", "matricula": "0999", "cnh_numero": "12345678900",
                                          "cnh_categoria": "D", "cnh_validade": "2030-01-01"}))
    assert dados(ponte.motorista_termos(pedro["id"])) == [], "TER-03 motorista sem termo"
    for motorista_id in (999999, "1", None):
        erro(ponte.motorista_termos(motorista_id), "nao_encontrado", f"TER-03 motorista {motorista_id!r}")
    for sql in ("UPDATE termos SET arquivo_nome = 'outro.pdf'", "DELETE FROM termos"):
        try:
            ponte._n().banco.executar(sql)
        except sqlite3.DatabaseError as falha:
            assert "nunca" in str(falha), f"TER-03 mensagem do gatilho: {falha}"
        else:
            raise AssertionError(f"TER-03 o gatilho deixou passar: {sql}")
    assert not hasattr(ponte, "termo_apagar") and not ponte._falhas, "TER-03 sem método de apagar termo"
    fechar(ponte)
ok("TER-03 importar de novo e revogar criam registros novos; motorista_termos do mais novo para o mais velho com quem, "
   "quando e o arquivo (sem caminho nem hash); arquivos continuam; gatilhos recusam alterar e apagar")

# TER-04 · só administrador e supervisor importam, veem e listam; Consulta recebe sem_permissao
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t, abertos = [T0], []
    ponte = pronta(tmp, t, abertos)
    marcos = por_ref(ponte, "m-05")
    dados(ponte.termo_importar(marcos["id"], arquivo("termo-marcos.pdf", PDF), {"data": HOJE}), "TER-04 supervisor")
    chamadas = (("termo_importar", (marcos["id"], arquivo("outro.png", PNG), {"data": HOJE})),
                ("termo_ver", (marcos["id"],)), ("motorista_termos", (marcos["id"],)))
    entrar_como(ponte, "ana.souza", SENHA_CON)
    for metodo, args in chamadas:
        antes = len(linhas(ponte, "tentou sem permissão"))
        resposta = getattr(ponte, metodo)(*args)
        assert resposta == {"ok": False, "erro": "Sua função não permite fazer isso.", "codigo": "sem_permissao"}, \
            f"TER-04 consulta × {metodo}: {resposta}"
        novas = linhas(ponte, "tentou sem permissão")[antes:]
        assert [(l["usuario"], l["alvo"]) for l in novas] == [("Ana Souza", "cadastrar")], f"TER-04 registro {metodo}"
    ponte.sair()
    for metodo, args in chamadas:
        erro(getattr(ponte, metodo)(*args), "sem_sessao", f"TER-04 sem sessão × {metodo}")
    entrar_como(ponte, "paulo.reis", SENHA_SUP)
    dados(ponte.bloquear())
    for metodo, args in chamadas:
        erro(getattr(ponte, metodo)(*args), "bloqueado", f"TER-04 tela bloqueada × {metodo}")
    dados(ponte.desbloquear(SENHA_SUP))
    assert abertos == [] and contar(ponte, "termos") == 5 and len(arquivos_termos(tmp)) == 1, "TER-04 nada feito"
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    assert dados(ponte.termo_ver(marcos["id"]))["aberto"] is True and len(abertos) == 1, "TER-04 administradora abre"
    assert len(dados(ponte.motorista_termos(marcos["id"]))) == 1, "TER-04 administradora lista"
    fechar(ponte)
ok("TER-04 consulta recebe sem_permissao em termo_importar, termo_ver e motorista_termos (registro 'tentou sem "
   "permissão' em cadastrar); sem sessão e tela bloqueada recusados; administradora e supervisor passam")

# TER-05 · importar e abrir vão para o registro de atividades
assert [cadastros.formatar_tamanho(n) for n in (0, 1, 1023, 1024, 1536, LIMITE, 1572864)] == \
    ["0 bytes", "1 byte", "1023 bytes", "1 KB", "2 KB", "10 MB", "1,5 MB"], "TER-05 tamanho em pt-BR"
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t, abertos = [T0], []
    ponte = pronta(tmp, t, abertos)
    marcos, carlos = por_ref(ponte, "m-05"), por_ref(ponte, "m-01")

    def ultima(acao):
        achadas = linhas(ponte, acao)
        assert achadas, f"TER-05 falta a linha '{acao}'"
        return (achadas[-1]["usuario"], achadas[-1]["em"], achadas[-1]["alvo"], achadas[-1]["detalhe"])

    t[0] += 60
    dados(ponte.termo_importar(marcos["id"], arquivo("termo-marcos.pdf", PDF), {"data": HOJE}))
    assert ultima("importou termo assinado") == ("Paulo Reis", iso_utc(t[0]), "Marcos T. (matrícula 0467)",
                                                 f"termo-marcos.pdf, {len(PDF)} bytes"), \
        f"TER-05 linha da importação: {ultima('importou termo assinado')}"
    t[0] += 60
    dados(ponte.termo_ver(marcos["id"]))
    assert ultima("abriu termo") == ("Paulo Reis", iso_utc(t[0]), "Marcos T. (matrícula 0467)", "termo-marcos.pdf"), \
        f"TER-05 linha da abertura: {ultima('abriu termo')}"
    t[0] += 60
    dados(ponte.termo_importar(carlos["id"], arquivo("foto.png", PNG + bytes(2048 - len(PNG))), {"data": HOJE}))
    assert ultima("importou termo assinado")[2:] == ("Carlos M. (matrícula 0412)", "foto.png, 2 KB"), "TER-05 KB"
    antes = (len(linhas(ponte, "importou termo assinado")), len(linhas(ponte, "abriu termo")))
    erro(ponte.termo_importar(marcos["id"], arquivo("t.exe", EXE), {"data": HOJE}), "invalido")
    erro(ponte.termo_ver(por_ref(ponte, "m-03")["id"]), "nao_encontrado")
    caminho = Path(tmp) / "dados" / termo_mais_novo(ponte, marcos["id"])["arquivo_caminho"]
    liberar_escrita(caminho)
    caminho.write_bytes(PDF + b"mexido")
    t[0] += 60
    erro(ponte.termo_ver(marcos["id"]), "conflito")
    assert (len(linhas(ponte, "importou termo assinado")), len(linhas(ponte, "abriu termo"))) == antes, \
        "TER-05 recusado não vira 'importou' nem 'abriu'"
    assert ultima("achou termo alterado fora do painel") == ("Paulo Reis", iso_utc(t[0]), "Marcos T. (matrícula 0467)",
                                                             "termo-marcos.pdf"), "TER-05 alteração fica no registro"
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    assert dados(ponte.atividades_listar({}))["integro"] is True, "TER-05 registro íntegro"
    fechar(ponte)
ok("TER-05 'importou termo assinado' (alvo motorista, detalhe nome e tamanho), 'abriu termo' e 'achou termo alterado "
   "fora do painel' com quem e quando; recusados não registram importação nem abertura; registro íntegro")

# TER-06 · a cópia de segurança leva os arquivos dos termos, idênticos
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t, abertos = [T0], []
    ponte = pronta(tmp, t, abertos)
    dados(ponte.termo_importar(por_ref(ponte, "m-05")["id"], arquivo("termo-marcos.pdf", PDF), {"data": HOJE}))
    dados(ponte.termo_importar(por_ref(ponte, "m-01")["id"], arquivo("termo-carlos.png", PNG), {"data": HOJE}))
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    t[0] += 60
    feita = Path(dados(ponte.copia_fazer(SENHA_COPIA))["caminho"])
    bruto = feita.read_bytes()
    for texto in (MARCA, b"termos/", b"painel.db", b"IHDR"):
        assert texto not in bruto, f"TER-06 texto aberto dentro da cópia: {texto!r}"
    cabecalho, conteudo = copia.abrir_copia(feita, SENHA_COPIA)
    assert cabecalho["formato"] == "rotaguard-copia/2", f"TER-06 formato novo: {cabecalho}"
    pacote = copia.conteudo_da_copia(cabecalho, conteudo)
    guardados = {l["arquivo_caminho"]: l["arquivo_sha256"] for l in ponte._n().banco.todos(
        "SELECT arquivo_caminho, arquivo_sha256 FROM termos WHERE arquivo_caminho IS NOT NULL")}
    assert len(guardados) == 2 and set(pacote["arquivos"]) == set(guardados), f"TER-06 arquivos: {list(pacote['arquivos'])}"
    for caminho, impressao in guardados.items():
        original = (Path(tmp) / "dados" / caminho).read_bytes()
        assert sha(pacote["arquivos"][caminho]) == impressao == sha(original), f"TER-06 {caminho} idêntico (SHA-256)"
    restaurado = sqlite3.connect(":memory:")
    restaurado.deserialize(pacote["banco"])
    assert {l[0]: l[1] for l in restaurado.execute(
        "SELECT arquivo_caminho, arquivo_sha256 FROM termos WHERE arquivo_caminho IS NOT NULL")} == guardados, \
        "TER-06 o banco da cópia aponta para os mesmos arquivos"
    restaurado.close()
    banco_bytes = ponte._n().banco.serializar()
    antigo = copia.cifrar(banco_bytes, SENHA_COPIA, CUSTO_TESTE, "2026-09-01T00:00:00Z", formato=copia.FORMATO_1)
    cabecalho_1, conteudo_1 = copia.decifrar(antigo, SENHA_COPIA)
    try:
        pacote_1 = copia.conteudo_da_copia(cabecalho_1, conteudo_1)
    except ErroPainel as falha:
        raise AssertionError(f"TER-06 cópia no formato 1 não abriu: {falha.resposta()}") from None
    assert cabecalho_1["formato"] == "rotaguard-copia/1" and pacote_1 == {"banco": banco_bytes, "arquivos": {}}, \
        "TER-06 cópia no formato 1 continua abrindo, só com o banco"

    def zipado(entradas):
        memoria = io.BytesIO()
        with zipfile.ZipFile(memoria, "w") as pacote_zip:
            for nome, conteudo_zip in entradas:
                pacote_zip.writestr(nome, conteudo_zip)
        return memoria.getvalue()

    for entradas in ((("painel.db", banco_bytes), ("../fora.pdf", PDF)), (("termos/x.pdf", PDF),),
                     (("painel.db", banco_bytes), ("termos/../../fora.pdf", PDF)), (("painel.db", b""), ("outro", b"x"))):
        cab, cont = copia.decifrar(copia.cifrar(zipado(entradas), SENHA_COPIA, CUSTO_TESTE, "", formato=copia.FORMATO),
                                   SENHA_COPIA)
        try:
            copia.conteudo_da_copia(cab, cont)
        except ErroPainel as falha:
            assert falha.campo == "arquivo", f"TER-06 pacote estranho recusado no campo arquivo: {falha.resposta()}"
        else:
            raise AssertionError(f"TER-06 pacote com entradas estranhas aceito: {[n for n, _ in entradas]}")
    try:
        copia.decifrar(copia.cifrar(b"x", SENHA_COPIA, CUSTO_TESTE, "", formato="rotaguard-copia/9"), SENHA_COPIA)
    except ErroPainel:
        pass
    else:
        raise AssertionError("TER-06 formato desconhecido aceito")
    assert not ponte._falhas, f"TER-06 falha interna: {ponte._falhas}"
    fechar(ponte)
ok("TER-06 cópia rotaguard-copia/2 cifrada com painel.db e termos/*, cada arquivo com o mesmo SHA-256 do original e do "
   "banco; formato 1 continua abrindo; pacote com caminho estranho ou formato desconhecido é recusado")

# TER-07 · banco da versão 1 (com dados) sobe para a 2 sem perder nada e com o registro íntegro
TABELAS_V1 = ("meta", "usuarios", "atividades", "motoristas", "termos", "veiculos", "caixas", "caixa_vinculos",
              "configuracoes", "decisoes")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t, abertos = [T0], []
    pasta = Path(tmp) / "v1"
    migracoes = modulo_dados.MIGRACOES
    assert len(migracoes) == 2, f"TER-07 esquema novo é a migração 2: {len(migracoes)}"
    modulo_dados.MIGRACOES = migracoes[:1]
    try:
        antigo = Banco(pasta, relogio=lambda: t[0])
        assert antigo.versao_esquema() == 1, "TER-07 banco criado só com a migração 1"
        atividades, contas = Atividades(antigo), Contas(antigo, Atividades(antigo), lambda: t[0], CUSTO_TESTE)
        with antigo.transacao():
            Configuracoes(antigo, atividades).iniciar(cadastros.DEMO_EMPRESA)
            cadastros.carregar_demonstracao(antigo)
            linha_admin, _codigo = contas.criar_admin_inicial(ADMIN)
            antigo.meta_gravar("modo", "demonstracao")
            antigo.meta_gravar("ativado", "1")
        marina = dict(linha_admin)
        atividades.registrar("ativou o painel", marina, detalhe="demonstração")
        contas.equipe_adicionar({"nome": "Paulo Reis", "usuario": "paulo.reis", "funcao": "supervisor"}, marina)
        marcos_id = antigo.um("SELECT id FROM motoristas WHERE ref = 'm-05'")["id"]
        for assinado, data in ((1, "2026-09-10"), (0, None)):
            antigo.inserir("termos", {"motorista_id": marcos_id, "assinado": assinado, "data": data,
                                      "versao": "1" if assinado else None, "registrado_por": "Marina Lopes"})
        cadastros.Decisoes(antigo, atividades).registrar("v-2240-e-001", "confirmado", marina)
        atividades.registrar("entrou", marina)
        colunas = {tabela: [c["name"] for c in antigo.todos(f"PRAGMA table_info({tabela})")] for tabela in TABELAS_V1}
        antes = {tabela: [tuple(l) for l in antigo.todos(f"SELECT * FROM {tabela} ORDER BY rowid")]
                 for tabela in TABELAS_V1}
        gatilhos = {l["name"] for l in antigo.todos("SELECT name FROM sqlite_master WHERE type = 'trigger'")}
        assert "arquivo_nome" not in colunas["termos"] and atividades.verificar() is True, "TER-07 banco antigo"
        assert all(antes[tabela] for tabela in TABELAS_V1), "TER-07 todas as tabelas antigas com dados"
        antigo.fechar()
    finally:
        modulo_dados.MIGRACOES = migracoes
    ponte = nova_ponte(tmp, t, abertos, pasta=pasta)
    estado = dados(ponte.estado(), "TER-07 abrir o banco antigo")
    banco = ponte._n().banco
    assert banco.versao_esquema() == 2, "TER-07 subiu para a versão 2"
    for tabela in TABELAS_V1:
        depois = [tuple(l) for l in banco.todos(f"SELECT {', '.join(colunas[tabela])} FROM {tabela} ORDER BY rowid")]
        assert depois == antes[tabela], f"TER-07 {tabela} mudou na migração"
    novas = {c["name"] for c in banco.todos("PRAGMA table_info(termos)")} - set(colunas["termos"])
    assert novas == {"arquivo_nome", "arquivo_caminho", "arquivo_tipo", "arquivo_mime", "arquivo_bytes",
                     "arquivo_sha256"}, f"TER-07 colunas novas do termo: {novas}"
    assert banco.um("SELECT COUNT(*) AS n FROM termos WHERE arquivo_caminho IS NOT NULL")["n"] == 0, \
        "TER-07 termos antigos sobem sem arquivo"
    assert {c["name"] for c in banco.todos("PRAGMA table_info(preferencias)")} == \
        {"usuario_id", "uid", "criado_em", "alterado_em", "valores"} and contar(ponte, "preferencias") == 0, \
        "TER-07 tabela preferencias criada vazia"
    assert {l["name"] for l in banco.todos("SELECT name FROM sqlite_master WHERE type = 'trigger'")} == gatilhos, \
        "TER-07 gatilhos continuam"
    assert (estado["ativado"], estado["modo"], estado["tema"], estado["preferencias"], estado["videos_dias"]) == \
        (True, "demonstracao", "claro", None, 30), f"TER-07 estado depois de migrar: {estado}"
    dados(ponte.entrar("marina.lopes", SENHA_ADM), "TER-07 a senha antiga continua entrando")
    assert dados(ponte.atividades_listar({}))["integro"] is True, "TER-07 registro de atividades íntegro depois de migrar"
    marcos = por_ref(ponte, "m-05")
    assert marcos["termo"] == {"assinado": False, "data": None, "versao": None, "arquivo": None}, \
        f"TER-07 termo revogado antes da migração: {marcos['termo']}"
    assert por_ref(ponte, "m-01")["termo"] == {"assinado": True, "data": "2026-09-02", "versao": "1", "arquivo": None}, \
        "TER-07 termo de demonstração antigo continua assinado, sem arquivo"
    assert [(h["assinado"], h["arquivo"]) for h in dados(ponte.motorista_termos(marcos["id"]))] == \
        [(False, None), (True, None)], "TER-07 histórico antigo sem arquivo"
    assert "v-2240-e-001" in [d["momento_id"] for d in dados(ponte.decisoes_listar())], "TER-07 decisão antiga"
    dados(ponte.termo_importar(marcos["id"], arquivo("termo-marcos.pdf", PDF), {"data": HOJE}), "TER-07 importar")
    dados(ponte.preferencias_salvar({"tema": "escuro"}), "TER-07 preferências no banco migrado")
    assert dados(ponte.atividades_listar({}))["integro"] is True, "TER-07 íntegro com atividades novas"
    fechar(ponte)
    de_novo = nova_ponte(tmp, t, abertos, pasta=pasta)
    assert dados(de_novo.estado())["tema"] == "escuro" and de_novo._n().banco.versao_esquema() == 2, "TER-07 reabrir"
    assert not ponte._falhas and not de_novo._falhas, f"TER-07 falha interna: {ponte._falhas} {de_novo._falhas}"
    fechar(de_novo)
ok("TER-07 banco da versão 1 com contas, motoristas, termos, decisões, configurações e atividades sobe para a 2 sem "
   "mudar nenhuma linha; colunas do arquivo e tabela preferencias novas; gatilhos mantidos; entra, registro íntegro, "
   "importa termo e salva preferência")

print(f"\n{checks} verificações OK")
