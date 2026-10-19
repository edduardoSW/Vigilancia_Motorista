"""Spec 026: trechos de vídeo do app de teste e envio para a central (TRE-01 a TRE-08).

Usa um servidor de mentira em http.server no lugar da central. Precisa de numpy e opencv:
    python tests/test_trechos.py
"""
import hashlib
import json
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "caixa"))
sys.path.insert(0, str(RAIZ / "tests"))
from vision import sync, trechos  # noqa: E402

checks = 0


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def jpeg(i: int) -> bytes:
    quadro = np.zeros((360, 480, 3), dtype=np.uint8)
    quadro[:, :, 1] = (i * 3) % 255
    cv2.circle(quadro, (40 + (i * 4) % 400, 180), 30, (105, 246, 213), -1)
    return cv2.imencode(".jpg", quadro, [int(cv2.IMWRITE_JPEG_QUALITY), 70])[1].tobytes()


QUADROS = [jpeg(i) for i in range(30)]


def alimentar(gravador, inicio: float, fim: float, fps: float = 20.0, gatilhos=None):
    """Quadros de inicio a fim; gatilhos: {t: tipo}."""
    gatilhos = dict(gatilhos or {})
    t, i = inicio, 0
    while t < fim:
        gravador.quadro(t, QUADROS[i % len(QUADROS)])
        for momento in [m for m in gatilhos if m <= t]:
            gravador.gatilho(gatilhos.pop(momento), momento)
        t += 1.0 / fps
        i += 1


# ---------------------------------------------------------------- TRE-01 a TRE-06 · gravação local
for formato in ("webm", "rgclip"):
    with tempfile.TemporaryDirectory() as tmp:
        pasta = Path(tmp)
        gravados = []
        gravador = trechos.GravadorTrechos(pasta, "a" * 32, formato=formato, ao_gravar=gravados.append, em_thread=False)
        alimentar(gravador, 0.0, 30.0)
        assert not gravador.trechos and not list((pasta / "trechos").rglob("*.*")), "TRE-01"
        if formato == "webm":
            ok("TRE-01 sem gatilho, nenhum trecho é gravado")

        assert gravador.gatilho("bocejo_qualquer", 31.0) is None, "tipo fora dos gatilhos não grava"
        alimentar(gravador, 30.0, 60.0, gatilhos={40.0: "microssono", 52.0: "celular_na_mao"})
        assert len(gravador.trechos) == 1, gravador.trechos
        meta = gravador.trechos[0]
        assert meta["tipo"] == "microssono" and meta["formato"] == formato
        assert abs(meta["duracao_s"] - 16.0) <= 1.0 and abs(meta["antes_s"] - 8.0) <= 1.0, meta
        if formato == "webm":
            ok("TRE-02 microssono gera um trecho com ~8 s antes e ~8 s depois")
            ok("TRE-03 dois gatilhos a menos de 30 s geram um trecho só")

        arquivo = pasta / "trechos" / meta["sessao_uid"] / meta["arquivo"]
        dados = arquivo.read_bytes()
        assert meta["sha256"] == hashlib.sha256(dados).hexdigest() and meta["tamanho"] == len(dados)
        for chave in ("uid", "sessao_uid", "tipo", "inicio", "fim", "duracao_s", "formato", "sha256", "quadros", "fps"):
            assert meta.get(chave) not in (None, ""), chave
        assert meta["inicio"].endswith("Z") and meta["fim"].endswith("Z")
        salvo = json.loads(arquivo.with_suffix(".json").read_text(encoding="utf-8"))
        assert salvo["sha256"] == meta["sha256"] and salvo["enviado"] is False
        assert gravados == [meta], "ao_gravar recebe o metadado"
        if formato == "webm":
            assert dados[:4] == b"\x1a\x45\xdf\xa3", "assinatura WebM"
            leitor = cv2.VideoCapture(str(arquivo))
            lidos = 0
            while leitor.read()[0]:
                lidos += 1
            leitor.release()
            assert abs(lidos - meta["quadros"]) <= 2 and lidos >= 200, (lidos, meta["quadros"])
        else:
            with zipfile.ZipFile(arquivo) as pacote:
                indice = json.loads(pacote.read("indice.json"))
                assert indice["formato"] == "rotaguard-trecho/1" and len(indice["quadros"]) == meta["quadros"]
                primeiro = cv2.imdecode(np.frombuffer(pacote.read(indice["quadros"][0]["arquivo"]), np.uint8), 1)
                assert primeiro is not None and primeiro.shape[1] <= trechos.LARGURA_TRECHO
        ok(f"TRE-05 o arquivo {formato} abre e confere com os quadros gravados")
        if formato == "webm":
            ok("TRE-06 metadado com uid, tipo, início, fim, duração, formato e SHA-256 conferindo com o arquivo")

# Formato escolhido sozinho: WebM VP8 (o OpenCV desta máquina não grava H.264) ou o .rgclip se nem isso funcionar.
assert trechos.formato_de_video() in ("webm", "rgclip")

# TRE-04 · limite de 20 por sessão (com o intervalo de 30 s respeitado)
with tempfile.TemporaryDirectory() as tmp:
    gravador = trechos.GravadorTrechos(Path(tmp), "b" * 32, formato="rgclip", em_thread=False)
    gatilhos = {10.0 + 40.0 * n: "microssono" for n in range(25)}
    alimentar(gravador, 0.0, 10.0 + 40.0 * 25 + 10.0, fps=4.0, gatilhos=gatilhos)
    assert len(gravador.trechos) == trechos.MAX_TRECHOS == 20, len(gravador.trechos)
ok("TRE-04 no máximo 20 trechos por sessão")

# Encerrar no meio de um trecho grava o que já tem; marca d'água sem acento (fonte do OpenCV)
with tempfile.TemporaryDirectory() as tmp:
    gravador = trechos.GravadorTrechos(Path(tmp), "c" * 32, formato="rgclip", em_thread=False)
    alimentar(gravador, 0.0, 14.0, gatilhos={10.0: "celular_no_ouvido"})
    assert gravador.gravando and not gravador.trechos
    gravador.finalizar()
    assert len(gravador.trechos) == 1 and 11.0 <= gravador.trechos[0]["duracao_s"] <= 13.0, gravador.trechos
assert trechos.marca_dagua("celular_na_mao").isascii() and "mao" in trechos.marca_dagua("celular_na_mao").lower()
ok("TRE-02 encerrar o teste no meio de um trecho grava o que já foi juntado")

# ---------------------------------------------------------------- MAL-05 · trecho com o rosto limpo (spec 029)
# A faixa com hora, tipo e "RotaGuard" vai num rodapé ACRESCENTADO embaixo do quadro: nenhum pixel da imagem (e do rosto)
# muda. O quadro que entra já é o limpo (tela_teste/sessao.py manda o original, sem malha).
with tempfile.TemporaryDirectory() as tmp:
    gravador = trechos.GravadorTrechos(Path(tmp), "d" * 32, formato="rgclip", em_thread=False)
    gerador = np.random.default_rng(3)
    original = cv2.GaussianBlur(gerador.integers(40, 220, (480, 640, 3), dtype=np.uint8), (0, 0), 2)
    marcado = gravador._marcar(original, gravador._t_ref + 1.0, "microssono")
    assert marcado.shape == (480 + trechos.FAIXA_PX, 640, 3), marcado.shape
    assert np.array_equal(marcado[:480], original), "nenhum pixel do quadro (nem do rosto) é alterado"
    faixa = marcado[480:]
    assert faixa.std() > 5, "a faixa tem o texto"
    assert trechos.FAIXA_PX % 2 == 0 and 16 <= trechos.FAIXA_PX <= 28, "faixa fina e altura par (VP8)"
    # De ponta a ponta: o primeiro quadro gravado é o original (só a perda do JPEG) com a faixa embaixo
    liso = cv2.GaussianBlur(original, (0, 0), 3)
    jpeg_limpo = cv2.imencode(".jpg", liso, [int(cv2.IMWRITE_JPEG_QUALITY), 90])[1].tobytes()
    for numero in range(int(13.0 * 15)):  # gatilho em 4 s: o trecho fecha 8 s depois
        gravador.quadro(numero / 15, jpeg_limpo)
        if numero == 60:
            gravador.gatilho("microssono", numero / 15)
    gravado = gravador.trechos[0]
    indice, quadros_trecho = trechos.ler_rgclip(Path(tmp) / "trechos" / ("d" * 32) / gravado["arquivo"])
    primeiro = cv2.imdecode(np.frombuffer(quadros_trecho[0], np.uint8), cv2.IMREAD_COLOR)
    assert primeiro.shape == (480 + trechos.FAIXA_PX, 640, 3) and gravado["altura"] == 480 + trechos.FAIXA_PX
    diferenca = np.abs(primeiro[:480].astype(int) - liso.astype(int)).mean()
    assert diferenca < 2.0, f"o rosto do trecho é o quadro original (diferença média {diferenca:.2f}, só do JPEG)"
ok(f"MAL-05 trecho com o rosto limpo: o quadro fica intacto e a faixa com hora e tipo vai num rodapé de "
   f"{trechos.FAIXA_PX} px embaixo dele (diferença média {diferenca:.2f}, só da compressão)")


# ---------------------------------------------------------------- servidor de mentira da central
from central_falsa import TOKEN, Central  # noqa: E402

# Pareamento por código
central = Central().subir()
try:
    troca = sync.trocar_codigo(central.url, "abcd-2345", computador="Notebook de teste", programa="RotaGuard Teste")
    assert troca["token"].startswith("dsk_") and troca["empresa"]["nome"] == "Transportes Exemplo"
    try:
        sync.trocar_codigo(central.url, "ZZZZ-9999")
    except sync.ApiError as exc:
        assert exc.status == 404 and "inválido" in exc.message, exc
    else:
        raise AssertionError("código errado deveria falhar")
finally:
    central.descer()
ok("TRE-07 pareamento: o código vira token do aparelho e nome da empresa; código errado falha com a mensagem")

# ---------------------------------------------------------------- TRE-07 · sem conexão fica na fila e sobe depois
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp)
    fila = sync.FilaCentral(pasta / "central" / "fila.db")
    gravador = trechos.GravadorTrechos(pasta, "f" * 32, formato="rgclip", em_thread=False,
                                       ao_gravar=lambda meta: fila.adicionar_trecho(meta, pasta / "trechos"))
    alimentar(gravador, 0.0, 30.0, gatilhos={12.0: "microssono"})
    trecho = gravador.trechos[0]
    fila.salvar_sessao("f" * 32, {"iniciada_em": "2026-10-19T13:00:00Z", "encerrada_em": "2026-10-19T13:01:00Z",
                                  "programa": "RotaGuard Teste", "camera": "Câmera 1",
                                  "resumo": {"duracao_s": 60.0, "frequencia_cardiaca": {"media": 70}, "trechos": 1}})
    fila.adicionar_evento({"event_uid": "1" * 32, "alert_type": "microssono", "risk_level": 3, "duration": 1.4,
                           "occurred_at": "2026-10-19T13:00:12.000+00:00",
                           "details": {"sessao_uid": "f" * 32, "trecho_uid": trecho["uid"], "bpm": 70,
                                       "cardio": {"bpm": 70}, "fechado_s": 1.4}})
    assert fila.pendentes() == {"sessoes": 1, "eventos": 1, "trechos": 1}

    fora = Central().subir()
    endereco_fora = fora.url
    fora.descer()  # porta fechada: "central fora do ar"
    cliente = sync.ServerClient(endereco_fora, TOKEN, timeout=2)
    try:
        fila.enviar(cliente, {"hostname": "teste"})
    except OSError:
        pass
    else:
        raise AssertionError("sem central, enviar deveria falhar com erro de rede")
    assert fila.pendentes() == {"sessoes": 1, "eventos": 1, "trechos": 1}, "nada some da fila sem conexão"

    central = Central().subir()
    try:
        enviados = fila.enviar(sync.ServerClient(central.url, TOKEN, timeout=5), {"hostname": "teste"})
        assert enviados == {"sessoes": 1, "eventos": 1, "trechos": 1}, enviados
        assert fila.pendentes() == {"sessoes": 0, "eventos": 0, "trechos": 0}
        sessao = central.sessoes["f" * 32]
        assert "frequencia_cardiaca" not in json.dumps(sessao), "resumo enviado sem cardio"
        evento = central.eventos["1" * 32]
        assert evento["details"] == {"sessao_uid": "f" * 32, "trecho_uid": trecho["uid"], "fechado_s": 1.4}, evento
        cabecalhos, corpo = central.trechos[trecho["uid"]]
        for chave, valor in (("X-RotaGuard-Sessao", "f" * 32), ("X-RotaGuard-Tipo", "microssono"),
                             ("X-RotaGuard-Formato", "rgclip"), ("X-RotaGuard-Sha256", trecho["sha256"]),
                             ("X-RotaGuard-Inicio", trecho["inicio"]), ("X-RotaGuard-Fim", trecho["fim"])):
            assert cabecalhos.get(chave.lower()) == valor, (chave, cabecalhos.get(chave.lower()))
        assert hashlib.sha256(corpo).hexdigest() == trecho["sha256"]
        assert json.loads((pasta / "trechos" / ("f" * 32) / f"{trecho['uid']}.json").read_text("utf-8"))["enviado"]
        # Reenviar não repete nada; mudar a sessão manda de novo só ela
        assert fila.enviar(sync.ServerClient(central.url, TOKEN), {}) == {"sessoes": 0, "eventos": 0, "trechos": 0}
        fila.salvar_sessao("f" * 32, {"iniciada_em": "2026-10-19T13:00:00Z", "encerrada_em": "2026-10-19T13:02:00Z",
                                      "resumo": {"duracao_s": 120.0}})
        assert fila.enviar(sync.ServerClient(central.url, TOKEN), {})["sessoes"] == 1
    finally:
        central.descer()
    fila.fechar()
    # A fila sobrevive a fechar o app: abre de novo do disco
    reaberta = sync.FilaCentral(pasta / "central" / "fila.db")
    assert reaberta.pendentes() == {"sessoes": 0, "eventos": 0, "trechos": 0}
    reaberta.fechar()
ok("TRE-07 sem conexão, sessão, eventos e trechos ficam na fila e sobem quando a central volta, sem cardio")
assert sync.sem_cardio({"a": 1, "bpm": 2, "x": {"frequencia_cardiaca_bpm": 3, "y": [{"cardio": 1, "z": 2}]}}) == \
    {"a": 1, "x": {"y": [{"z": 2}]}}
ok("TRE-07 nenhum dado de cardio sai do computador (eventos, detalhes aninhados e resumo da sessão)")

# ---------------------------------------------------------------- TRE-08 · desligar o envio para e não apaga nada
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp)
    fila = sync.FilaCentral(pasta / "central" / "fila.db")
    fila.salvar_sessao("9" * 32, {"iniciada_em": "2026-10-19T13:00:00Z", "resumo": {}})
    central = Central().subir()
    try:
        envio = sync.EnvioCentral(fila, sync.ServerClient(central.url, TOKEN), intervalo=0.1, heartbeat_s=0.2)
        envio.start()
        assert envio.estado()["situacao"] == "desligado", "começa desligado até a tela ligar"
        time.sleep(0.6)
        assert not central.pedidos, "desligado não manda nada"
        envio.ligar()
        fim = time.monotonic() + 5
        while fila.pendentes()["sessoes"] and time.monotonic() < fim:
            time.sleep(0.05)
        assert not fila.pendentes()["sessoes"] and envio.estado()["situacao"] == "em_dia", envio.estado()
        envio.desligar()
        time.sleep(0.3)
        antes = len(central.pedidos)
        fila.salvar_sessao("8" * 32, {"iniciada_em": "2026-10-19T14:00:00Z", "resumo": {}})
        time.sleep(0.6)
        assert len(central.pedidos) == antes and fila.pendentes()["sessoes"] == 1, "desligado parou o envio"
        assert envio.estado()["situacao"] == "desligado"
        envio.parar()
        envio.join(timeout=5)
    finally:
        central.descer()
    assert (pasta / "central" / "fila.db").exists(), "nada local é apagado"
    fila.fechar()
ok("TRE-08 desligar 'Enviar para a empresa' para o envio e não apaga nada local")

# ---------------------------------------------------------------- respostas da central (mudanças do contrato da 026)
with tempfile.TemporaryDirectory() as tmp:
    pasta = Path(tmp)
    fila = sync.FilaCentral(pasta / "central" / "fila.db")
    gravador = trechos.GravadorTrechos(pasta, "7" * 32, formato="rgclip", em_thread=False,
                                       ao_gravar=lambda meta: fila.adicionar_trecho(meta, pasta / "trechos"))
    alimentar(gravador, 0.0, 80.0, fps=6.0, gatilhos={12.0: "microssono", 50.0: "olhos_esfregados"})
    assert len(gravador.trechos) == 2
    central = Central().subir()
    revogado = []
    try:
        cliente = sync.ServerClient(central.url, TOKEN, timeout=5)
        # 429 com Retry-After: o trecho continua na fila e o envio espera o tempo pedido
        central.forcar["/api/trechos"] = (429, {"Retry-After": "7"})
        try:
            fila.enviar(cliente, {})
        except sync.ApiError as exc:
            assert exc.status == 429 and exc.retry_after == 7.0, (exc.status, exc.retry_after)
        else:
            raise AssertionError("429 tem de subir para o envio esperar")
        assert fila.pendentes()["trechos"] == 2, "429 não perde trecho"
        envio = sync.EnvioCentral(fila, cliente, intervalo=0.1, heartbeat_s=60)
        envio.ligar()
        assert envio.uma_vez() == 7.0 and envio.estado()["situacao"] == "limite", envio.estado()
        # 409 (mesmo uid com outro SHA, ou já apagado): não adianta reenviar igual; o arquivo local fica
        central.forcar["/api/trechos"] = (409, {})
        assert fila.enviar(cliente, {})["trechos"] == 0 and fila.pendentes()["trechos"] == 0
        assert all((pasta / "trechos" / ("7" * 32) / meta["arquivo"]).exists() for meta in gravador.trechos)
        del central.forcar["/api/trechos"]
        # 401/403 no envio: "desconectado pela empresa", o envio para e nada local é apagado
        fila.salvar_sessao("6" * 32, {"iniciada_em": "2026-10-19T13:00:00Z", "resumo": {}})
        central.forcar["/api/sessoes"] = (401, {})
        envio = sync.EnvioCentral(fila, cliente, intervalo=0.1, heartbeat_s=60, ao_recusar=lambda: revogado.append(1))
        envio.ligar()
        envio.uma_vez()
        assert revogado == [1] and not envio.ligado and envio.estado()["situacao"] == "desligado"
        assert fila.pendentes()["sessoes"] == 1, "a sessão continua na fila"
    finally:
        central.descer()
    fila.fechar()
ok("TRE-07 429 espera o Retry-After sem perder o trecho; 409 não reenvia; 401/403 para o envio sem apagar nada")

print(f"\n{checks} verificações OK")
