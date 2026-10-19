"""Distração visual pelo olhar e pela cabeça, sem resposta depois do aviso e postura (spec 027: DMS-01, DMS-13 porta,
DMS-17 e DMS-18). Só números: nenhuma imagem sai daqui.

Fontes:
- Euro NCAP 2026, Safe Driving · Driver Engagement Protocol v1.2 (jul/2026), e SD-202 v1.2:
  - distração longa (LGA, §1.2.1): UM olhar fora da via de 3 a 4 s (valor do fabricante; aqui 3,0 s), com cabeça
    (*owl*), só olhos (*lizard*) ou corpo; tolerância do teste 0,2 s (SD-202 4.1.1.1);
  - distração curta repetida (VATS, §1.2.2): olhares fora que somam 10 s em 30 s; zera quando a atenção volta à via
    "tempo suficiente" (T_VATS_reset do fabricante; 2 s segundo resumo da Seeing Machines, fonte secundária);
  - sem resposta (§1.3.5): o olhar não volta à via 3 s depois do aviso de distração (DMS-17);
  - aviso a partir de 20 km/h (§1.1): sem velocidade (PRD §5, sem GPS) o módulo roda em modo "sem velocidade" e diz
    isso nos detalhes do evento; com telemetria (vision/context.py), abaixo de 20 km/h só registra (DMS-13).
- AttenD (Kircher & Ahlström, 2010): balde de atenção de 2 s que esvazia fora do campo da direção e enche na via
  depois de 0,1 s; espelhos e painel têm 1 s de tolerância antes de começar a esvaziar. Balde vazio = nível
  "atenção visual" (sem alarme).
- Klauer et al., 2006 (100-Car) e NHTSA 2013: olhar fora da via por mais de 2 s dobra o risco → nível 1.
- ADDW (Reg. UE 2023/2590, texto oficial não lido; fontes secundárias): Área 3 = abaixo de 30° do ponto ocular;
  +1,5 s em situação "não nominal" (sem íris: óculos escuros) → aqui o modo "cabeca" ganha 1,5 s no limiar.
- Seeing Machines (estudo naturalístico, secundária): não separar espelho de distração quase triplica os alertas →
  espelho e painel são zonas "ligadas à direção" e só avisam depois de 6 s (hipótese).
- Victor et al., 2005 (PRC) e Shiferaw et al., 2018: vision/gaze.py (frente pela moda e PRC no registro).
- Postura (DMS-18): a translação da matriz facial do MediaPipe (cm na câmera virtual) mostra o corpo inclinado ou o
  motorista fora da posição (Euro NCAP §1.2.1 cita a inclinação do corpo). Limiares de 15 cm e 2 s são hipótese.

Zonas padrão (Brasil, volante à esquerda; graus relativos à frente; + yaw = esquerda do motorista, + pitch = para
baixo): todas são hipótese da pesquisa (§2.2 d) e podem ser ajustadas pela calibração guiada. Histerese de 3° na
borda e transição confirmada em 2 quadros; o tempo do olhar conta desde o primeiro quadro da transição (ISO 15007).
"""
from __future__ import annotations

import math
import statistics
from collections import deque
from dataclasses import dataclass, field

from vision.drowsiness import DetectedEvent
from vision.gaze import GazeTracker

INF = math.inf
LGA_S = 3.0
DEGRADED_EXTRA_S = 1.5
DRIVING_ZONE_WARN_S = 6.0
VATS_WINDOW_S = 30.0
VATS_LIMIT_S = 10.0
VATS_RESET_S = 2.0
ATTEND_BUFFER_S = 2.0
ATTEND_ROAD_LATENCY_S = 0.1
ATTEND_DRIVING_LATENCY_S = 1.0
ATTENTION_GLANCE_S = 2.0
UNRESPONSIVE_AFTER_WARNING_S = 3.0
CONFIRM_FRAMES = 2
HYSTERESIS_DEG = 3.0
UNDEFINED_GRACE_S = 0.5  # piscada no meio do olhar não corta o olhar
MIN_SPEED_WARN_KMH = 20.0
MAX_STEP_S = 0.5
GLANCE_LOG = 50
COLO_MIN_PITCH_DEG = 20.0  # a calibração guiada pode baixar o limite do colo até aqui, nunca subir de 30°

POSTURE_SAMPLE_S = 0.5
POSTURE_WINDOW_S = 120.0
POSTURE_MIN_SAMPLES = 20
POSTURE_LIMIT_CM = 15.0
POSTURE_DISTANCE_LIMIT_CM = 25.0
POSTURE_CLEAR_CM = 10.0
POSTURE_HOLD_S = 2.0


@dataclass(frozen=True)
class Zone:
    name: str
    kind: str  # via, direcao (ligada à direção) ou nao_ligada
    yaw: tuple
    pitch: tuple

    def contains(self, dyaw: float, dpitch: float, margin: float = 0.0) -> bool:
        return (self.yaw[0] - margin <= dyaw <= self.yaw[1] + margin
                and self.pitch[0] - margin <= dpitch <= self.pitch[1] + margin)


DEFAULT_ZONES = (
    Zone("via", "via", (-25.0, 25.0), (-10.0, 12.0)),
    Zone("espelho_motorista", "direcao", (35.0, 70.0), (-15.0, 15.0)),
    Zone("retrovisor", "direcao", (-35.0, -15.0), (-20.0, -5.0)),
    Zone("espelho_passageiro", "direcao", (-80.0, -50.0), (-15.0, 15.0)),
    Zone("painel", "direcao", (-12.0, 12.0), (12.0, 30.0)),
    Zone("multimidia", "nao_ligada", (-50.0, -20.0), (15.0, 35.0)),
    Zone("colo", "nao_ligada", (-INF, INF), (30.0, INF)),  # Área 3 do ADDW
)
OUTSIDE = Zone("fora", "nao_ligada", (-INF, INF), (-INF, INF))  # janela, passageiro, banco de trás


def classify(dyaw: float, dpitch: float, zones, current: Zone | None = None, hysteresis: float = HYSTERESIS_DEG) -> Zone:
    """Zona do olhar. Fica na zona atual enquanto estiver a até `hysteresis` graus dela (evita pisca-pisca na borda).
    Para sair de "fora", precisa entrar `hysteresis` graus numa zona."""
    if current is not None and current is not OUTSIDE and current.contains(dyaw, dpitch, hysteresis):
        return current
    margin = -hysteresis if current is OUTSIDE else 0.0
    return next((zone for zone in zones if zone.contains(dyaw, dpitch, margin)), OUTSIDE)


def apply_guided_zones(zones, measured: dict):
    """Recentra cada zona medida na calibração guiada, mantendo o tamanho. "via" recentra a frente (vision/gaze.py);
    o colo só pode baixar o limite (de 30° até 20°)."""
    result = []
    for zone in zones:
        point = measured.get(zone.name)
        if point is None or zone.name == "via":
            result.append(zone)
        elif zone.name == "colo":
            limit = max(COLO_MIN_PITCH_DEG, min(zone.pitch[0], point[1] - 8.0))
            result.append(Zone(zone.name, zone.kind, zone.yaw, (limit, zone.pitch[1])))
        else:
            half_yaw = (zone.yaw[1] - zone.yaw[0]) / 2.0
            half_pitch = (zone.pitch[1] - zone.pitch[0]) / 2.0
            result.append(Zone(zone.name, zone.kind, (point[0] - half_yaw, point[0] + half_yaw),
                               (point[1] - half_pitch, point[1] + half_pitch)))
    return tuple(result)


@dataclass
class DistractionAssessment:
    """Canal de distração para a tela, o registro e a fusão (vision/risk.py). Nível: 0 nada, 1 atenção visual
    (balde vazio ou olhar fora > 2 s), 2 distração com aviso, 3 sem resposta depois do aviso."""

    state: str = "aprendendo_frente"  # aprendendo_frente, atento, atencao_visual, distraido, sem_resposta, sem_rosto
    level: int = 0
    zone: str | None = None
    zone_kind: str | None = None  # via, direcao, nao_ligada
    mode: str | None = None  # olhar (cabeça + olho), cabeca (sem íris), olhar_para_baixo, olhos_fechados, sem_rosto
    delta_yaw: float | None = None
    delta_pitch: float | None = None
    glance_s: float = 0.0  # olhar contínuo fora da via em zona não ligada à direção
    driving_glance_s: float = 0.0  # olhar contínuo em espelho ou painel
    vats_s: float = 0.0  # soma dos olhares fora nos últimos 30 s
    attention_buffer_s: float = ATTEND_BUFFER_S  # balde AttenD
    alarm: bool = False
    alarm_kind: str | None = None  # "distracao" (aviso curto) ou "critico" (sem resposta)
    warnings_enabled: bool = True  # False abaixo de 20 km/h (com telemetria)
    speed_source: str = "nenhuma"  # nenhuma ou telemetria
    posture: str | None = None  # "fora_da_posicao" enquanto durar
    posture_offset_cm: float | None = None
    reasons: list = field(default_factory=list)
    events: list = field(default_factory=list)

    def to_details(self) -> dict:
        return {"estado": self.state, "nivel": self.level, "zona": self.zone, "tipo_zona": self.zone_kind,
                "modo": self.mode, "olhar_fora_s": round(self.glance_s, 2), "soma_30s_s": round(self.vats_s, 2),
                "balde_atencao_s": round(self.attention_buffer_s, 2)}


class PostureTracker:
    """DMS-18: cabeça longe da posição habitual (mediana dos últimos 2 min) por 2 s."""

    def __init__(self):
        self._samples = deque()
        self._next_sample = -math.inf
        self._reference = None  # (x, y, z) medianos, recalculados só quando entra amostra (2 Hz)
        self._out_since = None
        self._emitted = False

    def update(self, t: float, metrics):
        """(deslocamento em cm ou None, evento ou None)."""
        x, y, z = (getattr(metrics, name, None) for name in ("head_x_cm", "head_y_cm", "head_z_cm"))
        if not metrics.face_found or x is None or y is None:
            self._out_since = None
            return None, None
        if t >= self._next_sample:
            self._next_sample = t + POSTURE_SAMPLE_S
            self._samples.append((t, x, y, z))
            while self._samples and self._samples[0][0] < t - POSTURE_WINDOW_S:
                self._samples.popleft()
            if len(self._samples) >= POSTURE_MIN_SAMPLES:
                zs = [s[3] for s in self._samples if s[3] is not None]
                self._reference = (statistics.median(s[1] for s in self._samples),
                                   statistics.median(s[2] for s in self._samples),
                                   statistics.median(zs) if zs else None)
        if self._reference is None or len(self._samples) < POSTURE_MIN_SAMPLES:
            return None, None
        rx, ry, rz = self._reference
        dx, dy = x - rx, y - ry
        dz = z - rz if z is not None and rz is not None else 0.0
        offset = math.hypot(dx, dy)
        if offset >= POSTURE_LIMIT_CM or abs(dz) >= POSTURE_DISTANCE_LIMIT_CM:
            if self._out_since is None:
                self._out_since = t
            if not self._emitted and t - self._out_since >= POSTURE_HOLD_S - 1e-9:
                self._emitted = True
                return offset, DetectedEvent("fora_da_posicao", 1, round(t - self._out_since, 2), {
                    "deslocamento_cm": round(offset, 1), "lateral_cm": round(dx, 1), "vertical_cm": round(dy, 1),
                    "distancia_cm": round(dz, 1), "fonte": "matriz_facial_mediapipe"})
        elif offset < POSTURE_CLEAR_CM and abs(dz) < POSTURE_CLEAR_CM:
            self._out_since = None
            self._emitted = False
        return offset, None

    @property
    def out(self) -> bool:
        return self._emitted


class DistractionMonitor:
    def __init__(self, profile=None, zones=None):
        self.gaze = GazeTracker()
        self.zones = tuple(zones) if zones is not None else DEFAULT_ZONES
        self.posture = PostureTracker()
        # Últimos olhares fora da via (zona, duração, se avisou): "olhar registrado" mesmo sem aviso.
        self.glances = deque(maxlen=GLANCE_LOG)
        self._last_t = None
        self._zone: Zone | None = None
        self._pending = None  # (zona candidata, instante do 1º quadro, quadros, tempo guardado)
        self._undefined_s = 0.0
        self._road_s = 0.0
        self._offroad_s = 0.0
        self._offroad_start = None
        self._offroad_zone = None
        self._offroad_degraded = False
        self._offroad_warned = False
        self._driving_s = 0.0
        self._driving_start = None
        self._driving_zone = None
        self._driving_warned = False
        self._buffer = ATTEND_BUFFER_S
        self._vats = deque()  # (fim, duração) dos olhares fora já terminados
        self._vats_from = 0.0  # parte do olhar atual que já entrou num aviso de VATS
        self._await_since = None
        self._await_event = None
        self._unresponsive = False
        self._unresponsive_emitted = False
        self._quiet_glances = 0
        if profile is not None:
            self.set_profile(profile)

    def set_profile(self, profile) -> None:
        self.gaze.set_profile(profile)
        zones = getattr(profile, "gaze_zones", None)
        if zones:
            self.zones = apply_guided_zones(DEFAULT_ZONES, zones)

    # Calibração guiada (opcional): a tela pede cada alvo por ~3 s e chama guided_target com o nome da zona.
    def start_guided_calibration(self) -> None:
        self.gaze.start_guided_calibration()

    def guided_target(self, name: str | None) -> None:
        self.gaze.guided_target(name)

    def finish_guided_calibration(self, profile=None) -> dict:
        """Aplica e devolve {zona: [Δyaw, Δpitch]}. Com `profile`, grava em profile.gaze_zones (quem chama salva)."""
        measured = self.gaze.finish_guided_calibration()
        self.zones = apply_guided_zones(self.zones, measured)
        if profile is not None:
            profile.gaze_zones = dict(measured)
            if self.gaze.center is not None:
                profile.gaze_center_yaw, profile.gaze_center_pitch = (round(v, 1) for v in self.gaze.center)
        return measured

    def window_metrics(self, t: float) -> dict:
        metrics = self.gaze.window_metrics(t)
        metrics["olhares_longos_sem_aviso"] = self._quiet_glances
        return metrics

    def update(self, metrics, openness: float | None = None, source: str = "",
               speed_kmh: float | None = None) -> DistractionAssessment:
        t = metrics.timestamp
        dt = t - self._last_t if self._last_t is not None and 0 < t - self._last_t <= MAX_STEP_S else 0.0
        self._last_t = t
        reading = self.gaze.update(metrics, openness, source, speed_kmh)
        result = DistractionAssessment(mode=reading.mode, delta_yaw=reading.delta_yaw, delta_pitch=reading.delta_pitch,
                                       warnings_enabled=speed_kmh is None or speed_kmh >= MIN_SPEED_WARN_KMH,
                                       speed_source="nenhuma" if speed_kmh is None else "telemetria")
        offset, posture_event = self.posture.update(t, metrics)
        result.posture_offset_cm = None if offset is None else round(offset, 1)
        result.posture = "fora_da_posicao" if self.posture.out else None
        if posture_event is not None:
            result.events.append(posture_event)

        if not reading.ready:
            result.state = "sem_rosto" if reading.mode == "sem_rosto" else "aprendendo_frente"
            return result

        if self.gaze.guided_active:
            result.warnings_enabled = False  # calibração guiada: a tela está pedindo para olhar os espelhos
        counted = self._place(t, dt, reading)
        if self._offroad_start is not None and reading.mode == "cabeca":
            self._offroad_degraded = True  # sem íris neste olhar: limiar +1,5 s (ADDW "não nominal")
        if self._zone is not None:
            self._advance(counted)
            self._check_warnings(t, reading, speed_kmh, result)
            self._check_unresponsive(t, result)
        self._fill(t, result)
        return result

    # --- zona e tempo -------------------------------------------------------------------------------------------
    def _candidate(self, reading) -> Zone | None:
        if reading.mode == "olhar_para_baixo":
            return next((zone for zone in self.zones if zone.name == "colo"), OUTSIDE)
        if reading.mode in ("olhar", "cabeca") and reading.delta_yaw is not None:
            return classify(reading.delta_yaw, reading.delta_pitch, self.zones, self._zone)
        return None  # olhos fechados ou sem rosto: olhar indefinido

    def _place(self, t: float, dt: float, reading) -> float:
        """Atualiza a zona e devolve o tempo deste quadro que conta para a zona atual."""
        candidate = self._candidate(reading)
        if candidate is None:
            self._undefined_s += dt
            self._pending = None
            if self._zone is None:
                return 0.0
            # Rosto perdido no meio de um olhar fora (virou para trás): o olhar continua. Olho fechado ou piscada:
            # o olhar continua só durante uma piscada; depois, o tempo para (a sonolência cuida do olho fechado).
            keep = ((reading.mode == "sem_rosto" and self._zone.kind == "nao_ligada")
                    or self._undefined_s <= UNDEFINED_GRACE_S)
            return dt if keep else 0.0
        self._undefined_s = 0.0
        if self._zone is None:
            self._switch(candidate, t, t)
            return 0.0
        if candidate.name == self._zone.name:
            held = self._pending[3] if self._pending is not None else 0.0
            self._pending = None
            return dt + held
        if self._pending is None or self._pending[0].name != candidate.name:
            self._pending = (candidate, t, 1, 0.0)
            return dt  # o tempo até este quadro ainda era da zona anterior
        zone, start, frames, held = self._pending
        self._pending = (zone, start, frames + 1, held + dt)
        if frames + 1 >= CONFIRM_FRAMES:
            self._pending = None
            self._switch(zone, start, t)
        return 0.0

    def _switch(self, zone: Zone, start: float, t: float) -> None:
        elapsed = max(0.0, t - start)
        previous = self._zone
        if zone.kind != "nao_ligada":
            self._end_offroad(start)
        if zone.kind != "direcao" or (previous is not None and previous.kind != "direcao"):
            self._end_driving(start)
        self._zone = zone
        if zone.kind == "via":
            self._road_s = elapsed
        else:
            self._road_s = 0.0
        if zone.kind == "nao_ligada":
            if self._offroad_start is None:
                self._offroad_start, self._offroad_s = start, elapsed
                self._offroad_warned = False
            else:
                self._offroad_s += elapsed  # de uma zona não ligada para outra: o mesmo olhar continua
            self._buffer = max(0.0, self._buffer - elapsed)
            self._offroad_zone = zone.name
        elif zone.kind == "direcao":
            if self._driving_start is None:
                self._driving_start, self._driving_s, self._driving_zone = start, elapsed, zone.name
                self._driving_warned = False
            else:
                self._driving_s += elapsed

    def _end_offroad(self, end: float) -> None:
        if self._offroad_start is None:
            return
        duration = self._offroad_s
        self._vats.append((end, max(0.0, duration - self._vats_from)))
        self.glances.append({"zona": self._offroad_zone, "tipo_zona": "nao_ligada", "inicio_s": round(self._offroad_start, 2),
                             "duracao_s": round(duration, 2), "aviso": self._offroad_warned})
        self._offroad_start, self._offroad_s, self._vats_from = None, 0.0, 0.0
        self._offroad_degraded = False

    def _end_driving(self, end: float) -> None:
        if self._driving_start is None:
            return
        self.glances.append({"zona": self._driving_zone, "tipo_zona": "direcao", "inicio_s": round(self._driving_start, 2),
                             "duracao_s": round(self._driving_s, 2), "aviso": self._driving_warned})
        self._driving_start, self._driving_s = None, 0.0

    def _advance(self, dt: float) -> None:
        if dt <= 0:
            return
        kind = self._zone.kind
        if kind == "via":
            self._road_s += dt
            if self._road_s >= ATTEND_ROAD_LATENCY_S:
                self._buffer = min(ATTEND_BUFFER_S, self._buffer + dt)
            if self._road_s >= VATS_RESET_S:
                self._vats.clear()
        elif kind == "direcao":
            self._driving_s += dt
            if self._driving_s > ATTEND_DRIVING_LATENCY_S:
                self._buffer = max(0.0, self._buffer - dt)
        else:
            self._offroad_s += dt
            self._buffer = max(0.0, self._buffer - dt)

    def _vats_sum(self, t: float) -> float:
        horizon = t - VATS_WINDOW_S
        while self._vats and self._vats[0][0] < horizon:
            self._vats.popleft()
        total = 0.0
        for end, duration in self._vats:
            total += max(0.0, min(duration, end - horizon))
        if self._offroad_start is not None:
            total += max(0.0, min(self._offroad_s - self._vats_from, VATS_WINDOW_S))
        return total

    # --- avisos -------------------------------------------------------------------------------------------------
    def _speed_details(self, speed_kmh) -> dict:
        details = {"fonte_velocidade": "nenhuma" if speed_kmh is None else "telemetria",
                   "modo_velocidade": "sem_velocidade" if speed_kmh is None else "com_velocidade"}
        if speed_kmh is not None:
            details["velocidade_kmh"] = round(speed_kmh, 1)
        return details

    def _details(self, t, reading, zone_name, kind, duration, threshold, speed_kmh) -> dict:
        details = {
            "zona": zone_name, "tipo_zona": kind, "duracao_s": round(duration, 2), "limiar_s": threshold,
            "modo": "cabeca" if self._offroad_degraded and kind == "nao_ligada" else reading.mode,
            "delta_yaw_graus": None if reading.delta_yaw is None else round(reading.delta_yaw, 1),
            "delta_pitch_graus": None if reading.delta_pitch is None else round(reading.delta_pitch, 1),
            "area3": zone_name == "colo" or (reading.delta_pitch is not None and reading.delta_pitch >= 30.0),
            "prc_60s": self.gaze.window_metrics(t)["prc_60s"], "aviso": True,
        }
        details.update(self._speed_details(speed_kmh))
        return details

    def _warn(self, t, result, event: DetectedEvent, enabled: bool) -> bool:
        if not enabled:
            self._quiet_glances += 1
            return False
        result.events.append(event)
        result.alarm = True
        result.alarm_kind = result.alarm_kind or "distracao"
        if self._await_since is None:
            self._await_since, self._await_event = t, event.alert_type
        return True

    def _check_warnings(self, t, reading, speed_kmh, result) -> None:
        enabled = result.warnings_enabled
        if self._offroad_start is not None and not self._offroad_warned:
            threshold = LGA_S + (DEGRADED_EXTRA_S if self._offroad_degraded else 0.0)
            if self._offroad_s >= threshold - 1e-9:
                self._offroad_warned = True
                details = self._details(t, reading, self._offroad_zone, "nao_ligada", self._offroad_s, threshold,
                                        speed_kmh)
                self._warn(t, result, DetectedEvent("distracao_longa", 2, round(self._offroad_s, 2), details), enabled)
        if self._driving_start is not None and not self._driving_warned and self._driving_s >= DRIVING_ZONE_WARN_S:
            self._driving_warned = True
            details = self._details(t, reading, self._driving_zone, "direcao", self._driving_s, DRIVING_ZONE_WARN_S,
                                    speed_kmh)
            self._warn(t, result, DetectedEvent("distracao_longa", 2, round(self._driving_s, 2), details), enabled)
        total = self._vats_sum(t)
        if total >= VATS_LIMIT_S - 1e-9:
            details = self._details(t, reading, self._offroad_zone or (self._zone.name if self._zone else None),
                                    "nao_ligada", total, VATS_LIMIT_S, speed_kmh)
            details.update(soma_30s_s=round(total, 2), janela_s=VATS_WINDOW_S,
                           olhares=len(self._vats) + (1 if self._offroad_start is not None else 0))
            self._vats.clear()
            self._vats_from = self._offroad_s if self._offroad_start is not None else 0.0
            self._warn(t, result, DetectedEvent("distracao_repetida", 2, round(total, 2), details), enabled)

    def _check_unresponsive(self, t, result) -> None:
        if self._zone is not None and self._zone.kind == "via":
            self._await_since = self._await_event = None
            self._unresponsive = self._unresponsive_emitted = False
            return
        if self._await_since is None or t - self._await_since < UNRESPONSIVE_AFTER_WARNING_S - 1e-9:
            return
        self._unresponsive = True
        if not self._unresponsive_emitted:
            self._unresponsive_emitted = True
            result.events.append(DetectedEvent("nao_responsivo", 5, round(t - self._await_since, 2), {
                "origem": "distracao", "aviso_anterior": self._await_event,
                "segundos_sem_voltar": round(t - self._await_since, 2),
                "zona": self._zone.name if self._zone else None}))
        result.alarm = True
        result.alarm_kind = "critico"

    def _fill(self, t: float, result: DistractionAssessment) -> None:
        zone = self._zone
        result.zone = zone.name if zone else None
        result.zone_kind = zone.kind if zone else None
        result.glance_s = self._offroad_s if self._offroad_start is not None else 0.0
        result.driving_glance_s = self._driving_s if self._driving_start is not None else 0.0
        result.vats_s = self._vats_sum(t)
        result.attention_buffer_s = self._buffer
        if self._unresponsive:
            result.level, result.state = 3, "sem_resposta"
            result.reasons = ["sem_resposta_apos_aviso_de_distracao"]
        elif self._await_since is not None:
            result.level, result.state = 2, "distraido"
            result.reasons = ["olhar_fora_da_via"]
        elif self._buffer <= 0.0 or result.glance_s >= ATTENTION_GLANCE_S:
            result.level, result.state = 1, "atencao_visual"
            result.reasons = ["atencao_visual"]
        else:
            result.level, result.state = 0, "atento"
