"""Filtro One Euro para a pose da cabeça (zonas do olhar) e, se o cardio quiser, para os vértices das ROIs (spec 027,
DMS-14).

Fontes:
- Casiez, Roussel & Vogel, "1€ Filter", CHI 2012 (https://gery.casiez.net/1euro/):
  α = 1 / (1 + τ/Te), τ = 1/(2π·fc), fc = min_cutoff + β·|dx̂|. Parado, o corte baixo tira o tremor; em movimento
  rápido, o corte sobe e o atraso some.
- O MediaPipe Face Landmarker JÁ aplica One Euro nos pontos em modo VIDEO com num_faces = 1 (min_cutoff 0,05,
  beta 80; face_landmarks_detector_graph.cc:156-167). Por isso este filtro NUNCA entra antes do EAR, da abertura ou
  das piscadas: filtrar de novo atrasaria a pálpebra e inflaria duração e AVR (pesquisa §4.1). Ele vale só para a
  pose usada nas zonas do olhar (vision/gaze.py), onde o "pisca-pisca" na borda de uma zona vira alarme falso.

Parâmetros da pose (graus, 30 fps), escolhidos por simulação contra o critério DMS-14a: degrau de 30° chega a 90% em
1 quadro e ruído uniforme de ±1° parado sai com 0,24° de valor eficaz. Hipótese até medir com vídeo real.
"""
from __future__ import annotations

import math

POSE_FILTER = {"min_cutoff": 1.0, "beta": 0.1, "d_cutoff": 1.0}
# Vértices das ROIs do cardio (pixels): corte bem baixo, sem β (ROI tremendo vira ruído no rPPG). Hipótese; o
# vision/cardio.py decide se usa.
ROI_FILTER = {"min_cutoff": 0.3, "beta": 0.0, "d_cutoff": 1.0}
# Buraco maior que isso (rosto perdido) recomeça o filtro em vez de arrastar o valor antigo.
MAX_GAP_S = 0.5


def _alpha(cutoff: float, dt: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter:
    """Aceita número ou numpy.ndarray (filtra cada elemento com o mesmo α, pela maior derivada)."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.0, d_cutoff: float = 1.0, max_gap_s: float = MAX_GAP_S):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.max_gap_s = max_gap_s
        self.reset()

    def reset(self) -> None:
        self._t = None
        self._x = None
        self._dx = None

    def __call__(self, t: float, x):
        if self._t is not None and t <= self._t:
            return self._x  # carimbo repetido ou voltando: mantém a saída
        if self._t is None or t - self._t > self.max_gap_s:
            self._t, self._x, self._dx = t, x, x * 0.0
            return x
        dt = t - self._t
        dx = (x - self._x) / dt
        self._dx = self._dx + _alpha(self.d_cutoff, dt) * (dx - self._dx)
        speed = float(abs(self._dx).max()) if hasattr(self._dx, "max") else abs(self._dx)
        self._x = self._x + _alpha(self.min_cutoff + self.beta * speed, dt) * (x - self._x)
        self._t = t
        return self._x
