"""Fusão e alertas (módulo 4): nível de risco de 0 a 3 com histerese, regra de rebote e contexto da viagem.

0 normal, 1 atenção, 2 alto, 3 crítico. A linguagem é sempre "nível de risco" e "sinais compatíveis com":
o sistema não faz diagnóstico.

- Sonolência (módulo 1) define a base: perigo → crítico, sonolência → alto, atenção → atenção.
- Contexto (janela circadiana forte, 02h a 06h, ou mais de 5 h 30 min ao volante com telemetria, vision/context.py):
  sinais leves de sonolência que duram 5 min viram risco alto, em vez de esperar os 10 min normais.
- Olhos esfregados (vision/face_touch.py): 3 ou mais em 10 min fazem o mesmo que o contexto. Sozinhos não mudam o
  risco (sinal leve, limiar a validar). Mão parada no rosto não pesa: é comum acordado (Ralph et al., 2022).
- Rebote: quando o efeito do estimulante passa, vêm depressão, fadiga e sono (Takitane et al., 2013, Ciência &
  Saúde Coletiva). Depois de ativação atípica sustentada por 10 min, qualquer sinal de sonolência na hora seguinte
  eleva o risco para alto na mesma hora, com alarme. Tempos e limiares são hipóteses a validar.
- Histerese: o risco sobe na hora e desce um nível por vez, só depois de o motivo sumir por 10 s (crítico) ou 60 s.

Spec 027, pacote 1 (pesquisa de 19/10/2026, §1.3 e §3.3):
- Dois canais: `risco_sono` (0 a 3) e `risco_distracao` (celular 0 a 2; olhar até 3, sem resposta). `level` é o
  maior deles (e da jornada e da ativação), para o painel. Celular nunca pede o sinal crítico.
- Sinal sonoro por urgência (`alarm_kind`: info, distracao, sonolencia, critico; vision/alarm.py). `alarm` continua
  valendo só para alarme de verdade (distração, sonolência, crítico).
- Escalonamento (DDAW "cascade and intensify"; Gaspar et al., 2017): sonolência → 1º estágio (som e frase de
  procurar local para parar); 5 min depois, ainda com sono → 2º estágio (som repetido e "pare e descanse").
- Memória de sonolência (Euro NCAP 2026, §1.4.3): depois de nível 2 por sono, o risco não desce de 1 até uma pausa
  de 15 min (rosto ausente ou telemetria parada) ou 30 min sem sinais. Hoje voltava a 0 em ~2 min.
- `pausa_sugerida` e `pausa_detectada` no registro (o alerta sozinho não faz parar: NHTSA DOT HS 813 439). Na hora
  seguinte a uma pausa por sono, sinal leve vira alto em 30 s (a pausa ajuda por pouco tempo: FMCSA).
- Distração pelo olhar (vision/distraction.py, `distraction=`) entra no mesmo canal do celular; o "sem resposta"
  depois do aviso (olhar que não volta em 3 s, Euro NCAP §1.3.5) pede o crítico.
- Orçamento de avisos de distração (celular e olhar): do 6º na última hora em diante, som suave (info) e uma linha no
  registro (fadiga de alarme: Lees & Lee, 2007). O crítico nunca é limitado.
- "Sem visão" (Euro NCAP 1.1.1.2; DDAW §3.5.3): 10 s sem ver os olhos → texto fixo enquanto durar e o som info uma
  vez por viagem.
- `sono_estimado`: faixa de KSS compatível com o nível, com confiança e o aviso fixo "estimativa, não é medida de
  KSS nem diagnóstico". Não altera alarme nem nível.
- PERCLOS por quadros (AAA, Owens et al., 2018): todos os quadros com a pálpebra ≥ 80% fechada, piscadas incluídas.
  Só registro, ao lado do PERCLOS de vision/drowsiness.py (que conta fechamentos de mais de 250 ms).
"""
from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field

from vision.context import STOPPED_KMH
from vision.drowsiness import DetectedEvent
from vision.eyes import MAX_FRAME_GAP_S, P80_OPENNESS

logger = logging.getLogger("drivesafe.risk")

LEVEL_NAMES = ("normal", "atencao", "alto", "critico")
HOLD_DOWN_S = {3: 10.0, 2: 60.0, 1: 60.0}
CONTEXT_ESCALATION_S = 300.0
HAND_GESTURES_LIGHT_SIGNAL = 3
REBOUND_MIN_ACTIVATION_S = 600.0
REBOUND_GAP_S = 120.0  # intervalo tolerado sem sinais dentro de um mesmo episódio de ativação
REBOUND_WINDOW_S = 3600.0
REBOUND_HOLD_S = 300.0
REBOUND_DURATION_Z = 1.5  # piscadas mais longas que o normal da pessoa também contam como sinal de sonolência
ALARM_COOLDOWN_S = 60.0
COOLDOWN_S = {"sonolencia_abrupta": 600.0, "ativacao_atipica": 1800.0, "direcao_continua": 1800.0,
              "pausa_sugerida": 1800.0, "descanso_previsto_em_atraso": 1800.0,
              "avisos_de_distracao_suavizados": 3600.0}
REBOUND_WINDOW_KEYS = ("perclos_60s", "perclos_3min", "duracao_mediana_ms", "fechamentos_longos_5min", "piscadas_por_min")

# Spec 027, pacote 1.
SOUND_PRIORITY = {"info": 0, "distracao": 1, "sonolencia": 2, "critico": 3}
ALARM_SOUNDS = frozenset({"distracao", "sonolencia", "critico"})
SLEEP_EPISODE_GAP_S = 120.0  # sem nível 2 por sono por mais que isso, o episódio (e o estágio) termina
SLEEP_STAGE2_S = 300.0
MEMORY_PAUSE_S = 900.0
MEMORY_QUIET_S = 1800.0
PRESENCE_CONFIRM_S = 2.0  # rosto de volta por 2 s encerra a ausência (um quadro falso não divide a pausa)
RECENT_PAUSE_WINDOW_S = 3600.0
RECENT_PAUSE_ESCALATION_S = 30.0
PHONE_BUDGET_PER_HOUR = 5  # avisos de distração (celular e olhar) com o som normal, por hora
PHONE_BUDGET_WINDOW_S = 3600.0
NO_VISION_WARN_S = 10.0
NO_VISION_CLEAR_S = 1.0
SUGGESTION_RECENT_S = 1800.0  # rosto some logo depois de sugerir pausa: provável pausa, o "sem visão" fica sem som
PERCLOS_FRAMES_WINDOW_S = 180.0
PERCLOS_FRAMES_MIN_VALID = 0.5
LOW_FPS = 10.0
DURATION_FPS = 24.0

AVISO_SONO = "estimativa, não é medida de KSS nem diagnóstico"
FAIXAS_SONO = ("sem sinais de sono", "sinais compatíveis com KSS 6–7", "sinais compatíveis com KSS ≥ 8",
               "sono comportamental (microssono)")
# Textos fixos para o motorista (tela e, depois, a frase gravada: o DDAW pede o mesmo vocabulário no som e no texto).
TEXTOS = {
    "critico": "Olhos fechados. Abra os olhos e pare em um local seguro.",
    "sonolencia_1": "Sinais de sono. Procure um local seguro para parar.",
    "sonolencia_2": "Pare e descanse de 15 a 20 minutos.",
    "distracao": "Celular ao volante. Olhe para a estrada.",
    "olhar": "Atenção: olhe para a estrada.",
    "sem_resposta": "Olhe para a estrada agora.",
    "sem_visao": "Não consigo ver seus olhos. Ajuste a câmera ou tire os óculos escuros.",
    "memoria": "Você teve sinais de sono há pouco. Faça uma pausa assim que puder.",
    "descanso": "Hora do descanso: pare por 30 minutos.",
}
_LOW_CONFIDENCE = frozenset({"sem_taxa_de_quadros", "taxa_de_quadros_abaixo_de_10", "sem_calibracao",
                             "calibracao_suspeita"})


def estimar_sono(nivel: int, fps: float | None = None, window: dict | None = None, calibracao_suspeita: bool = False,
                 memoria: bool = False) -> dict:
    """Faixa de KSS compatível com o nível de sono (tabela 3.3 da pesquisa), nunca um número de KSS."""
    window = window or {}
    motivos = []
    if fps is None:
        motivos.append("sem_taxa_de_quadros")
    elif fps < LOW_FPS:
        motivos.append("taxa_de_quadros_abaixo_de_10")
    elif fps < DURATION_FPS:
        motivos.append("taxa_de_quadros_abaixo_de_24")  # duração da piscada não confiável
    if window.get("perclos_base") is None:
        motivos.append("sem_calibracao")
    if calibracao_suspeita:
        motivos.append("calibracao_suspeita")
    confianca = "baixa" if _LOW_CONFIDENCE & set(motivos) else ("media" if motivos else "alta")
    nivel = max(0, min(int(nivel), 3))
    return {"nivel": nivel, "faixa": FAIXAS_SONO[nivel], "confianca": confianca, "motivos_confianca": motivos,
            "mantido_pela_memoria": bool(memoria), "aviso": AVISO_SONO}


class PerclosQuadros:
    """Fração dos quadros válidos com abertura ≤ 20% (pálpebra ≥ 80% fechada), em baldes de 1 s."""

    def __init__(self, window_s: float = PERCLOS_FRAMES_WINDOW_S):
        self.window_s = window_s
        self._buckets = deque()  # [segundo, quadros válidos, quadros fechados, tempo válido]

    def add(self, t: float, openness: float | None, dt: float) -> None:
        if openness is None:
            return
        second = math.floor(t)
        if not self._buckets or self._buckets[-1][0] != second:
            self._buckets.append([second, 0, 0, 0.0])
            while self._buckets and self._buckets[0][0] < second - self.window_s:
                self._buckets.popleft()
        bucket = self._buckets[-1]
        bucket[1] += 1
        bucket[2] += openness <= P80_OPENNESS
        bucket[3] += dt

    def value(self, now: float) -> float | None:
        valid = closed = 0
        seconds = 0.0
        for second, frames, closed_frames, valid_s in reversed(self._buckets):
            if second < now - self.window_s:
                break
            valid += frames
            closed += closed_frames
            seconds += valid_s
        if not valid or seconds < self.window_s * PERCLOS_FRAMES_MIN_VALID:
            return None
        return closed / valid


@dataclass
class RiskAssessment:
    level: int = 0
    name: str = "normal"
    reasons: list = field(default_factory=list)
    alarm: bool = False
    events: list = field(default_factory=list)
    activation_sustained: bool = False
    rebound: bool = False
    # Spec 027, pacote 1.
    alarm_kind: str | None = None  # info, distracao, sonolencia ou critico (vision/alarm.py)
    alarm_repeticoes: int = 1
    parar_alarme: bool = False  # o crítico acabou (olho abriu): corta o som
    alarm_suavizado: bool = False  # aviso de celular acima do orçamento por hora: som suave
    risco_sono: int = 0
    risco_distracao: int = 0
    estagio_sonolencia: int = 0
    memoria_sonolencia: bool = False
    sem_visao: bool = False
    mensagem: str | None = None  # texto fixo para o motorista (TEXTOS)
    perclos_quadros_3min: float | None = None
    sono_estimado: dict = field(default_factory=lambda: estimar_sono(0))
    detalhes: dict = field(default_factory=dict)  # vai para os detalhes dos eventos (vision/engine.py)


class RiskFusion:
    def __init__(self, share_activation: bool = False):
        # False: a ativação atípica é usada só no próprio dispositivo e não aparece em nenhum evento enviado.
        self.share_activation = share_activation
        self._level = 0
        self._below_since = None
        self._mild_since = None
        self._episode_start = None
        self._episode_last = None
        self._episode_peak = 0.0
        self._sustained_last = None
        self._sustained_minutes = 0.0
        self._rebound_until = -math.inf
        self._last_event_at = {}
        self._last_alarm_at = -math.inf
        # Spec 027.
        self._last_t = None
        self._sleep_level = 0
        self._sleep_below_since = None
        self._perclos = PerclosQuadros()
        self._sleep_start = None
        self._sleep_last = None
        self._stage = 0
        self._memory = False
        self._last_sleep_sign = None
        self._absent_since = None
        self._absent_source = None
        self._absent_with_memory = False
        self._present_since = None
        self._pause_recent_until = -math.inf
        self._last_suggestion_at = None
        self._phone_warnings = deque()
        self._blind_since = None
        self._sight_back_since = None
        self._blind_warned = False
        self._critical_active = False
        self._calibration_suspect = False

    @property
    def level(self) -> int:
        return self._level

    def update(self, t: float, drowsiness, activation=None, context: dict | None = None, zscores: dict | None = None,
               window: dict | None = None, phone=None, visibility=None, distraction=None) -> RiskAssessment:
        """visibility: vision.visibility.Visibility do quadro (olhos tapados por óculos escuros etc.). Sem ela, o
        "sem visão" usa só o rosto perdido.
        distraction: DistractionAssessment do olhar (vision/distraction.py): nível 0 a 3, `alarm` e `alarm_kind`
        ("distracao" no aviso, "critico" sem resposta depois do aviso). Entra no canal de distração, nunca no de
        sono."""
        result = RiskAssessment()
        context, zscores, window = context or {}, zscores or {}, window or {}
        sounds = []
        dt = self._step(t)
        self._perclos.add(t, getattr(drowsiness, "openness", None), dt)
        if self._track_calibration(drowsiness):
            sounds.append("info")  # calibração concluída: nota suave (§1.3 da pesquisa)
        face = bool(getattr(drowsiness, "face_found", False))

        sleep_target = drowsiness.level
        reasons = list(drowsiness.reasons) if drowsiness.level else []
        touch = getattr(phone, "face_touch", None)
        hand_on_face = touch is not None and touch.face_hidden
        hand_gestures = touch is not None and touch.rubs_10min >= HAND_GESTURES_LIGHT_SIGNAL
        if drowsiness.level == 1:
            self._mild_since = t if self._mild_since is None else self._mild_since
            risky_context = context.get("madrugada") or context.get("limite_direcao_excedido")
            if hand_gestures:
                reasons.append("olhos_esfregados_repetidamente")
            if (risky_context or hand_gestures) and t - self._mild_since >= CONTEXT_ESCALATION_S:
                sleep_target = max(sleep_target, 2)
                reasons.append("sinais_leves_em_contexto_de_risco" if risky_context else "sinais_leves_com_gestos_de_sono")
            elif t < self._pause_recent_until and t - self._mild_since >= RECENT_PAUSE_ESCALATION_S:
                sleep_target = max(sleep_target, 2)
                reasons.append("sinais_leves_logo_apos_pausa")
        else:
            self._mild_since = None

        other_target = 0
        if context.get("limite_direcao_excedido"):
            other_target = 1
            reasons.append("direcao_continua_acima_de_5h30")
            self._emit(t, result, "direcao_continua", 2, (context.get("direcao_continua_h") or 0.0) * 3600.0,
                       dict(context))

        result.activation_sustained = self._track_activation(t, activation)
        if result.activation_sustained:
            other_target = 1
            reasons.append("padrao_ocular_atipico_sustentado")
            if self.share_activation:
                details = dict(activation.to_details(), duracao_min=round((t - self._episode_start) / 60.0, 1),
                               indice_max=round(self._episode_peak, 2))
                self._emit(t, result, "ativacao_atipica", 2, t - self._episode_start, details)

        drowsy_signs = (drowsiness.level >= 1 or (zscores.get("duracao_mediana_ms") or 0.0) >= REBOUND_DURATION_Z
                        or (window.get("fechamentos_longos_5min") or 0) >= 1)
        if drowsy_signs and self._in_rebound_window(t):
            if t >= self._rebound_until:
                details = {key: window[key] for key in REBOUND_WINDOW_KEYS if window.get(key) is not None}
                details["motivos_sonolencia"] = list(drowsiness.reasons)
                if self.share_activation:
                    details["ativacao"] = {"duracao_min": round(self._sustained_minutes, 1),
                                           "indice_max": round(self._episode_peak, 2),
                                           "min_desde_o_ultimo_sinal": round((t - self._sustained_last) / 60.0, 1)}
                if self._emit(t, result, "sonolencia_abrupta", 4, 0.0, details):
                    sounds.append("sonolencia")
            self._rebound_until = t + REBOUND_HOLD_S
        if t < self._rebound_until:
            sleep_target = max(sleep_target, 2)
            reasons.append("sonolencia_logo_apos_periodo_de_ativacao")
            result.rebound = True

        # Memória de sonolência (ALM-07) e pausa (CTX-01).
        raw_sleep = sleep_target
        if raw_sleep >= 1:
            self._last_sleep_sign = t
        self._track_absence(t, face, hand_on_face, context, result)
        if self._memory and self._last_sleep_sign is not None and t - self._last_sleep_sign >= MEMORY_QUIET_S:
            self._release_memory("30 min sem sinais de sono")
        if raw_sleep >= 2:
            self._memory = True
        held_by_memory = self._memory and raw_sleep < 1
        if self._memory:
            sleep_target = max(sleep_target, 1)
            if held_by_memory:
                reasons.append("sonolencia_recente_sem_pausa")

        # Escalonamento (ALM-06).
        stage_before = self._stage
        stage = self._track_stage(t, raw_sleep, face)
        if stage > stage_before:
            sounds.append("sonolencia")
            sleep_reasons = [reason for reason in reasons if reason not in ("direcao_continua_acima_de_5h30",
                                                                            "padrao_ocular_atipico_sustentado")]
            if self._emit(t, result, "pausa_sugerida", 2, 0.0,
                          {"estagio": stage, "mensagem": TEXTOS[f"sonolencia_{stage}"], "motivos": sleep_reasons},
                          key=f"pausa_sugerida:{stage}"):
                self._last_suggestion_at = t

        phone_level = phone.risk_level if phone is not None else 0
        if phone is not None and phone.risk_level:
            reasons.extend(phone.reasons)
        gaze_level = int(getattr(distraction, "level", 0) or 0)
        # RSK-02: o nível 1 do olhar ("atenção visual", ex.: olhada de 3 s ao espelho) é comum e fica só no canal de
        # distração, para a tela; do nível 2 (distração com aviso) em diante entra nos motivos e no risco geral.
        if gaze_level >= 2:
            reasons.extend(getattr(distraction, "reasons", None) or [])
        distraction_level = max(phone_level, gaze_level)

        target = max(sleep_target, other_target, phone_level, gaze_level if gaze_level >= 2 else 0)
        previous = self._level
        level = self._hysteresis(t, target)
        if level > target:
            reasons.append("reducao_gradual_do_risco")
        result.level, result.name, result.reasons = level, LEVEL_NAMES[level], reasons
        self._sleep_level, self._sleep_below_since = self._step_down(t, sleep_target, self._sleep_level,
                                                                     self._sleep_below_since)
        result.risco_sono, result.risco_distracao = self._sleep_level, distraction_level
        result.estagio_sonolencia, result.memoria_sonolencia = stage, self._memory

        # Sons pedidos neste quadro.
        if drowsiness.alarm:
            sounds.append("critico" if drowsiness.level >= 3 else "sonolencia")
        warning = "celular" if phone is not None and phone.alarm else None
        if distraction is not None and getattr(distraction, "alarm", False):
            if getattr(distraction, "alarm_kind", None) == "critico":
                sounds.append("critico")  # sem resposta depois do aviso (Euro NCAP §1.3.5): olhar, nunca celular
            else:
                warning = warning or "olhar"
        if level >= 2 and previous < 2 and t - self._last_alarm_at >= ALARM_COOLDOWN_S:
            if self._sleep_level < 2 and distraction_level >= 2:
                warning = warning or ("celular" if phone_level >= 2 else "olhar")
            else:
                sounds.append("sonolencia")
        if warning:
            sounds.append(self._distraction_sound(t, result, warning))
        result.sem_visao = self._track_blindness(t, face, hand_on_face, drowsiness, visibility, context, sounds)
        if context.get("descanso_previsto_excedido") and self._emit(
                t, result, "descanso_previsto_em_atraso", 2, (context.get("direcao_continua_h") or 0.0) * 3600.0,
                {"tipo_veiculo": context.get("tipo_veiculo"), "descanso_previsto_h": context.get("descanso_previsto_h"),
                 "mensagem": TEXTOS["descanso"]}):
            sounds.append("info")

        kind = max(sounds, key=SOUND_PRIORITY.__getitem__) if sounds else None
        result.alarm_kind = kind
        result.alarm = kind in ALARM_SOUNDS
        result.alarm_repeticoes = 2 if kind == "sonolencia" and stage >= 2 else 1
        if result.alarm:
            self._last_alarm_at = t
        critical = drowsiness.level >= 3 or gaze_level >= 3
        result.parar_alarme = self._critical_active and not critical
        self._critical_active = critical
        result.mensagem = self._message(drowsiness, stage, phone_level, gaze_level, result.sem_visao, held_by_memory,
                                        context)

        frames = self._perclos.value(t)
        result.perclos_quadros_3min = round(frames, 3) if frames is not None else None
        result.sono_estimado = estimar_sono(self._sleep_level, getattr(drowsiness, "fps", None), window,
                                            self._calibration_suspect, held_by_memory)
        details = {"perclos_quadros_3min": result.perclos_quadros_3min, "perclos_3min": window.get("perclos_3min"),
                   "risco_sono": result.risco_sono, "risco_distracao": result.risco_distracao}
        result.detalhes = {key: value for key, value in details.items() if value is not None}
        result.detalhes["sono_estimado"] = result.sono_estimado
        for event in result.events:
            for key, value in result.detalhes.items():
                event.details.setdefault(key, value)
        return result

    # ------------------------------------------------------------------------------------------------------------
    def _step(self, t: float) -> float:
        dt = 0.0
        if self._last_t is not None and 0 < t - self._last_t <= MAX_FRAME_GAP_S:
            dt = t - self._last_t
        self._last_t = t
        return dt

    def _track_calibration(self, drowsiness) -> bool:
        """Lembra se a calibração saiu suspeita (baixa a confiança do sono_estimado). True quando acabou de concluir."""
        concluded = False
        for event in getattr(drowsiness, "events", None) or ():
            if event.alert_type == "calibracao_suspeita":
                self._calibration_suspect = True
            elif event.alert_type == "calibracao_concluida":
                self._calibration_suspect = False
                concluded = True
        return concluded

    def _track_activation(self, t: float, activation) -> bool:
        if activation is not None and activation.compatible:
            if self._episode_start is None or t - self._episode_last > REBOUND_GAP_S:
                self._episode_start, self._episode_peak = t, 0.0
            self._episode_last = t
            self._episode_peak = max(self._episode_peak, activation.index or 0.0)
        active = self._episode_start is not None and t - self._episode_last <= REBOUND_GAP_S
        sustained = active and self._episode_last - self._episode_start >= REBOUND_MIN_ACTIVATION_S
        if sustained:
            self._sustained_last = self._episode_last
            self._sustained_minutes = (self._episode_last - self._episode_start) / 60.0
        return sustained

    def _in_rebound_window(self, t: float) -> bool:
        return self._sustained_last is not None and t - self._sustained_last <= REBOUND_WINDOW_S

    def _track_stage(self, t: float, raw_sleep: int, face: bool) -> int:
        """1º estágio ao começar um episódio de nível ≥ 2 por sono; 2º depois de 5 min dele, com o motorista no
        banco (rosto na câmera)."""
        if raw_sleep >= 2:
            if self._sleep_start is None or t - self._sleep_last > SLEEP_EPISODE_GAP_S:
                self._sleep_start, self._stage = t, 1
            self._sleep_last = t
            if self._stage < 2 and face and t - self._sleep_start >= SLEEP_STAGE2_S:
                self._stage = 2
        elif self._sleep_start is not None and t - self._sleep_last > SLEEP_EPISODE_GAP_S:
            self._sleep_start = self._sleep_last = None
            self._stage = 0
        return self._stage

    def _track_absence(self, t: float, face: bool, hand_on_face: bool, context: dict, result: RiskAssessment) -> None:
        """Pausa = rosto ausente (sem mão na frente) ou telemetria parada. Com 15 min, encerra a memória de sonolência;
        quando o motorista volta (2 s seguidos), vira `pausa_detectada` com a duração."""
        speed = context.get("velocidade_kmh")
        stopped = speed is not None and speed < STOPPED_KMH
        if stopped or not (face or hand_on_face):
            self._present_since = None
            if self._absent_since is None:
                self._absent_since = t
                self._absent_source = "telemetria" if stopped else "rosto_ausente"
                self._absent_with_memory = self._memory
            elif self._memory and t - self._absent_since >= MEMORY_PAUSE_S:
                self._release_memory("pausa de 15 min")
            return
        if self._absent_since is None:
            return
        if self._present_since is None:
            self._present_since = t
        if t - self._present_since < PRESENCE_CONFIRM_S:
            return
        duration = self._present_since - self._absent_since
        if duration >= MEMORY_PAUSE_S:
            suggested = self._last_suggestion_at is not None and self._last_suggestion_at <= self._absent_since
            details = {"duracao_s": round(duration), "fonte": self._absent_source, "apos_sugestao": suggested,
                       "min_desde_sugestao": round((self._absent_since - self._last_suggestion_at) / 60.0, 1)
                       if suggested else None}
            self._emit(t, result, "pausa_detectada", 1, duration, details)
            if suggested or self._absent_with_memory:
                self._pause_recent_until = t + RECENT_PAUSE_WINDOW_S
            self._last_suggestion_at = None
        self._absent_since = self._present_since = None

    def _release_memory(self, why: str) -> None:
        self._memory = False
        logger.info("Memória de sonolência encerrada: %s.", why)

    def _distraction_sound(self, t: float, result: RiskAssessment, origin: str) -> str:
        """ALM-08: até 5 avisos de distração (celular ou olhar) por hora com o som de distração; do 6º em diante, som
        suave e uma linha no registro. O crítico nunca passa por aqui."""
        while self._phone_warnings and t - self._phone_warnings[0] >= PHONE_BUDGET_WINDOW_S:
            self._phone_warnings.popleft()
        self._phone_warnings.append(t)
        count = len(self._phone_warnings)
        if count <= PHONE_BUDGET_PER_HOUR:
            return "distracao"
        result.alarm_suavizado = True
        if self._emit(t, result, "avisos_de_distracao_suavizados", 1, 0.0,
                      {"avisos_na_ultima_hora": count, "limite_por_hora": PHONE_BUDGET_PER_HOUR, "som": "info",
                       "origem": origin}):
            logger.info("Avisos de distração: %d na última hora; daqui em diante, som suave.", count)
        return "info"

    def _track_blindness(self, t, face, hand_on_face, drowsiness, visibility, context, sounds) -> bool:
        """DMS-04: 10 s sem ver os olhos (rosto perdido, óculos escuros, rosto longe demais) → texto fixo; o som info
        só no primeiro episódio da viagem, e nunca com o veículo parado ou logo depois de sugerir pausa."""
        if not face:
            blind = not hand_on_face
        else:
            blind = (visibility is not None and not visibility.eyes_ok) or \
                getattr(drowsiness, "frame_source", "") == "rosto_pequeno"
        if blind:
            self._sight_back_since = None
            if self._blind_since is None:
                self._blind_since = t
        elif self._blind_since is not None:
            if self._sight_back_since is None:
                self._sight_back_since = t
            if t - self._sight_back_since >= NO_VISION_CLEAR_S:
                self._blind_since = self._sight_back_since = None
        active = blind and self._blind_since is not None and t - self._blind_since >= NO_VISION_WARN_S
        if active and not self._blind_warned:
            speed = context.get("velocidade_kmh")
            parked = speed is not None and speed < STOPPED_KMH
            # Rosto some logo depois de sugerir pausa: provavelmente saiu para descansar. Óculos escuros não.
            left_to_rest = not face and self._last_suggestion_at is not None and \
                t - self._last_suggestion_at < SUGGESTION_RECENT_S
            if not parked and not left_to_rest:
                self._blind_warned = True
                sounds.append("info")
        return active

    @staticmethod
    def _message(drowsiness, stage, phone_level, gaze_level, blind, held_by_memory, context) -> str | None:
        if drowsiness.level >= 3:
            return TEXTOS["critico"]
        if gaze_level >= 3:
            return TEXTOS["sem_resposta"]
        if blind:  # sem ver os olhos o sistema não detecta sono: isso vem antes da frase de pausa (DDAW §3.5.3)
            return TEXTOS["sem_visao"]
        if stage >= 2:
            return TEXTOS["sonolencia_2"]
        if stage == 1:
            return TEXTOS["sonolencia_1"]
        if phone_level >= 2:
            return TEXTOS["distracao"]
        if gaze_level >= 2:
            return TEXTOS["olhar"]
        if held_by_memory:
            return TEXTOS["memoria"]
        if context.get("descanso_previsto_excedido"):
            return TEXTOS["descanso"]
        return None

    def _hysteresis(self, t: float, target: int) -> int:
        self._level, self._below_since = self._step_down(t, target, self._level, self._below_since)
        return self._level

    @staticmethod
    def _step_down(t: float, target: int, level: int, below_since):
        """Sobe na hora; desce um nível por vez depois de HOLD_DOWN_S abaixo do nível atual."""
        if target >= level:
            return target, None
        if below_since is None:
            return level, t
        if t - below_since >= HOLD_DOWN_S[level]:
            level -= 1
            return level, (t if target < level else None)
        return level, below_since

    def _emit(self, t, result, alert_type, risk_level, duration, details, key: str | None = None) -> bool:
        key = key or alert_type
        last = self._last_event_at.get(key)
        if last is not None and t - last < COOLDOWN_S.get(alert_type, 0.0):
            return False
        self._last_event_at[key] = t
        result.events.append(DetectedEvent(alert_type, risk_level, round(duration, 2), details))
        return True
