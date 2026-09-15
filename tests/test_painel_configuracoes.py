"""Spec 016: configurações e cópia de segurança do painel (núcleo Python).

Sem janela e sem pywebview: a Ponte é chamada direto, com relógio falso, scrypt barato, pasta temporária e script local
falso. Biblioteca padrão e o cryptography do .venv (a cópia usa AES-GCM):
    python tests/test_painel_configuracoes.py
"""
import hashlib
import inspect
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import configuracoes  # noqa: E402
import contas  # noqa: E402
import copia  # noqa: E402
from dados import ErroPainel, iso_utc  # noqa: E402
from ponte import Ponte  # noqa: E402

checks = 0
CUSTO_TESTE = (2**4, 8, 1)
T0 = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc).timestamp()
# Senhas descartáveis, só deste teste.
SENHA_ADM = "frase comprida de teste um"
SENHA_SUP = "frase comprida de teste dois"
SENHA_CON = "frase comprida de teste tres"
SENHA_COPIA = "frase da copia de teste"
ADMIN = {"nome": "Marina Lopes", "usuario": "marina.lopes", "senha": SENHA_ADM}


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


def pronta(tmp, relogio, destinos=None):
    """Demonstração ativada, com supervisor e consulta criados; volta com a administradora na sessão."""
    ponte = nova_ponte(tmp, relogio, destinos)
    dados(ponte.ativar_demonstracao(ADMIN), "ativar demonstração")
    for nome, usuario, funcao, senha in (("Paulo Reis", "paulo.reis", "supervisor", SENHA_SUP),
                                         ("Ana Souza", "ana.souza", "consulta", SENHA_CON)):
        entrar_como(ponte, "marina.lopes", SENHA_ADM)
        novo = dados(ponte.equipe_adicionar({"nome": nome, "usuario": usuario, "funcao": funcao}), usuario)
        entrar_como(ponte, usuario, novo["senha_temporaria"])
        dados(ponte.trocar_senha(novo["senha_temporaria"], senha), usuario)
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    return ponte


# CFG-01 · só o administrador lê e muda as configurações; a ponte recusa as outras funções
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    config = dados(ponte.config_ler(), "CFG-01 administrador lê")
    assert set(config) == {"empresa", "regras", "guarda", "acesso", "aparencia"}, f"CFG-01 seções: {config}"
    for usuario, senha, nome in (("paulo.reis", SENHA_SUP, "Paulo Reis"), ("ana.souza", SENHA_CON, "Ana Souza")):
        entrar_como(ponte, usuario, senha)
        erro(ponte.config_ler(), "sem_permissao", f"CFG-01 {nome} lê")
        erro(ponte.config_salvar("regras", {"direcao_continua_min": 300}), "sem_permissao", f"CFG-01 {nome} muda")
        erro(ponte.copia_fazer(SENHA_COPIA), "sem_permissao", f"CFG-01 {nome} faz cópia")
        tentativas = [l for l in linhas(ponte, "tentou sem permissão") if l["usuario"] == nome]
        assert len(tentativas) == 3 and {l["alvo"] for l in tentativas} == {"configuracoes"}, f"CFG-01 registro {nome}"
    entrar_como(ponte, "marina.lopes", SENHA_ADM)
    assert dados(ponte.config_ler())["regras"]["direcao_continua_min"] == 330, "CFG-01 recusado não muda nada"
    assert not linhas(ponte, "mudou configuração"), "CFG-01 recusado não registra mudança"
    ponte.sair()
    erro(ponte.config_ler(), "sem_sessao", "CFG-01 sem sessão")
    fechar(ponte)
ok("CFG-01 administradora lê as 5 seções; supervisor e consulta recebem sem_permissao em config_ler, config_salvar "
   "e copia_fazer, com a tentativa no registro e nada mudado")

# CFG-02 · toda mudança registra valor antigo, novo, quem e quando
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    for secao, valores, esperadas in (
            ("regras", {"direcao_continua_min": 300}, [("regras.direcao_continua_min", "5 h 30 → 5 h")]),
            ("empresa", {"nome": "Viação Teste", "cnpj": "11222333000181", "telefone": "(11) 3333-4444"},
             [("empresa.nome", "Viação Demonstração → Viação Teste"), ("empresa.cnpj", "(vazio) → 11.222.333/0001-81"),
              ("empresa.telefone", "(vazio) → (11) 3333-4444")]),
            ("guarda", {"videos_dias": 15}, [("guarda.videos_dias", "30 → 15")]),
            ("acesso", {"bloqueio_min": 10}, [("acesso.bloqueio_min", "15 → 10")]),
            ("aparencia", {"texto_maior": True}, [("aparencia.texto_maior", "não → sim")])):
        t[0] += 60
        antes = len(linhas(ponte, "mudou configuração"))
        dados(ponte.config_salvar(secao, valores), f"CFG-02 {secao}")
        novas = linhas(ponte, "mudou configuração")[antes:]
        assert [(l["alvo"], l["detalhe"]) for l in novas] == esperadas, \
            f"CFG-02 {secao}: {[(l['alvo'], l['detalhe']) for l in novas]}"
        assert all(l["usuario"] == "Marina Lopes" and l["em"] == iso_utc(t[0]) for l in novas), f"CFG-02 quem e quando"
    config = dados(ponte.config_ler())
    assert config["empresa"]["cnpj"] == "11.222.333/0001-81" and config["acesso"]["bloqueio_min"] == 10, config
    assert dados(ponte.estado())["empresa"] == {"nome": "Viação Teste"}, "CFG-02 nome novo no estado"
    antes = len(linhas(ponte, "mudou configuração"))
    dados(ponte.config_salvar("regras", {"direcao_continua_min": 300}))
    dados(ponte.config_salvar("empresa", {"cnpj": "11.222.333/0001-81"}))
    assert len(linhas(ponte, "mudou configuração")) == antes, "CFG-02 salvar o mesmo valor não registra"
    assert erro(ponte.config_salvar("empresa", {"cnpj": "11.222.333/0001-82"}), "invalido")["campo"] == "cnpj"
    assert erro(ponte.config_salvar("empresa", {"nome": "  "}), "invalido")["campo"] == "nome", "CFG-02 nome vazio"
    fechar(ponte)
ok("CFG-02 regras, empresa (CNPJ formatado), guarda, acesso e aparência: uma linha por campo com 'antigo → novo', "
   "quem e quando; mesmo valor não registra; CNPJ e nome inválidos recusados")

# CFG-03 · direção contínua de 1 h até 5 h 30; acima disso, a mensagem da lei
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    for valor in (331, 360, 600):
        resposta = erro(ponte.config_salvar("regras", {"direcao_continua_min": valor}), "invalido", f"CFG-03 {valor}")
        assert resposta["erro"] == "O máximo é 5 h 30, pela lei (CTB, art. 67-C)" and \
            resposta["campo"] == "direcao_continua_min", f"CFG-03 {valor}: {resposta}"
    for valor in (59, 0, -5):
        resposta = erro(ponte.config_salvar("regras", {"direcao_continua_min": valor}), "invalido", f"CFG-03 {valor}")
        assert resposta["erro"] == "O mínimo é 1 h." and resposta["campo"] == "direcao_continua_min", resposta
    for valor in ("300", 300.0, True, None):
        resposta = erro(ponte.config_salvar("regras", {"direcao_continua_min": valor}), "invalido", f"CFG-03 {valor!r}")
        assert resposta["campo"] == "direcao_continua_min", resposta
    assert dados(ponte.config_ler())["regras"]["direcao_continua_min"] == 330, "CFG-03 recusado não muda"
    assert not linhas(ponte, "mudou configuração"), "CFG-03 recusado não registra"
    for valor in (60, 299, 330):
        assert dados(ponte.config_salvar("regras", {"direcao_continua_min": valor}))["regras"]["direcao_continua_min"] \
            == valor, f"CFG-03 {valor} aceito"
    fechar(ponte)
assert [configuracoes.formatar_minutos(m) for m in (330, 300, 65, 60)] == ["5 h 30", "5 h", "1 h 05", "1 h"]
ok("CFG-03 331, 360 e 600 min recusados com a frase do CTB art. 67-C; menos de 1 h e valor que não é inteiro "
   "recusados; 60, 299 e 330 aceitos")

# CFG-04 · a viagem guarda a regra com que foi lida; mudar a regra não muda a cópia antiga
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    config = ponte._n().config
    antiga = config.regra_para_importacao()
    assert antiga == {"direcao_continua_min": 330}, f"CFG-04 {antiga}"
    dados(ponte.config_salvar("regras", {"direcao_continua_min": 300}))
    assert antiga == {"direcao_continua_min": 330} and config.regra_para_importacao() == {"direcao_continua_min": 300}
    antiga["direcao_continua_min"] = 1
    assert config.regra_para_importacao() == {"direcao_continua_min": 300}, "CFG-04 a cópia é independente"
    fechar(ponte)
print("-- CFG-04 parcial: a importação de viagem ainda não existe; conferida só a cópia da regra para guardar na viagem")
ok("CFG-04 regra_para_importacao devolve uma cópia: mudar a configuração depois não mexe na regra já copiada")

# CFG-05 · prazos de guarda só com as opções da decisão 4; padrões 30 dias, 5 anos e 5 anos
assert configuracoes.OPCOES_VIDEOS_DIAS == (7, 15, 30, 60, 90) and configuracoes.OPCOES_ANOS == (1, 2, 5)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    assert dados(ponte.config_ler())["guarda"] == {"videos_dias": 30, "registros_anos": 5, "desligados_anos": 5}, \
        "CFG-05 padrões"
    for dias in (7, 15, 30, 60, 90):
        assert dados(ponte.config_salvar("guarda", {"videos_dias": dias}))["guarda"]["videos_dias"] == dias, dias
    for anos in (1, 2, 5):
        guarda = dados(ponte.config_salvar("guarda", {"registros_anos": anos, "desligados_anos": anos}))["guarda"]
        assert (guarda["registros_anos"], guarda["desligados_anos"]) == (anos, anos), anos
    for campo, valor in (("videos_dias", 10), ("videos_dias", 0), ("videos_dias", 365), ("videos_dias", "30"),
                         ("videos_dias", True), ("videos_dias", 30.0), ("registros_anos", 3), ("registros_anos", True),
                         ("desligados_anos", 10), ("desligados_anos", 1.0)):
        resposta = erro(ponte.config_salvar("guarda", {campo: valor}), "invalido", f"CFG-05 {campo}={valor!r}")
        assert resposta["campo"] == campo, f"CFG-05 {campo}: {resposta}"
    assert erro(ponte.config_salvar("guarda", {"videos_dias": 30, "outro": 1}), "invalido")["campo"] == "outro"
    assert erro(ponte.config_salvar("cores", {"x": 1}), "invalido")["campo"] == "secao", "CFG-05 seção desconhecida"
    erro(ponte.config_salvar("guarda", {}), "invalido", "CFG-05 nada para salvar")
    erro(ponte.config_salvar("guarda", "30"), "invalido", "CFG-05 valores que não são objeto")
    fechar(ponte)
ok("CFG-05 padrões 30 dias, 5 anos e 5 anos; aceita só 7/15/30/60/90 dias e 1/2/5 anos (sem texto, bool ou decimal); "
   "campo e seção desconhecidos recusados")

# CFG-06 · regra pura: vídeo com prazo vencido sai com quando e por quê
AGORA = "2026-10-15T12:00:00Z"
videos = [{"id": "v-31-dias", "coletado_em": "2026-09-14T11:59:59Z"},
          {"id": "v-30-dias", "coletado_em": "2026-09-15T12:00:00Z"},
          {"id": "v-29-dias", "coletado_em": "2026-09-16T12:00:00Z"}]
assert configuracoes.videos_vencidos(videos, AGORA, 30) == \
    [{"id": "v-31-dias", "apagado_em": AGORA, "motivo": "prazo de 30 dias"}], "CFG-06 31 dias com prazo de 30"
assert configuracoes.videos_vencidos(videos, AGORA, 90) == [], "CFG-06 prazo de 90 dias guarda todos"
assert [v["id"] for v in configuracoes.videos_vencidos(videos, AGORA, 7)] == ["v-31-dias", "v-30-dias", "v-29-dias"]
print("-- CFG-06 parcial: apagar na abertura, o relatório dizer 'Vídeo apagado em' e o registro contar os apagados "
      "ainda não existem (vídeos não ficam no banco do painel); conferida só a regra pura")
ok("CFG-06 videos_vencidos: 31 dias sai com apagado_em e 'prazo de 30 dias'; exatamente 30 e 29 dias ficam")

# CFG-07 · vídeo "em apuração" não é apagado pelo prazo
velhos = [{"id": "em-apuracao", "coletado_em": "2026-01-01T00:00:00Z", "em_apuracao": True},
          {"id": "velho", "coletado_em": "2026-01-01T00:00:00Z"},
          {"id": "apuracao-encerrada", "coletado_em": "2026-01-01T00:00:00Z", "em_apuracao": False}]
assert [v["id"] for v in configuracoes.videos_vencidos(velhos, AGORA, 7)] == ["velho", "apuracao-encerrada"], \
    "CFG-07 em apuração fica"
print("-- CFG-07 parcial: a marca 'em apuração' ainda não existe na tela nem no banco (pergunta 2 da spec 016)")
ok("CFG-07 videos_vencidos não devolve vídeo marcado em apuração, mesmo com 9 meses; sem a marca, sai")

# BKP-01 · cópia em um arquivo só, AES-GCM com chave de scrypt; sem a senha certa não abre e nada muda
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    destinos = []
    ponte = pronta(tmp, t, destinos)
    assert erro(ponte.copia_fazer("curta"), "invalido")["campo"] == "senha" and destinos == [], "BKP-01 senha curta"
    t[0] += 60
    feita = dados(ponte.copia_fazer(SENHA_COPIA))
    caminho = Path(feita["caminho"])
    assert caminho == Path(tmp) / "rotaguard-copia-2026-09-14.rotaguard-copia", f"BKP-01 nome: {caminho}"
    assert sorted(p.name for p in Path(tmp).iterdir() if p.is_file()) == [caminho.name], "BKP-01 um arquivo só, sem .tmp"
    bruto = caminho.read_bytes()
    assert len(bruto) == feita["bytes"] and bruto.startswith(copia.MAGICO), "BKP-01 tamanho e assinatura do formato"
    for texto in ("Carlos Menezes", "Viação Demonstração", "marina.lopes", "CREATE TABLE", SENHA_COPIA):
        assert texto.encode("utf-8") not in bruto, f"BKP-01 texto aberto dentro da cópia: {texto}"
    linha = linhas(ponte, "fez cópia de segurança")[-1]
    assert (linha["alvo"], linha["detalhe"], linha["em"]) == (caminho.name, f"{feita['bytes']} bytes", iso_utc(t[0]))
    assert ponte._n().banco.meta_ler("ultima_copia_em") == iso_utc(t[0]), "BKP-01 data da última cópia"
    cabecalho, conteudo = copia.abrir_copia(caminho, SENHA_COPIA)
    kdf, cifra = cabecalho["kdf"], cabecalho["cifra"]
    # Spec 019 (TER-06): formato 2, um zip cifrado com painel.db e termos/*; o arquivo do termo é provado em test_painel_termos.
    assert (cabecalho["formato"], cifra["nome"], kdf["nome"]) == ("rotaguard-copia/2", "AES-256-GCM", "scrypt"), cabecalho
    assert (kdf["n"], kdf["r"], kdf["p"]) == CUSTO_TESTE and len(bytes.fromhex(kdf["sal"])) == 16 and \
        len(bytes.fromhex(cifra["nonce"])) == 12 and cabecalho["criado_em"] == iso_utc(t[0]), f"BKP-01 {cabecalho}"
    assert inspect.signature(copia.fazer_copia).parameters["custo"].default == contas.CUSTO_PRODUCAO == (2**17, 8, 1), \
        "BKP-01 fora dos testes a chave usa o scrypt de produção"
    pacote = copia.conteudo_da_copia(cabecalho, conteudo)
    assert pacote["arquivos"] == {}, f"BKP-01 demonstração sem termo importado não leva arquivo: {list(pacote['arquivos'])}"
    restaurado = sqlite3.connect(":memory:")
    restaurado.deserialize(pacote["banco"])
    assert restaurado.execute("SELECT COUNT(*) FROM motoristas").fetchone()[0] == 5, "BKP-01 a cópia devolve o banco"
    assert {l[0] for l in restaurado.execute("SELECT usuario FROM usuarios")} == \
        {"marina.lopes", "paulo.reis", "ana.souza"}, "BKP-01 contas na cópia"
    assert restaurado.execute("SELECT COUNT(*) FROM configuracoes").fetchone()[0] == 5, "BKP-01 configurações na cópia"
    restaurado.close()
    impressao = hashlib.sha256(bruto).hexdigest()
    atividades_antes = contar(ponte, "atividades")
    try:
        copia.abrir_copia(caminho, "frase errada da copia")
    except ErroPainel as falha:
        assert falha.erro.startswith("Senha da cópia errada") and falha.campo == "senha", falha.resposta()
    else:
        raise AssertionError("BKP-01 abriu com a senha errada")
    assert hashlib.sha256(caminho.read_bytes()).hexdigest() == impressao, "BKP-01 senha errada não mexe no arquivo"
    assert contar(ponte, "atividades") == atividades_antes and contar(ponte, "motoristas") == 5, "BKP-01 nada muda"
    for posicao in (0, len(copia.MAGICO) + 6, len(bruto) // 2, len(bruto) - 1):
        mexido = bytearray(bruto)
        mexido[posicao] ^= 0x01
        try:
            copia.decifrar(bytes(mexido), SENHA_COPIA)
        except ErroPainel:
            pass
        else:
            raise AssertionError(f"BKP-01 cópia com o byte {posicao} alterado abriu")
    for cortado in (bruto[:-1], bruto[:len(copia.MAGICO) + 2], b""):
        try:
            copia.decifrar(cortado, SENHA_COPIA)
        except ErroPainel:
            pass
        else:
            raise AssertionError("BKP-01 cópia cortada abriu")
    sem_extensao = copia.fazer_copia(ponte._n().banco, SENHA_COPIA, Path(tmp) / "sem-extensao", CUSTO_TESTE)
    assert sem_extensao["caminho"].endswith("sem-extensao.rotaguard-copia"), sem_extensao
    ponte._escolher_destino_injetado = lambda nome: None
    assert erro(ponte.copia_fazer(SENHA_COPIA), "invalido")["erro"] == "Nada foi salvo.", "BKP-01 cancelar"
    fechar(ponte)
ok("BKP-01 um arquivo .rotaguard-copia sem texto aberto, AES-256-GCM com scrypt (sal 16, nonce 12); a senha certa "
   "devolve banco, contas e configurações; senha errada dá 'Senha da cópia errada' e nada muda; byte alterado ou "
   "arquivo cortado não abre")

# BKP-01 (pacote) · cryptography travado no requirements.txt e com a licença no pacote
travadas = {}
for linha in (RAIZ / "painel" / "desktop" / "requirements.txt").read_text(encoding="utf-8").splitlines():
    linha = linha.split("#", 1)[0].strip()
    if linha:
        requisito, _, marcador = linha.partition(";")
        nome, _, versao = requisito.strip().partition("==")
        travadas[nome.strip().lower().replace("_", "-")] = (versao.strip(), marcador.strip())
assert travadas.get("cryptography") == (metadata.version("cryptography"), ""), \
    f"BKP-01 cryptography travado com a versão instalada, para todo sistema: {travadas.get('cryptography')}"
for nome in ("cffi", "pycparser"):
    assert nome in travadas and "win32" not in travadas[nome][1], \
        f"BKP-01 {nome} é dependência do cryptography em todo sistema: {travadas.get(nome)}"
especificacao = (RAIZ / "implantacao" / "painel" / "rotaguard-painel.spec").read_text(encoding="utf-8")
assert '"cryptography"' in especificacao, "BKP-01 metadados de licença do cryptography no pacote (copy_metadata)"
ok("BKP-01 (pacote) cryptography==versão instalada sem marcador; cffi e pycparser para todo sistema; licença no .spec")

# BKP-03 · aviso no Início quando a última cópia tem mais de 7 dias (relógio falso)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    t = [T0]
    ponte = pronta(tmp, t)
    assert dados(ponte.inicio_resumo())["dias_desde_copia"] is None, "BKP-03 sem cópia"
    t[0] += 60
    dados(ponte.copia_fazer(SENHA_COPIA))
    feita_em = iso_utc(t[0])
    for passado, dias, avisa in ((7 * 86400, 7, False), (8 * 86400, 8, True)):
        t[0] = T0 + 60 + passado
        entrar_como(ponte, "marina.lopes", SENHA_ADM)
        resumo = dados(ponte.inicio_resumo())
        assert resumo["ultima_copia_em"] == feita_em and resumo["dias_desde_copia"] == dias, f"BKP-03 {resumo}"
        assert (resumo["dias_desde_copia"] > 7) is avisa, f"BKP-03 aviso só com mais de 7 dias: {resumo}"
    dados(ponte.copia_fazer(SENHA_COPIA))
    assert dados(ponte.inicio_resumo())["dias_desde_copia"] == 0, "BKP-03 cópia nova zera a conta"
    fechar(ponte)
print("-- BKP-02 não testado: restaurar a cópia ainda não existe (nem na ponte nem na tela)")
ok("BKP-03 inicio_resumo: 7 dias depois da cópia não avisa, 8 dias avisa (dias_desde_copia 8); cópia nova volta a 0")

print(f"\n{checks} verificações OK")
