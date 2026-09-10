"""Tipos de evento: nome em português, categoria e quais entram na fila de revisão do gestor."""

ALERT_TYPE_LABELS = {
    "looking_down": "Olhando para baixo",
    "eyes_closed": "Olhos fechados",
    "phone_usage": "Usando celular",
    "inattention": "Desatenção prolongada",
    "distracted": "Distraído",
    "possivel_sonolencia": "Possível sonolência",
    "atencao": "Atenção: sinais iniciais de sonolência",
    "sonolencia": "Sonolência",
    "microssono": "Microssono (olhos fechados 1 s)",
    "sono": "Sono (olhos fechados 3 s)",
    "nao_responsivo": "Sem resposta (olhos fechados 6 s)",
    "rosto_nao_detectado": "Câmera sem visão do rosto",
    "calibracao_concluida": "Calibração concluída",
    "calibracao_suspeita": "Calibração suspeita (motorista já cansado?)",
    "sonolencia_abrupta": "Sonolência abrupta (queda rápida do estado de alerta)",
    "ativacao_atipica": "Sinais compatíveis com ativação atípica (não é diagnóstico)",
    "direcao_continua": "Direção contínua acima de 5 h 30 min",
    "olhos_nao_visiveis": "Olhos não visíveis (óculos escuros ou fora da imagem)",
    "celular_na_mao": "Celular na mão",
    "celular_no_ouvido": "Celular no ouvido",
    "olhando_celular": "Olhando o celular (mais de 2 s)",
}

CATEGORIES = {
    "sonolencia": {"atencao", "sonolencia", "microssono", "sono", "nao_responsivo", "sonolencia_abrupta",
                   "possivel_sonolencia", "eyes_closed"},
    "celular": {"celular_na_mao", "celular_no_ouvido", "olhando_celular", "phone_usage"},
    "ativacao": {"ativacao_atipica"},
    "jornada": {"direcao_continua"},
    "distracao": {"looking_down", "inattention", "distracted"},
    "sistema": {"rosto_nao_detectado", "olhos_nao_visiveis", "calibracao_concluida", "calibracao_suspeita"},
}
_CATEGORY_BY_TYPE = {alert_type: category for category, types in CATEGORIES.items() for alert_type in types}

# Aviso de sistema e evento de risco 1 não pedem revisão humana.
REVIEWABLE_CATEGORIES = {"sonolencia", "celular", "ativacao", "jornada", "distracao"}
MIN_RISK_TO_REVIEW = 2


def label_of(alert_type: str | None) -> str:
    return ALERT_TYPE_LABELS.get(alert_type or "", alert_type or "")


def category_of(alert_type: str | None) -> str:
    return _CATEGORY_BY_TYPE.get(alert_type or "", "outro")


def types_in(category: str) -> set:
    return CATEGORIES.get(category, set())


def needs_review(alert_type: str | None, risk_level: int | None) -> bool:
    return category_of(alert_type) in REVIEWABLE_CATEGORIES and (risk_level or 0) >= MIN_RISK_TO_REVIEW
