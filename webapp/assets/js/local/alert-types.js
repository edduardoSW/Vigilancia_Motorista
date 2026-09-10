/* Tipos de evento para o modo local. Espelho de backend/alert_types.py: mudou lá, muda aqui. */

export const ALERT_TYPE_LABELS = {
  looking_down: "Olhando para baixo",
  eyes_closed: "Olhos fechados",
  phone_usage: "Usando celular",
  inattention: "Desatenção prolongada",
  distracted: "Distraído",
  possivel_sonolencia: "Possível sonolência",
  atencao: "Atenção: sinais iniciais de sonolência",
  sonolencia: "Sonolência",
  microssono: "Microssono (olhos fechados 1 s)",
  sono: "Sono (olhos fechados 3 s)",
  nao_responsivo: "Sem resposta (olhos fechados 6 s)",
  rosto_nao_detectado: "Câmera sem visão do rosto",
  calibracao_concluida: "Calibração concluída",
  calibracao_suspeita: "Calibração suspeita (motorista já cansado?)",
  sonolencia_abrupta: "Sonolência abrupta (queda rápida do estado de alerta)",
  ativacao_atipica: "Sinais compatíveis com ativação atípica (não é diagnóstico)",
  direcao_continua: "Direção contínua acima de 5 h 30 min",
  olhos_nao_visiveis: "Olhos não visíveis (óculos escuros ou fora da imagem)",
  celular_na_mao: "Celular na mão",
  celular_no_ouvido: "Celular no ouvido",
  olhando_celular: "Olhando o celular (mais de 2 s)",
};

export const CATEGORIES = {
  sonolencia: ["atencao", "sonolencia", "microssono", "sono", "nao_responsivo", "sonolencia_abrupta", "possivel_sonolencia", "eyes_closed"],
  celular: ["celular_na_mao", "celular_no_ouvido", "olhando_celular", "phone_usage"],
  ativacao: ["ativacao_atipica"],
  jornada: ["direcao_continua"],
  distracao: ["looking_down", "inattention", "distracted"],
  sistema: ["rosto_nao_detectado", "olhos_nao_visiveis", "calibracao_concluida", "calibracao_suspeita"],
};

const CATEGORY_BY_TYPE = Object.fromEntries(
  Object.entries(CATEGORIES).flatMap(([category, types]) => types.map((type) => [type, category])),
);
const REVIEWABLE = new Set(["sonolencia", "celular", "ativacao", "jornada", "distracao"]);

export function labelOf(type) {
  return ALERT_TYPE_LABELS[type] || type || "";
}

export function categoryOf(type) {
  return CATEGORY_BY_TYPE[type] || "outro";
}

/** Aviso do equipamento e evento de risco 1 não pedem revisão humana. */
export function needsReview(type, risk) {
  return REVIEWABLE.has(categoryOf(type)) && (risk || 0) >= 2;
}
