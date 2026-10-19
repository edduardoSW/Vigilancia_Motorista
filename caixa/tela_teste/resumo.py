"""Resumo da sessão de teste (spec 023, decisão 7): somado quadro a quadro, salvo em JSON e CSV só se a pessoa pedir.

- Eventos: os de `state.events` de cada quadro, por tipo, e a linha do tempo com a hora.
- PERCLOS médio: média do PERCLOS de 60 s, amostrado uma vez por segundo enquanto existe.
- Piscadas por minuto: piscadas completas (as mesmas que vision/drowsiness.py conta) pelo tempo com o olho medido.
- Frequência cardíaca: média, mínima e máxima só das leituras "pronto", uma por segundo (o cardio atualiza a cada 1 s).
  É estimativa pela câmera, não é medida médica: o aviso vai junto no arquivo.
"""
from __future__ import annotations

import csv
import io
import json
import math
from collections import Counter, deque
from datetime import datetime
from pathlib import Path

from tela_teste.estado import AVISO_CARDIO, NIVEIS, categoria_evento, numero, rotulo_evento
from vision.calibration import COMPLETE_BLINK_OPENNESS, MAX_BLINK_S

# Spec 029, decisão 6: o resumo começa pela resposta. Alerta = evento de sono, celular, distração, jornada ou ativação;
# avisos do sistema (calibração, rosto fora, estado do aparelho) e "pausa feita" ficam só nos detalhes.
GRUPOS = (("sono", "de sono"), ("celular", "de celular"), ("distracao", "de distração"), ("jornada", "de jornada"),
          ("ativacao", "de ativação"))
TIPOS_CELULAR = frozenset({"celular_na_mao", "celular_no_ouvido", "olhando_celular"})
TIPOS_DISTRACAO = frozenset({"distracao_longa", "distracao_repetida"})
INFORMATIVOS = frozenset({"pausa_detectada"})


def grupo_do_alerta(tipo: str) -> str | None:
    if tipo in INFORMATIVOS:
        return None
    if tipo in TIPOS_CELULAR:
        return "celular"
    if tipo in TIPOS_DISTRACAO:
        return "distracao"
    return {"sonolencia": "sono", "jornada": "jornada", "ativacao": "ativacao"}.get(categoria_evento(tipo))


def situacao_do_evento(nivel_evento: int) -> tuple[str, int]:
    """Nível do evento (1 a 5, vision/drowsiness.py) em palavra e cor: 4 e 5 crítico, 3 alto, até 2 atenção."""
    if nivel_evento >= 4:
        return "Crítico", 3
    if nivel_evento == 3:
        return "Alto", 2
    return "Atenção", 1


def duracao_texto(segundos) -> str:
    """'45 s', '12 min', '2 min 03 s', '1 h 05 min'."""
    total = int(round(segundos or 0))
    if total < 60:
        return f"{total} s"
    if total < 3600:
        minutos, resto = divmod(total, 60)
        return f"{minutos} min" if resto == 0 else f"{minutos} min {resto:02d} s"
    horas, resto = divmod(total, 3600)
    return f"{horas} h {resto // 60:02d} min"


def frase_resumo(duracao_s, alertas) -> str:
    """'Teste de 12 min: 2 alertas de sono e 1 de celular.' ou 'Nenhum alerta em 12 min.'"""
    contagem = Counter(alerta["grupo"] for alerta in alertas)
    texto_duracao = duracao_texto(duracao_s)
    if not contagem:
        return f"Nenhum alerta em {texto_duracao}."
    partes = []
    for grupo, rotulo in GRUPOS:
        n = contagem.get(grupo)
        if n:
            partes.append(f"{n} {'alerta' if n == 1 else 'alertas'} {rotulo}" if not partes else f"{n} {rotulo}")
    lista = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]
    return f"Teste de {texto_duracao}: {lista}."


def _br(valor, casas: int = 0) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")

FORMATO = "rotaguard-resumo-teste/1"
PASTA_RESUMOS = "resumos"
AMOSTRA_S = 1.0
MAX_DT_S = 1.0  # buraco maior que isso (câmera parada) não conta tempo
MIN_TEMPO_OLHOS_S = 20.0  # piscadas por minuto só com pelo menos 20 s de olho medido
EVENTOS_GUARDADOS = 500


def _agora() -> datetime:
    return datetime.now().astimezone()


class ResumoSessao:
    def __init__(self, camera: str | None = None, versao: str | None = None, agora=_agora):
        self.camera = camera
        self.versao = versao
        self._agora = agora
        self.inicio_em: datetime | None = None
        self.fim_em: datetime | None = None
        self.t0 = self.t_ultimo = None
        self.quadros = 0
        self.eventos_por_tipo: Counter = Counter()
        self.eventos = deque(maxlen=EVENTOS_GUARDADOS)
        self.tempo_por_nivel = [0.0, 0.0, 0.0, 0.0]
        self.tempo_olhos = 0.0
        self.tempo_celular = 0.0
        self.piscadas = 0
        # Totais da sessão a partir dos contadores de 10 min do motor: soma só o que aumentou de um quadro para o
        # outro. Um sinal novo no mesmo segundo em que um antigo sai da janela de 10 min se perde (raro).
        self.totais = Counter()
        self._contadores: dict[str, int] = {}
        self._perclos: list[float] = []
        self._proximo_perclos = -math.inf
        self._bpm: list[float] = []
        self._proximo_bpm = -math.inf
        self.alertas: deque = deque(maxlen=EVENTOS_GUARDADOS)
        self._duracoes: list[float] = []
        self._proxima_duracao = -math.inf
        self.base: dict = {}  # linha de base da calibração (perclos_base, duracao_base_ms), para "seu normal"

    def quadro(self, estado, t: float | None = None) -> list[dict]:
        """Soma um quadro. Devolve os eventos novos já no formato da linha do tempo."""
        t = float(estado.metrics.timestamp if t is None else t)
        if self.t0 is None:
            self.t0 = t
            self.inicio_em = self._agora()
        dt = 0.0 if self.t_ultimo is None else min(max(t - self.t_ultimo, 0.0), MAX_DT_S)
        self.t_ultimo = t
        self.quadros += 1

        nivel = min(max(int(getattr(estado.risk, "level", 0) or 0), 0), 3)
        self.tempo_por_nivel[nivel] += dt
        drowsy = estado.drowsiness
        if getattr(drowsy, "openness", None) is not None:
            self.tempo_olhos += dt
        perclos = getattr(drowsy, "perclos_60s", None)
        if perclos is not None and t >= self._proximo_perclos:
            self._proximo_perclos = t + AMOSTRA_S
            self._perclos.append(float(perclos))

        cardio = getattr(estado, "cardio", None)
        bpm = numero(getattr(cardio, "bpm", None)) if cardio is not None else None
        if getattr(cardio, "estado", None) == "pronto" and bpm is not None and t >= self._proximo_bpm:
            self._proximo_bpm = t + AMOSTRA_S
            self._bpm.append(bpm)

        phone = getattr(estado, "phone", None)
        if phone is not None and getattr(phone, "state", "sem_celular") != "sem_celular":
            self.tempo_celular += dt
        touch = getattr(phone, "face_touch", None)
        if touch is not None:
            self._somar("olhos_esfregados", getattr(touch, "rubs_10min", None))
            self._somar("mao_no_rosto", getattr(touch, "touches_10min", None))
        janela = getattr(estado, "window", None) or {}
        self._somar("bocejos", janela.get("bocejos_10min"))
        self._somar("cabeceios", janela.get("cabeceios_10min"))
        for chave in ("perclos_base", "duracao_base_ms"):
            if janela.get(chave) is not None:
                self.base[chave] = float(janela[chave])
        duracao_piscada = numero(janela.get("duracao_mediana_ms"))
        if duracao_piscada is not None and t >= self._proxima_duracao:
            self._proxima_duracao = t + AMOSTRA_S
            self._duracoes.append(duracao_piscada)

        novos = []
        for evento in getattr(estado, "events", None) or ():
            tipo = evento.alert_type
            self.eventos_por_tipo[tipo] += 1
            item = {
                "hora": self._agora().strftime("%H:%M:%S"),
                "t": round(t - self.t0, 1),
                "tipo": tipo,
                "rotulo": rotulo_evento(tipo),
                "categoria": categoria_evento(tipo),
                "nivel": int(evento.risk_level),
                "duracao_s": numero(evento.duration, 1),
            }
            self.eventos.append(item)
            novos.append(item)
            grupo = grupo_do_alerta(tipo)
            if grupo is not None:
                situacao, cor = situacao_do_evento(int(evento.risk_level))
                trecho = (getattr(evento, "details", None) or {}).get("trecho_uid")
                self.alertas.append({**item, "grupo": grupo, "situacao": situacao, "cor": cor,
                                     "trecho_uid": trecho if isinstance(trecho, str) else None})
        return novos

    def _somar(self, chave: str, contador) -> None:
        if contador is None:
            return
        atual = int(contador)
        anterior = self._contadores.get(chave, 0)
        if atual > anterior:
            self.totais[chave] += atual - anterior
        self._contadores[chave] = atual

    def piscada(self, t: float, piscada) -> None:
        """Ouvinte de DrowsinessMonitor.blink_listeners: conta só as piscadas completas, como o próprio monitor."""
        if piscada.min_openness <= COMPLETE_BLINK_OPENNESS and piscada.duration <= MAX_BLINK_S:
            self.piscadas += 1

    def finalizar(self, t: float | None = None) -> None:
        if t is not None and self.t0 is not None:
            self.t_ultimo = max(self.t_ultimo or t, t)
        self.fim_em = self._agora()

    @property
    def duracao_s(self) -> float:
        return 0.0 if self.t0 is None else max(0.0, self.t_ultimo - self.t0)

    def dados(self) -> dict:
        duracao = self.duracao_s
        bpm = self._bpm
        por_tipo = dict(self.eventos_por_tipo.most_common())
        dados = {
            "formato": FORMATO,
            "versao": self.versao,
            "inicio": self.inicio_em.isoformat(timespec="seconds") if self.inicio_em else None,
            "fim": self.fim_em.isoformat(timespec="seconds") if self.fim_em else None,
            "duracao_s": round(duracao, 1),
            "camera": self.camera,
            "quadros": self.quadros,
            "fps_medio": round((self.quadros - 1) / duracao, 1) if duracao > 0 and self.quadros > 1 else None,
            "total_eventos": sum(por_tipo.values()),
            "eventos_por_tipo": por_tipo,
            "eventos_por_tipo_lista": [
                {"tipo": tipo, "rotulo": rotulo_evento(tipo), "categoria": categoria_evento(tipo), "quantidade": n}
                for tipo, n in por_tipo.items()
            ],
            "perclos_medio": round(sum(self._perclos) / len(self._perclos), 4) if self._perclos else None,
            "piscadas": self.piscadas,
            "piscadas_por_min": (round(self.piscadas / (self.tempo_olhos / 60.0), 1)
                                 if self.tempo_olhos >= MIN_TEMPO_OLHOS_S else None),
            "frequencia_cardiaca": {
                "media": round(sum(bpm) / len(bpm), 1) if bpm else None,
                "minima": round(min(bpm), 1) if bpm else None,
                "maxima": round(max(bpm), 1) if bpm else None,
                "leituras": len(bpm),
                "observacao": AVISO_CARDIO,
            },
            "tempo_por_nivel_s": {nome: round(segundos, 1) for nome, segundos in zip(NIVEIS, self.tempo_por_nivel)},
            "celular_s": round(self.tempo_celular, 1),
            "bocejos": self.totais["bocejos"],
            "cabeceios": self.totais["cabeceios"],
            "olhos_esfregados": self.totais["olhos_esfregados"],
            "mao_no_rosto": self.totais["mao_no_rosto"],
            "eventos": list(self.eventos),
            "duracao_piscada_ms": round(sum(self._duracoes) / len(self._duracoes)) if self._duracoes else None,
            "base": dict(self.base),
        }
        alertas = list(self.alertas)
        dados["frase"] = frase_resumo(duracao, alertas)
        dados["alertas"] = alertas
        dados["como_estava"] = como_estava(dados)
        return dados


def _linha(id_, nome, o_que_e, faixa_normal, valor=None, unidade="", situacao="Normal", nivel=0, seu_normal=None,
           tecnico=None, espera=None) -> dict:
    return {"id": id_, "nome": nome, "valor": valor, "unidade": unidade, "situacao": situacao, "nivel": nivel,
            "o_que_e": o_que_e, "faixa_normal": faixa_normal, "seu_normal": seu_normal, "tecnico": tecnico,
            "espera": espera}


def como_estava(dados: dict) -> list:
    """Tabela 'Como a pessoa estava': a média do teste de cada medida, a explicação, a faixa normal e a situação."""
    minutos = max((dados.get("duracao_s") or 0.0) / 60.0, 1e-6)
    por_10min = lambda total: total / minutos * 10.0  # noqa: E731
    base = dados.get("base") or {}
    linhas = []

    perclos = dados.get("perclos_medio")
    seu_normal = f"seu normal: {_br(base['perclos_base'] * 100, 1)}%" if "perclos_base" in base else None
    o_que_e = "Média do tempo com o olho quase fechado, minuto a minuto. Alerta a partir de 12%."
    if perclos is None:
        linhas.append(_linha("olho_fechado", "Tempo de olho fechado", o_que_e, "abaixo de 8%", situacao="Indisponível",
                             nivel=None, seu_normal=seu_normal, tecnico="PERCLOS médio",
                             espera="Não deu para medir: pouco tempo com o olho visível."))
    else:
        situacao, nivel = ("Alto", 2) if perclos >= 0.12 else ("Atenção", 1) if perclos >= 0.08 else ("Normal", 0)
        linhas.append(_linha("olho_fechado", "Tempo de olho fechado", o_que_e, "abaixo de 8%", _br(perclos * 100, 1),
                             "% do tempo", situacao, nivel, seu_normal, "PERCLOS médio"))

    piscadas = dados.get("piscadas_por_min")
    o_que_e = "Piscadas completas por minuto de olho medido. Sozinha não indica sono."
    if piscadas is None:
        linhas.append(_linha("piscadas", "Piscadas por minuto", o_que_e, "10 a 20 por minuto", situacao="Indisponível",
                             nivel=None, espera="Precisa de pelo menos 20 s com o olho medido."))
    else:
        linhas.append(_linha("piscadas", "Piscadas por minuto", o_que_e, "10 a 20 por minuto", _br(piscadas, 1),
                             "por minuto", "Normal" if 6 <= piscadas <= 30 else "Fora do comum", 0))

    duracao, base_ms = dados.get("duracao_piscada_ms"), base.get("duracao_base_ms")
    o_que_e = "Quanto durou cada piscada, em média. Mais longa que o seu normal é sinal de sono."
    faixa = f"até {_br(base_ms * 1.15)} ms" if base_ms else "de 100 a 400 ms"
    seu_normal = f"seu normal: {_br(base_ms)} ms" if base_ms else None
    if duracao is None:
        linhas.append(_linha("duracao_piscada", "Duração da piscada", o_que_e, faixa, situacao="Indisponível",
                             nivel=None, seu_normal=seu_normal,
                             espera="Precisa de 24 imagens por segundo e 15 piscadas."))
    else:
        razao = duracao / base_ms if base_ms else None
        situacao, nivel = ("Normal", 0)
        if razao is not None and razao >= 1.25:
            situacao, nivel = "Bem acima do seu normal", 2
        elif razao is not None and razao >= 1.15:
            situacao, nivel = "Acima do seu normal", 1
        linhas.append(_linha("duracao_piscada", "Duração da piscada", o_que_e, faixa, str(duracao), "ms", situacao,
                             nivel, seu_normal))

    def contagem(id_, nome, total, o_que_e, faixa, atencao, alto=None):
        taxa = por_10min(total)
        situacao, nivel = "Normal", 0
        if alto is not None and taxa >= alto:
            situacao, nivel = "Alto", 2
        elif taxa >= atencao and total > 0:
            situacao, nivel = "Atenção", 1
        return _linha(id_, nome, o_que_e, faixa, str(total), "no teste", situacao, nivel)

    linhas.append(contagem("bocejos", "Bocejos", dados.get("bocejos") or 0,
                           "Boca bem aberta por 2 s ou mais. É sinal complementar de sono.", "menos de 2 a cada 10 min", 2))
    linhas.append(contagem("cabeceios", "Cabeceios", dados.get("cabeceios") or 0,
                           "A cabeça caiu de repente e voltou, como quem cochila sentado.", "nenhum", 2, 3))
    linhas.append(contagem("olhos_esfregados", "Olhos esfregados", dados.get("olhos_esfregados") or 0,
                           "Vezes que a mão esfregou os olhos. Três em 10 min contam como sinal leve.",
                           "menos de 3 a cada 10 min", 3))
    celular_s = dados.get("celular_s") or 0.0
    linhas.append(_linha("celular", "Tempo com celular", "Tempo com o celular na mão, no ouvido ou com o olhar nele.",
                         "nenhum", duracao_texto(celular_s), "", "Atenção" if celular_s >= 3 else "Normal",
                         1 if celular_s >= 3 else 0))
    linhas.append(_linha("mao_no_rosto", "Mão no rosto", "Mão parada no rosto por mais de 1 s. É contada, mas não "
                         "pesa no risco.", "não pesa no risco", str(dados.get("mao_no_rosto") or 0), "no teste",
                         "Normal", 0))
    cardio = dados.get("frequencia_cardiaca") or {}
    o_que_e = "Média das leituras boas do pulso. Estimativa pela câmera, não é medida médica."
    if cardio.get("media") is None:
        linhas.append(_linha("pulso", "Pulso (estimativa)", o_que_e, "60 a 100 bpm em repouso", situacao="Indisponível",
                             nivel=None, espera="Sem leitura estável neste teste."))
    else:
        linhas.append(_linha("pulso", "Pulso (estimativa)", o_que_e, "60 a 100 bpm em repouso", _br(cardio["media"]),
                             f"bpm (de {_br(cardio['minima'])} a {_br(cardio['maxima'])})",
                             "Leitura boa" if cardio.get("leituras", 0) >= 10 else "Leitura fraca", None))
    return linhas


def _decimal(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor}".replace(".", ",")
    return str(valor)


def texto_csv(dados: dict) -> str:
    """CSV para abrir no Excel em português: separador ";" e vírgula decimal. Medidas e, depois, os eventos."""
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\n")
    escritor.writerow(["medida", "valor"])
    escritor.writerow(["resumo", dados.get("frase", "")])
    for chave in ("inicio", "fim", "duracao_s", "camera", "quadros", "fps_medio", "total_eventos", "perclos_medio",
                  "piscadas", "piscadas_por_min", "celular_s", "bocejos", "cabeceios", "olhos_esfregados",
                  "mao_no_rosto"):
        escritor.writerow([chave, _decimal(dados.get(chave))])
    cardio = dados.get("frequencia_cardiaca") or {}
    for chave in ("media", "minima", "maxima", "leituras"):
        escritor.writerow([f"frequencia_cardiaca_{chave}", _decimal(cardio.get(chave))])
    escritor.writerow(["frequencia_cardiaca_observacao", cardio.get("observacao", AVISO_CARDIO)])
    for nivel, segundos in (dados.get("tempo_por_nivel_s") or {}).items():
        escritor.writerow([f"tempo_risco_{nivel}_s", _decimal(segundos)])
    for tipo, quantidade in (dados.get("eventos_por_tipo") or {}).items():
        escritor.writerow([f"eventos_{tipo}", quantidade])
    escritor.writerow([])
    escritor.writerow(["hora", "segundos_desde_o_inicio", "tipo", "descricao", "nivel", "duracao_s"])
    for evento in dados.get("eventos") or ():
        escritor.writerow([evento["hora"], _decimal(evento["t"]), evento["tipo"], evento["rotulo"], evento["nivel"],
                           _decimal(evento["duracao_s"])])
    return saida.getvalue()


def salvar(dados: dict, pasta_dados: Path) -> tuple[Path, Path]:
    """Grava resumo-AAAA-MM-DD-HHMMSS.json e .csv em <pasta de dados>/resumos. Nada fora dessa pasta."""
    destino = Path(pasta_dados) / PASTA_RESUMOS
    destino.mkdir(parents=True, exist_ok=True)
    try:
        quando = datetime.fromisoformat(dados["inicio"]) if dados.get("inicio") else _agora()
    except ValueError:
        quando = _agora()
    base = f"resumo-{quando.strftime('%Y-%m-%d-%H%M%S')}"
    nome, numero_copia = base, 1
    while (destino / f"{nome}.json").exists() or (destino / f"{nome}.csv").exists():
        numero_copia += 1
        nome = f"{base}-{numero_copia}"
    caminho_json = destino / f"{nome}.json"
    caminho_csv = destino / f"{nome}.csv"
    caminho_json.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    caminho_csv.write_text(texto_csv(dados), encoding="utf-8-sig")
    return caminho_json, caminho_csv
