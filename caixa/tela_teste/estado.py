"""O que a tela mostra de cada quadro: medidas do motor (vision/engine.py) em JSON, com os textos em português.

Só números e textos curtos: nenhuma imagem, nenhum ponto do rosto e nenhum polígono saem daqui.
"""
from __future__ import annotations

import math

AVISO_CARDIO = "estimativa pela câmera, não é medida médica"
NIVEIS = ("normal", "atencao", "alto", "critico")

# Tipos de evento (vision/drowsiness.py, phone.py, face_touch.py, engine.py e risk.py). Os rótulos seguem os do painel
# (painel/app/src/content/tipos-de-evento.json) onde o tipo existe lá.
EVENTOS = {
    "calibracao_concluida": ("Calibração concluída", "sistema"),
    "calibracao_suspeita": ("Calibração suspeita: pode já haver sinais de sono", "sistema"),
    "rosto_nao_detectado": ("Câmera sem visão do rosto", "sistema"),
    "olhos_nao_visiveis": ("Olhos não visíveis", "sistema"),
    "atencao": ("Atenção: sinais iniciais de sonolência", "sonolencia"),
    "sonolencia": ("Sonolência", "sonolencia"),
    "sonolencia_abrupta": ("Sonolência logo depois de um período de ativação", "sonolencia"),
    "microssono": ("Microssono (olhos fechados 1 s)", "sonolencia"),
    "sono": ("Sono (olhos fechados 3 s)", "sonolencia"),
    "nao_responsivo": ("Sem resposta (olhos fechados 6 s)", "sonolencia"),
    "olhos_esfregados": ("Olhos esfregados ou coçados", "sonolencia"),
    "mao_no_rosto": ("Mão no rosto por mais de 1 s", "sonolencia"),
    "celular_na_mao": ("Celular na mão", "celular"),
    "celular_no_ouvido": ("Celular no ouvido", "celular"),
    "olhando_celular": ("Olhando o celular (mais de 2 s)", "celular"),
    "direcao_continua": ("Direção contínua acima de 5 h 30 min", "jornada"),
    "ativacao_atipica": ("Sinais compatíveis com ativação atípica (não é diagnóstico)", "ativacao"),
    # Spec 027 (pacote 1 e 2): distração pelo olhar, pausas e estado do aparelho.
    "sono_rosto_perdido": ("Possível sono (rosto perdido com os olhos fechando)", "sonolencia"),
    "distracao_longa": ("Olhar fora da estrada por tempo demais", "celular"),
    "distracao_repetida": ("Olhar fora da estrada várias vezes", "celular"),
    "fora_da_posicao": ("Fora da posição de dirigir", "sistema"),
    "pausa_sugerida": ("Pausa sugerida", "jornada"),
    "pausa_detectada": ("Pausa feita", "jornada"),
    "descanso_previsto_em_atraso": ("Descanso previsto em atraso", "jornada"),
    "avisos_de_distracao_suavizados": ("Avisos de distração suavizados", "sistema"),
    "estado_aparelho": ("Estado do aparelho (som, câmera)", "sistema"),
}
CIRCADIANO = {"forte": "Madrugada: horário de mais sono", "moderado": "Início da tarde: horário de mais sono"}

# Motivos do nível de risco (vision/drowsiness.py, risk.py e phone.py).
MOTIVOS = {
    "piscadas_mais_longas": "Piscadas mais longas",
    "palpebra_mais_lenta": "Pálpebra mais lenta",
    "olhos_fechados_por_mais_tempo": "Olhos fechados por mais tempo",
    "olhos_fechados_acima_do_normal": "Olhos fechados acima do normal",
    "fechamentos_longos": "Fechamentos longos do olho",
    "fechamento_longo": "Fechamento longo do olho",
    "cabeceios": "Cabeceios",
    "bocejos": "Bocejos",
    "atencao_persistente": "Sinais leves há mais de 10 min",
    "microssono": "Microssono",
    "sono": "Olhos fechados há 3 s",
    "nao_responsivo": "Sem resposta",
    "olhos_esfregados_repetidamente": "Olhos esfregados várias vezes",
    "sinais_leves_em_contexto_de_risco": "Sinais leves em horário de risco",
    "sinais_leves_com_gestos_de_sono": "Sinais leves com gestos de sono",
    "direcao_continua_acima_de_5h30": "Direção contínua acima de 5 h 30 min",
    "padrao_ocular_atipico_sustentado": "Padrão dos olhos fora do habitual",
    "sonolencia_logo_apos_periodo_de_ativacao": "Sonolência depois de ativação",
    "olhos_no_celular": "Olhos no celular",
    "celular_no_ouvido": "Celular no ouvido",
    "celular_na_mao": "Celular na mão",
    "reducao_gradual_do_risco": "Risco baixando aos poucos",
}

CELULAR = {"sem_celular": "Nenhum celular", "celular_na_mao": "Celular na mão", "celular_no_ouvido": "Celular no ouvido",
           "olhando_celular": "Olhando o celular"}
GESTOS = {"olhos_esfregados": "Esfregando os olhos", "mao_no_rosto": "Mão no rosto"}
VISIBILIDADE = {"oculos_escuros": "Olhos não visíveis (óculos escuros?)", "olhos_fora_da_imagem": "Olhos fora da imagem"}
# Por que a abertura do olho está sem número (Assessment.frame_source, vision/eyes.py).
PAUSAS = {
    "rosto_virado": "Rosto virado: abertura em pausa",
    "rosto_pequeno": "Rosto pequeno na imagem: chegue mais perto",
    "sem_referencia": "Sem referência do olho ainda",
    "sem_rosto": "Sem rosto na imagem",
}
PUPILA = {
    "ok": "Medida boa",
    "camera_rgb": "Câmera comum (RGB): a pupila só é medida com câmera infravermelha",
    "iris_pequena": "Íris pequena na imagem",
    "sem_contraste": "Sem contraste na íris",
    "olho_fechando": "Olho fechando",
    "sem_pontos_da_iris": "Sem os pontos da íris (modo alternativo)",
    "olhos_fora_do_quadro": "Olhos fora da imagem",
    "olhos_nao_visiveis": "Olhos não visíveis",
}
ATIVACAO = {"sem_dados": "Sem dados ainda", "sem_sinais": "Sem sinais",
            "sinais_leves": "Sinais leves", "sinais_compativeis": "Sinais compatíveis"}
AVISO_AVANCADO = "sinais compatíveis, não é diagnóstico"
COMPARACAO = ("duracao_base_ms", "razao_duracao", "perclos_base", "avr_fechamento_ms", "avr_fechamento_base_ms",
              "razao_avr_fechamento", "amplitude_mediana", "razao_frequencia_piscadas")


def _humano(chave: str) -> str:
    texto = str(chave or "").replace("_", " ").strip()
    return texto[:1].upper() + texto[1:]


def rotulo_evento(tipo: str) -> str:
    return EVENTOS.get(tipo, (_humano(tipo), "sistema"))[0]


def categoria_evento(tipo: str) -> str:
    return EVENTOS.get(tipo, ("", "sistema"))[1]


def texto_motivo(motivo: str) -> str:
    return MOTIVOS.get(motivo, _humano(motivo))


def numero(valor, casas: int | None = None):
    """float do Python (o json não aceita numpy) ou None; NaN e infinito viram None."""
    if valor is None:
        return None
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(valor):
        return None
    return round(valor, casas) if casas is not None else valor


def inteiro(valor):
    valor = numero(valor)
    return None if valor is None else int(round(valor))


def cardio_json(leitura) -> dict:
    """Leitura do vision/cardio.py (CardioReading) sem as regiões do rosto: elas só servem para desenhar a malha."""
    if leitura is None:
        return {"estado": "desligado", "aviso": AVISO_CARDIO}
    onda = getattr(leitura, "onda", None) or []
    historico = getattr(leitura, "historico_bpm", None) or []
    return {
        "estado": str(getattr(leitura, "estado", "medindo") or "medindo"),
        "bpm": inteiro(getattr(leitura, "bpm", None)),
        "ultimo_bpm": inteiro(getattr(leitura, "ultimo_bpm", None)),
        "confianca": numero(getattr(leitura, "confianca", None), 2),
        "snr_db": numero(getattr(leitura, "snr_db", None), 1),
        "respiracao_rpm": numero(getattr(leitura, "respiracao_rpm", None), 1),
        "rmssd_ms": inteiro(getattr(leitura, "rmssd_ms", None)),
        "progresso": numero(getattr(leitura, "progresso", None), 3),
        "onda": [numero(v, 3) or 0.0 for v in list(onda)[-240:]],
        "historico_bpm": [numero(v, 1) for v in list(historico)[-120:] if numero(v) is not None],
        "canal": getattr(leitura, "canal", None),
        "aviso": AVISO_CARDIO,
    }


def _sem_repetir(itens) -> list:
    vistos, saida = set(), []
    for item in itens or ():
        if item not in vistos:
            vistos.add(item)
            saida.append(item)
    return saida


def _sono_estimado(valor) -> dict | None:
    """Faixa de KSS compatível (vision/risk.py estimar_sono), sempre com o aviso: estimativa, não é medida de KSS."""
    if not isinstance(valor, dict):
        return None
    confianca = {"media": "média"}.get(valor.get("confianca"), valor.get("confianca"))
    return {"nivel": inteiro(valor.get("nivel")), "faixa": valor.get("faixa"), "confianca": confianca,
            "aviso": valor.get("aviso") or "estimativa, não é medida de KSS nem diagnóstico"}


def _pausa_do_olho(drowsy, visibility, touch) -> str | None:
    if getattr(drowsy, "openness", None) is not None:
        return None
    if touch is not None and getattr(touch, "eye_covered", False):
        return "Mão no olho: medidas do olho em pausa"
    if visibility is not None and not getattr(visibility, "eyes_ok", True):
        motivo = VISIBILIDADE.get(getattr(visibility, "reason", None), "Olhos não visíveis")
        return f"{motivo}: abertura em pausa"
    fonte = getattr(drowsy, "frame_source", "") or ""
    return PAUSAS.get(fonte, "Abertura em pausa")


def _calibracao(drowsy, calibrador) -> dict:
    dados = {"ativa": bool(getattr(drowsy, "calibrating", False)),
             "progresso": numero(getattr(drowsy, "calibration_progress", 1.0), 3)}
    if calibrador is not None:
        dados.update(segundos=numero(getattr(calibrador, "valid_seconds", None), 1),
                     minimo_s=numero(getattr(calibrador, "min_seconds", None), 1),
                     maximo_s=numero(getattr(calibrador, "max_seconds", None), 1),
                     piscadas=getattr(calibrador, "live_blinks", None),
                     piscadas_alvo=getattr(calibrador, "target_blinks", None))
    return dados


def _avancado(metrics, activation) -> dict:
    """Pupila e sinais de ativação: dados sensíveis, só nesta tela (nada vai para evento nem servidor)."""
    qualidade = getattr(metrics, "pupil_quality", None)
    estado_ativacao = getattr(activation, "state", None) if activation is not None else None
    return {
        "aviso": AVISO_AVANCADO,
        "pupila": {"razao": numero(getattr(metrics, "pupil_ratio", None), 3),
                   "qualidade": PUPILA.get(qualidade, _humano(qualidade)) if qualidade else None},
        "ativacao": None if activation is None else {
            "estado": estado_ativacao,
            "texto": ATIVACAO.get(estado_ativacao, _humano(estado_ativacao)),
            "indice": numero(getattr(activation, "index", None), 2),
            "confianca": numero(getattr(activation, "confidence", None), 2),
            "confianca_texto": getattr(activation, "confidence_label", None),
        },
    }


def medidas(state, latencia: dict | None = None, malha_ms: float | None = None, calibrador=None,
            baixa_em_s: float | None = None, pontos_rosto: bool = True) -> dict:
    """Tudo o que o motor mediu no último quadro, no formato do /estado.

    calibrador: o Calibrator em andamento (segundos válidos, mínimo e piscadas contadas); baixa_em_s: quanto falta para
    o risco descer um nível se nada mudar (histerese de vision/risk.py); pontos_rosto: False no modo YuNet, que não
    tem os 478 pontos (sem malha nem pulso)."""
    metrics = state.metrics
    drowsy = state.drowsiness
    risk = state.risk
    window = getattr(state, "window", None) or {}
    visibility = getattr(state, "visibility", None)
    phone = getattr(state, "phone", None)
    touch = getattr(phone, "face_touch", None)
    nivel = int(getattr(risk, "level", 0) or 0)
    motivos = _sem_repetir(getattr(risk, "reasons", None))
    motivo_olhos = getattr(visibility, "reason", None)
    contexto = getattr(state, "context", None) or {}
    dados = {
        "risco": {
            "nivel": nivel,
            "nome": getattr(risk, "name", NIVEIS[min(max(nivel, 0), 3)]),
            "motivos": [texto_motivo(m) for m in motivos[:4]],
            "motivos_codigos": list(motivos[:6]),
            "alarme": bool(getattr(risk, "alarm", False)),
            "baixa_em_s": inteiro(baixa_em_s) if baixa_em_s is not None and nivel > 0 else None,
            # Spec 027, pacote 1: texto fixo ao motorista, sono e distração separados, sem visão e memória de sono.
            "mensagem": getattr(risk, "mensagem", None),
            "alarme_tipo": getattr(risk, "alarm_kind", None),
            "risco_sono": inteiro(getattr(risk, "risco_sono", None)),
            "risco_distracao": inteiro(getattr(risk, "risco_distracao", None)),
            "sem_visao": bool(getattr(risk, "sem_visao", False)),
            "memoria_sonolencia": bool(getattr(risk, "memoria_sonolencia", False)),
            "sono_estimado": _sono_estimado(getattr(risk, "sono_estimado", None)),
        },
        "rosto": {
            "encontrado": bool(getattr(metrics, "face_found", False)),
            "olhos_visiveis": bool(getattr(visibility, "eyes_ok", True)),
            "motivo_olhos": VISIBILIDADE.get(motivo_olhos, _humano(motivo_olhos)) if motivo_olhos else None,
            "infravermelho": bool(getattr(metrics, "infrared", False)),
            "olhos_ocultos_s": numero(getattr(visibility, "hidden_for", None), 1),
            "pontos_disponiveis": bool(pontos_rosto),
            "mao_na_frente": bool(getattr(touch, "face_hidden", False)) if touch is not None else False,
        },
        "calibracao": _calibracao(drowsy, calibrador),
        "olhos": {
            "abertura": numero(getattr(drowsy, "openness", None), 3),
            "fechado_s": numero(getattr(drowsy, "closed_for", 0.0), 2) or 0.0,
            "perclos_60s": numero(getattr(drowsy, "perclos_60s", None), 4),
            "perclos_3min": numero(window.get("perclos_3min"), 4),
            "medida": getattr(drowsy, "frame_source", None) or None,
            "pausa": _pausa_do_olho(drowsy, visibility, touch),
            "mao_no_olho": bool(getattr(touch, "eye_covered", False)) if touch is not None else False,
            "comparacao": {chave: numero(window.get(chave), 3) for chave in COMPARACAO},
            "piscadas_ultimo_min": int(getattr(drowsy, "blinks_last_minute", 0) or 0),
            "piscadas_por_min": numero(window.get("piscadas_por_min"), 1),
            "piscadas_5min": window.get("piscadas_5min"),
            "duracao_mediana_ms": inteiro(window.get("duracao_mediana_ms")),
            "fechamentos_longos_5min": window.get("fechamentos_longos_5min"),
        },
        "cabeca": {
            "inclinacao": numero(getattr(metrics, "pitch", None), 1),
            "giro": numero(getattr(metrics, "yaw", None), 1),
            "rolagem": numero(getattr(metrics, "roll", None), 1),
            "cabeceios_10min": window.get("cabeceios_10min"),
        },
        "boca": {
            "abertura": numero(getattr(metrics, "jaw_open", None), 3),
            "bocejos_10min": window.get("bocejos_10min"),
        },
        "cardio": cardio_json(getattr(state, "cardio", None)),
        "celular": {
            "ligado": phone is not None,
            "estado": getattr(phone, "state", "sem_celular") if phone is not None else None,
            "texto": CELULAR.get(getattr(phone, "state", "sem_celular"), "") if phone is not None else None,
            "duracao_s": numero(getattr(phone, "duration", None), 1),
            "confianca": numero(getattr(phone, "phone_score", None), 2),
            "maos": int(getattr(phone, "hands", 0) or 0),
            "gesto": GESTOS.get(getattr(touch, "gesture", None)) if touch is not None else None,
            "esfregados_10min": getattr(touch, "rubs_10min", None),
            "mao_no_rosto_10min": getattr(touch, "touches_10min", None),
        },
        "atencao": {
            "olhar_x": numero(getattr(metrics, "gaze_x", None), 3),
            "olhar_y": numero(getattr(metrics, "gaze_y", None), 3),
            "giro": numero(getattr(metrics, "yaw", None), 1),
            "inclinacao": numero(getattr(metrics, "pitch", None), 1),
        },
        "contexto": {
            "circadiano": contexto.get("circadiano"),
            "circadiano_texto": CIRCADIANO.get(contexto.get("circadiano")),
            "tempo_com_rosto_h": numero(contexto.get("tempo_com_rosto_h"), 2),
            "madrugada": contexto.get("madrugada"),
            "direcao_continua_h": numero(contexto.get("direcao_continua_h"), 2),
            "limite_direcao_excedido": bool(contexto.get("limite_direcao_excedido", False)),
        },
        "avancado": _avancado(metrics, getattr(state, "activation", None)),
        "distracao": _distracao(getattr(state, "distraction", None)),
        "desempenho": {
            "fps": numero(getattr(drowsy, "fps", None), 1),
            "latencia_ms": numero((latencia or {}).get("media_ms"), 1),
            "p95_ms": numero((latencia or {}).get("p95_ms"), 1),
            "malha_ms": numero(malha_ms, 1),
        },
    }
    dados["painel"] = montar_painel(dados)
    return dados


def _distracao(distracao) -> dict | None:
    """Canal de distração pelo olhar (vision/distraction.py, spec 027): zona e tempos, só números e nomes."""
    if distracao is None:
        return None
    return {
        "estado": getattr(distracao, "state", None),
        "nivel": inteiro(getattr(distracao, "level", 0)) or 0,
        "zona": getattr(distracao, "zone", None),
        "olhar_fora_s": numero(getattr(distracao, "glance_s", None), 1),
        "espelho_s": numero(getattr(distracao, "driving_glance_s", None), 1),
        "soma_30s_s": numero(getattr(distracao, "vats_s", None), 1),
        "postura": getattr(distracao, "posture", None),
    }


# ------------------------------------------------------------------ painel por pergunta (spec 029, decisão 5)
# A tela não mostra número solto: cada medida tem nome simples, valor com unidade (ou o que falta para medir), situação
# em palavra e uma frase de "o que é". Os limiares são os do motor (vision/drowsiness.py, phone.py, distraction.py).
SITUACAO = {0: "Normal", 1: "Atenção", 2: "Alto", 3: "Crítico"}
ZONAS = {"via": "Para a estrada", "espelho_motorista": "Espelho do motorista", "retrovisor": "Retrovisor",
         "espelho_passageiro": "Espelho do passageiro", "painel": "Painel do veículo", "multimidia": "Central multimídia",
         "colo": "Para baixo, no colo", "fora": "Fora da estrada"}
CELULAR_CURTO = {"celular_na_mao": "Na mão", "celular_no_ouvido": "No ouvido", "olhando_celular": "Olhando o celular"}
LIMITE_CELULAR_S = {"celular_na_mao": 3.0, "celular_no_ouvido": 3.0, "olhando_celular": 2.0}
MOTIVOS_DISTRACAO = frozenset({"olhos_no_celular", "celular_no_ouvido", "celular_na_mao", "distracao_longa",
                               "distracao_repetida", "olhar_fora_da_via", "sem_resposta_a_distracao"})


def _br(valor, casas: int = 0) -> str:
    """Número com vírgula decimal (pt-BR)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def _medida(id_, nome: str, o_que_e: str, valor=None, unidade: str = "", situacao: str = "Normal", nivel=0,
            seu_normal: str | None = None, tecnico: str | None = None, espera: str | None = None) -> dict:
    """nivel: 0 a 3 pinta a situação (0 sem cor); None é situação neutra (medindo, em pausa, desligado)."""
    return {"id": id_, "nome": nome, "valor": valor, "unidade": unidade, "situacao": situacao, "nivel": nivel,
            "o_que_e": o_que_e, "seu_normal": seu_normal, "tecnico": tecnico, "espera": espera}


def _plural(n: int, um: str, varios: str) -> str:
    return f"{n} {um if n == 1 else varios}"


def _agora(d: dict) -> dict:
    risco, olhos, rosto, celular = d["risco"], d["olhos"], d["rosto"], d["celular"]
    distracao = d.get("distracao") or {}
    nivel = int(risco["nivel"] or 0)
    fechado = olhos.get("fechado_s") or 0.0
    nota = None
    if risco.get("memoria_sonolencia"):
        nota = "Teve sinal de sono há pouco: faça uma pausa assim que puder."
    elif risco.get("baixa_em_s") is not None and nivel > 0:
        nota = f"Volta para {SITUACAO[nivel - 1]} em {risco['baixa_em_s']} s se nada mudar."
    usando = celular.get("ligado") and celular.get("estado") not in (None, "sem_celular")
    if not rosto["encontrado"]:
        if rosto.get("mao_na_frente"):
            frase, detalhe = "Mão na frente do rosto", "As medidas do olho voltam quando a mão sair."
        elif nivel >= 2:
            frase = "O rosto saiu da imagem"
            detalhe = "O rosto sumiu com os olhos fechando: pode ser sono."
        else:
            frase, detalhe = "Procurando o rosto", "Centralize o rosto na câmera, chegue mais perto e deixe a luz de frente."
    elif fechado >= 1.0:
        frase = f"Olhos fechados há {_br(fechado, 1)} s"
        detalhe = ("Seis segundos ou mais: sem resposta." if fechado >= 6 else
                   "Três segundos ou mais contam como sono." if fechado >= 3 else
                   "Um segundo ou mais conta como microssono.")
        nivel = max(nivel, 3)
    elif usando:
        estado = celular["estado"]
        frase = f"{CELULAR.get(estado, 'Celular')} há {int(celular.get('duracao_s') or 0)} s"
        detalhe = f"Vira alerta depois de {int(LIMITE_CELULAR_S.get(estado, 3.0))} s."
        nivel = max(nivel, 1)
    elif risco.get("sem_visao"):
        frase = "Não estou vendo os olhos"
        detalhe = f"{rosto.get('motivo_olhos') or 'Óculos escuros, reflexo ou mão na frente'}."
    elif (distracao.get("nivel") or 0) > 0 and (distracao.get("olhar_fora_s") or 0) > 0:
        frase = f"Olhando fora da estrada há {_br(distracao['olhar_fora_s'], 1)} s"
        detalhe = "Um olhar de 3 s ou mais vira alerta."
        nivel = max(nivel, int(distracao["nivel"]))
    elif nivel > 0:
        sono = (risco.get("risco_sono") or 0) >= (risco.get("risco_distracao") or 0)
        frase = ({1: "Sinais leves de sono", 2: "Sinais de sono", 3: "Sono: risco crítico"} if sono else
                 {1: "Atenção à estrada", 2: "Distração", 3: "Distração: risco crítico"})[nivel]
        detalhe = (" · ".join(risco["motivos"][:3]) + ".") if risco["motivos"] else "Sinais acima do seu normal."
    elif d["calibracao"].get("ativa"):
        frase = "Aprendendo o seu normal"
        detalhe = "Olhe para a câmera e pisque normalmente. O microssono e o celular já contam."
    else:
        frase, detalhe = "Tudo normal", "Nenhum sinal de sono ou de distração agora."
    return {"frase": frase, "detalhe": detalhe, "nivel": nivel, "situacao": SITUACAO[nivel], "nota": nota,
            "mensagem": risco.get("mensagem") if nivel > 0 else None}


def _situacao_por_razao(razao):
    if razao is None:
        return "Normal", 0
    if razao >= 1.25:
        return "Bem acima do seu normal", 2
    if razao >= 1.15:
        return "Acima do seu normal", 1
    return "Normal", 0


def _cartao_sono(d: dict) -> dict:
    olhos, risco, rosto = d["olhos"], d["risco"], d["rosto"]
    comparacao = olhos.get("comparacao") or {}
    calibrando = bool(d["calibracao"].get("ativa"))
    fps = (d.get("desempenho") or {}).get("fps")

    abertura, fechado = olhos.get("abertura"), olhos.get("fechado_s") or 0.0
    o_que_e = "Quanto o olho está aberto agora; 100% é o seu olho aberto. Abaixo de 20% conta como fechado."
    if not rosto["encontrado"]:
        principal = _medida("olho_aberto", "Olho aberto agora", o_que_e, situacao="Em pausa", nivel=None,
                            espera="Sem rosto na imagem.")
    elif abertura is None:
        principal = _medida("olho_aberto", "Olho aberto agora", o_que_e, situacao="Em pausa", nivel=None,
                            espera=f"{olhos.get('pausa') or 'Abertura em pausa'}.")
    else:
        situacao, nivel = "Normal", 0
        if abertura < 0.2 and fechado >= 1.0:
            situacao, nivel = "Crítico", 3
        elif abertura < 0.2 and fechado >= 0.5:
            situacao, nivel = "Atenção", 1
        principal = _medida("olho_aberto", "Olho aberto agora", o_que_e, _br(min(abertura, 1.0) * 100), "%",
                            situacao, nivel)

    perclos, base = olhos.get("perclos_3min"), comparacao.get("perclos_base")
    o_que_e = "Parte dos últimos 3 min com o olho quase fechado. Alerta a partir de 12%."
    seu_normal = f"seu normal: {_br(base * 100, 1)}%" if base is not None else None
    if perclos is None:
        fechado_3min = _medida("olho_fechado_3min", "Tempo de olho fechado", o_que_e, situacao="Medindo", nivel=None,
                               seu_normal=seu_normal, tecnico="PERCLOS de 3 min",
                               espera="Ainda medindo: fica pronto com 1 min e meio de rosto na câmera.")
    else:
        situacao, nivel = "Normal", 0
        if perclos >= 0.12:
            situacao, nivel = "Alto", 2
        elif perclos >= max(0.08, 1.5 * base if base is not None else 0.08):
            situacao, nivel = "Atenção", 1
        fechado_3min = _medida("olho_fechado_3min", "Tempo de olho fechado", o_que_e, _br(perclos * 100, 1),
                               "% em 3 min", situacao, nivel, seu_normal, "PERCLOS de 3 min")

    por_min, razao = olhos.get("piscadas_por_min"), comparacao.get("razao_frequencia_piscadas")
    o_que_e = "Média dos últimos 5 min. O comum é de 10 a 20 por minuto; sozinha não muda o risco."
    if por_min is None:
        piscadas = _medida("piscadas_min", "Piscadas por minuto", o_que_e, situacao="Medindo", nivel=None,
                           espera=f"Contando: {_plural(olhos.get('piscadas_ultimo_min') or 0, 'piscada', 'piscadas')} "
                                  "no último minuto. A média sai com 1 min de olho medido.")
    else:
        normal = f"seu normal: {_br(por_min / razao)} por minuto" if razao else None
        piscadas = _medida("piscadas_min", "Piscadas por minuto", o_que_e, _br(por_min), "por minuto",
                           "Normal" if 6 <= por_min <= 30 else "Fora do comum", 0, normal)

    duracao, base_ms = olhos.get("duracao_mediana_ms"), comparacao.get("duracao_base_ms")
    o_que_e = "Quanto dura cada piscada (mediana de 5 min). Mais longa que o seu normal é sinal de sono."
    seu_normal = f"seu normal: {base_ms} ms" if base_ms else None
    if duracao is None:
        if fps is not None and fps < 24:
            espera = (f"Não dá para medir agora: a câmera está em {_br(fps)} quadros por segundo e precisa de 24.")
            situacao = "Indisponível"
        else:
            faltam = max(1, 15 - int(olhos.get("piscadas_5min") or 0))
            espera = f"Ainda medindo: {'falta' if faltam == 1 else 'faltam'} {_plural(faltam, 'piscada', 'piscadas')}."
            situacao = "Medindo"
        duracao_piscada = _medida("duracao_piscada", "Duração da piscada", o_que_e, situacao=situacao, nivel=None,
                                  seu_normal=seu_normal, espera=espera)
    else:
        situacao, nivel = _situacao_por_razao(comparacao.get("razao_duracao"))
        duracao_piscada = _medida("duracao_piscada", "Duração da piscada", o_que_e, str(duracao), "ms", situacao,
                                  nivel, seu_normal)

    bocejos_n = d["boca"].get("bocejos_10min")
    o_que_e = "Boca bem aberta por 2 s ou mais. Dois em 10 min já pedem atenção."
    bocejos = (_medida("bocejos", "Bocejos", o_que_e, situacao="Medindo", nivel=None,
                       espera="Aparece com o rosto na câmera.") if bocejos_n is None else
               _medida("bocejos", "Bocejos", o_que_e, str(bocejos_n), "em 10 min",
                       "Atenção" if bocejos_n >= 2 else "Normal", 1 if bocejos_n >= 2 else 0))
    cabeceios_n = d["cabeca"].get("cabeceios_10min")
    o_que_e = "A cabeça cai de repente e volta, como quem cochila sentado. Dois em 10 min pedem atenção."
    if cabeceios_n is None:
        cabeceios = _medida("cabeceios", "Cabeceios", o_que_e, situacao="Medindo", nivel=None,
                            espera="Aparece com o rosto na câmera.")
    else:
        situacao, nivel = ("Alto", 2) if cabeceios_n >= 3 else ("Atenção", 1) if cabeceios_n >= 2 else ("Normal", 0)
        cabeceios = _medida("cabeceios", "Cabeceios", o_que_e, str(cabeceios_n), "em 10 min", situacao, nivel)

    nivel = int(risco.get("risco_sono") or 0)
    motivos = [texto_motivo(m) for m in risco.get("motivos_codigos") or () if m not in MOTIVOS_DISTRACAO]
    if fechado >= 1.0:
        nivel = 3
        resumo = "Olhos fechados agora."
    elif nivel > 0:
        resumo = (" · ".join(motivos[:3]) + ".") if motivos else "Sinais de sono acima do seu normal."
    elif calibrando:
        resumo = "Aprendendo o seu normal: os sinais leves de sono contam depois da calibração."
    else:
        resumo = "Nenhum sinal de sono agora."
    return {"id": "sono", "titulo": "Sono", "pergunta": "Tem sinal de sono?", "nivel": nivel,
            "situacao": SITUACAO[nivel], "resumo": resumo, "principal": principal,
            "medidas": [fechado_3min, duracao_piscada, piscadas, bocejos, cabeceios]}


def _direcao(d: dict):
    """Para onde olha: a zona do canal de distração ou, sem ele, a direção da cabeça e dos olhos."""
    distracao, atencao = d.get("distracao") or {}, d["atencao"]
    if distracao.get("zona") in ZONAS:
        return ZONAS[distracao["zona"]]
    giro, inclinacao, olhar_y = atencao.get("giro"), atencao.get("inclinacao"), atencao.get("olhar_y")
    if giro is not None and abs(giro) >= 25:
        return "Cabeça virada para o lado"
    if inclinacao is not None and inclinacao >= 20:
        return "Cabeça baixa"
    if inclinacao is not None and inclinacao <= -20:
        return "Cabeça erguida"
    if olhar_y is not None and olhar_y >= 0.25:
        return "Olhando para baixo"
    return "Para a frente"


def _cartao_atencao(d: dict) -> dict:
    risco, rosto, celular = d["risco"], d["rosto"], d["celular"]
    distracao = d.get("distracao") or {}
    nivel_canal = int(distracao.get("nivel") or 0)

    o_que_e = "Para onde o rosto e os olhos apontam. Fora da estrada por mais de 2 s pede atenção."
    if not rosto["encontrado"]:
        principal = _medida("para_onde_olha", "Para onde olha", o_que_e, situacao="Em pausa", nivel=None,
                            espera="Sem rosto na imagem.")
    elif distracao.get("estado") == "aprendendo_frente":
        principal = _medida("para_onde_olha", "Para onde olha", o_que_e, _direcao(d), "", "Aprendendo", None)
    else:
        principal = _medida("para_onde_olha", "Para onde olha", o_que_e, _direcao(d), "",
                            SITUACAO[nivel_canal], nivel_canal)

    o_que_e = "Olhar contínuo fora da estrada agora. Um olhar de 3 s ou mais vira alerta."
    fora = distracao.get("olhar_fora_s")
    if fora is None:
        tempo_fora = _medida("tempo_fora", "Tempo olhando fora", o_que_e, situacao="Indisponível", nivel=None,
                             espera="Aparece quando a frente do motorista estiver aprendida.")
    else:
        situacao, nivel = ("Alto", 2) if fora >= 3 else ("Atenção", 1) if fora >= 2 else ("Normal", 0)
        tempo_fora = _medida("tempo_fora", "Tempo olhando fora", o_que_e, _br(fora, 1), "s", situacao, nivel)

    o_que_e = "Celular na mão, no ouvido ou o olhar no celular. Vira alerta depois de 2 a 3 s."
    if not celular.get("ligado"):
        uso = _medida("celular", "Celular", o_que_e, "Desligado", "", "Desligado", None)
        esfregados = _medida("olhos_esfregados", "Olhos esfregados",
                             "Vezes que a mão esfregou os olhos. Três em 10 min contam como sinal leve de sono.",
                             "Desligado", "", "Desligado", None)
    else:
        estado = celular.get("estado") or "sem_celular"
        if estado == "sem_celular":
            uso = _medida("celular", "Celular", o_que_e, "Nenhum", "", "Normal", 0)
        else:
            duracao = celular.get("duracao_s") or 0.0
            alto = duracao >= LIMITE_CELULAR_S.get(estado, 3.0)
            uso = _medida("celular", "Celular", o_que_e, f"{CELULAR_CURTO.get(estado, 'Em uso')} há {int(duracao)} s",
                          "", "Alto" if alto else "Atenção", 2 if alto else 1)
        n = celular.get("esfregados_10min") or 0
        esfregados = _medida("olhos_esfregados", "Olhos esfregados",
                             "Vezes que a mão esfregou os olhos. Três em 10 min contam como sinal leve de sono.",
                             str(n), "em 10 min", "Atenção" if n >= 3 else "Normal", 1 if n >= 3 else 0)

    nivel = int(risco.get("risco_distracao") or 0)
    if uso["nivel"]:
        nivel = max(nivel, uso["nivel"])
    if not rosto["encontrado"]:
        resumo = "Sem rosto na imagem: nada para avaliar agora."
    elif nivel > 0:
        resumo = "Atenção fora da estrada agora." if uso["nivel"] == 0 else "Celular em uso agora."
    else:
        resumo = "Olhando para a estrada."
    return {"id": "atencao", "titulo": "Atenção na estrada", "pergunta": "Está olhando para a estrada?",
            "nivel": nivel, "situacao": SITUACAO[nivel], "resumo": resumo, "principal": principal,
            "medidas": [tempo_fora, uso, esfregados]}


def _cartao_coracao(d: dict) -> dict:
    cardio = d["cardio"]
    estado = cardio.get("estado")
    if d["rosto"].get("pontos_disponiveis") is False:
        estado = "sem_pontos"
    o_que_e = ("Estimativa pela cor da pele da testa e das bochechas; não é medida médica. Em repouso, o comum é de 60 "
               "a 100 bpm.")
    bpm, ultimo, confianca = cardio.get("bpm"), cardio.get("ultimo_bpm"), cardio.get("confianca")
    if estado == "pronto" and bpm is not None:
        boa = confianca is not None and confianca >= 0.5
        principal = _medida("pulso", "Pulso", o_que_e, str(bpm), "bpm", "Leitura boa" if boa else "Leitura fraca", None)
    elif estado == "medindo":
        progresso = min(max(cardio.get("progresso") or 0.0, 0.0), 1.0)
        restam = max(1, int(round((1.0 - progresso) * 15)))
        principal = _medida("pulso", "Pulso", o_que_e, situacao="Medindo", nivel=None,
                            espera=f"Medindo: faltam {restam} s. Fique parado, com luz de frente no rosto.")
    elif estado in ("sinal_fraco", "movimento"):
        espera = ("Movimento: fique parado para medir." if estado == "movimento" else
                  "Sinal fraco: mais luz no rosto e menos movimento.")
        principal = _medida("pulso", "Pulso", o_que_e, str(ultimo) if ultimo is not None else None,
                            "bpm (última leitura)", "Sinal fraco", None, espera=espera)
    elif estado == "sem_rosto":
        principal = _medida("pulso", "Pulso", o_que_e, situacao="Sem rosto", nivel=None, espera="Sem rosto para medir.")
    elif estado == "sem_pontos":
        principal = _medida("pulso", "Pulso", o_que_e, situacao="Indisponível", nivel=None,
                            espera="Pulso indisponível neste modo de câmera.")
    else:
        principal = _medida("pulso", "Pulso", o_que_e, situacao="Desligado", nivel=None,
                            espera="Desligado nas opções do teste.")

    o_que_e = "Quanto dá para confiar no número agora, pela força do sinal na pele."
    if confianca is None or estado in ("desligado", "sem_pontos", None):
        conf = _medida("confianca", "Confiança da leitura", o_que_e, situacao="Medindo", nivel=None,
                       espera="Aparece junto com a leitura.")
    else:
        situacao = "Leitura boa" if confianca >= 0.7 else "Leitura fraca" if confianca >= 0.4 else "Sinal fraco"
        conf = _medida("confianca", "Confiança da leitura", o_que_e, _br(confianca * 100), "%", situacao, None,
                       tecnico=f"sinal-ruído {_br(cardio['snr_db'], 1)} dB" if cardio.get("snr_db") is not None else None)
    return {"id": "coracao", "titulo": "Coração (estimativa)", "pergunta": "Como está o pulso?", "nivel": 0,
            "situacao": principal["situacao"], "resumo": "Estimativa pela câmera, não é medida médica.",
            "principal": principal, "medidas": [conf]}


def _detalhes(d: dict) -> list:
    cabeca, boca, olhos, celular = d["cabeca"], d["boca"], d["olhos"], d["celular"]
    cardio, avancado, desempenho, contexto = d["cardio"], d["avancado"], d["desempenho"], d["contexto"]
    distracao, risco = d.get("distracao") or {}, d["risco"]
    comparacao = olhos.get("comparacao") or {}

    def angulo(id_, nome, valor, positivo, negativo, reto, limite, o_que_e):
        if valor is None:
            return _medida(id_, nome, o_que_e, situacao="Em pausa", nivel=None, espera="Sem rosto na imagem.")
        texto = reto if abs(valor) < 3 else f"{_br(abs(valor))}° {positivo if valor > 0 else negativo}"
        return _medida(id_, nome, o_que_e, texto, "", "Atenção" if abs(valor) >= limite else "Normal",
                       1 if abs(valor) >= limite else 0)

    longos = olhos.get("fechamentos_longos_5min")
    grupo_cabeca = [
        angulo("inclinacao", "Cabeça para baixo ou para cima", cabeca.get("inclinacao"), "para baixo", "para cima",
               "reta", 20, "Inclinação da cabeça. Uma queda rápida de 15° conta como cabeceio."),
        angulo("giro", "Cabeça para os lados", cabeca.get("giro"), "para um lado", "para o outro lado", "de frente",
               25, "Quanto a cabeça está virada. Acima de 25° o rosto sai da estrada."),
        (_medida("boca", "Boca aberta", "Quanto a boca está aberta. Aberta por 2 s ou mais conta como bocejo.",
                 situacao="Em pausa", nivel=None, espera="Sem rosto na imagem.") if boca.get("abertura") is None else
         _medida("boca", "Boca aberta", "Quanto a boca está aberta. Aberta por 2 s ou mais conta como bocejo.",
                 _br(min(boca["abertura"], 1.0) * 100), "%", "Atenção" if boca["abertura"] >= 0.45 else "Normal",
                 1 if boca["abertura"] >= 0.45 else 0)),
        (_medida("fechamentos_longos", "Fechamentos longos do olho",
                 "Olho fechado de meio segundo a 1 s. Um já é sinal leve; três em 5 min, sinal forte.",
                 situacao="Medindo", nivel=None, espera="Aparece com o rosto na câmera.") if longos is None else
         _medida("fechamentos_longos", "Fechamentos longos do olho",
                 "Olho fechado de meio segundo a 1 s. Um já é sinal leve; três em 5 min, sinal forte.",
                 str(longos), "em 5 min", "Alto" if longos >= 3 else "Atenção" if longos >= 1 else "Normal",
                 2 if longos >= 3 else 1 if longos >= 1 else 0)),
    ]

    soma = distracao.get("soma_30s_s")
    grupo_olhar = [
        (_medida("soma_fora", "Olhares fora em 30 s", "Soma dos olhares fora da estrada nos últimos 30 s. Com 10 s "
                 "vira alerta.", situacao="Indisponível", nivel=None, espera="Aparece quando a frente do motorista "
                 "estiver aprendida.") if soma is None else
         _medida("soma_fora", "Olhares fora em 30 s", "Soma dos olhares fora da estrada nos últimos 30 s. Com 10 s "
                 "vira alerta.", _br(soma, 1), "s", "Alto" if soma >= 10 else "Normal", 2 if soma >= 10 else 0)),
        _medida("maos", "Mãos na imagem", "Quantas mãos a câmera vê agora. Serve para achar o celular e a mão no rosto.",
                str(celular.get("maos") or 0) if celular.get("ligado") else "Desligado",
                "na imagem" if celular.get("ligado") else "", "Normal" if celular.get("ligado") else "Desligado",
                0 if celular.get("ligado") else None),
        _medida("mao_no_rosto", "Mão no rosto", "Mão parada no rosto por mais de 1 s. É contada, mas não pesa no risco.",
                str(celular.get("mao_no_rosto_10min") or 0) if celular.get("ligado") else "Desligado",
                "em 10 min" if celular.get("ligado") else "", "Normal" if celular.get("ligado") else "Desligado",
                0 if celular.get("ligado") else None),
    ]
    if celular.get("ligado") and celular.get("confianca") is not None:
        grupo_olhar.append(_medida("celular_confianca", "Certeza do celular", "Quanto o detector tem certeza de que é "
                                   "um celular, e não a mão.", _br(celular["confianca"] * 100), "%", "Normal", 0))

    respiracao, variabilidade = cardio.get("respiracao_rpm"), cardio.get("rmssd_ms")
    grupo_coracao = [
        _medida("respiracao", "Respiração", "Estimada pelo mesmo sinal da pele. Experimental: só para avaliar o "
                "protótipo.", _br(respiracao) if respiracao is not None else None, "por minuto", "Experimental", None,
                espera=None if respiracao is not None else "Precisa de mais tempo com leitura boa do pulso."),
        _medida("variabilidade", "Variação entre batimentos", "Diferença entre batimentos seguidos. Experimental: "
                "precisa de 25 quadros por segundo e sinal forte.", str(variabilidade) if variabilidade is not None
                else None, "ms", "Experimental", None, tecnico="RMSSD",
                espera=None if variabilidade is not None else "Ainda sem sinal forte o bastante."),
    ]

    sono_estimado = risco.get("sono_estimado") or {}
    pupila, ativacao = avancado.get("pupila") or {}, avancado.get("ativacao")
    avr, avr_base = comparacao.get("avr_fechamento_ms"), comparacao.get("avr_fechamento_base_ms")
    razao_avr = comparacao.get("razao_avr_fechamento")
    grupo_avancado = [
        _medida("sono_estimado", "Escala de sono estimada", "Faixa de sono compatível com os sinais medidos. "
                "Estimativa, não é a nota da pessoa nem diagnóstico.", sono_estimado.get("faixa") or None, "",
                "Experimental", None, tecnico="Escala de Karolinska (KSS)",
                espera=None if sono_estimado.get("faixa") else "Aparece depois da calibração."),
        _medida("pupila", "Pupila em relação à íris", "Tamanho da pupila comparado com a íris. Só é medida com câmera "
                "infravermelha.", _br(pupila["razao"] * 100) if pupila.get("razao") is not None else None, "%",
                "Experimental", None, espera=None if pupila.get("razao") is not None else
                f"{pupila.get('qualidade') or 'Sem medida'}."),
        _medida("ativacao", "Padrão dos olhos fora do habitual", "Sinais compatíveis com ativação atípica, pelas "
                "piscadas e pelo olhar. Não é diagnóstico.", (ativacao or {}).get("texto") or None, "", "Experimental",
                None, espera=None if (ativacao or {}).get("texto") else "Precisa da linha de base da calibração."),
        (_medida("palpebra", "Velocidade da pálpebra", "Quanto tempo a pálpebra leva para fechar. Mais lenta que o seu "
                 "normal é sinal leve de sono.", situacao="Medindo", nivel=None, tecnico="AVR de fechamento",
                 espera="Precisa de 28 quadros por segundo e 15 piscadas.") if avr is None else
         _medida("palpebra", "Velocidade da pálpebra", "Quanto tempo a pálpebra leva para fechar. Mais lenta que o seu "
                 "normal é sinal leve de sono.", _br(avr), "ms", "Atenção" if (razao_avr or 0) >= 1.3 else "Normal",
                 1 if (razao_avr or 0) >= 1.3 else 0, f"seu normal: {_br(avr_base)} ms" if avr_base else None,
                 "AVR de fechamento")),
    ]

    fps = desempenho.get("fps")
    lento = fps is not None and fps < 24
    grupo_sessao = [
        (_medida("fps", "Imagens por segundo", "Quantas imagens são analisadas por segundo. Abaixo de 24, a duração "
                 "da piscada não vale.", situacao="Medindo", nivel=None, espera="Aparece em alguns segundos.")
         if fps is None else
         _medida("fps", "Imagens por segundo", "Quantas imagens são analisadas por segundo. Abaixo de 24, a duração "
                 "da piscada não vale.", _br(fps), "por segundo", "Lento" if lento else "Normal", 1 if lento else 0)),
        (_medida("latencia", "Tempo de análise", "Tempo para analisar cada imagem, em média e no pior caso de 20.",
                 situacao="Medindo", nivel=None, espera="Aparece em alguns segundos.")
         if desempenho.get("latencia_ms") is None else
         _medida("latencia", "Tempo de análise", "Tempo para analisar cada imagem, em média e no pior caso de 20.",
                 f"{_br(desempenho['latencia_ms'])} (pior {_br(desempenho.get('p95_ms') or 0)})", "ms", "Normal", 0)),
        (_medida("malha_ms", "Tempo da malha", "Tempo para desenhar a malha em cada imagem da tela.",
                 situacao="Medindo", nivel=None, espera="Aparece com a primeira imagem.")
         if desempenho.get("malha_ms") is None else
         _medida("malha_ms", "Tempo da malha", "Tempo para desenhar a malha em cada imagem da tela.",
                 _br(desempenho["malha_ms"], 1), "ms", "Normal", 0)),
    ]
    if contexto.get("tempo_com_rosto_h") is not None:
        minutos = int(round(contexto["tempo_com_rosto_h"] * 60))
        grupo_sessao.append(_medida("tempo_rosto", "Tempo com o rosto na câmera", "Tempo seguido com o rosto na "
                                    "imagem neste teste.", f"{minutos // 60} h {minutos % 60:02d}" if minutos >= 60
                                    else str(minutos), "min" if minutos < 60 else "", "Normal", 0))
    if contexto.get("circadiano_texto") or contexto.get("madrugada"):
        grupo_sessao.append(_medida("horario", "Horário", "Na madrugada e no começo da tarde os sinais leves de sono "
                                    "pesam mais.", contexto.get("circadiano_texto") or "Madrugada", "", "Atenção", 1))
    return [
        {"id": "cabeca", "titulo": "Cabeça e boca", "medidas": grupo_cabeca},
        {"id": "olhar", "titulo": "Olhar e mãos", "medidas": grupo_olhar},
        {"id": "coracao", "titulo": "Coração, mais medidas", "medidas": grupo_coracao},
        {"id": "avancado", "titulo": "Sinais experimentais", "medidas": grupo_avancado},
        {"id": "sessao", "titulo": "Desempenho e contexto", "medidas": grupo_sessao},
    ]


def montar_painel(d: dict) -> dict:
    """A tela do teste por pergunta: frase do topo, os cartões Sono, Atenção na estrada e Coração, e os Detalhes."""
    return {"agora": _agora(d), "cartoes": [_cartao_sono(d), _cartao_atencao(d), _cartao_coracao(d)],
            "detalhes": _detalhes(d)}
