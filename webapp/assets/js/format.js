/* Datas no fuso do servidor, números em pt-BR e os textos que explicam cada coisa na tela. */

let TIME_ZONE = "America/Sao_Paulo";
const dateFormats = new Map();
const numberFormats = new Map();

export function setTimeZone(timeZone) {
  if (!timeZone) return;
  TIME_ZONE = timeZone;
  dateFormats.clear();
}

function formatter(options) {
  const key = JSON.stringify(options);
  if (!dateFormats.has(key)) dateFormats.set(key, new Intl.DateTimeFormat("pt-BR", { timeZone: TIME_ZONE, ...options }));
  return dateFormats.get(key);
}

function toDate(value) {
  return value instanceof Date ? value : new Date(value);
}

function parts(value) {
  const result = {};
  const options = { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23" };
  for (const part of formatter(options).formatToParts(toDate(value))) result[part.type] = part.value;
  return result;
}

/** "2026-09-10" no fuso do servidor. */
export function localDay(value = new Date()) {
  const p = parts(value);
  return `${p.year}-${p.month}-${p.day}`;
}

export function localHour(value) {
  return Number(parts(value).hour) % 24;
}

export function time(value, withSeconds = false) {
  if (!value) return "—";
  return formatter({ hour: "2-digit", minute: "2-digit", ...(withSeconds ? { second: "2-digit" } : {}) }).format(toDate(value));
}

export function date(value) {
  if (!value) return "—";
  return formatter({ day: "2-digit", month: "2-digit", year: "numeric" }).format(toDate(value));
}

export function dateTime(value) {
  if (!value) return "—";
  const sameYear = parts(value).year === parts(new Date()).year;
  const options = { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
  if (!sameYear) options.year = "numeric";
  return formatter(options).format(toDate(value));
}

/** Dia vindo da API como "AAAA-MM-DD" (sem hora). */
export function dayLabel(isoDay) {
  const [, month, day] = String(isoDay).split("-");
  return `${day}/${month}`;
}

export function relative(value) {
  if (!value) return "—";
  const moment = toDate(value);
  const seconds = (Date.now() - moment.getTime()) / 1000;
  if (seconds < 45) return "agora";
  if (seconds < 3600) return `há ${Math.max(1, Math.round(seconds / 60))} min`;
  if (localDay(moment) === localDay()) return `hoje, ${time(moment)}`;
  if (localDay(moment) === localDay(new Date(Date.now() - 86400000))) return `ontem, ${time(moment)}`;
  return dateTime(moment);
}

export function number(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  if (!numberFormats.has(digits)) {
    numberFormats.set(digits, new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits }));
  }
  return numberFormats.get(digits).format(Number(value));
}

export function percent(ratio, digits = 0) {
  if (ratio === null || ratio === undefined) return "—";
  return `${number(ratio * 100, digits)}%`;
}

export function duration(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds < 60) return `${number(seconds, seconds < 10 ? 1 : 0)} s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    const rest = Math.round(seconds - minutes * 60);
    return rest ? `${minutes} min ${rest} s` : `${minutes} min`;
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes - hours * 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

export function drivingHours(value) {
  if (value === null || value === undefined) return "—";
  const total = Math.round(value * 60);
  return `${Math.floor(total / 60)} h ${String(total % 60).padStart(2, "0")} min`;
}

export function plural(count, one, many) {
  return `${number(count)} ${count === 1 ? one : many}`;
}

export function initials(name) {
  const words = String(name || "?").trim().split(/\s+/);
  return (words[0][0] + (words.length > 1 ? words[words.length - 1][0] : "")).toUpperCase();
}

/** "olhos_fechados_por_mais_tempo" → "Olhos fechados por mais tempo". */
export function humanize(code) {
  const text = String(code ?? "").replaceAll("_", " ").trim();
  return text ? text[0].toUpperCase() + text.slice(1) : "—";
}

// ---------- rótulos ----------

export const LIVE_TEXT = {
  ao_vivo: "ao vivo", conectando: "conectando", reconectando: "reconectando", desligado: "sem tempo real",
  local: "modo local",
};

export const ROLE_LABELS = { admin: "Equipe DriveSafe", gestor: "Gestor", motorista: "Motorista" };

export const REVIEW_LABELS = {
  pendente: "Para revisar", confirmado: "Confirmado", falso_alarme: "Alarme falso",
  orientado: "Motorista orientado", arquivado: "Sem revisão",
};

export const DECISIONS = [
  { value: "confirmado", label: "Confirmar", text: "O evento aconteceu de verdade." },
  { value: "falso_alarme", label: "Alarme falso", text: "O sistema errou: reflexo, óculos, câmera fora de posição." },
  { value: "orientado", label: "Motorista orientado", text: "Houve conversa ou orientação com o motorista." },
];

export const CATEGORY_LABELS = {
  sonolencia: "Sonolência", celular: "Celular", ativacao: "Ativação atípica", jornada: "Jornada",
  distracao: "Distração", sistema: "Aviso do equipamento", outro: "Outro",
};

export const CATEGORY_HELP = {
  sonolencia: "Olhos fechando por mais tempo, piscadas lentas, cabeceio ou bocejos, comparados com o próprio motorista descansado (calibração). Confira o contexto: horário, horas ao volante e o que o motorista relata.",
  celular: "Celular na mão, no ouvido ou olhar preso no celular por mais de 2 segundos. Celular parado no suporte não gera alerta.",
  ativacao: "Sinais do olhar fora do padrão do próprio motorista (pupila, só com câmera infravermelha; piscadas; movimentos dos olhos). Não é diagnóstico nem exame toxicológico: é motivo para conversar, nunca para punir.",
  jornada: "Direção contínua acima de 5 h 30 min, limite do Código de Trânsito Brasileiro (art. 67-C).",
  distracao: "Olhar fora da via por tempo prolongado.",
  sistema: "Aviso do próprio equipamento: câmera sem ver o rosto, olhos não visíveis ou calibração.",
  outro: "Evento sem categoria conhecida.",
};

export const CONSENTS = [
  {
    kind: "monitoramento",
    title: "Monitoramento durante a viagem",
    text: "A câmera do veículo mede sinais de sonolência e de uso do celular enquanto você dirige. Nenhuma imagem é gravada nem enviada: só os eventos, como “olhos fechados por 1,2 s às 02:14”.",
  },
  {
    kind: "perfil_entre_viagens",
    title: "Guardar meu perfil entre viagens",
    text: "O equipamento guarda como são seus olhos e piscadas quando você está descansado, para não recalibrar toda viagem. Sem esta autorização, o perfil é apagado do equipamento e a calibração acontece de novo a cada viagem.",
  },
  {
    kind: "sinais_ativacao_envio",
    title: "Enviar sinais de ativação atípica",
    text: "Alguns sinais do olhar podem indicar um estado de ativação diferente do seu normal. Isso não é diagnóstico nem exame de drogas. Sem esta autorização, esses sinais ficam só no equipamento e não chegam à empresa.",
  },
];

export const CHANNEL_LABELS = { app_motorista: "pelo app do motorista", termo_assinado: "termo assinado", admin: "registro da equipe" };

export const POLICIES = [
  { value: "desligado", title: "Desligado", text: "O equipamento não calcula sinais de ativação atípica." },
  { value: "local", title: "Só no equipamento", text: "Os sinais ajudam no alerta sonoro dentro do veículo, mas não saem dele." },
  { value: "enviar", title: "Enviar para a empresa", text: "Os sinais chegam ao app só dos motoristas que autorizaram. Quem não autorizou continua “só no equipamento”." },
];

export const PHONE_STATES = {
  sem_celular: "sem celular", celular_na_mao: "celular na mão", celular_no_ouvido: "celular no ouvido",
  olhando_celular: "olhando o celular",
};

export const DETAIL_LABELS = {
  fechado_s: "Tempo de olhos fechados", perclos_60s: "Olhos fechados no último minuto (PERCLOS)",
  perclos_3min: "Olhos fechados em 3 min (PERCLOS)", piscadas_60s: "Piscadas no último minuto",
  piscadas_5min: "Piscadas em 5 min", piscadas_por_min: "Piscadas por minuto",
  duracao_mediana_ms: "Duração típica da piscada", avr_fechamento_ms: "Relação amplitude/velocidade ao fechar (AVR)",
  avr_abertura_ms: "Relação amplitude/velocidade ao abrir (AVR)", amplitude_mediana: "Amplitude típica da piscada",
  fechamentos_longos_5min: "Fechamentos longos em 5 min", bocejos_10min: "Bocejos em 10 min",
  cabeceios_10min: "Cabeceios em 10 min", sem_rosto_s: "Tempo sem ver o rosto", calibrando: "Em calibração",
  medida: "Medida usada", fps: "Quadros por segundo", perfil: "Perfil", usando_perfil_anterior: "Usando perfil anterior",
  velocidade_kmh: "Velocidade", direcao_continua_h: "Direção contínua", limite_direcao_excedido: "Limite de direção excedido",
  madrugada: "Madrugada (0 h às 7 h)", fonte_tempo_direcao: "Origem do tempo de direção", indice: "Índice",
  indice_max: "Índice máximo", confianca: "Confiança", confianca_nivel: "Nível de confiança", estado: "Estado",
  sinais: "Sinais", motivo: "Motivo", motivos: "Motivos", fracao_valida_60s: "Imagem útil no último minuto",
  pupila_iris: "Pupila em relação à íris", sacadas_por_min: "Movimentos rápidos dos olhos por minuto",
  entropia_transicao_bits: "Variação do olhar (bits)", duracao_min: "Duração",
  min_desde_o_ultimo_sinal: "Minutos desde o último sinal", confianca_celular: "Confiança da detecção do celular",
  maos_detectadas: "Mãos detectadas", olhando_para_baixo: "Olhando para baixo", demo: "Dado de demonstração",
};

export function detailLabel(key) {
  return DETAIL_LABELS[key] || humanize(key);
}

export function detailValue(key, value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "sim" : "não";
  if (typeof value === "number") {
    if (key === "direcao_continua_h") return drivingHours(value);
    if (key.endsWith("_ms")) return `${number(value, value < 10 ? 1 : 0)} ms`;
    if (key.endsWith("_s")) return `${number(value, 1)} s`;
    if (key.endsWith("_kmh")) return `${number(value)} km/h`;
    if (key === "duracao_min") return `${number(value, 1)} min`;
    if (key.startsWith("perclos") || key.startsWith("fracao")) return percent(value, 1);
    return number(value, Number.isInteger(value) ? 0 : 2);
  }
  if (Array.isArray(value)) return value.length ? value.map((item) => (typeof item === "string" ? humanize(item) : JSON.stringify(item))).join("; ") : "—";
  if (typeof value === "object") {
    return Object.entries(value).map(([innerKey, innerValue]) => `${detailLabel(innerKey)}: ${detailValue(innerKey, innerValue)}`).join(" · ");
  }
  return typeof value === "string" && /^[a-z0-9_]+$/.test(value) ? humanize(value) : String(value);
}
