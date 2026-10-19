"""Spec 027, pacote 1: alarme, risco e contexto (ALM-03 a ALM-08, CTX-01 a CTX-04, PER-01, RSK-01, FIL-01, DMS-04).

Critérios detalhados em docs/pesquisa/2026-10-19-alarme-calibracao-e-registro.md (§1.3, §3.3, §4 e §6.1) e
docs/pesquisa/2026-10-19-estado-da-arte-dms.md (DMS-04). Sem câmera e sem tocar som: a saída de áudio é falsa.
    python tests/test_alarme_risco.py
"""
import hashlib
import io
import json
import sys
import tempfile
import threading
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "caixa"))
from vision import alarm as alarme  # noqa: E402
from vision.alarm import Alarm  # noqa: E402
from vision.context import DrivingContext, janela_circadiana  # noqa: E402
from vision.drowsiness import Assessment, DetectedEvent, DrowsinessMonitor  # noqa: E402
from vision.event_queue import EventStore  # noqa: E402
from vision.eyes import DriverProfile, Sample  # noqa: E402
from vision.face_touch import FaceTouchAssessment  # noqa: E402
from vision.phone import PhoneAssessment  # noqa: E402
from vision.risk import AVISO_SONO, FAIXAS_SONO, TEXTOS, RiskAssessment, RiskFusion  # noqa: E402
from vision.visibility import Visibility  # noqa: E402

checks = 0
work = Path(tempfile.mkdtemp(prefix="rotaguard-alarme-risco-"))


def ok(message):
    global checks
    checks += 1
    print(f"OK {checks:02d} {message}")


def esperar(condicao, limite_s=1.0):
    fim = time.perf_counter() + limite_s
    while time.perf_counter() < fim:
        if condicao():
            return True
        time.sleep(0.002)
    return condicao()


def sono(level=0, reasons=(), alarm=False, face=True, openness=1.0, fps=30.0):
    return Assessment(level=level, reasons=list(reasons), alarm=alarm, face_found=face,
                      openness=openness if face else None, fps=fps)


def celular(risco=0, alarme=False, motivo="olhos_no_celular"):
    return PhoneAssessment(state="olhando_celular" if risco else "sem_celular", risk_level=risco,
                           reasons=[motivo] if risco else [], alarm=alarme)


def tipos(resultados):
    return [e.alert_type for r in resultados for e in r.events]


# ---------------------------------------------------------------------------------------------------------------
# ALM-03 · quatro sinais sintetizados, determinísticos, com harmônicos; crítico com a maior taxa de pulsos
# ---------------------------------------------------------------------------------------------------------------
def ler_wav(dados: bytes):
    with wave.open(io.BytesIO(dados)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, alarme.SAMPLE_RATE)
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32767.0
    return x


def pulsos(x, sr):
    """Trechos com som: envelope em janelas de 2 ms acima de 5% do pico."""
    passo = int(sr * 0.002)
    env = np.array([np.abs(x[i:i + passo]).max() for i in range(0, len(x), passo)])
    ativo = env > 0.05 * env.max()
    trechos, inicio = [], None
    for i, a in enumerate(ativo):
        if a and inicio is None:
            inicio = i
        elif not a and inicio is not None:
            trechos.append((inicio * passo, i * passo))
            inicio = None
    if inicio is not None:
        trechos.append((inicio * passo, len(x)))
    return trechos


def harmonicos(trecho, sr):
    """Quantos múltiplos da fundamental (1 a 8) ficam entre 200 e 8.000 Hz e a no máximo 15 dB do maior pico."""
    janela = trecho * np.hanning(len(trecho))
    espectro = np.abs(np.fft.rfft(janela, 1 << 16))
    freqs = np.fft.rfftfreq(1 << 16, 1 / sr)
    f0 = freqs[np.argmax(espectro)]
    maior = espectro.max()
    contados = 0
    for k in range(1, 9):
        alvo = k * f0
        if not 200.0 <= alvo <= 8000.0 or alvo >= sr / 2:
            continue
        perto = (freqs > alvo - 25) & (freqs < alvo + 25)
        if 20 * np.log10(espectro[perto].max() / maior) >= -15.0:
            contados += 1
    return f0, contados


primeira = {tipo: alarme.wav_bytes(tipo) for tipo in alarme.SOUND_KINDS}
segunda = {tipo: alarme.wav_bytes(tipo) for tipo in alarme.SOUND_KINDS}
assert alarme.SOUND_KINDS == ("info", "distracao", "sonolencia", "critico")
hashes = {tipo: hashlib.sha256(dados).hexdigest() for tipo, dados in primeira.items()}
segundos_hashes = {tipo: hashlib.sha256(dados).hexdigest() for tipo, dados in segunda.items()}
assert hashes == segundos_hashes, "ALM-03 não determinístico"
assert len(set(hashes.values())) == 4, "ALM-03 / DMS-04a os quatro sinais precisam ser diferentes"

taxas, resumo = {}, []
for tipo, dados in primeira.items():
    x = ler_wav(dados)
    sr = alarme.SAMPLE_RATE
    trechos = pulsos(x, sr)
    assert trechos, tipo
    for inicio, fim in trechos:
        f0, n = harmonicos(x[inicio:fim], sr)
        assert n >= 4, f"ALM-03 {tipo}: pulso em {inicio / sr:.2f} s com {n} harmônicos (f0 {f0:.0f} Hz)"
        assert 150.0 <= f0 <= 1200.0, (tipo, f0)
    duracao = (trechos[-1][1] - trechos[0][0]) / sr
    taxas[tipo] = len(trechos) / duracao
    pico = float(np.abs(x).max())
    assert 0.2 <= pico <= 0.95, (tipo, pico)
    assert abs(x[0]) < 0.01 and abs(x[-1]) < 0.01, f"{tipo}: começo ou fim sem rampa (clique)"
    resumo.append(f"{tipo} {len(x) / sr:.2f} s, {len(trechos)} pulsos, pico {pico:.2f}")
assert max(taxas, key=taxas.get) == "critico", taxas
assert taxas["critico"] > 1.5 * max(v for k, v in taxas.items() if k != "critico"), taxas
assert alarme.PICO["info"] < alarme.PICO["distracao"] < alarme.PICO["sonolencia"] < alarme.PICO["critico"]
ok("ALM-03 4 WAVs determinísticos e distintos; todo pulso com ≥ 4 harmônicos a ≤ 15 dB; crítico com a maior taxa "
   f"de pulsos ({taxas['critico']:.1f}/s); " + "; ".join(resumo))

pasta = work / "dados"
pasta.mkdir()
caminhos = alarme.garantir_sons(pasta / "sirene.wav")
assert set(caminhos) == set(alarme.SOUND_KINDS)
assert {c.name for c in caminhos.values()} == {f"sirene_{t}.wav" for t in alarme.SOUND_KINDS}
assert all(caminhos[t].read_bytes() == primeira[t] for t in alarme.SOUND_KINDS)
mtimes = {t: c.stat().st_mtime_ns for t, c in caminhos.items()}
time.sleep(0.02)
alarme.garantir_sons(pasta / "sirene.wav")
assert {t: c.stat().st_mtime_ns for t, c in caminhos.items()} == mtimes, "regravou WAV igual"
caminhos["info"].write_bytes(b"estragado")
alarme.garantir_sons(pasta / "sirene.wav")
assert caminhos["info"].read_bytes() == primeira["info"]
ok("ALM-03 WAVs gerados na pasta de dados na primeira vez, sem regravar quando iguais e refeitos se estragados")

fusao = RiskFusion()
pedidos = []
for t in range(0, 1200):
    alerta = t % 40 == 0
    r = fusao.update(float(t), sono(), phone=celular(2 if t % 40 < 5 else 0, alarme=alerta))
    pedidos.append(r.alarm_kind)
assert "critico" not in pedidos and "distracao" in pedidos
ok("ALM-03 celular nunca gera o sinal crítico (30 avisos em 20 min)")


# ---------------------------------------------------------------------------------------------------------------
# ALM-04 · reprodução interrompível com preempção; ALM-05 · autoteste do som
# ---------------------------------------------------------------------------------------------------------------
class SaidaFalsa:
    nome = "falsa"

    def __init__(self, duracao_s=2.0, falha=False):
        self.duracao_s = duracao_s
        self.falha = falha
        self.log = []
        self._trava = threading.Lock()

    def tocar(self, tipo, cancelar):
        with self._trava:
            self.log.append(("tocar", tipo, time.perf_counter()))
        if self.falha:
            raise RuntimeError("sem dispositivo de áudio")
        cancelar.wait(self.duracao_s)

    def parar(self):
        with self._trava:
            self.log.append(("parar", None, time.perf_counter()))

    def tocados(self):
        with self._trava:
            return [tipo for acao, tipo, _ in self.log if acao == "tocar"]

    def quando(self, acao, tipo=None):
        with self._trava:
            return [m for a, k, m in self.log if a == acao and (tipo is None or k == tipo)]


saida = SaidaFalsa(duracao_s=3.0)
sino = Alarm(pasta / "sirene.wav", saida=saida)
assert sino.saida_nome == "falsa" and not sino.is_playing
sino.trigger("distracao")
assert esperar(lambda: saida.tocados() == ["distracao"]) and sino.tocando == "distracao"
antes = time.perf_counter()
sino.trigger("critico")
assert esperar(lambda: "critico" in saida.tocados())
atraso = saida.quando("tocar", "critico")[0] - antes
assert atraso <= 0.100, f"ALM-04 crítico demorou {atraso * 1000:.0f} ms para interromper a distração"
assert saida.quando("parar") and saida.quando("parar")[0] <= saida.quando("tocar", "critico")[0]
for menor in ("distracao", "sonolencia", "info", "critico"):
    sino.trigger(menor)
time.sleep(0.05)
assert saida.tocados() == ["distracao", "critico"] and sino.tocando == "critico", saida.tocados()
antes = time.perf_counter()
sino.stop()
parou = time.perf_counter() - antes
assert not sino.is_playing and sino.tocando is None and parou <= 0.100, parou
assert saida.quando("parar")[-1] - antes <= 0.100
ok(f"ALM-04 crítico interrompe a distração em {atraso * 1000:.1f} ms; nada interrompe o crítico; stop() em "
   f"{parou * 1000:.1f} ms")

saida = SaidaFalsa(duracao_s=3.0)
sino = Alarm(pasta / "sirene.wav", saida=saida)
sino.update(RiskAssessment(alarm=True, alarm_kind="critico"))
assert esperar(lambda: sino.tocando == "critico")
antes = time.perf_counter()
sino.update(RiskAssessment(parar_alarme=True))
assert not sino.is_playing and time.perf_counter() - antes <= 0.100
sino.trigger()
assert esperar(lambda: saida.tocados()[-1:] == ["critico"]), "trigger() sem argumento = som mais urgente"
sino.stop()
sino.update(RiskAssessment(alarm=True))
assert esperar(lambda: saida.tocados() == ["critico"] * 3), "risco antigo com alarm=True e sem tipo = crítico"
sino.stop()
sino.update(RiskAssessment(alarm_kind="sonolencia"))
assert esperar(lambda: sino.tocando == "sonolencia")
sino.update(RiskAssessment(parar_alarme=True))
assert sino.tocando == "sonolencia", "o olho abrindo para só o crítico"
sino.stop()
ok("ALM-04 Alarm.update(risco): toca o tipo pedido e para o crítico quando o olho abre; trigger() sem tipo = crítico")

saida = SaidaFalsa(duracao_s=0.05)
sino = Alarm(pasta / "sirene.wav", saida=saida)
sino.trigger("sonolencia", repeticoes=2)
assert esperar(lambda: saida.tocados() == ["sonolencia", "sonolencia"] and not sino.is_playing, 2.0), saida.tocados()
sino.muted = True
sino.trigger("critico")
time.sleep(0.05)
assert saida.tocados() == ["sonolencia", "sonolencia"]
saida.duracao_s = 3.0
sino.muted = False
sino.trigger("critico")
assert esperar(lambda: sino.tocando == "critico")
sino.muted = True
assert not sino.is_playing, "mudo na hora para o som"
ok("ALM-06 2º estágio repete o som; mudo (tecla S da tela) não toca e corta o que estiver tocando")

terminal = alarme.descobrir_saida(caminhos, plataforma="linux", which=lambda nome: None, usar_sounddevice=False)
assert terminal.nome == "terminal"
aplay = alarme.descobrir_saida(caminhos, plataforma="linux", which=lambda nome: f"/usr/bin/{nome}" if nome == "aplay"
                               else None, usar_sounddevice=False)
assert aplay.nome == "aplay"
assert alarme.descobrir_saida(caminhos, plataforma="win32", usar_sounddevice=False).nome == "winsound"
store = EventStore(work / "autoteste.db")
sino = Alarm(pasta / "sirene.wav", saida=terminal)
resultado = sino.autoteste(store)
assert resultado["som"] == "sem_saida_de_som", resultado
linhas = store.pending()
assert [(e["alert_type"], e["details"]["som"]) for e in linhas] == [("estado_aparelho", "sem_saida_de_som")], linhas
saida = SaidaFalsa(duracao_s=0.05)
store_ok = EventStore(work / "autoteste-ok.db")
resultado = Alarm(pasta / "sirene.wav", saida=saida).autoteste(store_ok)
assert resultado == {"som": "ok", "saida": "falsa"} and saida.tocados() == ["info"] and not store_ok.pending()
quebrada = SaidaFalsa(falha=True)
assert Alarm(pasta / "sirene.wav", saida=quebrada).autoteste()["som"] == "sem_saida_de_som"
assert Alarm(pasta / "sirene.wav", saida=SaidaFalsa(), muted=True).autoteste()["som"] == "mudo"
store.close()
store_ok.close()
ok("ALM-05 autoteste toca info uma vez; sem player (ou player com erro) registra estado_aparelho sem_saida_de_som")


# ---------------------------------------------------------------------------------------------------------------
# ALM-06 · escalonamento; ALM-07 · memória de sonolência; CTX-01 · pausa sugerida e detectada
# ---------------------------------------------------------------------------------------------------------------
fusao = RiskFusion()
rs = [fusao.update(float(t), sono(2, ["olhos_fechados_por_mais_tempo"])) for t in range(0, 400)]
assert rs[0].alarm_kind == "sonolencia" and rs[0].estagio_sonolencia == 1 and rs[0].alarm_repeticoes == 1
assert rs[0].mensagem == TEXTOS["sonolencia_1"] and "pausa_sugerida" in tipos(rs[:1])
assert all(r.estagio_sonolencia == 1 for r in rs[1:300]) and rs[299].alarm_kind is None
assert rs[300].estagio_sonolencia == 2 and rs[300].alarm_kind == "sonolencia" and rs[300].alarm_repeticoes == 2
assert rs[300].mensagem == TEXTOS["sonolencia_2"]
sugeridas = [e for r in rs for e in r.events if e.alert_type == "pausa_sugerida"]
assert [e.details["estagio"] for e in sugeridas] == [1, 2], sugeridas
assert all(r.estagio_sonolencia == 2 for r in rs[300:])
ok("ALM-06 sonolência por 5 min passa ao 2º estágio: som repetido, frase de parar e pausa sugerida de novo")

fusao = RiskFusion()
rs = [fusao.update(float(t), sono(2 if t < 60 else 0, ["olhos_fechados_por_mais_tempo"] if t < 60 else []))
      for t in range(0, 2000)]
assert all(r.level >= 1 for r in rs[:1859]), [t for t, r in enumerate(rs[:1859]) if r.level < 1][:5]
assert rs[1000].memoria_sonolencia and "sonolencia_recente_sem_pausa" in rs[1000].reasons
assert rs[1000].risco_sono == 1 and rs[1000].mensagem == TEXTOS["memoria"]
assert not rs[1925].memoria_sonolencia and rs[1925].level == 0, (rs[1925].level, rs[1925].reasons)
ok("ALM-07 depois de nível 2 por sono, o risco fica ≥ 1 por 30 min sem sinais e só então volta a 0")

fusao = RiskFusion()
rs = []
for t in range(0, 1400):
    if t < 60:
        rs.append(fusao.update(float(t), sono(2, ["fechamentos_longos"])))
    elif t < 120:
        rs.append(fusao.update(float(t), sono(0)))
    elif t < 1200:
        rs.append(fusao.update(float(t), sono(0, face=False)))
    else:
        rs.append(fusao.update(float(t), sono(0)))
assert "pausa_sugerida" in tipos(rs[:1])
assert not rs[1050].memoria_sonolencia, "pausa de 15 min encerra a memória"
detectadas = [e for r in rs for e in r.events if e.alert_type == "pausa_detectada"]
assert len(detectadas) == 1, detectadas
assert abs(detectadas[0].details["duracao_s"] - 1080) <= 3 and detectadas[0].details["apos_sugestao"]
assert detectadas[0].details["fonte"] == "rosto_ausente" and abs(detectadas[0].duration - 1080) <= 3
assert rs[1300].level == 0
leve = [fusao.update(float(t), sono(1, ["fechamento_longo"])) for t in range(1400, 1470)]
subiu = next(i for i, r in enumerate(leve) if r.level == 2)
assert subiu <= 60 and "sinais_leves_logo_apos_pausa" in leve[subiu].reasons, subiu
controle = RiskFusion()
assert max(controle.update(float(t), sono(1, ["fechamento_longo"])).level for t in range(0, 70)) == 1
ok(f"CTX-01 pausa sugerida; rosto ausente 18 min = pausa_detectada de {detectadas[0].details['duracao_s']} s; "
   f"sinal leve na hora seguinte vira nível 2 em {subiu} s (sem pausa recente fica em 1)")

fusao = RiskFusion()
for t in range(0, 60):
    fusao.update(float(t), sono(2, ["fechamentos_longos"]))
parado = {"velocidade_kmh": 0.0, "fonte_tempo_direcao": "telemetria"}
rs = [fusao.update(float(t), sono(0), context=parado) for t in range(60, 1100)]
assert not rs[-1].memoria_sonolencia and rs[-1].level == 0
ok("ALM-07 telemetria parada por 15 min também conta como pausa e encerra a memória")


# ---------------------------------------------------------------------------------------------------------------
# ALM-08 · orçamento de avisos de celular por hora (o crítico nunca é limitado)
# ---------------------------------------------------------------------------------------------------------------
fusao = RiskFusion()
avisos, registro = [], []
for t in range(0, 3600):
    alerta = t % 180 == 0
    r = fusao.update(float(t), sono(), phone=celular(2 if alerta else 0, alarme=alerta))
    if alerta:
        avisos.append((r.alarm_kind, r.alarm_suavizado, r.alarm))
    registro += [e for e in r.events if e.alert_type == "avisos_de_distracao_suavizados"]
assert len(avisos) == 20
assert avisos[:5] == [("distracao", False, True)] * 5, avisos[:6]
assert avisos[5:] == [("info", True, False)] * 15, avisos[5:]
assert len(registro) == 1 and registro[0].details["limite_por_hora"] == 5
assert registro[0].details["origem"] == "celular"
assert registro[0].details["avisos_na_ultima_hora"] == 6
critico = fusao.update(3600.5, sono(3, ["microssono"], alarm=True, openness=0.0))
assert critico.alarm_kind == "critico" and critico.alarm
depois = fusao.update(7300.0, sono(), phone=celular(2, alarme=True))
assert depois.alarm_kind == "distracao", "uma hora depois o orçamento volta"
ok("ALM-08 20 avisos de celular em 1 h: 5 com som de distração, 15 suaves e 1 linha no registro; crítico não limitado")


# ---------------------------------------------------------------------------------------------------------------
# CTX-02 a CTX-04 · contexto da jornada
# ---------------------------------------------------------------------------------------------------------------
def contexto_em(hora, minuto=0, ano=2026):
    return DrivingContext(now=lambda: datetime(ano, 10, 19, hora, minuto, tzinfo=timezone.utc)).snapshot()


assert contexto_em(3)["circadiano"] == "forte" and contexto_em(3)["madrugada"] is True
assert contexto_em(15)["circadiano"] == "moderado" and contexto_em(15)["madrugada"] is False
assert contexto_em(1)["circadiano"] is None and contexto_em(1)["madrugada"] is False
assert contexto_em(5, 59)["circadiano"] == "forte" and contexto_em(6)["circadiano"] is None
assert contexto_em(14)["circadiano"] == "moderado" and contexto_em(16)["circadiano"] is None
assert contexto_em(3, ano=2000)["circadiano"] is None and contexto_em(3, ano=2000)["madrugada"] is None
assert [janela_circadiana(h) for h in (1, 2, 3, 6, 13, 14, 15, 16)] == [None, "forte", "forte", None, None, "moderado",
                                                                       "moderado", None]
leve = sono(1, ["fechamento_longo"])
forte = RiskFusion()
moderado = RiskFusion()
rf = [forte.update(float(t), leve, context=contexto_em(3)) for t in range(0, 320)]
rm = [moderado.update(float(t), leve, context=contexto_em(15)) for t in range(0, 320)]
assert rf[300].level == 2 and "sinais_leves_em_contexto_de_risco" in rf[300].reasons
assert max(r.level for r in rm) == 1
ok("CTX-02 03h = janela forte (antecipa a escalada); 15h = moderada (só registro); 01h = nada; relógio inválido = null")

contexto = DrivingContext()
t = 0.0
while t <= 6 * 3600:
    contexto.update(t, face_found=True)
    t += 5.0
foto = contexto.snapshot()
assert foto["limite_direcao_excedido"] is None and foto["direcao_continua_h"] is None, foto
assert abs(foto["tempo_com_rosto_h"] - 6.0) <= 0.01 and foto["fonte_tempo_direcao"] == "camera", foto
fusao = RiskFusion()
r = fusao.update(0.0, sono(), context=foto)
assert not r.events and "direcao_continua_acima_de_5h30" not in r.reasons and r.level == 0
ok("CTX-03 sem telemetria, 6 h com rosto na câmera: limite legal = null e tempo_com_rosto_h = 6 (estimativa)")

telemetria = work / "telemetria.json"
telemetria.write_text(json.dumps({"velocidade_kmh": 80, "atualizado_em": 1000.0}), encoding="utf-8")


def dirigir(tipo, horas):
    contexto = DrivingContext(telemetry_path=telemetria, wall_time=lambda: 1000.0, tipo_veiculo=tipo,
                              now=lambda: datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc))
    t = 0.0
    while t <= horas * 3600:
        contexto.update(t, face_found=False)
        t += 5.0
    return contexto.snapshot()


assert dirigir("passageiros", 3.95)["descanso_previsto_excedido"] is False
passageiros = dirigir("passageiros", 4.02)
assert passageiros["descanso_previsto_excedido"] is True and passageiros["descanso_previsto_h"] == 4.0
assert passageiros["limite_direcao_excedido"] is False and passageiros["fonte_tempo_direcao"] == "telemetria"
assert dirigir("carga", 4.02)["descanso_previsto_excedido"] is None
assert DrivingContext().snapshot()["descanso_previsto_excedido"] is None
try:
    DrivingContext(tipo_veiculo="moto")
    raise AssertionError("tipo de veículo inválido aceito")
except ValueError:
    pass
fusao = RiskFusion()
rs = [fusao.update(float(t), sono(), context=passageiros) for t in range(0, 120)]
aviso = [e for r in rs for e in r.events if e.alert_type == "descanso_previsto_em_atraso"]
assert len(aviso) == 1 and rs[0].alarm_kind == "info" and not rs[0].alarm, (aviso, rs[0].alarm_kind)
assert rs[50].mensagem == TEXTOS["descanso"] and all(r.alarm_kind is None for r in rs[1:])
ok("CTX-04 passageiros com telemetria: aviso de descanso em 4 h (som info, registro, sem alarme); carga não")


# ---------------------------------------------------------------------------------------------------------------
# PER-01 · PERCLOS por quadros (AAA) junto do atual
# ---------------------------------------------------------------------------------------------------------------
def abertura(t, periodo=3.0):
    """Piscada de 120 ms a cada 3 s (20 por minuto): 30 ms fechando, 60 ms fechado, 30 ms abrindo."""
    tau = (t % periodo) - 1.0
    if tau < 0 or tau >= 0.12:
        return 1.0
    if tau < 0.03:
        return 1.0 - tau / 0.03
    if tau < 0.09:
        return 0.0
    return (tau - 0.09) / 0.03


perfil = DriverProfile(ear_open=0.30, ear_closed=0.06, score_open=0.05, score_closed=0.90, perclos_baseline=0.0)
monitor = DrowsinessMonitor(profile=perfil)
fusao = RiskFusion()
fps = 30.0
for i in range(int(200 * fps)):
    t = i / fps
    o = abertura(t)
    amostra = Sample(timestamp=t, face_found=True, ear=0.06 + o * 0.24, blink_score=0.05 + (1.0 - o) * 0.85,
                     jaw_open=0.02, pitch=0.0, yaw=0.0, eye_distance_px=90.0)
    avaliacao = monitor.update(amostra)
    r = fusao.update(t, avaliacao, window=monitor.details)
assert monitor.details["perclos_3min"] == 0.0 and monitor.details["fechamentos_longos_5min"] == 0, monitor.details
assert r.perclos_quadros_3min is not None and 0.0 < r.perclos_quadros_3min < 0.05, r.perclos_quadros_3min
assert r.detalhes["perclos_3min"] == 0.0 and r.detalhes["perclos_quadros_3min"] == r.perclos_quadros_3min
assert r.level == 0, "o PERCLOS por quadros é registro: não muda o nível"
ok(f"PER-01 piscadas de 120 ms a 20/min: perclos_3min = 0 e perclos_quadros_3min = {r.perclos_quadros_3min:.3f}; "
   "os dois nos detalhes")


# ---------------------------------------------------------------------------------------------------------------
# RSK-01 · sono_estimado (faixa de KSS com confiança) e canais sono × distração
# ---------------------------------------------------------------------------------------------------------------
assert AVISO_SONO == "estimativa, não é medida de KSS nem diagnóstico"
assert FAIXAS_SONO == ("sem sinais de sono", "sinais compatíveis com KSS 6–7", "sinais compatíveis com KSS ≥ 8",
                       "sono comportamental (microssono)")
for nivel in range(4):
    r = RiskFusion().update(0.0, sono(nivel, ["x"] if nivel else [], alarm=nivel == 3, openness=0.0 if nivel == 3
                                      else 1.0), window={"perclos_base": 0.01})
    estimado = r.sono_estimado
    assert estimado["faixa"] == FAIXAS_SONO[nivel] and estimado["aviso"] == AVISO_SONO, estimado
    assert estimado["nivel"] == nivel == r.risco_sono and estimado["confianca"] in ("alta", "media", "baixa")
    assert r.detalhes["sono_estimado"] == estimado
assert RiskAssessment().sono_estimado["faixa"] == FAIXAS_SONO[0]
sem_quadros = RiskFusion().update(0.0, sono(2, ["x"], fps=None))
assert sem_quadros.sono_estimado["confianca"] == "baixa"
assert "sem_calibracao" in sem_quadros.sono_estimado["motivos_confianca"]
lento = RiskFusion().update(0.0, sono(0, fps=15.0), window={"perclos_base": 0.01})
assert lento.sono_estimado["confianca"] == "media", lento.sono_estimado
fusao = RiskFusion()
rs = [fusao.update(float(t), sono(), phone=celular(2, alarme=t % 30 == 0)) for t in range(0, 300)]
assert all(r.risco_sono == 0 and r.sono_estimado["faixa"] == FAIXAS_SONO[0] for r in rs)
assert rs[-1].risco_distracao == 2 and rs[-1].level == 2 and not rs[-1].memoria_sonolencia
assert rs[0].mensagem == TEXTOS["distracao"]
ok("RSK-01 cada nível gera a faixa da tabela 3.3 com o aviso fixo; confiança cai sem calibração e com fps baixo; "
   "celular sozinho mantém risco_sono = 0")


# ---------------------------------------------------------------------------------------------------------------
# FIL-01 · fila com synchronous=FULL
# ---------------------------------------------------------------------------------------------------------------
fila = EventStore(work / "fila.db")
assert fila._conn.execute("PRAGMA synchronous").fetchone()[0] == 2
assert fila._conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
fila.add("teste", 1, 0.0, {"a": 1})
assert fila.count_pending() == 1
fila.close()
ok("FIL-01 PRAGMA synchronous = 2 (FULL) com WAL")


# ---------------------------------------------------------------------------------------------------------------
# DMS-04 · "sem visão": som info uma vez por viagem aos 10 s e texto fixo
# ---------------------------------------------------------------------------------------------------------------
def episodio(fusao, inicio, segundos, oculos=True, contexto=None, fps=10.0):
    saida = []
    for i in range(int(segundos * fps)):
        t = inicio + i / fps
        if oculos:
            vis = Visibility(eyes_ok=False, reason="oculos_escuros", hidden_for=i / fps)
            saida.append(fusao.update(t, sono(openness=None), context=contexto, visibility=vis))
        else:
            saida.append(fusao.update(t, sono(face=False), context=contexto))
    return saida


fusao = RiskFusion()
primeiro = episodio(fusao, 0.0, 12.0)
sons = [(i / 10.0, r.alarm_kind) for i, r in enumerate(primeiro) if r.alarm_kind]
assert len(sons) == 1 and sons[0][1] == "info" and 10.0 <= sons[0][0] <= 10.2, sons
assert not any(r.alarm for r in primeiro)
assert all(r.sem_visao and r.mensagem == TEXTOS["sem_visao"] for r in primeiro[101:])
assert not any(r.sem_visao for r in primeiro[:99]) and primeiro[50].mensagem is None
volta = [fusao.update(12.0 + i / 10.0, sono(), visibility=Visibility()) for i in range(50)]
assert not volta[-1].sem_visao and volta[-1].mensagem is None
segundo = episodio(fusao, 20.0, 12.0)
assert not any(r.alarm_kind for r in segundo) and segundo[-1].mensagem == TEXTOS["sem_visao"]
ok("DMS-04 óculos escuros 10 s: 1 som info e texto fixo; 2º episódio na mesma viagem: só texto")

sem_rosto = episodio(RiskFusion(), 0.0, 12.0, oculos=False)
assert [r.alarm_kind for r in sem_rosto].count("info") == 1 and sem_rosto[-1].sem_visao
mao = RiskFusion()
mao_na_frente = PhoneAssessment(face_touch=FaceTouchAssessment(face_hidden=True))
tapado = [mao.update(i / 10.0, sono(face=False), phone=mao_na_frente) for i in range(120)]
assert not any(r.sem_visao or r.alarm_kind for r in tapado), "mão no rosto não é 'sem visão'"
estacionado = episodio(RiskFusion(), 0.0, 12.0, contexto={"velocidade_kmh": 0.0})
assert not any(r.alarm_kind for r in estacionado) and estacionado[-1].sem_visao
apos_micro = RiskFusion()
for i in range(20):
    apos_micro.update(i / 10.0, sono(3 if i < 15 else 0, ["microssono"] if i < 15 else [], alarm=i < 15,
                                     openness=0.0 if i < 15 else 1.0))
oculos_depois = episodio(apos_micro, 30.0, 12.0)
assert [r.alarm_kind for r in oculos_depois].count("info") == 1, "óculos escuros depois de sugerir pausa ainda avisam"
assert oculos_depois[-1].mensagem == TEXTOS["sem_visao"], oculos_depois[-1].mensagem
saiu = RiskFusion()
for i in range(20):
    saiu.update(i / 10.0, sono(3 if i < 15 else 0, ["microssono"] if i < 15 else [], alarm=i < 15,
                               openness=0.0 if i < 15 else 1.0))
foi_parar = episodio(saiu, 30.0, 12.0, oculos=False)
assert not any(r.alarm_kind for r in foi_parar) and foi_parar[-1].sem_visao, "rosto some logo depois de sugerir pausa"
calibrou = sono()
calibrou.events = [DetectedEvent("calibracao_concluida", 1, 300.0, {})]
assert RiskFusion().update(0.0, calibrou).alarm_kind == "info", "calibração concluída toca o info (§1.3)"
suspeita = sono()
suspeita.events = [DetectedEvent("calibracao_suspeita", 2, 300.0, {})]
assert RiskFusion().update(0.0, suspeita).alarm_kind is None
microssono = RiskFusion().update(0.0, sono(3, ["microssono"], alarm=True, openness=0.0))
assert microssono.alarm_kind == "critico" and microssono.mensagem == TEXTOS["critico"]
distracao = RiskFusion().update(0.0, sono(), phone=celular(2, alarme=True))
assert distracao.alarm_kind == "distracao" and hashes["critico"] != hashes["distracao"]
ok("DMS-04 sem rosto também avisa (menos logo depois de sugerir pausa); óculos sempre avisam; mão tapando não; "
   "parado (telemetria) só texto; calibração concluída = info; microssono = crítico, celular = "
   "distração, com WAVs diferentes")


# ---------------------------------------------------------------------------------------------------------------
# Canal de distração pelo olhar (vision/distraction.py, pacote 2) na fusão
# ---------------------------------------------------------------------------------------------------------------
def olhar(nivel=0, alarme=False, tipo=None, motivo="olhar_fora_da_via"):
    return SimpleNamespace(level=nivel, alarm=alarme, alarm_kind=tipo, reasons=[motivo] if nivel else [], events=[])


fusao = RiskFusion()
aviso = fusao.update(0.0, sono(), distraction=olhar(2, True, "distracao"))
assert aviso.alarm_kind == "distracao" and aviso.alarm and aviso.risco_distracao == 2 and aviso.risco_sono == 0
assert aviso.level == 2 and aviso.mensagem == TEXTOS["olhar"] and "olhar_fora_da_via" in aviso.reasons
sem_resposta = [fusao.update(3.0 + i / 10.0, sono(), distraction=olhar(3, True, "critico")) for i in range(10)]
assert all(r.alarm_kind == "critico" and r.level == 3 and r.risco_distracao == 3 for r in sem_resposta)
assert sem_resposta[0].mensagem == TEXTOS["sem_resposta"]
voltou = fusao.update(4.1, sono(), distraction=olhar(0))
assert voltou.parar_alarme and voltou.alarm_kind is None and not voltou.memoria_sonolencia
fusao = RiskFusion()
tipos_som = []
for i in range(6):
    t = i * 300.0
    if i % 2:
        r = fusao.update(t, sono(), distraction=olhar(2, True, "distracao"))
    else:
        r = fusao.update(t, sono(), phone=celular(2, alarme=True))
    tipos_som.append(r.alarm_kind)
    for k in range(1, 130):
        fusao.update(t + k, sono())
assert tipos_som == ["distracao"] * 5 + ["info"], tipos_som
ok("canal de distração pelo olhar: aviso = som de distração; sem resposta = crítico até o olhar voltar; celular e "
   "olhar dividem o orçamento de 5 avisos por hora; nada disso mexe no risco_sono")


# ---------------------------------------------------------------------------------------------------------------
# Compatibilidade: chamadas antigas continuam valendo
# ---------------------------------------------------------------------------------------------------------------
antigo = RiskAssessment(level=2, name="alto", reasons=["microssono"])
assert antigo.alarm_kind is None and antigo.alarm_repeticoes == 1 and antigo.risco_sono == 0 and antigo.detalhes == {}
fusao = RiskFusion()
r = fusao.update(0.0, sono(3, ["microssono"], alarm=True, openness=0.0), None, {}, {}, {}, None)
assert r.level == 3 and r.alarm and r.alarm_kind == "critico"
fim = fusao.update(0.1, sono(0, openness=1.0))
assert fim.parar_alarme and fim.alarm_kind is None
assert not fusao.update(0.2, sono(0)).parar_alarme
assert alarme.write_siren_wav(work / "legado.wav") is None and (work / "legado.wav").read_bytes() == primeira["critico"]
ok("compatibilidade: RiskAssessment antigo, update posicional, parar_alarme ao abrir o olho e write_siren_wav")

# RSK-02 (decisão de 19/10/2026): o nível 1 do olhar ("atenção visual": balde vazio, olhada de 3 s ao espelho) fica
# só no canal de distração, para a tela; não sobe o risco geral nem entra nos motivos. Do nível 2 em diante, entra.
fusao = RiskFusion()
atencao = SimpleNamespace(level=1, alarm=False, alarm_kind=None, reasons=["atencao_visual"])
resultado = fusao.update(0.0, sono(0), distraction=atencao)
assert resultado.level == 0 and resultado.risco_distracao == 1, (resultado.level, resultado.risco_distracao)
assert "atencao_visual" not in resultado.reasons
distraido = SimpleNamespace(level=2, alarm=False, alarm_kind=None, reasons=["olhar_fora_da_via"])
resultado = fusao.update(0.5, sono(0), distraction=distraido)
assert resultado.level == 2 and resultado.risco_distracao == 2 and "olhar_fora_da_via" in resultado.reasons
ok("RSK-02: atenção visual (nível 1 do olhar) só no canal de distração; distração (nível 2) sobe o risco geral")

print(f"\n{checks} verificações OK (spec 027, pacote 1)")
