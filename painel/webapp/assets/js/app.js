/* DriveSafe AI — casca do app instalável: rotas por perfil, menu, sessão e tempo real. */
import { api, onApiEvent, query } from "./api.js";
import { errorBlock, h, icon, loadingBlock, mount, openDialog, s, toast } from "./dom.js";
import { LIVE_TEXT, ROLE_LABELS, initials, setTimeZone } from "./format.js";
import { live } from "./live.js";
import {
  currentTheme, endSession, home, navigate, scope, session, setHooks, setTheme, startSession,
} from "./session.js";

const MODULES = {
  login: () => import("./views/login.js"),
  password: () => import("./views/password.js"),
  fleet: () => import("./views/fleet.js"),
  review: () => import("./views/review.js"),
  drivers: () => import("./views/drivers.js"),
  driver: () => import("./views/driver.js"),
  reports: () => import("./views/reports.js"),
  vehicles: () => import("./views/vehicles.js"),
  devices: () => import("./views/devices.js"),
  company: () => import("./views/company.js"),
  companies: () => import("./views/companies.js"),
  users: () => import("./views/users.js"),
  testmode: () => import("./views/testmode.js"),
  analyses: () => import("./views/analyses.js"),
  mypanel: () => import("./views/mypanel.js"),
  consents: () => import("./views/consents.js"),
  account: () => import("./views/account.js"),
};

const ALL = ["admin", "gestor", "motorista"];
const MANAGERS = ["admin", "gestor"];

const ROUTES = [
  { path: "/entrar", module: "login", public: true, title: "Entrar" },
  { path: "/trocar-senha", module: "password", bare: true, roles: ALL, title: "Trocar a senha" },
  { path: "/frota", module: "fleet", roles: MANAGERS, title: "Frota", icon: "truck", group: "Estrada", tab: 1 },
  { path: "/revisar", module: "review", roles: MANAGERS, title: "Revisar", icon: "inbox", group: "Estrada", tab: 2, badge: true },
  { path: "/motoristas", module: "drivers", roles: MANAGERS, title: "Motoristas", icon: "wheel", group: "Estrada", tab: 3 },
  { path: "/motoristas/:id", module: "driver", roles: MANAGERS, title: "Motorista", parent: "/motoristas" },
  { path: "/relatorios", module: "reports", roles: MANAGERS, title: "Relatórios", icon: "sheet", group: "Estrada" },
  { path: "/veiculos", module: "vehicles", roles: MANAGERS, title: "Veículos", icon: "bus", group: "Cadastro" },
  { path: "/dispositivos", module: "devices", roles: MANAGERS, title: "Dispositivos", icon: "chip", group: "Cadastro" },
  { path: "/empresa", module: "company", roles: ["gestor"], title: "Minha empresa", icon: "building", group: "Cadastro" },
  { path: "/empresas", module: "companies", roles: ["admin"], title: "Empresas", icon: "building", group: "Equipe" },
  { path: "/usuarios", module: "users", roles: ["admin"], title: "Acessos", icon: "users", group: "Equipe" },
  { path: "/teste", module: "testmode", roles: ["admin"], title: "Modo teste", icon: "eye", group: "Equipe", tab: 4 },
  { path: "/analises", module: "analyses", roles: ["admin"], title: "Análise de vídeo", icon: "film", group: "Equipe" },
  { path: "/meu-painel", module: "mypanel", roles: ["motorista"], title: "Meu painel", icon: "gauge", group: "Você", tab: 1 },
  { path: "/consentimentos", module: "consents", roles: ["motorista"], title: "Autorizações", icon: "shield", group: "Você", tab: 2 },
  { path: "/conta", module: "account", roles: ALL, title: "Conta", icon: "user", group: "Você", tab: 5 },
];

const COMPILED = ROUTES.map((route) => {
  const names = [];
  const source = route.path.replace(/:([a-z]+)/g, (_, name) => {
    names.push(name);
    return "([^/]+)";
  });
  return { route, names, pattern: new RegExp(`^${source}/?$`) };
});

const app = document.getElementById("app");
let shell = null;
let current = null;
let renderId = 0;
let badgeTimer = null;

function match(hash) {
  const raw = hash.replace(/^#/, "");
  const [pathPart, search = ""] = raw.split("?");
  const path = pathPart || "/";
  for (const { route, names, pattern } of COMPILED) {
    const found = pattern.exec(path);
    if (!found) continue;
    const params = {};
    names.forEach((name, index) => {
      params[name] = decodeURIComponent(found[index + 1]);
    });
    return { route, params, query: new URLSearchParams(search), path, full: raw };
  }
  return null;
}

function createContext(matched) {
  const controller = new AbortController();
  const cleanups = [];
  const me = session.me;
  return {
    params: matched.params,
    query: matched.query,
    path: matched.path,
    signal: controller.signal,
    me,
    role: me?.role,
    scopeId: me?.role === "admin" ? scope.get() : null,
    titleSet: false,
    title(text) {
      this.titleSet = true;
      document.title = `${text} · DriveSafe AI`;
    },
    onLive(type, handler) {
      cleanups.push(live.on(type, handler));
    },
    every(ms, handler) {
      const id = setInterval(handler, ms);
      cleanups.push(() => clearInterval(id));
    },
    listen(target, type, handler, options) {
      target.addEventListener(type, handler, options);
      cleanups.push(() => target.removeEventListener(type, handler, options));
    },
    onCleanup(handler) {
      cleanups.push(handler);
    },
    refreshBadges: () => scheduleBadges(0),
    rerender: () => render(),
    get alive() {
      return !controller.signal.aborted;
    },
    destroy() {
      controller.abort();
      for (const handler of cleanups.splice(0)) {
        try {
          handler();
        } catch (error) {
          console.error(error);
        }
      }
    },
  };
}

async function render() {
  const id = ++renderId;
  if (location.hash === "#main") return;
  const matched = match(location.hash);
  const me = session.me;

  if (!me) {
    if (!matched || !matched.route.public) {
      if (matched && matched.path !== "/") session.redirectAfterLogin = matched.full;
      navigate("/entrar", { replace: true });
      return;
    }
  } else if (me.must_change_password) {
    if (!matched || matched.route.module !== "password") {
      navigate("/trocar-senha", { replace: true });
      return;
    }
  } else if (!matched || matched.route.public || matched.route.bare || !matched.route.roles.includes(me.role)) {
    navigate(home(), { replace: true });
    return;
  }

  if (current) current.destroy();
  const context = createContext(matched);
  current = context;

  let target;
  if (matched.route.public || matched.route.bare) {
    shell = null;
    target = app;
  } else {
    ensureShell();
    updateNav(matched.route);
    target = shell.main;
  }
  mount(target, loadingBlock());

  try {
    const module = await MODULES[matched.route.module]();
    if (id !== renderId) return;
    const view = await module.default(context);
    if (id !== renderId || !context.alive) return;
    mount(target, view);
    if (!context.titleSet) context.title(matched.route.title);
    const heading = target.querySelector(".page-title");
    if (heading && shell) heading.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  } catch (error) {
    if (id !== renderId || error.name === "AbortError") return;
    if (error.status === 401) return;
    mount(target, errorBlock(error, () => render()));
  }
}

// ---------- casca: menu lateral, topo e abas no celular ----------

function brandMark() {
  return s("svg", { viewBox: "0 0 32 32", class: "brand-mark", "aria-hidden": "true" },
    s("path", { d: "M16 1.8 30.2 16 16 30.2 1.8 16z", class: "brand-sign" }),
    s("path", { d: "M9.6 15.2q6.4 5.8 12.8 0", class: "brand-lid" }));
}

function themeToggle() {
  const button = h("button", { type: "button", class: "icon-btn" });
  const paint = () => {
    const day = currentTheme() === "dia";
    const label = day ? "Usar o tema da noite" : "Usar o tema do dia";
    button.replaceChildren(icon(day ? "moon" : "sun"));
    button.setAttribute("aria-label", label);
    button.title = label;
  };
  button.addEventListener("click", () => {
    setTheme(currentTheme() === "dia" ? "noite" : "dia");
    paint();
  });
  paint();
  return button;
}

function scopeControl() {
  const select = h("select", { class: "input input-compact", "aria-label": "Empresa exibida" });
  const fill = () => {
    select.replaceChildren(
      h("option", { value: "" }, "Todas as empresas"),
      ...session.companies.map((company) => h("option", { value: String(company.id) }, company.name)),
    );
    const selected = scope.get();
    select.value = selected ? String(selected) : "";
  };
  fill();
  select.addEventListener("change", () => {
    scope.set(select.value ? Number(select.value) : null);
    scheduleBadges(0);
    render();
  });
  return { element: h("div", { class: "scope" }, icon("building", { size: 18 }), select), fill };
}

function openMore(routes) {
  let ref = null;
  const list = h("nav", { class: "more-list", "aria-label": "Mais opções" },
    routes.map((route) => h("a", { class: "more-link", href: `#${route.path}`, on: { click: () => ref && ref.close() } },
      icon(route.icon), h("span", null, route.title), icon("chevron", { size: 16 }))));
  ref = openDialog({ title: "Mais opções", body: list });
}

function installButton() {
  const button = h("button", {
    type: "button", class: "btn btn-small btn-install", hidden: !session.installPrompt,
    on: {
      click: async () => {
        const prompt = session.installPrompt;
        if (!prompt) return;
        prompt.prompt();
        await prompt.userChoice.catch(() => null);
        session.installPrompt = null;
        button.hidden = true;
      },
    },
  }, icon("install", { size: 16 }), h("span", null, "Instalar o app"));
  return button;
}

function ensureShell() {
  if (shell && app.contains(shell.root)) return;
  const me = session.me;
  const routes = ROUTES.filter((route) => route.icon && route.roles.includes(me.role));
  const links = new Map();
  const badges = [];
  const register = (path, element) => {
    if (!links.has(path)) links.set(path, []);
    links.get(path).push(element);
  };
  const badgeFor = (route) => {
    if (!route.badge) return null;
    const badge = h("span", { class: "nav-badge", hidden: true });
    badges.push(badge);
    return badge;
  };

  const groups = [...new Set(routes.map((route) => route.group))];
  const install = installButton();
  const rail = h("nav", { class: "rail", "aria-label": "Menu principal" },
    h("a", { class: "brand", href: `#${home()}` }, brandMark(),
      h("span", { class: "brand-name" }, "DriveSafe", h("small", null, ROLE_LABELS[me.role]))),
    groups.map((group) => h("div", { class: "nav-group" },
      h("p", { class: "nav-group-label" }, group),
      routes.filter((route) => route.group === group).map((route) => {
        const link = h("a", { class: "nav-link", href: `#${route.path}` }, icon(route.icon), h("span", null, route.title), badgeFor(route));
        register(route.path, link);
        return link;
      }))),
    h("div", { class: "rail-foot" }, install, h("p", null, `DriveSafe AI ${session.info?.version || ""}`)));

  const liveText = h("span", { class: "live-text" }, LIVE_TEXT[live.status] || live.status);
  const liveStatus = h("span", { class: "live-status", "data-status": live.status, title: "Conexão em tempo real" },
    h("span", { class: "live-dot", "aria-hidden": "true" }), liveText);
  const scopeUi = me.role === "admin" ? scopeControl() : null;
  const topbar = h("header", { class: "topbar" },
    h("a", { class: "brand brand-compact", href: `#${home()}`, "aria-label": "DriveSafe, início" }, brandMark()),
    scopeUi ? scopeUi.element : h("p", { class: "topbar-company" }, me.company?.name || ROLE_LABELS[me.role]),
    h("div", { class: "topbar-spacer" }),
    liveStatus,
    themeToggle(),
    h("a", { class: "topbar-user", href: "#/conta", title: "Sua conta" },
      h("span", { class: "avatar", "aria-hidden": "true" }, initials(me.name)),
      h("span", { class: "topbar-user-name" }, me.name)));

  const main = h("main", { id: "main", class: "main", tabIndex: -1 });

  const tabRoutes = routes.filter((route) => route.tab).sort((a, b) => a.tab - b.tab);
  const primary = tabRoutes.slice(0, 4);
  const overflow = routes.filter((route) => !primary.includes(route));
  const moreButton = overflow.length
    ? h("button", { type: "button", class: "tab", on: { click: () => openMore(overflow) } }, icon("menu"), h("span", null, "Mais"))
    : null;
  const tabbar = h("nav", { class: "tabbar", "aria-label": "Menu" },
    primary.map((route) => {
      const badge = badgeFor(route);
      const link = h("a", { class: "tab", href: `#${route.path}` }, icon(route.icon), h("span", null, route.title), badge ? h("span", { class: "tab-badge" }, badge) : null);
      register(route.path, link);
      return link;
    }),
    moreButton);
  tabbar.style.setProperty("--tabs", String(primary.length + (moreButton ? 1 : 0)));

  const root = h("div", { class: "shell" }, rail, topbar, main, tabbar);
  mount(app, root);
  shell = { root, main, links, badges, liveStatus, liveText, install, moreButton, overflow, scopeUi };
  scheduleBadges(0);
}

function updateNav(route) {
  const active = route.parent || route.path;
  for (const [path, elements] of shell.links) {
    for (const element of elements) {
      if (path === active) element.setAttribute("aria-current", "page");
      else element.removeAttribute("aria-current");
    }
  }
  if (shell.moreButton) {
    const inOverflow = shell.overflow.some((item) => item.path === active);
    shell.moreButton.classList.toggle("is-active", inOverflow);
  }
}

function scheduleBadges(delay = 1500) {
  clearTimeout(badgeTimer);
  badgeTimer = setTimeout(refreshBadges, delay);
}

async function refreshBadges() {
  if (!shell || !MANAGERS.includes(session.me?.role)) return;
  try {
    const page = await api(`/api/alerts${query({ review_status: "pendente", limit: 1, company_id: scope.get() })}`);
    for (const badge of shell.badges) {
      badge.textContent = page.total > 99 ? "99+" : String(page.total);
      badge.hidden = page.total === 0;
      badge.setAttribute("aria-label", `${page.total} para revisar`);
    }
  } catch (error) {
    console.warn("Contador de revisão não atualizou:", error.message);
  }
}

// ---------- eventos globais ----------

live.on("status", (status) => {
  if (!shell) return;
  shell.liveStatus.dataset.status = status;
  shell.liveText.textContent = LIVE_TEXT[status] || status;
});
live.on("alert", () => scheduleBadges());
live.on("alert_review", () => scheduleBadges());

onApiEvent("unauthorized", () => {
  if (!session.me) return;
  toast("Sua sessão terminou. Entre de novo.", "info");
  endSession({ callServer: false });
});

onApiEvent("password-change", () => {
  if (session.me) session.me.must_change_password = true;
  navigate("/trocar-senha", { replace: true });
});

setHooks({
  render,
  resetShell: () => {
    if (current) current.destroy();
    current = null;
    shell = null;
  },
  companiesChanged: () => {
    if (shell && shell.scopeUi) shell.scopeUi.fill();
  },
});

document.addEventListener("click", (event) => {
  const skip = event.target.closest(".skip-link");
  if (!skip) return;
  event.preventDefault();
  const main = document.getElementById("main") || app;
  if (!main.hasAttribute("tabindex")) main.setAttribute("tabindex", "-1");
  main.focus();
});

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  session.installPrompt = event;
  if (shell) shell.install.hidden = false;
  document.dispatchEvent(new Event("drivesafe:instalar"));
});

window.addEventListener("appinstalled", () => {
  session.installPrompt = null;
  if (shell) shell.install.hidden = true;
  document.dispatchEvent(new Event("drivesafe:instalar"));
  toast("App instalado. Abra pelo ícone, como qualquer aplicativo.");
});

async function boot() {
  try {
    session.info = await api("/api/app-info");
    setTimeZone(session.info.timezone);
  } catch (error) {
    mount(app, h("div", { class: "boot" }, errorBlock(error, () => boot())));
    return;
  }
  try {
    await startSession(await api("/api/auth/me"));
  } catch (error) {
    if (error.status !== 401) {
      mount(app, h("div", { class: "boot" }, errorBlock(error, () => boot())));
      return;
    }
    session.me = null;
  }
  window.addEventListener("hashchange", render);
  render();

  const secure = location.protocol === "https:" || ["localhost", "127.0.0.1"].includes(location.hostname);
  if ("serviceWorker" in navigator && secure) {
    navigator.serviceWorker.register("/sw.js").catch((error) => console.warn("Service worker não registrado:", error));
  }
}

boot();
