"""Os olhos estão visíveis o bastante para medir? Óculos escuros e olhos fora da imagem.

Quando não estão, as medidas do olho são desligadas: não viram "olho fechado" nem alarme falso, e o sistema
avisa. Óculos escuros deixam a região do olho bem mais escura e lisa que a bochecha logo abaixo.
Limiares iniciais, conferidos só em fotos de teste: validar com vídeos reais (com e sem óculos, dia e noite).
Muitos óculos escuros deixam passar infravermelho; com câmera IR os olhos continuam sendo medidos.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

SUNGLASSES_MAX_RATIO = 0.45  # luminância do olho ÷ luminância da bochecha
SUNGLASSES_MAX_CONTRAST = 18.0  # desvio-padrão do cinza na região do olho: lente escura é lisa
SUNGLASSES_CLEAR_RATIO = 0.55
# O quadro escuro já desliga as medidas na hora (olho fechado é pálpebra, clara como a bochecha, e não cai
# aqui); o estado "de óculos" só é assumido depois de 1,5 s e só sai depois de 3 s claros.
SUNGLASSES_ON_S = 1.5
SUNGLASSES_OFF_S = 3.0
MIN_CHEEK_LUMINANCE = 30.0  # imagem escura demais: não dá para comparar
MAX_YAW_FOR_RATIO_DEG = 25.0

_EYE_SIGNALS = {
    "ear": None, "ear_left": None, "ear_right": None, "eye_width_left": 0.0, "eye_width_right": 0.0,
    "blink_score": None, "eye_open_prob": None, "pupil_ratio": None, "gaze_x": None, "gaze_y": None,
}


@dataclass
class Visibility:
    eyes_ok: bool = True
    reason: str | None = None  # oculos_escuros ou olhos_fora_da_imagem
    hidden_for: float = 0.0


def mask_eye_signals(metrics):
    """Cópia das medidas sem os sinais do olho. Aceita FaceMetrics ou Sample."""
    names = {f.name for f in fields(metrics)}
    changes = {name: value for name, value in _EYE_SIGNALS.items() if name in names}
    if "pupil_quality" in names:
        changes["pupil_quality"] = "olhos_nao_visiveis"
    return replace(metrics, **changes)


class EyeVisibility:
    def __init__(self, detect_sunglasses: bool = True):
        self.detect_sunglasses = detect_sunglasses
        self.sunglasses = False
        self._dark_now = False
        self._dark_since = None
        self._clear_since = None
        self._hidden_since = None

    def update(self, metrics) -> Visibility:
        t = metrics.timestamp
        if not metrics.face_found:
            # Sem rosto é outro aviso (rosto_nao_detectado); o estado dos óculos fica como estava.
            self._hidden_since = None
            return Visibility()
        if self.detect_sunglasses:
            self._track_sunglasses(t, metrics)

        if self.sunglasses or self._dark_now:
            reason = "oculos_escuros"
        elif not getattr(metrics, "eyes_in_frame", True):
            reason = "olhos_fora_da_imagem"
        else:
            self._hidden_since = None
            return Visibility()
        if self._hidden_since is None:
            self._hidden_since = t
        return Visibility(False, reason, t - self._hidden_since)

    def _track_sunglasses(self, t: float, metrics) -> None:
        eye = getattr(metrics, "eye_luminance", None)
        cheek = getattr(metrics, "cheek_luminance", None)
        contrast = getattr(metrics, "eye_contrast", None)
        yaw = getattr(metrics, "yaw", None)
        self._dark_now = False
        if eye is None or cheek is None or contrast is None or cheek < MIN_CHEEK_LUMINANCE or (
                yaw is not None and abs(yaw) > MAX_YAW_FOR_RATIO_DEG):
            return  # quadro sem comparação possível: mantém o estado dos óculos
        ratio = eye / cheek
        self._dark_now = ratio <= SUNGLASSES_MAX_RATIO and contrast <= SUNGLASSES_MAX_CONTRAST
        if not self.sunglasses:
            if self._dark_now:
                self._dark_since = t if self._dark_since is None else self._dark_since
                if t - self._dark_since >= SUNGLASSES_ON_S:
                    self.sunglasses = True
                    self._clear_since = None
            else:
                self._dark_since = None
        elif ratio >= SUNGLASSES_CLEAR_RATIO:
            self._clear_since = t if self._clear_since is None else self._clear_since
            if t - self._clear_since >= SUNGLASSES_OFF_S:
                self.sunglasses = False
                self._dark_since = None
        else:
            self._clear_since = None
