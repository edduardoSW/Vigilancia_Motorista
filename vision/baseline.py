"""Linha de base individual (módulo 3): média e variação de cada métrica da própria pessoa, e z-scores.

- Linha de base da viagem: montada no fim da calibração, reprocessando os quadros da calibração com o perfil
  final, em janelas avaliadas a cada 30 s.
- Linha de base acumulada: soma as viagens do mesmo motorista. Só existe com consentimento, porque padrão de
  piscada e de pupila são dados pessoais sensíveis (LGPD, Lei 13.709/2018, art. 5º, II, e art. 11).
- Desvio-padrão com piso por métrica: uma calibração de 5 a 10 min tem poucas janelas, e uma variação quase zero
  transformaria qualquer oscilação num z enorme. Pisos iniciais, a ajustar com dados reais.
- Pupila só é comparada dentro da mesma faixa de luz.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("drivesafe.baseline")

METRIC_FLOORS = {
    # módulo 1
    "piscadas_por_min": 3.0,
    "duracao_mediana_ms": 20.0,
    "amplitude_mediana": 0.05,
    "avr_fechamento_ms": 10.0,
    "avr_abertura_ms": 15.0,
    "perclos_60s": 0.02,
    "fechamentos_longos_5min": 0.5,
    "bocejos_10min": 0.5,
    "cabeceios_10min": 0.5,
    # módulo 2
    "pupila_iris": 0.03,
    "sacadas_por_min": 5.0,
    "entropia_olhar_bits": 0.15,
    "entropia_transicao_bits": 0.15,
}
MODULE2_METRICS = ("pupila_iris", "sacadas_por_min", "entropia_olhar_bits", "entropia_transicao_bits")
LIGHT_BINNED = ("pupila_iris",)
MIN_WINDOWS = 3
WINDOW_STEP_S = 30.0
WARMUP_S = 60.0
# Esquecimento na linha de base acumulada: janelas antigas pesam menos depois de ~20 viagens.
MAX_ACCUMULATED_WINDOWS = 600
MIN_TRIPS_FOR_ACCUMULATED = 3
TRIP_QUALITY = 0.75
SUSPECT_QUALITY = 0.4
ACCUMULATED_QUALITY = 1.0
FORMAT_VERSION = 1


@dataclass
class RunningStats:
    n: float = 0.0
    mean: float = 0.0
    var: float = 0.0

    def add(self, value: float, max_n: float | None = None) -> None:
        # Média e variância incrementais; com n limitado viram médias móveis exponenciais.
        n = self.n + 1 if max_n is None else min(self.n + 1, max_n)
        delta = value - self.mean
        self.mean += delta / n
        self.var += (delta * (value - self.mean) - self.var) / n
        self.n = n

    def std(self, floor: float) -> float:
        return max(math.sqrt(max(self.var, 0.0)), floor)


def metric_key(name: str, window: dict) -> str | None:
    if name in LIGHT_BINNED:
        band = window.get("pupila_faixa_luz")
        return f"{name}@{band}" if band else None
    return name


class Baseline:
    def __init__(self, source: str, quality: float, trips: int = 1):
        self.source = source  # "viagem" ou "acumulada"
        self.quality = quality
        self.trips = trips
        self.stats: dict[str, RunningStats] = {}
        self.windows: list[dict] = []  # valores de cada janela desta viagem, só em memória

    def add_window(self, window: dict) -> None:
        values = {}
        for name in METRIC_FLOORS:
            key = metric_key(name, window)
            if key is not None and window.get(name) is not None:
                values[key] = float(window[name])
        if values:
            self.add_values(values)
            self.windows.append(values)

    def add_values(self, values: dict, max_n: float | None = None) -> None:
        for key, value in values.items():
            self.stats.setdefault(key, RunningStats()).add(value, max_n)

    def zscores(self, window: dict, names=None) -> dict:
        result = {}
        for name in names or METRIC_FLOORS:
            key = metric_key(name, window)
            stats = self.stats.get(key) if key else None
            if window.get(name) is None or stats is None or stats.n < MIN_WINDOWS:
                continue
            result[name] = round((float(window[name]) - stats.mean) / stats.std(METRIC_FLOORS[name]), 2)
        return result

    def reference_window(self) -> dict:
        """Médias no formato de uma janela, para comparar esta linha de base com outra."""
        window, pupil_n = {}, 0.0
        for key, stats in self.stats.items():
            if stats.n < MIN_WINDOWS:
                continue
            name, _, band = key.partition("@")
            if not band:
                window[name] = stats.mean
            elif stats.n > pupil_n:
                window[name], window["pupila_faixa_luz"], pupil_n = stats.mean, band, stats.n
        return window

    def to_dict(self) -> dict:
        return {
            "versao": FORMAT_VERSION,
            "viagens": self.trips,
            "atualizado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "metricas": {key: {"n": s.n, "media": s.mean, "variancia": s.var} for key, s in sorted(self.stats.items())},
        }

    @classmethod
    def from_dict(cls, data: dict) -> Baseline:
        baseline = cls("acumulada", ACCUMULATED_QUALITY, trips=int(data.get("viagens", 0)))
        for key, item in data.get("metricas", {}).items():
            baseline.stats[key] = RunningStats(float(item["n"]), float(item["media"]), float(item["variancia"]))
        return baseline


def build_trip_baseline(samples, profile, activation_factory=None, quality: float = TRIP_QUALITY) -> Baseline:
    """Reprocessa os quadros da calibração com o perfil final e junta as janelas numa linha de base."""
    from vision.drowsiness import DrowsinessMonitor  # evita importação circular

    baseline = Baseline("viagem", quality)
    if not samples:
        return baseline
    monitor = DrowsinessMonitor(profile=profile)
    activation = activation_factory() if activation_factory else None
    next_window = samples[0].timestamp + WARMUP_S
    for sample in samples:
        assessment = monitor.update(sample)
        if activation is not None:
            activation.observe(sample, assessment.openness)
        if sample.timestamp >= next_window:
            next_window = sample.timestamp + WINDOW_STEP_S
            window = monitor.window_details(sample.timestamp)
            if activation is not None:
                window.update(activation.window_metrics(sample.timestamp, monitor.fps))
            baseline.add_window(window)
    return baseline


class BaselineStore:
    """Linha de base acumulada de um motorista, em JSON no dispositivo. Só usar com consentimento."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> Baseline | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except ValueError as exc:
            logger.warning("Linha de base %s ilegível (%s); ignorando.", self.path, exc)
            return None
        if data.get("versao") != FORMAT_VERSION:
            logger.warning("Linha de base %s em formato desconhecido; ignorando.", self.path)
            return None
        return Baseline.from_dict(data)

    def merge(self, trip: Baseline) -> Baseline:
        accumulated = self.load() or Baseline("acumulada", ACCUMULATED_QUALITY, trips=0)
        for values in trip.windows:
            accumulated.add_values(values, MAX_ACCUMULATED_WINDOWS)
        accumulated.trips += 1
        self.save(accumulated)
        return accumulated

    def save(self, baseline: Baseline) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(baseline.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
