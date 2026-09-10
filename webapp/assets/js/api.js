/* Conversa com o servidor. Toda alteração leva o cabeçalho de segurança do app (X-DriveSafe: 1).
   No modo local (config.js), as mesmas rotas são respondidas dentro do navegador por local/server.js. */
import { IS_LOCAL } from "./config.js";

let localModule = null;

export async function localServer() {
  if (!localModule) localModule = await import("./local/server.js");
  return localModule;
}

const FIELD_NAMES = {
  name: "nome", email: "e-mail", phone: "celular", login: "e-mail ou celular", password: "senha",
  new_password: "nova senha", current_password: "senha atual", license_number: "CNH", plate: "placa",
  model: "modelo", type: "tipo", company_id: "empresa", driver_id: "motorista", vehicle_id: "veículo",
  document: "CNPJ", contact_name: "responsável", contact_phone: "celular do responsável", note: "observação",
  camera: "câmera", calibration_min_s: "calibração mínima", calibration_max_s: "calibração máxima",
};

const OFFLINE_MESSAGE = "Sem conexão com o servidor. Confira a internet e tente de novo.";

export class ApiError extends Error {
  constructor(status, message, data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

const listeners = new Map();

/** "unauthorized" (sessão caiu) e "password-change" (senha temporária ainda não trocada). */
export function onApiEvent(kind, handler) {
  if (!listeners.has(kind)) listeners.set(kind, new Set());
  listeners.get(kind).add(handler);
  return () => listeners.get(kind).delete(handler);
}

function emit(kind, detail) {
  for (const handler of listeners.get(kind) || []) handler(detail);
}

function messageFor(status, data) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    const names = detail.map((item) => {
      const key = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
      return FIELD_NAMES[key] || key;
    });
    const fields = [...new Set(names.filter((name) => typeof name === "string"))];
    return fields.length ? `Confira: ${fields.join(", ")}.` : "Confira os dados preenchidos.";
  }
  const messages = {
    400: "Confira os dados preenchidos.",
    401: "Sessão encerrada. Entre de novo.",
    403: "Seu perfil não tem acesso a isso.",
    404: "Registro não encontrado.",
    409: "Já existe um registro com esses dados.",
    413: "Arquivo grande demais.",
    429: "Muitas tentativas. Aguarde um pouco.",
  };
  return messages[status] || `O servidor respondeu com erro (${status}). Tente de novo.`;
}

async function failure(response, path) {
  let data = null;
  if ((response.headers.get("content-type") || "").includes("application/json")) {
    data = await response.json().catch(() => null);
  }
  const error = new ApiError(response.status, messageFor(response.status, data), data);
  if (response.status === 401 && !path.startsWith("/api/auth/login")) emit("unauthorized", error);
  if (response.status === 403 && /senha temporária/i.test(error.message)) emit("password-change", error);
  return error;
}

export async function api(path, { method = "GET", body, signal } = {}) {
  if (IS_LOCAL) {
    const server = await localServer();
    try {
      const result = await server.handle(method, path, body);
      return result === null || result === undefined ? null : structuredClone(result);
    } catch (error) {
      if (error instanceof ApiError && error.status === 401 && !path.startsWith("/api/auth/login")) emit("unauthorized", error);
      throw error;
    }
  }
  const headers = { Accept: "application/json" };
  const init = { method, headers, credentials: "same-origin", cache: "no-store", signal };
  if (method !== "GET" && method !== "HEAD") headers["X-DriveSafe"] = "1";
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(0, OFFLINE_MESSAGE);
  }
  if (!response.ok) throw await failure(response, path);
  if (response.status === 204) return null;
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

/** Monta "?a=1&b=2" ignorando valores vazios. */
export function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

function filenameFrom(header) {
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header || "");
  return match ? decodeURIComponent(match[1]) : null;
}

/** Baixa um arquivo que exige sessão (CSV, exportação LGPD, resultados de análise). */
export function saveBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

export async function download(path, fallbackName = "arquivo") {
  if (IS_LOCAL) {
    const { blob, filename } = await (await localServer()).file(path);
    saveBlob(blob, filename || fallbackName);
    return;
  }
  let response;
  try {
    response = await fetch(path, { credentials: "same-origin", cache: "no-store" });
  } catch {
    throw new ApiError(0, OFFLINE_MESSAGE);
  }
  if (!response.ok) throw await failure(response, path);
  saveBlob(await response.blob(), filenameFrom(response.headers.get("content-disposition")) || fallbackName);
}

/** Envia um arquivo grande em PUT, com progresso (0 a 1). */
export function upload(path, file, onProgress) {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("PUT", path);
    request.withCredentials = true;
    request.setRequestHeader("X-DriveSafe", "1");
    request.setRequestHeader("Content-Type", "application/octet-stream");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(event.loaded / event.total);
    };
    request.onload = () => {
      let data = null;
      try {
        data = JSON.parse(request.responseText);
      } catch {
        data = null;
      }
      if (request.status >= 200 && request.status < 300) resolve(data);
      else {
        if (request.status === 401) emit("unauthorized");
        reject(new ApiError(request.status, messageFor(request.status, data), data));
      }
    };
    request.onerror = () => reject(new ApiError(0, "A conexão caiu durante o envio. Tente de novo."));
    request.send(file);
  });
}
