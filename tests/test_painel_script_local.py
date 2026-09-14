"""Spec 018: o painel reconhece o script local aberto e captura os eventos dele.

Sem câmera, sem janela e sem matar processo: pasta falsa, processo falso e o escritor real do script
(caixa/vision/event_queue.py e caixa/vision/em_execucao.py, carregados pelo caminho). Só biblioteca padrão:
    python tests/test_painel_script_local.py
"""
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "painel" / "desktop"))
import script_local as sl  # noqa: E402

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def carregar(caminho, nome):
    especificacao = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


fila = carregar(RAIZ / "caixa" / "vision" / "event_queue.py", "event_queue_do_script")
anuncio_mod = carregar(RAIZ / "caixa" / "vision" / "em_execucao.py", "em_execucao_do_script")
T0 = datetime(2026, 9, 14, 17, 20, 0, tzinfo=timezone.utc)
UID_HEX = re.compile(r"[0-9a-f]{32}")


def relogio_em(instante):
    return lambda: instante


def sem_processos():
    return []


def hash_de(caminho):
    return hashlib.sha256(Path(caminho).read_bytes()).hexdigest()


def painel(tmp, pasta_script, **opcoes):
    opcoes.setdefault("listar_processos", sem_processos)
    opcoes.setdefault("pid_vivo", lambda pid: True)
    opcoes.setdefault("cache_processos_s", 0)
    return sl.ScriptLocal(Path(tmp) / "painel", [pasta_script], **opcoes)


# SCR-01 · nada aberto → fechado, com as chaves do ScriptEstado
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    local = painel(tmp, pasta)
    estado = local.estado()
    assert tuple(estado) == sl.CHAVES_ESTADO, estado
    assert estado == {"aberto": False, "programa": None, "desde": None, "pid": None, "camera": None, "ultimo_sinal": None,
                      "eventos": 0, "pasta": None}, estado
    assert local.eventos(0) == [] and local.capturar() == 0
    local.parar()
ok("SCR-01 sem anúncio e sem processo: aberto false, campos nulos, 0 eventos")

# SCR-02 · aberto pelo anúncio do script (sinal novo e pid vivo), sem precisar listar processos
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    anuncio = anuncio_mod.AnuncioExecucao(pasta, "RotaGuard Teste", relogio=relogio_em(T0), pid=4242)
    anuncio.definir_camera("Câmera 1")
    listagens = []
    local = painel(tmp, pasta, relogio=relogio_em(T0 + timedelta(seconds=4)), pid_vivo=lambda pid: pid == 4242,
                   listar_processos=lambda: listagens.append(1) or [])
    estado = local.estado()
    assert estado["aberto"] is True and estado["programa"] == "RotaGuard Teste" and estado["pid"] == 4242, estado
    assert estado["desde"] == "2026-09-14T17:20:00.000+00:00" and estado["camera"] == "Câmera 1", estado
    assert estado["ultimo_sinal"] == "2026-09-14T17:20:00.000+00:00" and estado["pasta"] == str(pasta), estado
    assert listagens == [], "com anúncio válido não precisa listar processos"
    local.parar()
ok("SCR-02 anúncio com sinal de 4 s e pid vivo: aberto, programa, desde, pid, câmera e pasta")

# SCR-03 · plano B: processo achado pelo nome (pacote instalado que ainda não anuncia)
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    local = painel(tmp, pasta, relogio=relogio_em(T0), listar_processos=lambda: [sl.Processo(812, "RotaGuardTeste.exe")])
    estado = local.estado()
    assert estado["aberto"] is True and estado["pid"] == 812 and estado["programa"] == "RotaGuard Teste", estado
    assert estado["camera"] is None and estado["desde"] == "2026-09-14T17:20:00.000+00:00", estado
    local.parar()
    tasklist = ('"System Idle Process","0","Services","0","8 K"\r\n"python.exe","22464","Console","3","44.312 K"\r\n'
                '"RotaGuardTeste.exe","812","Console","3","1.204.556 K"\r\n')
    assert sl.ler_tasklist_csv(tasklist) == [sl.Processo(0, "System Idle Process"), sl.Processo(22464, "python.exe"),
                                             sl.Processo(812, "RotaGuardTeste.exe")]
    ps = "    1 /sbin/init\n  900 /usr/bin/python3 caixa/app_teste.py --monitor --camera auto\n 950 python3 outro.py\n"
    processos = sl.ler_ps(ps)
    assert [p.pid for p in processos if sl.eh_processo_do_script(p)] == [900], processos
    assert not sl.eh_processo_do_script(sl.Processo(22464, "python.exe"))
    assert sl.eh_processo_do_script(sl.Processo(5, "python", "python run_monitor.py --sem-servidor"))
    assert sl.pid_vivo_do_sistema(os.getpid()) is True
    filho = subprocess.run([sys.executable, "-c", "import os; print(os.getpid())"], capture_output=True, text=True)
    assert sl.pid_vivo_do_sistema(int(filho.stdout.strip())) is False
    assert sl.pid_vivo_do_sistema(0) is False
ok("SCR-03 processo RotaGuardTeste.exe (tasklist) ou python app_teste.py (ps) conta como aberto; pid vivo sem psutil")

# SCR-04 · sinal velho ou pid morto = fechado
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    anuncio = anuncio_mod.AnuncioExecucao(pasta, "RotaGuard Teste", relogio=relogio_em(T0), pid=4242)
    anuncio.renovar()
    velho = painel(tmp, pasta, relogio=relogio_em(T0 + timedelta(seconds=16)))
    assert velho.estado()["aberto"] is False
    velho.parar()
    no_limite = painel(tmp, pasta, relogio=relogio_em(T0 + timedelta(seconds=14)))
    assert no_limite.estado()["aberto"] is True
    no_limite.parar()
    morto = painel(tmp, pasta, relogio=relogio_em(T0 + timedelta(seconds=2)), pid_vivo=lambda pid: False)
    assert morto.estado()["aberto"] is False
    morto.parar()
    (pasta / sl.ARQUIVO_ANUNCIO).write_text("{meio arquivo", encoding="utf-8")
    quebrado = painel(tmp, pasta, relogio=relogio_em(T0))
    assert quebrado.estado()["aberto"] is False
    quebrado.parar()
ok("SCR-04 sinal de 16 s, pid morto ou anúncio ilegível = fechado; 14 s ainda aberto")

# SCR-05 · captura incremental, sem duplicar, com uid/criado_em/alterado_em
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    pasta.mkdir(parents=True)
    store = fila.EventStore(pasta / "eventos.db")
    for tipo, risco, duracao in (("sono", 4, 3.07), ("microssono", 3, 1.0), ("celular_no_ouvido", 3, 3.03)):
        store.add(tipo, risco, duracao, {"fechado_s": duracao})
    local = painel(tmp, pasta)
    assert local.capturar() == 3
    assert local.capturar() == 0
    store.add("olhando_celular", 4, 2.03)
    store.add("atencao", 2, 0.0)
    assert local.capturar() == 2
    todos = local.eventos(0)
    assert [e["tipo"] for e in todos] == ["sono", "microssono", "celular_no_ouvido", "olhando_celular", "atencao"], todos
    assert set(todos[0]) == {"id", "em", "tipo", "risco", "duracao_s", "sessao"}, todos[0]
    assert todos[0]["risco"] == 4 and todos[0]["duracao_s"] == 3.07 and todos[0]["em"].endswith("+00:00"), todos[0]
    assert [e["tipo"] for e in local.eventos(todos[2]["id"])] == ["olhando_celular", "atencao"]
    local.parar()
    de_novo = painel(tmp, pasta)
    assert de_novo.capturar() == 0, "painel reaberto não duplica"
    de_novo.parar()
    banco = sqlite3.connect(Path(tmp) / "painel" / sl.ARQUIVO_CAPTURAS)
    linhas = banco.execute("SELECT uid, criado_em, alterado_em, evento_uid FROM eventos").fetchall()
    assert len(linhas) == 5 and len({linha[3] for linha in linhas}) == 5
    assert all(UID_HEX.fullmatch(uid) and criado.endswith("+00:00") and alterado for uid, criado, alterado, _ in linhas)
    banco.close()
    store.close()
ok("SCR-05 captura 3, depois 0, depois 2; eventos(desde_id); painel reaberto não duplica; uid hex, criado_em, alterado_em")

# SCR-06 · os arquivos do script não mudam e o script continua gravando durante a captura
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    pasta.mkdir(parents=True)
    store = fila.EventStore(pasta / "eventos.db")
    store.add("sono", 4, 3.0)
    anuncio = anuncio_mod.AnuncioExecucao(pasta, "RotaGuard Teste")
    anuncio.renovar()
    local = painel(tmp, pasta)
    assert local.capturar() == 1
    inicio = time.monotonic()
    store.add("microssono", 3, 1.0)  # a leitura do painel não deixou trava no banco do script
    assert time.monotonic() - inicio < 1.0
    assert local.capturar() == 1
    local.parar()
    store.close()  # checkpoint: tudo no arquivo principal
    antes = {nome: hash_de(pasta / nome) for nome in ("eventos.db", sl.ARQUIVO_ANUNCIO)}
    conferir = painel(tmp, pasta)
    conferir.estado()
    assert conferir.capturar() == 0 and len(conferir.eventos(0)) == 2
    conferir.parar()
    assert {nome: hash_de(pasta / nome) for nome in antes} == antes, "o painel alterou arquivo do script"
    somente_leitura = sl.abrir_so_leitura(pasta / "eventos.db")
    try:
        somente_leitura.execute("DELETE FROM events")
    except sqlite3.OperationalError as erro:
        assert "readonly" in str(erro).lower(), erro
    else:
        raise AssertionError("a conexão com o banco do script precisa ser só leitura")
    finally:
        somente_leitura.close()
ok("SCR-06 eventos.db e em_execucao.json intactos; conexão mode=ro recusa escrita; script grava durante a captura")

# SCR-07 · sessão nova cada vez que o script abre
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    pasta.mkdir(parents=True)
    store = fila.EventStore(pasta / "eventos.db")
    local = painel(tmp, pasta, pid_vivo=lambda pid: pid == os.getpid())
    primeira = anuncio_mod.AnuncioExecucao(pasta, "RotaGuard Teste")
    primeira.renovar()
    assert local.estado()["aberto"] is True
    store.add("sono", 4, 3.0)
    assert local.capturar() == 1
    assert local.estado()["eventos"] == 1
    primeira.parar()
    assert not (pasta / sl.ARQUIVO_ANUNCIO).exists()
    assert local.estado()["aberto"] is False
    time.sleep(0.02)
    segunda = anuncio_mod.AnuncioExecucao(pasta, "RotaGuard Teste")
    segunda.definir_camera("Câmera 2")
    assert local.estado()["aberto"] is True and local.estado()["eventos"] == 0
    store.add("celular_na_mao", 3, 2.0)
    store.add("atencao", 2, 0.0)
    assert local.capturar() == 2
    eventos = local.eventos(0)
    sessoes = [e["sessao"] for e in eventos]
    assert all(UID_HEX.fullmatch(s or "") for s in sessoes) and sessoes[0] != sessoes[1] == sessoes[2], sessoes
    assert local.estado()["eventos"] == 2
    segunda.parar()
    local.estado()
    banco = sqlite3.connect(Path(tmp) / "painel" / sl.ARQUIVO_CAPTURAS)
    registros = banco.execute("SELECT uid, encerrado_em, criado_em, alterado_em FROM sessoes ORDER BY id").fetchall()
    banco.close()
    assert len(registros) == 2 and all(r[1] for r in registros) and all(UID_HEX.fullmatch(r[0]) for r in registros)
    local.parar()
    store.close()
ok("SCR-07 fechar e reabrir o script cria outra sessão; eventos separados por sessão; sessões encerradas com uid")

# SCR-08 · lado do script: anúncio com os campos, renovado a cada ≤ 5 s, apagado ao sair; ligado no run_monitor
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "dados"
    assert anuncio_mod.INTERVALO_S <= 5 and anuncio_mod.AnuncioExecucao(pasta, "x", intervalo_s=60)._intervalo <= 5
    anuncio = anuncio_mod.AnuncioExecucao(pasta, "RotaGuard Teste", intervalo_s=0.05)
    anuncio.iniciar()
    dados = json.loads((pasta / "em_execucao.json").read_text(encoding="utf-8"))
    assert {"formato", "sessao", "pid", "programa", "iniciado_em", "camera", "ultimo_sinal"} <= set(dados), dados
    assert dados["pid"] == os.getpid() and dados["formato"] == "rotaguard-em-execucao/1", dados
    time.sleep(0.3)
    assert json.loads((pasta / "em_execucao.json").read_text(encoding="utf-8"))["ultimo_sinal"] != dados["ultimo_sinal"]
    outro = anuncio_mod.AnuncioExecucao(pasta, "outro")
    anuncio.parar()
    assert not (pasta / "em_execucao.json").exists() and not list(pasta.glob(".em_execucao*"))
    outro.renovar()
    anuncio.parar()
    assert (pasta / "em_execucao.json").exists(), "parar() não apaga o anúncio de outra sessão"
    assert anuncio_mod.descrever_camera(fonte="0") == "Câmera 1"
    assert anuncio_mod.descrever_camera(type("C", (), {"describe": lambda self: "OpenCV 2"})()) == "Câmera 3"
    assert anuncio_mod.descrever_camera(type("C", (), {"describe": lambda self: r"OpenCV 'C:\v\teste.mp4'"})()) == \
        "Vídeo teste.mp4"
    assert anuncio_mod.descrever_camera(fonte="rtsp://user:senha@10.0.0.9/stream") == "Câmera de rede"
    assert anuncio_mod.nome_do_programa(congelado=True, argv0="x") == "RotaGuard Teste"
    assert anuncio_mod.nome_do_programa(congelado=False, argv0="caixa/app_teste.py") == "RotaGuard Teste"
fonte = (RAIZ / "caixa" / "run_monitor.py").read_text(encoding="utf-8")
corpo = fonte[fonte.index("def main("):]
assert corpo.index("AnuncioExecucao(data_dir") < corpo.index("try:") < corpo.index("anuncio.definir_camera(")
assert corpo.index("finally:") < corpo.index("anuncio.parar()") < corpo.index("store.close()")
legais = carregar(RAIZ / "caixa" / "textos_legais.py", "textos_legais_do_script")
assert "em_execucao.json" in "\n".join(texto for _, texto in legais.secoes(Path("/dados/RotaGuard/Teste"), "")), \
    "a seção de privacidade do app de teste precisa citar o arquivo novo da pasta de dados"
ok("SCR-08 em_execucao.json com pid, programa, iniciado_em, câmera e sinal renovado; apagado ao sair; ligado no run_monitor")

# SCR-09 · vigia em thread captura sozinha a cada volta e para limpo
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp) / "RotaGuard" / "Teste"
    pasta.mkdir(parents=True)
    store = fila.EventStore(pasta / "eventos.db")
    local = painel(tmp, pasta, intervalo_s=0.05)
    local.iniciar()
    store.add("sono", 4, 3.0)
    limite = time.monotonic() + 3
    while time.monotonic() < limite and not local.eventos(0):
        time.sleep(0.05)
    assert [e["tipo"] for e in local.eventos(0)] == ["sono"]
    linha = local._linha
    local.parar()
    assert not linha.is_alive()
    assert sl.INTERVALO_VIGIA_S == 2.0
    store.close()
ok("SCR-09 iniciar() captura em thread (2 s por padrão) e parar() encerra a thread")

# SCR-10 · pastas padrão do script
assert sl.pastas_padrao_do_script("win32", {"LOCALAPPDATA": r"C:\U\AppData\Local"}, Path(r"C:\U")) == \
    [Path(r"C:\U\AppData\Local") / "RotaGuard" / "Teste", Path(r"C:\U") / ".drivesafe"]
assert sl.pastas_padrao_do_script("linux", {}, Path("/home/m")) == \
    [Path("/home/m/.local/share/rotaguard/teste"), Path("/home/m/.drivesafe")]
assert sl.pastas_padrao_do_script("linux", {"XDG_DATA_HOME": "/x", "DRIVESAFE_DATA_DIR": "/dados"}, Path("/home/m")) == \
    [Path("/dados"), Path("/x/rotaguard/teste"), Path("/home/m/.drivesafe")]
ok("SCR-10 pastas do script: RotaGuard\\Teste (Windows), rotaguard/teste (Linux), ~/.drivesafe e DRIVESAFE_DATA_DIR")

print(f"\n{checks} verificações OK")
