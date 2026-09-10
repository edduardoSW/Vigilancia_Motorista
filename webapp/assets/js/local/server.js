/* "Servidor" do modo de testes local: responde as mesmas rotas da API dentro do navegador, sem servidor e sem banco.
   As regras de acesso seguem o backend (backend/routes/*.py): gestor só vê a própria empresa, motorista só o que é dele. */
import { ApiError } from "../api.js";
import { localDay, localHour } from "../format.js";
import { ALERT_TYPE_LABELS, CATEGORIES, categoryOf, labelOf } from "./alert-types.js";
import { publish } from "./bus.js";
import { db, persist, resetToExample } from "./db.js";
import { checkPin } from "./pin.js";

const VERSION = "0.3.0 · modo local";
const TIME_ZONE = "America/Sao_Paulo";
const SESSION_KEY = "drivesafe-local-sessao";
const SESSION_TTL_MS = 12 * 3600000;
const ONLINE_MS = 180000;
const DAY = 86400000;
const MAX_FAILURES = 5;
const FAILURE_WINDOW_MS = 15 * 60000;
const CONSENT_KINDS = ["monitoramento", "perfil_entre_viagens", "sinais_ativacao_envio"];
const CHANNELS_BY_ROLE = { motorista: ["app_motorista"], gestor: ["termo_assinado"], admin: ["termo_assinado", "admin"] };
const REVIEW_DECISIONS = ["pendente", "confirmado", "falso_alarme", "orientado"];
const POLICIES = ["desligado", "local", "enviar"];
const RISK_NAMES = ["normal", "atencao", "alto", "critico"];
const failures = new Map();
const dayCache = new Map();

function fail(status, message) {
  throw new ApiError(status, message);
}

const nowIso = () => new Date().toISOString();

function find(table, id) {
  if (id === null || id === undefined || id === "") return null;
  return db()[table].find((row) => row.id === Number(id)) || null;
}

function ref(row, field = "name") {
  return row ? { id: row.id, name: row[field] } : null;
}

function toNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function dayOf(timestamp) {
  let day = dayCache.get(timestamp);
  if (!day) {
    day = localDay(timestamp);
    dayCache.set(timestamp, day);
  }
  return day;
}

// ---------- sessão e escopo ----------

function currentUser() {
  let session = null;
  try {
    session = JSON.parse(localStorage.getItem(SESSION_KEY) || "null");
  } catch {
    session = null;
  }
  if (!session || session.expires < Date.now()) return null;
  const user = find("users", session.userId);
  if (!user || !user.active) return null;
  if (user.role !== "admin" && !find("companies", user.company_id)?.active) return null;
  return user;
}

function requireUser(...roles) {
  const user = currentUser();
  if (!user) fail(401, "Sessão encerrada. Entre de novo.");
  if (roles.length && !roles.includes(user.role)) fail(403, "Seu perfil não tem acesso a esta área.");
  return user;
}

function scoped(user, requested) {
  if (user.role === "admin") return requested;
  if (requested !== null && requested !== user.company_id) fail(403, "Você só acessa dados da sua empresa.");
  return user.company_id;
}

function ensureCompany(user, companyId) {
  if (user.role !== "admin" && companyId !== user.company_id) fail(404, "Registro não encontrado.");
}

function ensureDriver(user, driver) {
  if (!driver) fail(404, "Motorista não encontrado.");
  ensureCompany(user, driver.company_id);
  if (user.role === "motorista" && user.driver_id !== driver.id) fail(404, "Motorista não encontrado.");
}

function audit(user, action, target, companyId = null) {
  const data = db();
  data.seq.audit = (data.seq.audit || 0) + 1;
  data.audit.push({ id: data.seq.audit, at: nowIso(), user_id: user?.id ?? null, company_id: companyId ?? user?.company_id ?? null, action, target });
  if (data.audit.length > 2000) data.audit.splice(0, data.audit.length - 2000);
}

function nextId(table) {
  const data = db();
  data.seq[table] = (data.seq[table] || 0) + 1;
  return data.seq[table];
}

// ---------- celular (mesma regra de backend/identifiers.py) ----------

function normalizePhone(raw) {
  if (!raw) return null;
  const text = String(raw).trim();
  let digits = text.replace(/\D/g, "");
  if (!text.startsWith("+")) {
    digits = digits.replace(/^0+/, "");
    if (digits.length === 10 || digits.length === 11) digits = `55${digits}`;
  }
  return digits.length >= 10 && digits.length <= 15 ? digits : null;
}

function formatPhone(digits) {
  if (!digits) return null;
  if (digits.startsWith("55") && (digits.length === 12 || digits.length === 13)) {
    const number = digits.slice(4);
    return `+55 (${digits.slice(2, 4)}) ${number.slice(0, -4)}-${number.slice(-4)}`;
  }
  return `+${digits}`;
}

// ---------- respostas no formato da API ----------

function isOnline(device, now = Date.now()) {
  return !device.revoked_at && Boolean(device.last_seen_at) && now - Date.parse(device.last_seen_at) <= ONLINE_MS;
}

export function deviceOut(device) {
  return {
    id: device.id, name: device.name, token_prefix: device.token_prefix,
    company: ref(find("companies", device.company_id)), vehicle: ref(find("vehicles", device.vehicle_id), "plate"),
    driver: ref(find("drivers", device.driver_id)), hostname: device.hostname, platform: device.platform,
    software_version: device.software_version, camera_ok: device.camera_ok, pending_events: device.pending_events || 0,
    last_seen_at: device.last_seen_at, online: isOnline(device), revoked: Boolean(device.revoked_at),
    created_at: device.created_at, live: device.live || null, status_at: device.status_at,
  };
}

export function alertOut(alert) {
  return {
    id: alert.id, alert_type: alert.alert_type, label: labelOf(alert.alert_type), category: categoryOf(alert.alert_type),
    risk_level: alert.risk_level || 0, duration: alert.duration || 0, details: alert.details || null,
    timestamp: alert.timestamp, received_at: alert.received_at, company: ref(find("companies", alert.company_id)),
    driver: ref(find("drivers", alert.driver_id)), vehicle: ref(find("vehicles", alert.vehicle_id), "plate"),
    device: ref(find("devices", alert.device_id)), review_status: alert.review_status || "pendente",
    reviewed_by: find("users", alert.reviewed_by_user_id)?.name || null, reviewed_at: alert.reviewed_at, review_note: alert.review_note,
  };
}

function meOut(user) {
  return {
    id: user.id, name: user.name, email: user.email, phone: formatPhone(user.phone), role: user.role,
    company: ref(find("companies", user.company_id)), driver_id: user.driver_id, must_change_password: false,
  };
}

function userOut(user) {
  return {
    id: user.id, name: user.name, email: user.email, phone: formatPhone(user.phone), role: user.role,
    company: ref(find("companies", user.company_id)), driver: ref(find("drivers", user.driver_id)), active: user.active,
    must_change_password: false, created_at: user.created_at, last_login_at: user.last_login_at,
  };
}

function companyOut(company) {
  const data = db();
  const count = (table, extra = () => true) => data[table].filter((row) => row.company_id === company.id && extra(row)).length;
  return {
    id: company.id, name: company.name, document: company.document, contact_name: company.contact_name,
    contact_phone: formatPhone(company.contact_phone), activation_policy: company.activation_policy, active: company.active,
    created_at: company.created_at, drivers: count("drivers"), vehicles: count("vehicles"),
    devices: count("devices", (device) => !device.revoked_at), users: count("users"),
  };
}

function vehicleOut(vehicle) {
  return { id: vehicle.id, plate: vehicle.plate, model: vehicle.model, type: vehicle.type, company: ref(find("companies", vehicle.company_id)), created_at: vehicle.created_at };
}

function consentOut(consent) {
  return {
    id: consent.id, kind: consent.kind, granted: consent.granted, term_version: consent.term_version, channel: consent.channel,
    recorded_at: consent.recorded_at, recorded_by: find("users", consent.recorded_by_user_id)?.name || null, note: consent.note,
  };
}

// ---------- consultas ----------

function queryAlerts({ companyId = null, driverId = null, deviceId = null, vehicleId = null, start = null, end = null,
  alertType = null, category = null, reviewStatus = null, includeSystem = true } = {}) {
  return db().alerts.filter((alert) => {
    if (companyId !== null && alert.company_id !== companyId) return false;
    if (driverId !== null && alert.driver_id !== driverId) return false;
    if (deviceId !== null && alert.device_id !== deviceId) return false;
    if (vehicleId !== null && alert.vehicle_id !== vehicleId) return false;
    if (alertType && alert.alert_type !== alertType) return false;
    if (reviewStatus && alert.review_status !== reviewStatus) return false;
    const alertCategory = categoryOf(alert.alert_type);
    if (category && alertCategory !== category) return false;
    if (!includeSystem && alertCategory === "sistema") return false;
    if (start && dayOf(alert.timestamp) < start) return false;
    if (end && dayOf(alert.timestamp) > end) return false;
    return true;
  }).sort((a, b) => b.timestamp.localeCompare(a.timestamp) || b.id - a.id);
}

function latestConsents(driverId) {
  const result = {};
  const rows = db().consents.filter((consent) => consent.driver_id === driverId)
    .sort((a, b) => a.recorded_at.localeCompare(b.recorded_at) || a.id - b.id);
  for (const consent of rows) result[consent.kind] = consent.granted;
  return result;
}

function driverOut(driver) {
  const data = db();
  const now = Date.now();
  const stats = { alerts_7d: 0, alerts_30d: 0, worst_risk_7d: 0, categories_7d: {}, last_alert_at: null };
  for (const alert of data.alerts) {
    if (alert.driver_id !== driver.id) continue;
    const category = categoryOf(alert.alert_type);
    const age = now - Date.parse(alert.timestamp);
    if (category === "sistema" || age > 30 * DAY) continue;
    stats.alerts_30d += 1;
    if (age <= 7 * DAY) {
      stats.alerts_7d += 1;
      stats.worst_risk_7d = Math.max(stats.worst_risk_7d, alert.risk_level || 0);
      stats.categories_7d[category] = (stats.categories_7d[category] || 0) + 1;
    }
    if (!stats.last_alert_at || alert.timestamp > stats.last_alert_at) stats.last_alert_at = alert.timestamp;
  }
  const device = data.devices.find((row) => row.driver_id === driver.id && !row.revoked_at && row.vehicle_id);
  return {
    id: driver.id, name: driver.name, license_number: driver.license_number, phone: driver.phone,
    company: ref(find("companies", driver.company_id)), created_at: driver.created_at, ...stats,
    consents: latestConsents(driver.id), vehicle: device ? ref(find("vehicles", device.vehicle_id), "plate") : null,
    has_login: data.users.some((user) => user.driver_id === driver.id),
  };
}

function trend(driverId, days = 30) {
  const buckets = new Map();
  for (let index = days - 1; index >= 0; index -= 1) {
    const day = localDay(new Date(Date.now() - index * DAY));
    buckets.set(day, { day, drowsiness: 0, phone: 0, other: 0, worst_risk: 0 });
  }
  for (const alert of db().alerts) {
    if (alert.driver_id !== driverId) continue;
    const bucket = buckets.get(dayOf(alert.timestamp));
    const category = categoryOf(alert.alert_type);
    if (!bucket || category === "sistema") continue;
    if (category === "sonolencia") bucket.drowsiness += 1;
    else if (category === "celular") bucket.phone += 1;
    else bucket.other += 1;
    bucket.worst_risk = Math.max(bucket.worst_risk, alert.risk_level || 0);
  }
  return [...buckets.values()];
}

function riskByHour(alerts) {
  const hours = Array(24).fill(0);
  for (const alert of alerts) {
    if (categoryOf(alert.alert_type) === "sistema") continue;
    const hour = localHour(alert.timestamp);
    hours[hour] = Math.max(hours[hour], alert.risk_level || 0);
  }
  return hours;
}

// ---------- rotas ----------

const ROUTES = [];

function on(method, pattern, handler) {
  const keys = [];
  const regex = new RegExp(`^${pattern.replace(/:(\w+)/g, (_, key) => {
    keys.push(key);
    return "([^/]+)";
  })}$`);
  ROUTES.push({ method, regex, keys, handler });
}

export async function handle(method, path, body) {
  const url = new URL(path, location.origin);
  for (const route of ROUTES) {
    if (route.method !== method) continue;
    const match = route.regex.exec(url.pathname);
    if (!match) continue;
    const params = Object.fromEntries(route.keys.map((key, index) => [key, decodeURIComponent(match[index + 1])]));
    const result = await route.handler({ params, query: url.searchParams, body: body || {} });
    return result === undefined ? null : result;
  }
  fail(404, "Esta função ainda não existe no modo de teste local.");
  return null;
}

on("GET", "/api/app-info", () => ({ version: VERSION, timezone: TIME_ZONE, self_signup: false, contact: null }));

on("POST", "/api/auth/login", async ({ body }) => {
  const identifier = String(body.login || "").trim().toLowerCase();
  const recent = (failures.get(identifier) || []).filter((moment) => Date.now() - moment < FAILURE_WINDOW_MS);
  if (recent.length >= MAX_FAILURES) {
    fail(429, `Muitas tentativas erradas. Tente de novo em ${Math.max(1, Math.ceil((recent[0] + FAILURE_WINDOW_MS - Date.now()) / 60000))} min.`);
  }
  const phone = normalizePhone(identifier);
  const user = db().users.find((row) => (row.email && row.email.toLowerCase() === identifier) || (phone && row.phone === phone));
  const pinOk = await checkPin(String(body.password || ""));
  const companyOk = user && (user.role === "admin" || find("companies", user.company_id)?.active);
  if (!user || !pinOk || !user.active || !companyOk) {
    recent.push(Date.now());
    failures.set(identifier, recent);
    fail(401, "Conta ou PIN incorretos.");
  }
  failures.delete(identifier);
  localStorage.setItem(SESSION_KEY, JSON.stringify({ userId: user.id, expires: Date.now() + SESSION_TTL_MS }));
  user.last_login_at = nowIso();
  audit(user, "login", user.email || user.phone);
  persist();
  return meOut(user);
});

on("POST", "/api/auth/logout", () => {
  localStorage.removeItem(SESSION_KEY);
  stopSimulation();
});

on("GET", "/api/auth/me", () => meOut(requireUser()));

on("POST", "/api/auth/password", () => {
  requireUser();
  fail(400, "No modo de teste local a entrada é pelo PIN: não há senha para trocar.");
});

on("GET", "/api/alert-types", () => {
  requireUser();
  return {
    types: Object.fromEntries(Object.entries(ALERT_TYPE_LABELS).map(([type, label]) => [type, { label, category: categoryOf(type) }])),
    categories: Object.keys(CATEGORIES).sort(),
  };
});

on("GET", "/api/overview", ({ query }) => {
  const user = requireUser("admin", "gestor");
  const scope = scoped(user, toNumber(query.get("company_id")));
  const data = db();
  const devices = data.devices.filter((device) => !device.revoked_at && (scope === null || device.company_id === scope));
  const now = { normal: 0, attention: 0, high: 0, critical: 0, no_signal: 0 };
  for (const device of devices) {
    const level = device.live?.risk_level;
    if (!isOnline(device) || level === null || level === undefined) now.no_signal += 1;
    else now[["normal", "attention", "high", "critical"][Math.max(0, Math.min(3, level))]] += 1;
  }
  const today = queryAlerts({ companyId: scope, start: localDay(), includeSystem: false });
  const drivers = data.drivers.filter((driver) => scope === null || driver.company_id === scope).map(driverOut)
    .filter((driver) => driver.alerts_7d)
    .sort((a, b) => b.worst_risk_7d - a.worst_risk_7d || b.alerts_7d - a.alerts_7d).slice(0, 5);
  return {
    now,
    devices_online: devices.filter((device) => isOnline(device)).length,
    devices_total: devices.length,
    alerts_today: today.length,
    critical_today: today.filter((alert) => alert.risk_level >= 3).length,
    to_review: queryAlerts({ companyId: scope, reviewStatus: "pendente" }).length,
    drivers_attention: drivers.map((driver) => {
      const categories = Object.entries(driver.categories_7d).sort((a, b) => b[1] - a[1]);
      return { driver: { id: driver.id, name: driver.name }, alerts_7d: driver.alerts_7d, worst_risk: driver.worst_risk_7d, top_category: categories[0]?.[0] || null };
    }),
    latest_alerts: queryAlerts({ companyId: scope, includeSystem: false }).slice(0, 8).map(alertOut),
  };
});

on("GET", "/api/fleet", ({ query }) => {
  const user = requireUser("admin", "gestor");
  const scope = scoped(user, toNumber(query.get("company_id")));
  const today = localDay();
  return db().devices.filter((device) => !device.revoked_at && (scope === null || device.company_id === scope)).map((device) => {
    const alerts = queryAlerts({ deviceId: device.id, start: today });
    return { device: deviceOut(device), alerts_today: alerts.filter((alert) => categoryOf(alert.alert_type) !== "sistema").length, risk_hours_today: riskByHour(alerts) };
  }).sort((a, b) => Number(b.device.online) - Number(a.device.online)
    || (b.device.live?.risk_level || 0) - (a.device.live?.risk_level || 0) || a.device.name.localeCompare(b.device.name));
});

function alertFilters(user, query) {
  const filters = {
    companyId: scoped(user, toNumber(query.get("company_id"))), driverId: toNumber(query.get("driver_id")),
    deviceId: toNumber(query.get("device_id")), vehicleId: toNumber(query.get("vehicle_id")), start: query.get("start") || null,
    end: query.get("end") || null, alertType: query.get("alert_type") || null, category: query.get("category") || null,
    reviewStatus: query.get("review_status") || null,
  };
  if (user.role === "motorista") filters.driverId = user.driver_id;
  return filters;
}

on("GET", "/api/alerts", ({ query }) => {
  const user = requireUser();
  const rows = queryAlerts(alertFilters(user, query));
  const skip = toNumber(query.get("skip")) || 0;
  const limit = Math.min(500, toNumber(query.get("limit")) || 50);
  return { items: rows.slice(skip, skip + limit).map(alertOut), total: rows.length };
});

on("PATCH", "/api/alerts/:id/review", ({ params, body }) => {
  const user = requireUser("admin", "gestor");
  const alert = find("alerts", params.id);
  if (!alert) fail(404, "Alerta não encontrado.");
  ensureCompany(user, alert.company_id);
  if (!REVIEW_DECISIONS.includes(body.status)) fail(400, "Decisão desconhecida.");
  alert.review_status = body.status;
  alert.review_note = String(body.note || "").trim() || null;
  alert.reviewed_by_user_id = body.status === "pendente" ? null : user.id;
  alert.reviewed_at = body.status === "pendente" ? null : nowIso();
  audit(user, "alerta_revisado", `alerta:${alert.id}`, alert.company_id);
  persist();
  const out = alertOut(alert);
  publish("alert_review", out);
  return out;
});

on("GET", "/api/drivers", ({ query }) => {
  const user = requireUser();
  const search = (query.get("search") || "").trim().toLowerCase();
  let rows = db().drivers;
  if (user.role === "motorista") rows = rows.filter((driver) => driver.id === user.driver_id);
  else {
    const scope = scoped(user, toNumber(query.get("company_id")));
    if (scope !== null) rows = rows.filter((driver) => driver.company_id === scope);
  }
  if (search) rows = rows.filter((driver) => driver.name.toLowerCase().includes(search) || (driver.license_number || "").toLowerCase().includes(search));
  return rows.slice().sort((a, b) => a.name.localeCompare(b.name)).map(driverOut);
});

on("GET", "/api/drivers/:id", ({ params }) => {
  const user = requireUser();
  const driver = find("drivers", params.id);
  ensureDriver(user, driver);
  const history = db().consents.filter((consent) => consent.driver_id === driver.id)
    .sort((a, b) => b.recorded_at.localeCompare(a.recorded_at) || b.id - a.id).map(consentOut);
  const devices = db().devices.filter((device) => device.driver_id === driver.id && !device.revoked_at).map((device) => ref(device));
  return { ...driverOut(driver), trend: trend(driver.id, 30), consent_history: history, devices };
});

on("GET", "/api/drivers/:id/day", ({ params, query }) => {
  const user = requireUser();
  const driver = find("drivers", params.id);
  ensureDriver(user, driver);
  const day = query.get("day") || localDay();
  const alerts = queryAlerts({ driverId: driver.id, start: day, end: day });
  return { day, hours: riskByHour(alerts), alerts: alerts.map(alertOut) };
});

on("POST", "/api/drivers/:id/consents", ({ params, body }) => {
  const user = requireUser();
  const driver = find("drivers", params.id);
  ensureDriver(user, driver);
  if (!CONSENT_KINDS.includes(body.kind)) fail(400, "Tipo de autorização desconhecido.");
  if (!CHANNELS_BY_ROLE[user.role].includes(body.channel)) fail(400, "Este canal de registro não vale para o seu perfil.");
  const consent = {
    id: nextId("consents"), driver_id: driver.id, kind: body.kind, granted: Boolean(body.granted), term_version: "2026-09",
    channel: body.channel, recorded_at: nowIso(), recorded_by_user_id: user.id, note: String(body.note || "").trim() || null,
  };
  db().consents.push(consent);
  audit(user, "consentimento_registrado", `motorista:${driver.id}`, driver.company_id);
  persist();
  return consentOut(consent);
});

on("GET", "/api/vehicles", ({ query }) => {
  const user = requireUser("admin", "gestor");
  const scope = scoped(user, toNumber(query.get("company_id")));
  return db().vehicles.filter((vehicle) => scope === null || vehicle.company_id === scope)
    .sort((a, b) => a.plate.localeCompare(b.plate)).map(vehicleOut);
});

on("GET", "/api/devices", ({ query }) => {
  const user = requireUser("admin", "gestor");
  const scope = scoped(user, toNumber(query.get("company_id")));
  return db().devices.filter((device) => scope === null || device.company_id === scope)
    .sort((a, b) => a.name.localeCompare(b.name)).map(deviceOut);
});

on("GET", "/api/companies", () => {
  const user = requireUser("admin", "gestor");
  return db().companies.filter((company) => user.role === "admin" || company.id === user.company_id)
    .sort((a, b) => a.name.localeCompare(b.name)).map(companyOut);
});

on("PATCH", "/api/companies/:id", ({ params, body }) => {
  const user = requireUser("admin", "gestor");
  const company = find("companies", params.id);
  if (!company) fail(404, "Empresa não encontrada.");
  ensureCompany(user, company.id);
  const fields = Object.keys(body);
  if (user.role !== "admin" && fields.some((field) => field !== "activation_policy")) fail(403, "Só a equipe DriveSafe altera os dados cadastrais da empresa.");
  if (body.activation_policy !== undefined && !POLICIES.includes(body.activation_policy)) fail(400, "Política desconhecida.");
  for (const field of ["name", "document", "contact_name", "activation_policy", "active"]) {
    if (body[field] !== undefined) company[field] = typeof body[field] === "string" ? body[field].trim() || null : body[field];
  }
  if (body.contact_phone !== undefined) company.contact_phone = normalizePhone(body.contact_phone);
  audit(user, "empresa_alterada", company.name, company.id);
  persist();
  return companyOut(company);
});

on("GET", "/api/users", ({ query }) => {
  const user = requireUser("admin", "gestor");
  const scope = scoped(user, toNumber(query.get("company_id")));
  return db().users.filter((row) => scope === null || row.company_id === scope)
    .sort((a, b) => a.name.localeCompare(b.name)).map(userOut);
});

on("PATCH", "/api/users/:id", ({ params, body }) => {
  const user = requireUser("admin", "gestor");
  const target = find("users", params.id);
  if (!target || (user.role !== "admin" && (target.role === "admin" || target.company_id !== user.company_id))) fail(404, "Usuário não encontrado.");
  const fields = Object.keys(body);
  if (user.role !== "admin" && (fields.length !== 1 || body.active !== false)) fail(403, "Para criar, reativar ou alterar um acesso, fale com a equipe DriveSafe pelo celular.");
  if (target.id === user.id && body.active === false) fail(400, "Você não pode bloquear o próprio acesso.");
  if (body.name) target.name = String(body.name).trim();
  if (typeof body.active === "boolean") target.active = body.active;
  audit(user, "usuario_alterado", target.email || target.phone, target.company_id);
  persist();
  return { user: userOut(target), temporary_password: null };
});

// ---------- arquivos (CSV e exportação LGPD) ----------

function csvCell(value) {
  let text = value === null || value === undefined ? "" : String(value);
  if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`;
  return /[;"\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

export async function file(path) {
  const url = new URL(path, location.origin);
  const user = requireUser();
  if (url.pathname === "/api/alerts/export.csv") {
    if (user.role === "motorista") fail(403, "Seu perfil não tem acesso a esta área.");
    const header = ["ID", `Data e hora (${TIME_ZONE})`, "Data e hora (UTC)", "Tipo de alerta", "Nível de risco", "Duração (s)", "Empresa", "Motorista", "CNH", "Veículo (placa)", "Dispositivo", "Revisão", "Revisado por", "Nota da revisão", "Detalhes", "ID do evento"];
    const lines = [header.map(csvCell).join(";")];
    for (const alert of queryAlerts(alertFilters(user, url.searchParams)).slice(0, 50000)) {
      const out = alertOut(alert);
      const driver = find("drivers", alert.driver_id);
      const local = new Intl.DateTimeFormat("pt-BR", { timeZone: TIME_ZONE, dateStyle: "short", timeStyle: "medium" }).format(new Date(alert.timestamp));
      lines.push([
        alert.id, local, alert.timestamp.replace("T", " ").slice(0, 19), out.label, alert.risk_level,
        (alert.duration || 0).toFixed(2).replace(".", ","), out.company?.name, driver?.name, driver?.license_number,
        out.vehicle?.name, out.device?.name, out.review_status, out.reviewed_by, alert.review_note,
        alert.details ? JSON.stringify(alert.details) : "", alert.event_uid,
      ].map(csvCell).join(";"));
    }
    audit(user, "alertas_exportados", `${lines.length - 1} linhas`);
    persist();
    return { blob: new Blob([`﻿${lines.join("\r\n")}`], { type: "text/csv;charset=utf-8" }), filename: `drivesafe-alertas-${localDay()}.csv` };
  }
  const exportMatch = /^\/api\/drivers\/(\d+)\/export$/.exec(url.pathname);
  if (exportMatch) {
    const driver = find("drivers", exportMatch[1]);
    ensureDriver(user, driver);
    const payload = {
      gerado_em: nowIso(), modo: "teste local (dados de exemplo)",
      motorista: { id: driver.id, nome: driver.name, cnh: driver.license_number, telefone: driver.phone, empresa: find("companies", driver.company_id)?.name || null },
      consentimentos: db().consents.filter((consent) => consent.driver_id === driver.id).map(consentOut),
      alertas: queryAlerts({ driverId: driver.id }).map(alertOut),
      observacao: "O DriveSafe não grava nem envia imagens: só métricas e eventos.",
    };
    audit(user, "dados_exportados", `motorista:${driver.id}`, driver.company_id);
    persist();
    return { blob: new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }), filename: `drivesafe-dados-motorista-${driver.id}.json` };
  }
  fail(404, "Arquivo não encontrado.");
  return null;
}

// ---------- frota simulada e ajustes do modo local ----------

let simulationTimer = null;

function simulateTick() {
  const user = currentUser();
  if (!user || user.role === "motorista") return;
  const data = db();
  if (!data.settings.simulate) return;
  const now = Date.now();
  const minutes = now / 60000;
  for (const device of data.devices) {
    if (!device.simulated || device.simulated === "desligado" || device.revoked_at) continue;
    const drivingHours = (((now - Date.parse(device.trip_started_at)) / 3600000) % 8);
    const wave = Math.sin(minutes / 3 + device.id);
    const live = {
      risk_level: 0, reasons: [], calibrating: false, calibration_progress: 1, face_found: true, eyes_visible: true,
      eyes_reason: null, phone_state: "sem_celular", fps: Number((24 + wave).toFixed(1)), latency_p95_ms: 38,
      driving_hours: Number(drivingHours.toFixed(2)), activation_mode: "local",
    };
    if (device.simulated === "sonolento") {
      live.risk_level = wave > 0.6 ? 2 : wave > 0.1 ? 1 : 0;
      if (live.risk_level) live.reasons = ["olhos_fechados_acima_do_normal"];
    } else if (device.simulated === "celular") {
      const phone = Math.sin(minutes * 1.7 + device.id) > 0.55;
      live.risk_level = phone ? 1 : 0;
      live.phone_state = phone ? "celular_na_mao" : "sem_celular";
      if (phone) live.reasons = ["celular_na_mao"];
    } else if (drivingHours < 0.1) {
      live.calibrating = true;
      live.calibration_progress = Number((drivingHours / 0.1).toFixed(2));
    }
    live.risk_name = RISK_NAMES[live.risk_level];
    device.live = live;
    device.last_seen_at = new Date(now).toISOString();
    device.status_at = device.last_seen_at;
    publish("device", deviceOut(device));
  }
  persist();
}

export function startSimulation() {
  if (simulationTimer) return;
  simulateTick();
  simulationTimer = setInterval(simulateTick, 15000);
}

export function stopSimulation() {
  clearInterval(simulationTimer);
  simulationTimer = null;
}

export function localSettings() {
  return { ...db().settings };
}

export function updateLocalSettings(patch) {
  Object.assign(db().settings, patch);
  persist();
}

export function resetLocalData() {
  resetToExample();
}

export function localAccounts() {
  return db().users.filter((user) => user.active).map((user) => ({
    id: user.id, name: user.name, role: user.role, company: find("companies", user.company_id)?.name || null,
    login: user.email || user.phone,
  }));
}
