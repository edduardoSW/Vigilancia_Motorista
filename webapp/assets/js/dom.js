/* Tela montada com elementos, nunca com innerHTML: texto que vem da API entra sempre como texto. */

const SVG_NS = "http://www.w3.org/2000/svg";
// Atributos que o DOM expõe como propriedade só de leitura: precisam de setAttribute.
const ATTRIBUTE_ONLY = new Set(["form", "list"]);
let uid = 0;

export function nextId(prefix = "id") {
  uid += 1;
  return `${prefix}-${uid}`;
}

function append(parent, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false || child === true) continue;
    parent.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function h(tag, props = null, ...children) {
  const el = document.createElement(tag);
  let value;
  for (const [key, raw] of Object.entries(props || {})) {
    if (raw === null || raw === undefined || raw === false) continue;
    if (key === "value") value = raw;
    else if (key === "class") el.className = Array.isArray(raw) ? raw.filter(Boolean).join(" ") : raw;
    else if (key === "on") for (const [event, handler] of Object.entries(raw)) el.addEventListener(event, handler);
    else if (key === "dataset") Object.assign(el.dataset, raw);
    else if (key === "style") for (const [name, styleValue] of Object.entries(raw)) el.style.setProperty(name, styleValue);
    else if (key.startsWith("aria-") || key.startsWith("data-") || ATTRIBUTE_ONLY.has(key) || !(key in el)) {
      el.setAttribute(key, raw === true ? "" : String(raw));
    } else el[key] = raw;
  }
  append(el, children);
  if (value !== undefined) el.value = value;
  return el;
}

export function s(tag, attrs = null, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, raw] of Object.entries(attrs || {})) {
    if (raw === null || raw === undefined || raw === false) continue;
    if (key === "on") for (const [event, handler] of Object.entries(raw)) el.addEventListener(event, handler);
    else el.setAttribute(key, String(raw));
  }
  append(el, children);
  return el;
}

export function mount(container, ...children) {
  container.replaceChildren();
  append(container, children);
  return container;
}

// ---------- ícones (desenhados para este app, traço de 1,75 numa grade de 24) ----------

const ICONS = {
  truck: "M2 6.5h12v9.5H2z M14 10h4.2L22 13.6V16h-8 M6 18.2m-1.8 0a1.8 1.8 0 1 0 3.6 0a1.8 1.8 0 1 0-3.6 0 M17.6 18.2m-1.8 0a1.8 1.8 0 1 0 3.6 0a1.8 1.8 0 1 0-3.6 0",
  inbox: "M3 13.5 5.6 5h12.8L21 13.5V19H3z M3 13.5h5.2l1.4 2.4h4.8l1.4-2.4H21",
  wheel: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M12 12m-2.2 0a2.2 2.2 0 1 0 4.4 0a2.2 2.2 0 1 0-4.4 0 M3.4 10.2 9.8 12 M14.2 12l6.4-1.8 M12 14.2V21",
  bus: "M5.5 3.5h13a1.5 1.5 0 0 1 1.5 1.5v12H4V5a1.5 1.5 0 0 1 1.5-1.5z M4 11.5h16 M7 20.5V17 M17 20.5V17 M7.5 14.3h.01 M16.5 14.3h.01",
  chip: "M7 7h10v10H7z M10 10h4v4h-4z M9.5 3v4 M14.5 3v4 M9.5 17v4 M14.5 17v4 M3 9.5h4 M3 14.5h4 M17 9.5h4 M17 14.5h4",
  sheet: "M6 3h9l4 4v14H6z M15 3v4h4 M9 12h7 M9 16h7 M9 8h3",
  building: "M4 21V5.5L12 3v18 M12 21V9l8 2.2V21 M2 21h20 M7 8h2 M7 12h2 M7 16h2 M15 14.5h2 M15 17.5h2",
  users: "M9 10.5m-3.5 0a3.5 3.5 0 1 0 7 0a3.5 3.5 0 1 0-7 0 M2.5 20c.8-3.2 3.3-5 6.5-5s5.7 1.8 6.5 5 M15.8 4.4a3.5 3.5 0 0 1 0 6.3 M18 15.2c1.9.7 3.1 2.3 3.5 4.8",
  eye: "M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0",
  film: "M3 5h18v14H3z M7 5v14 M17 5v14 M3 9.5h4 M3 14.5h4 M17 9.5h4 M17 14.5h4",
  shield: "M12 3l8 3v6c0 4.5-3.4 8.1-8 9-4.6-.9-8-4.5-8-9V6z M8.5 12l2.4 2.4 4.6-4.8",
  user: "M12 8m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0 M4 21c1-4 4.2-6 8-6s7 2 8 6",
  gauge: "M4 15a8 8 0 0 1 16 0 M12 15l4-4.5 M2.5 19h19 M6.5 11.5l1 .8 M12 7v1.3 M17.5 11.5l-1 .8",
  logout: "M14.5 4H19v16h-4.5 M10 8l-4 4 4 4 M6 12h10",
  moon: "M20 14.6A8.2 8.2 0 1 1 9.4 4a6.6 6.6 0 0 0 10.6 10.6z",
  sun: "M12 12m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0 M12 2.5v2 M12 19.5v2 M2.5 12h2 M19.5 12h2 M5.3 5.3l1.4 1.4 M17.3 17.3l1.4 1.4 M5.3 18.7l1.4-1.4 M17.3 6.7l1.4-1.4",
  menu: "M4 7h16 M4 12h16 M4 17h16",
  phone: "M8 2.5h8a1.5 1.5 0 0 1 1.5 1.5v16a1.5 1.5 0 0 1-1.5 1.5H8A1.5 1.5 0 0 1 6.5 20V4A1.5 1.5 0 0 1 8 2.5z M11 18.5h2",
  call: "M5 3.5h3.4l1.8 4.4-2.3 1.5a11 11 0 0 0 6.7 6.7l1.5-2.3 4.4 1.8V19a1.5 1.5 0 0 1-1.6 1.5A17 17 0 0 1 3.5 5.1 1.5 1.5 0 0 1 5 3.5z",
  chat: "M12 3.5a8.5 8.5 0 0 0-7.4 12.7L3.5 20.5l4.3-1.1A8.5 8.5 0 1 0 12 3.5z M8.5 12h.01 M12 12h.01 M15.5 12h.01",
  clock: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M12 7v5l3.2 2",
  download: "M12 3.5v11 M7.5 10l4.5 4.5 4.5-4.5 M5 20h14",
  upload: "M12 15.5v-11 M7.5 9 12 4.5 16.5 9 M5 20h14",
  copy: "M9 9h11v11H9z M5 15H4V4h11v1",
  check: "M5 12.5l4.5 4.5L19 7",
  x: "M6 6l12 12 M18 6 6 18",
  plus: "M12 5v14 M5 12h14",
  search: "M11 11m-7 0a7 7 0 1 0 14 0a7 7 0 1 0-14 0 M20 20l-4-4",
  refresh: "M20 11A8 8 0 0 0 5.6 6.4L4 8 M4 4v4h4 M4 13a8 8 0 0 0 14.4 4.6L20 16 M20 20v-4h-4",
  play: "M7 4.5v15l12-7.5z",
  stop: "M6.5 6.5h11v11h-11z",
  chevron: "M9 6l6 6-6 6",
  back: "M15 6l-6 6 6 6",
  key: "M8 15m-4 0a4 4 0 1 0 8 0a4 4 0 1 0-8 0 M10.8 12.2 20 3 M16.5 6.5l3 3 M14 9l2 2",
  ban: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M5.6 5.6l12.8 12.8",
  edit: "M4 20h4L19 9l-4-4L4 16z M13.5 6.5l4 4",
  target: "M12 12m-8 0a8 8 0 1 0 16 0a8 8 0 1 0-16 0 M12 12m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0",
  info: "M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0 M12 11v6 M12 7.5h.01",
  install: "M4 14.5V20h16v-5.5 M12 3.5v11 M7.5 10l4.5 4.5 4.5-4.5",
};

export function icon(name, { size = 20, label = null, className = null } = {}) {
  const svg = s("svg", {
    viewBox: "0 0 24 24", width: size, height: size, class: ["icon", className].filter(Boolean).join(" "),
    fill: "none", stroke: "currentColor", "stroke-width": 1.75, "stroke-linecap": "round", "stroke-linejoin": "round",
    "aria-hidden": label ? null : "true", role: label ? "img" : null, focusable: "false",
  });
  if (label) svg.append(s("title", null, label));
  svg.append(s("path", { d: ICONS[name] || ICONS.info }));
  return svg;
}

// ---------- gravidade: forma + texto (a cor só reforça) ----------

export const SEVERITY_TEXT = {
  none: "sem sinal", notice: "aviso", normal: "normal", attention: "atenção", high: "alto", critical: "crítico",
};

function severityShape(kind) {
  const svg = s("svg", { viewBox: "0 0 16 16", class: "sev-shape", "aria-hidden": "true", focusable: "false" });
  switch (kind) {
    case "normal":
      svg.append(s("circle", { cx: 8, cy: 8, r: 3.6, class: "sev-fill" }));
      break;
    case "notice":
      svg.append(s("circle", { cx: 8, cy: 8, r: 4.2, class: "sev-line" }));
      break;
    case "attention":
      svg.append(s("path", { d: "M8 2.2 13.8 8 8 13.8 2.2 8z", class: "sev-line" }));
      break;
    case "high":
      svg.append(s("path", { d: "M8 1.2 14.8 8 8 14.8 1.2 8z", class: "sev-fill" }),
        s("path", { d: "M8 4.9v3.8 M8 11.1v.1", class: "sev-mark" }));
      break;
    case "critical":
      svg.append(s("path", { d: "M5.3 1.4h5.4l3.9 3.9v5.4l-3.9 3.9H5.3l-3.9-3.9V5.3z", class: "sev-fill" }),
        s("path", { d: "M4.9 8h6.2", class: "sev-mark" }));
      break;
    default:
      svg.append(s("circle", { cx: 8, cy: 8, r: 4.6, class: "sev-dash" }));
  }
  return svg;
}

/** kind: none | notice | normal | attention | high | critical */
export function severityMark(kind, { text = null, showText = true, className = null } = {}) {
  const label = text || SEVERITY_TEXT[kind] || kind;
  return h("span", { class: ["sev", `sev-${kind}`, className] }, severityShape(kind),
    h("span", { class: showText ? "sev-text" : "sr-only" }, label));
}

/** Nível do evento (1 a 5) na escala visual. */
export function alertKind(risk) {
  if (risk >= 4) return "critical";
  if (risk >= 3) return "high";
  if (risk >= 2) return "attention";
  return "notice";
}

/** Nível ao vivo do dispositivo (0 a 3); sem conexão ou sem estado vira "sem sinal". */
export function deviceKind(device) {
  if (!device || !device.online || !device.live || device.live.risk_level === null || device.live.risk_level === undefined) {
    return "none";
  }
  return ["normal", "attention", "high", "critical"][Math.max(0, Math.min(3, device.live.risk_level))];
}

// ---------- avisos, diálogos e formulários ----------

let toastRegion = null;

export function toast(message, kind = "ok", timeout = 4200) {
  if (!toastRegion || !toastRegion.isConnected) {
    toastRegion = h("div", { class: "toasts", role: "status", "aria-live": "polite" });
    document.body.append(toastRegion);
  }
  const item = h("div", { class: ["toast", `toast-${kind}`] }, icon(kind === "error" ? "x" : kind === "info" ? "info" : "check", { size: 16 }),
    h("span", null, message));
  toastRegion.append(item);
  setTimeout(() => {
    item.classList.add("is-leaving");
    setTimeout(() => item.remove(), 260);
  }, timeout);
}

export function openDialog({ title, body, actions = [], wide = false, onClose = null }) {
  const titleId = nextId("dialogo");
  const dialog = h("dialog", { class: ["dialog", wide && "dialog-wide"], "aria-labelledby": titleId });
  const close = (value = "") => {
    if (dialog.open) dialog.close(value);
  };
  const footer = actions.length
    ? h("footer", { class: "dialog-actions" }, actions.map((action) => h("button", {
      type: "button", class: ["btn", action.kind && `btn-${action.kind}`],
      on: {
        click: async (event) => {
          if (action.onClick && (await action.onClick(event, close)) === false) return;
          close(action.value || "");
        },
      },
    }, action.label)))
    : null;
  dialog.append(
    h("header", { class: "dialog-head" },
      h("h2", { class: "dialog-title", id: titleId }, title),
      h("button", { type: "button", class: "icon-btn", "aria-label": "Fechar", on: { click: () => close() } }, icon("x"))),
    h("div", { class: "dialog-body" }, body),
    footer,
  );
  dialog.addEventListener("close", () => {
    if (onClose) onClose(dialog.returnValue);
    dialog.remove();
  });
  dialog.addEventListener("mousedown", (event) => {
    if (event.target === dialog) close();
  });
  document.body.append(dialog);
  dialog.showModal();
  return { dialog, close };
}

export function confirmDialog({ title, message, confirmLabel = "Confirmar", danger = false }) {
  return new Promise((resolve) => {
    let answered = false;
    openDialog({
      title,
      body: h("p", { class: "dialog-text" }, message),
      actions: [
        { label: "Cancelar", kind: "ghost", onClick: () => { answered = true; resolve(false); } },
        { label: confirmLabel, kind: danger ? "danger" : "primary", onClick: () => { answered = true; resolve(true); } },
      ],
      onClose: () => {
        if (!answered) resolve(false);
      },
    });
  });
}

/** Formulário num diálogo. onSubmit(FormData, form) pode lançar erro (mostrado no próprio diálogo). */
export function formDialog({ title, content, submitLabel = "Salvar", danger = false, wide = false, onSubmit }) {
  const error = h("p", { class: "form-error", role: "alert" });
  const submit = h("button", { type: "submit", class: ["btn", danger ? "btn-danger" : "btn-primary"] }, submitLabel);
  let ref = null;
  const form = h("form", { class: "dialog-form" }, content, error,
    h("footer", { class: "dialog-actions" },
      h("button", { type: "button", class: "btn btn-ghost", on: { click: () => ref.close() } }, "Cancelar"), submit));
  ref = openDialog({ title, body: form, wide });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    submit.disabled = true;
    try {
      const keepOpen = await onSubmit(new FormData(form), form, ref);
      if (keepOpen !== true) ref.close();
    } catch (problem) {
      error.textContent = problem.message || "Não deu certo. Tente de novo.";
    } finally {
      submit.disabled = false;
    }
  });
  const first = form.querySelector("input:not([type=hidden]), select, textarea");
  if (first) first.focus();
  return ref;
}

export function field(label, control, { hint = null, wide = false } = {}) {
  if (!control.id) control.id = nextId("campo");
  const hintId = hint ? `${control.id}-dica` : null;
  if (hintId) control.setAttribute("aria-describedby", hintId);
  return h("div", { class: ["field", wide && "field-wide"] },
    h("label", { class: "field-label", for: control.id }, label),
    control,
    hint ? h("p", { class: "field-hint", id: hintId }, hint) : null);
}

export function textInput(name, props = {}) {
  return h("input", { name, type: "text", class: "input", ...props });
}

export function selectInput(name, options, value = "", props = {}) {
  return h("select", { name, class: "input", ...props, value: value === null || value === undefined ? "" : String(value) },
    options.map(([optionValue, text]) => h("option", { value: String(optionValue) }, text)));
}

export function switchInput(name, checked, label, props = {}) {
  return h("label", { class: "switch" },
    h("input", { type: "checkbox", name, checked: Boolean(checked), ...props }),
    h("span", { class: "switch-track", "aria-hidden": "true" }),
    h("span", { class: "switch-label" }, label));
}

export function copyField(value, label = "Copiar") {
  const input = h("input", { class: "input input-mono", readOnly: true, value, "aria-label": "Valor para copiar" });
  input.addEventListener("focus", () => input.select());
  const text = h("span", null, label);
  const button = h("button", {
    type: "button", class: "btn btn-small",
    on: {
      click: async () => {
        try {
          await navigator.clipboard.writeText(value);
          text.textContent = "Copiado";
          setTimeout(() => { text.textContent = label; }, 1600);
        } catch {
          input.focus();
          toast("Selecionei o texto: copie com Ctrl+C.", "info");
        }
      },
    },
  }, icon("copy", { size: 16 }), text);
  return h("div", { class: "copy-field" }, input, button);
}

// ---------- blocos de página ----------

export function pageHeader(title, { lead = null, actions = null, back = null } = {}) {
  return h("header", { class: "page-head" },
    h("div", { class: "page-head-text" },
      back ? h("a", { class: "back-link", href: back.href }, icon("back", { size: 16 }), back.label) : null,
      h("h1", { class: "page-title", tabIndex: -1 }, title),
      lead ? h("p", { class: "page-lead" }, lead) : null),
    actions ? h("div", { class: "page-actions" }, actions) : null);
}

/** Painel com marco de quilômetro (km) no título. */
export function panel({ title, km = null, actions = null, className = null, lead = null }, ...children) {
  const headingId = nextId("painel");
  return h("section", { class: ["panel", className], "aria-labelledby": headingId },
    h("header", { class: "panel-head" },
      h("div", { class: "panel-heading" },
        km ? h("span", { class: "km", "aria-hidden": "true" }, h("small", null, "KM"), km) : null,
        h("h2", { class: "panel-title", id: headingId }, title)),
      actions ? h("div", { class: "panel-actions" }, actions) : null),
    lead ? h("p", { class: "panel-lead" }, lead) : null,
    children);
}

export function facts(entries, { className = null } = {}) {
  return h("dl", { class: ["facts", className] }, entries.filter(Boolean).map(([term, value]) =>
    h("div", { class: "fact" }, h("dt", null, term), h("dd", null, value === null || value === undefined || value === "" ? "—" : value))));
}

export function chip(text, kind = null) {
  return h("span", { class: ["chip", kind && `chip-${kind}`] }, text);
}

export function emptyState(title, text = null, action = null) {
  return h("div", { class: "empty" },
    s("svg", { viewBox: "0 0 32 32", class: "empty-mark", "aria-hidden": "true" }, s("path", { d: "M16 2.5 29.5 16 16 29.5 2.5 16z" })),
    h("p", { class: "empty-title" }, title),
    text ? h("p", { class: "empty-text" }, text) : null,
    action);
}

export function loadingBlock(label = "Carregando") {
  return h("div", { class: "loading", role: "status" }, h("span", { class: "loading-lane", "aria-hidden": "true" }), h("span", null, label));
}

export function errorBlock(error, retry = null) {
  return h("div", { class: "error-block", role: "alert" },
    icon("info", { size: 18 }),
    h("p", null, error && error.message ? error.message : "Não deu para carregar."),
    retry ? h("button", { type: "button", class: "btn btn-small", on: { click: retry } }, icon("refresh", { size: 16 }), "Tentar de novo") : null);
}

export function button(label, { kind = null, iconName = null, onClick = null, type = "button", small = false, ...props } = {}) {
  return h("button", { type, class: ["btn", kind && `btn-${kind}`, small && "btn-small"], on: onClick ? { click: onClick } : null, ...props },
    iconName ? icon(iconName, { size: small ? 16 : 18 }) : null, h("span", null, label));
}
