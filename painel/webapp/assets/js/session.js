/* Estado compartilhado: quem está logado, empresa escolhida pela equipe, tema e navegação. */
import { api, localServer } from "./api.js";
import { IS_LOCAL } from "./config.js";
import { live } from "./live.js";

export const session = {
  me: null,
  info: null,
  companies: [],
  alertTypes: null,
  installPrompt: null,
  redirectAfterLogin: null,
};

const hooks = { render: () => {}, resetShell: () => {}, companiesChanged: () => {} };

export function setHooks(values) {
  Object.assign(hooks, values);
}

export function home(role = session.me?.role) {
  return role === "motorista" ? "/meu-painel" : "/frota";
}

export function navigate(path, { replace = false } = {}) {
  const hash = `#${path}`;
  if (location.hash === hash) {
    hooks.render();
  } else if (replace) {
    history.replaceState(null, "", hash);
    hooks.render();
  } else {
    location.hash = hash;
  }
}

export function isManager() {
  return session.me?.role === "admin" || session.me?.role === "gestor";
}

/** Empresa que a equipe (admin) escolheu ver no topo. null = todas. Gestor e motorista não usam. */
export const scope = {
  get() {
    if (session.me?.role !== "admin") return null;
    let stored = null;
    try {
      stored = Number(localStorage.getItem("drivesafe-empresa")) || null;
    } catch {
      stored = null;
    }
    return session.companies.some((company) => company.id === stored) ? stored : null;
  },
  set(companyId) {
    try {
      if (companyId) localStorage.setItem("drivesafe-empresa", String(companyId));
      else localStorage.removeItem("drivesafe-empresa");
    } catch {
      // sem armazenamento local: a escolha vale só nesta tela
    }
  },
};

export async function loadCompanies() {
  if (session.me?.role !== "admin") return;
  session.companies = await api("/api/companies");
  hooks.companiesChanged();
}

export async function startSession(me) {
  session.me = me;
  if (me.must_change_password) return;
  try {
    await loadCompanies();
  } catch {
    session.companies = [];
  }
  live.start();
  if (IS_LOCAL && me.role !== "motorista") (await localServer()).startSimulation();
}

export async function endSession({ callServer = true } = {}) {
  if (callServer) {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch {
      // mesmo sem resposta do servidor, a tela sai da sessão
    }
  }
  session.me = null;
  session.companies = [];
  live.stop();
  hooks.resetShell();
  navigate("/entrar", { replace: true });
}

export async function alertTypes() {
  if (!session.alertTypes) session.alertTypes = await api("/api/alert-types");
  return session.alertTypes;
}

export function currentTheme() {
  return document.documentElement.getAttribute("data-theme") === "light" ? "dia" : "noite";
}

export function setTheme(name) {
  document.documentElement.setAttribute("data-theme", name === "dia" ? "light" : "dark");
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", name === "dia" ? "#f1ece2" : "#14110f");
  try {
    localStorage.setItem("drivesafe-tema", name);
  } catch {
    // tema vale só nesta aba
  }
}

/** Empresa para um cadastro novo: a do gestor, ou a escolhida pela equipe no topo. */
export function companyForNewRecord() {
  if (session.me?.role === "gestor") return session.me.company?.id ?? null;
  return scope.get();
}
