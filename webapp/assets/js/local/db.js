/* Banco do modo de testes local: um JSON no localStorage deste navegador. Nada sai do aparelho.
   Começa com dados de exemplo (empresas, motoristas, veículos e 30 dias de eventos fictícios marcados com "demo"). */
import { localDay } from "../format.js";
import { needsReview } from "./alert-types.js";
import { onRemoteChange, publish } from "./bus.js";

const KEY = "drivesafe-local-dados-v1";
const DAY = 86400000;
const MAX_ALERTS = 5000;
let data = null;

onRemoteChange(() => {
  data = null;
});

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && parsed.version === 1 ? parsed : null;
  } catch {
    return null;
  }
}

export function db() {
  if (!data) {
    data = read();
    if (!data) {
      data = seed();
      persist();
    }
  }
  return data;
}

export function persist() {
  if (data.alerts.length > MAX_ALERTS) {
    data.alerts.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
    data.alerts.length = MAX_ALERTS;
  }
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
  } catch (error) {
    if (data.alerts.length > 300) {
      data.alerts.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
      data.alerts.length = Math.floor(data.alerts.length * 0.7);
      persist();
    } else {
      console.warn("Não deu para salvar os dados locais:", error);
    }
  }
}

export function newId(table) {
  const current = db();
  current.seq[table] = (current.seq[table] || 0) + 1;
  return current.seq[table];
}

export function resetToExample() {
  data = seed();
  persist();
  publish("reset", null);
}

// ---------- dados de exemplo ----------

function mulberry32(seedValue) {
  let state = seedValue;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// [tipo, nível, peso, acontece mais de madrugada]
const EXAMPLE_KINDS = [
  ["atencao", 2, 22, true], ["sonolencia", 3, 14, true], ["microssono", 3, 11, true], ["sono", 4, 3, true],
  ["sonolencia_abrupta", 3, 2, true], ["olhando_celular", 4, 11, false], ["celular_na_mao", 3, 12, false],
  ["celular_no_ouvido", 3, 8, false], ["direcao_continua", 2, 5, false], ["rosto_nao_detectado", 1, 4, false],
  ["olhos_nao_visiveis", 1, 3, false],
];

const NOTES = ["Conversa na base: dormiu pouco na noite anterior.", "Parada de descanso combinada.", "Reflexo do sol no para-brisa.", null, null];

function pick(random, list) {
  const total = list.reduce((sum, item) => sum + item[2], 0);
  let roll = random() * total;
  for (const item of list) {
    roll -= item[2];
    if (roll <= 0) return item;
  }
  return list[list.length - 1];
}

function exampleDetails(type, random) {
  const between = (low, high, digits = 2) => Number((low + random() * (high - low)).toFixed(digits));
  switch (type) {
    case "atencao":
      return { perclos_3min: between(0.08, 0.12, 3), duracao_mediana_ms: between(230, 320, 0), piscadas_por_min: between(14, 26, 1), fechamentos_longos_5min: Math.round(between(1, 3, 0)), motivos: ["olhos_fechados_acima_do_normal"], demo: true };
    case "sonolencia":
      return { perclos_3min: between(0.12, 0.24, 3), duracao_mediana_ms: between(300, 460, 0), fechamentos_longos_5min: Math.round(between(3, 7, 0)), bocejos_10min: Math.round(between(0, 4, 0)), motivos: ["olhos_fechados_por_mais_tempo", "piscadas_mais_longas"], demo: true };
    case "microssono":
    case "sono":
      return { fechado_s: type === "sono" ? between(3, 4.5) : between(1, 2.6), perclos_60s: between(0.1, 0.35, 3), piscadas_por_min: between(8, 20, 1), demo: true };
    case "sonolencia_abrupta":
      return { motivos: ["sonolencia_depois_de_sinais_de_ativacao"], min_desde_o_ultimo_sinal: between(12, 50, 0), demo: true };
    case "olhando_celular":
    case "celular_na_mao":
    case "celular_no_ouvido":
      return { estado: type, confianca_celular: between(0.45, 0.92), maos_detectadas: 1, olhando_para_baixo: type === "olhando_celular", demo: true };
    case "direcao_continua":
      return { direcao_continua_h: between(5.55, 7.4), madrugada: random() < 0.3, fonte_tempo_direcao: "rosto_na_camera", demo: true };
    default:
      return { sem_rosto_s: between(10, 40, 1), demo: true };
  }
}

function exampleDuration(type, details, random) {
  if (details.fechado_s) return details.fechado_s;
  if (type.startsWith("celular") || type === "olhando_celular") return Number((2 + random() * 12).toFixed(1));
  if (details.sem_rosto_s) return details.sem_rosto_s;
  return 0;
}

function uid(random) {
  const hex = () => Math.floor(random() * 16).toString(16);
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (char) => (char === "x" ? hex() : ((Math.floor(random() * 4) + 8).toString(16))));
}

function exampleAlerts(random, now, devices) {
  const alerts = [];
  const intensity = { 1: 1.6, 2: 1.1, 3: 0.5, 4: 0.8, 5: 0.6, 6: 0.3 };
  for (const device of devices) {
    const count = Math.round(34 * (intensity[device.driver_id] || 0.5));
    for (let index = 0; index < count; index += 1) {
      const [type, risk, , night] = pick(random, EXAMPLE_KINDS);
      const daysAgo = index < 2 && device.id <= 2 ? 0 : Math.floor(random() ** 1.6 * 30);
      const day = localDay(new Date(now - daysAgo * DAY));
      const hour = night && random() < 0.7 ? Math.floor(random() * 6) : 6 + Math.floor(random() * 17);
      const minute = Math.floor(random() * 60);
      let moment = Date.parse(`${day}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00-03:00`);
      if (moment > now - 5 * 60000) moment = now - (20 + Math.floor(random() * 240)) * 60000;
      const details = exampleDetails(type, random);
      let reviewStatus = "arquivado";
      let reviewedAt = null;
      let reviewer = null;
      let note = null;
      if (needsReview(type, risk)) {
        if (now - moment < 2.5 * DAY) {
          reviewStatus = "pendente";
        } else {
          const roll = random();
          reviewStatus = roll < 0.5 ? "confirmado" : roll < 0.7 ? "falso_alarme" : "orientado";
          reviewedAt = new Date(moment + (2 + random() * 20) * 3600000).toISOString();
          reviewer = 2;
          note = reviewStatus === "falso_alarme" ? NOTES[2] : NOTES[Math.floor(random() * NOTES.length)];
        }
      }
      const timestamp = new Date(moment).toISOString();
      alerts.push({
        id: 0, event_uid: uid(random), company_id: device.company_id, driver_id: device.driver_id, vehicle_id: device.vehicle_id,
        device_id: device.id, alert_type: type, risk_level: risk, duration: exampleDuration(type, details, random), details,
        timestamp, received_at: timestamp, review_status: reviewStatus, reviewed_by_user_id: reviewer, reviewed_at: reviewedAt,
        review_note: note,
      });
    }
  }
  alerts.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  alerts.forEach((alert, index) => {
    alert.id = index + 1;
  });
  return alerts;
}

function consent(id, driverId, kind, granted, channel, userId, moment) {
  return {
    id, driver_id: driverId, kind, granted, term_version: "2026-09", channel, recorded_at: new Date(moment).toISOString(),
    recorded_by_user_id: userId, note: "Dado de exemplo",
  };
}

function seed() {
  const random = mulberry32(20260910);
  const now = Date.now();
  const iso = (moment) => new Date(moment).toISOString();
  const created = iso(now - 60 * DAY);
  const companies = [
    { id: 1, name: "Transportadora Exemplo Norte", document: "00.000.000/0001-00", contact_name: "Gestor de exemplo", contact_phone: null, activation_policy: "local", active: true, created_at: created },
    { id: 2, name: "Transportadora Exemplo Sul", document: null, contact_name: null, contact_phone: null, activation_policy: "desligado", active: true, created_at: created },
  ];
  const drivers = [
    ["Ana Ribeiro", 1], ["Carlos Menezes", 1], ["Joana Prado", 1], ["Rafael Tavares", 1], ["Beatriz Lima", 2], ["Diego Souza", 2],
  ].map(([name, companyId], index) => ({
    id: index + 1, company_id: companyId, name, license_number: `EXEMPLO${String(index + 1).padStart(4, "0")}`, phone: null, created_at: created,
  }));
  const vehicles = [
    ["DMO1A01", "Volvo FH 540", "Caminhão", 1], ["DMO2B02", "Scania R 450", "Caminhão", 1], ["DMO3C03", "Mercedes-Benz O 500", "Ônibus", 1],
    ["DMO4D04", "DAF XF 530", "Caminhão", 1], ["SUL5E05", "Iveco S-Way", "Caminhão", 2], ["SUL6F06", "Marcopolo Paradiso", "Ônibus", 2],
  ].map(([plate, model, type, companyId], index) => ({ id: index + 1, company_id: companyId, plate, model, type, created_at: created }));
  const patterns = ["sonolento", "celular", "estavel", "desligado", "estavel", "desligado"];
  const devices = vehicles.map((vehicle, index) => ({
    id: index + 1, company_id: vehicle.company_id, name: `Cabine ${vehicle.plate}`, token_prefix: `dsk_ex${index + 1}`,
    vehicle_id: vehicle.id, driver_id: drivers[index].id, hostname: `raspberrypi-${index + 1}`, platform: "Linux aarch64 (simulado)",
    software_version: "0.3.0", camera_ok: true, pending_events: 0,
    last_seen_at: patterns[index] === "desligado" ? iso(now - (2 + index) * 3600000) : iso(now), created_at: created, revoked_at: null,
    live: null, status_at: null, simulated: patterns[index], trip_started_at: iso(now - (1.5 + random() * 4) * 3600000),
  }));
  const users = [
    { id: 1, name: "Equipe DriveSafe (teste)", email: "equipe@drivesafe.local", phone: null, role: "admin", company_id: null, driver_id: null },
    { id: 2, name: "Gestor de exemplo", email: "gestor@exemplo.local", phone: null, role: "gestor", company_id: 1, driver_id: null },
    { id: 3, name: "Ana Ribeiro", email: "ana@exemplo.local", phone: null, role: "motorista", company_id: 1, driver_id: 1 },
  ].map((user) => ({ ...user, active: true, must_change_password: false, created_at: created, last_login_at: null }));
  const consents = [
    consent(1, 1, "monitoramento", true, "termo_assinado", 2, now - 40 * DAY),
    consent(2, 1, "perfil_entre_viagens", true, "app_motorista", 3, now - 39 * DAY),
    consent(3, 2, "monitoramento", true, "termo_assinado", 2, now - 38 * DAY),
    consent(4, 3, "monitoramento", true, "termo_assinado", 2, now - 35 * DAY),
    consent(5, 5, "monitoramento", true, "admin", 1, now - 20 * DAY),
  ];
  const alerts = exampleAlerts(random, now, devices);
  return {
    version: 1,
    created_at: iso(now),
    settings: { simulate: true, simulateEvents: false },
    seq: { companies: 2, drivers: 6, vehicles: 6, devices: 6, users: 3, consents: 5, alerts: alerts.length, analyses: 0, audit: 0 },
    companies, drivers, vehicles, devices, users, consents, alerts, analyses: [], audit: [],
  };
}
