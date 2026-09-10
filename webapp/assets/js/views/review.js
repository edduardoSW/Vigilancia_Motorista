/* Revisão de eventos: fila à esquerda, evento à direita, decisão com atalhos de teclado. */
import { api, query } from "../api.js";
import {
  alertKind, button, emptyState, errorBlock, facts, field, h, icon, pageHeader, selectInput, severityMark, toast,
} from "../dom.js";
import {
  CATEGORY_HELP, CATEGORY_LABELS, DECISIONS, REVIEW_LABELS, dateTime, detailLabel, detailValue, duration, localDay, relative,
} from "../format.js";

const STATUS_FILTERS = [
  ["pendente", "Para revisar"], ["confirmado", "Confirmados"], ["falso_alarme", "Alarmes falsos"],
  ["orientado", "Orientados"], ["todos", "Todos"],
];
const PERIODS = [["7", "7 dias"], ["30", "30 dias"], ["90", "90 dias"]];

export default async function reviewView(ctx) {
  ctx.title("Revisar eventos");
  const state = {
    status: STATUS_FILTERS.some(([value]) => value === ctx.query.get("situacao")) ? ctx.query.get("situacao") : "pendente",
    category: ctx.query.get("categoria") || "",
    days: Number(ctx.query.get("dias")) || 30,
    items: [],
    total: 0,
    selectedId: Number(ctx.query.get("alerta")) || null,
  };

  const queue = h("ul", { class: "queue", "aria-label": "Eventos" });
  const countLine = h("p", { class: "list-line" });
  const moreButton = button("Carregar mais", { small: true, onClick: () => load({ append: true }) });
  const detailHost = h("div");
  const statusButtons = h("div", { class: "segmented", role: "group", "aria-label": "Situação" });

  const startDay = () => localDay(new Date(Date.now() - (state.days - 1) * 86400000));

  function matchesFilters(alert) {
    if (state.status !== "todos" && alert.review_status !== state.status) return false;
    if (state.category && alert.category !== state.category) return false;
    return localDay(alert.timestamp) >= startDay();
  }

  function paintStatus() {
    statusButtons.replaceChildren(...STATUS_FILTERS.map(([value, label]) => h("button", {
      type: "button", "aria-pressed": String(state.status === value),
      on: { click: () => { state.status = value; state.selectedId = null; paintStatus(); load(); } },
    }, label)));
  }

  function queueItem(alert, fresh = false) {
    return h("li", { class: fresh ? "is-new" : null },
      h("button", {
        type: "button", class: "queue-item", "aria-current": alert.id === state.selectedId ? "true" : "false",
        dataset: { id: String(alert.id) },
        on: { click: () => select(alert.id, { focus: window.matchMedia("(max-width: 1180px)").matches }) },
      },
      severityMark(alertKind(alert.risk_level), { showText: false }),
      h("span", { class: "queue-title" }, alert.label),
      h("span", { class: "queue-time" }, relative(alert.timestamp)),
      h("span", { class: "queue-sub" }, [
        alert.driver?.name || "Sem motorista", alert.vehicle?.name,
        alert.review_status !== "pendente" ? REVIEW_LABELS[alert.review_status] : null,
      ].filter(Boolean).join(" · "))));
  }

  function paintQueue(freshId = null) {
    queue.replaceChildren(...state.items.map((alert) => queueItem(alert, alert.id === freshId)));
    if (!state.items.length) queue.replaceChildren(h("li", null, emptyState(state.status === "pendente" ? "Caixa zerada" : "Nenhum evento", "Nada com esses filtros no período.")));
    countLine.textContent = `${state.items.length} de ${state.total} ${state.total === 1 ? "evento" : "eventos"}`;
    moreButton.hidden = state.items.length >= state.total;
  }

  async function save(alert, status, note, errorTarget) {
    try {
      const updated = await api(`/api/alerts/${alert.id}/review`, { method: "PATCH", body: { status, note: note || null } });
      toast(status === "pendente" ? "O evento voltou para a revisão." : `Revisão salva: ${REVIEW_LABELS[status].toLowerCase()}.`);
      ctx.refreshBadges();
      const index = state.items.findIndex((item) => item.id === alert.id);
      if (index === -1) return;
      if (matchesFilters(updated)) {
        state.items[index] = updated;
        paintQueue();
        select(updated.id);
      } else {
        state.items.splice(index, 1);
        state.total = Math.max(0, state.total - 1);
        paintQueue();
        const next = state.items[Math.min(index, state.items.length - 1)];
        select(next ? next.id : null, { focus: true });
      }
    } catch (error) {
      if (errorTarget) errorTarget.textContent = error.message;
      else toast(error.message, "error");
    }
  }

  function detail(alert) {
    if (!alert) {
      return emptyState(state.status === "pendente" ? "Nenhum evento esperando revisão" : "Escolha um evento",
        state.status === "pendente" ? "Quando chegar um evento de risco alto, ele entra na fila na hora." : "Clique num evento da lista para ver as medidas.");
    }
    const note = h("textarea", { class: "input", name: "note", rows: 3, maxLength: 1000, placeholder: "O que foi feito ou combinado (opcional)", value: alert.review_note || "" });
    const error = h("p", { class: "form-error", role: "alert" });
    const form = h("form", { class: "review-form" },
      h("fieldset", { class: "choice-group" },
        h("legend", { class: "field-label" }, "Decisão"),
        h("div", { class: "choice-row" }, DECISIONS.map((decision, index) => h("label", { class: "choice" },
          h("input", { type: "radio", name: "decision", value: decision.value, checked: alert.review_status === decision.value }),
          h("span", { class: "choice-head" }, h("span", { class: "choice-title" }, decision.label), h("kbd", { class: "kbd" }, String(index + 1))),
          h("span", { class: "choice-text" }, decision.text))))),
      field("Observação", note),
      error,
      h("div", { class: "form-actions" },
        alert.review_status !== "pendente" && alert.review_status !== "arquivado"
          ? button("Voltar para a fila", { kind: "ghost", onClick: () => save(alert, "pendente", "", error) })
          : null,
        h("button", { type: "submit", class: "btn btn-primary" }, "Salvar revisão")),
      h("p", { class: "shortcut-hint" }, "Atalhos: J e K andam pela fila, 1 a 3 escolhem a decisão, Ctrl+Enter salva."));
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const value = new FormData(form).get("decision");
      if (!value) {
        error.textContent = "Escolha uma decisão.";
        return;
      }
      save(alert, value, note.value.trim(), error);
    });

    const details = Object.entries(alert.details || {});
    return h("article", { class: "review-detail", tabIndex: -1, "aria-labelledby": "evento-titulo" },
      h("header", { class: "review-head" },
        severityMark(alertKind(alert.risk_level), { className: "sev-large" }),
        h("h2", { class: "review-title", id: "evento-titulo" }, alert.label),
        h("p", { class: "review-when" }, `${dateTime(alert.timestamp)} · ${relative(alert.timestamp)}`)),
      facts([
        ["Motorista", alert.driver ? h("a", { href: `#/motoristas/${alert.driver.id}` }, alert.driver.name) : "Sem motorista vinculado"],
        ["Veículo", alert.vehicle?.name],
        ["Dispositivo", alert.device?.name],
        ["Duração", duration(alert.duration)],
        ["Nível do evento", `${alert.risk_level} de 5`],
        ctx.role === "admin" ? ["Empresa", alert.company?.name] : null,
        alert.reviewed_by ? ["Revisado por", `${alert.reviewed_by}, ${relative(alert.reviewed_at)}`] : null,
      ]),
      h("div", { class: "notice-box" },
        h("p", { class: "notice-title" }, CATEGORY_LABELS[alert.category] || "Evento"),
        h("p", null, CATEGORY_HELP[alert.category] || CATEGORY_HELP.outro)),
      details.length
        ? h("details", { class: "details-box", open: true },
          h("summary", null, "Medidas no momento do evento"),
          h("dl", { class: "kv" }, details.map(([key, value]) => [h("dt", null, detailLabel(key)), h("dd", null, detailValue(key, value))])))
        : null,
      form);
  }

  function select(id, { focus = false } = {}) {
    state.selectedId = id;
    for (const itemButton of queue.querySelectorAll(".queue-item")) {
      itemButton.setAttribute("aria-current", String(Number(itemButton.dataset.id) === id));
    }
    const alert = state.items.find((item) => item.id === id) || null;
    detailHost.replaceChildren(detail(alert));
    if (focus && alert) detailHost.firstElementChild.focus();
  }

  async function load({ append = false } = {}) {
    const params = {
      company_id: ctx.scopeId, review_status: state.status === "todos" ? null : state.status,
      category: state.category || null, start: startDay(), limit: 50, skip: append ? state.items.length : 0,
    };
    try {
      const page = await api(`/api/alerts${query(params)}`, { signal: ctx.signal });
      state.items = append ? state.items.concat(page.items) : page.items;
      state.total = page.total;
      paintQueue();
      if (!append) {
        const keep = state.items.some((item) => item.id === state.selectedId);
        select(keep ? state.selectedId : state.items[0]?.id ?? null);
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      queue.replaceChildren(h("li", null, errorBlock(error, () => load({ append }))));
    }
  }

  function move(step) {
    const index = state.items.findIndex((item) => item.id === state.selectedId);
    const next = state.items[Math.max(0, Math.min(state.items.length - 1, index + step))];
    if (!next) return;
    select(next.id);
    queue.querySelector(`[data-id="${next.id}"]`)?.scrollIntoView({ block: "nearest" });
  }

  ctx.listen(document, "keydown", (event) => {
    if (document.querySelector("dialog[open]")) return;
    const typing = event.target.closest("input[type=text], textarea, select, [contenteditable]");
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      const form = detailHost.querySelector("form");
      if (form) {
        event.preventDefault();
        form.requestSubmit();
      }
      return;
    }
    if (typing || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === "j") move(1);
    else if (event.key === "k") move(-1);
    else if (["1", "2", "3"].includes(event.key)) {
      const radio = detailHost.querySelectorAll('input[name="decision"]')[Number(event.key) - 1];
      if (radio) {
        radio.checked = true;
        radio.focus();
      }
    }
  });

  ctx.onLive("alert", (alert) => {
    if ((ctx.scopeId && alert.company?.id !== ctx.scopeId) || !matchesFilters(alert)) return;
    if (state.items.some((item) => item.id === alert.id)) return;
    state.items.unshift(alert);
    state.total += 1;
    paintQueue(alert.id);
    if (!state.selectedId) select(alert.id);
    else select(state.selectedId);
  });

  ctx.onLive("alert_review", (alert) => {
    const index = state.items.findIndex((item) => item.id === alert.id);
    if (index === -1) return;
    const selected = alert.id === state.selectedId;
    if (matchesFilters(alert)) state.items[index] = alert;
    else {
      state.items.splice(index, 1);
      state.total = Math.max(0, state.total - 1);
    }
    paintQueue();
    if (selected) {
      toast(`Este evento foi revisado por ${alert.reviewed_by || "outra pessoa"}.`, "info");
      select(matchesFilters(alert) ? alert.id : state.items[Math.min(index, state.items.length - 1)]?.id ?? null);
    } else {
      select(state.selectedId);
    }
  });

  const categorySelect = selectInput("categoria", [["", "Todas"], ...Object.entries(CATEGORY_LABELS).filter(([key]) => key !== "outro")], state.category);
  categorySelect.addEventListener("change", () => { state.category = categorySelect.value; load(); });
  const periodSelect = selectInput("periodo", PERIODS, String(state.days));
  periodSelect.addEventListener("change", () => { state.days = Number(periodSelect.value); load(); });

  paintStatus();
  await load();

  return h("div", { class: "page" },
    pageHeader("Revisar eventos", {
      lead: "Confirme, marque alarme falso ou registre a orientação. Cada decisão entra no histórico do motorista e mostra onde o sistema acerta e onde erra.",
    }),
    h("div", { class: "layout-review" },
      h("section", { class: "panel", "aria-label": "Fila de eventos" },
        h("div", { class: "toolbar" },
          h("div", { class: "toolbar-grow" }, statusButtons),
          field("Categoria", categorySelect),
          field("Período", periodSelect)),
        countLine,
        queue,
        h("div", { class: "panel-foot" }, moreButton)),
      h("section", { class: "panel", "aria-label": "Evento selecionado" }, detailHost)),
    h("p", { class: "field-hint" }, icon("info", { size: 14 }), " Eventos de aviso do equipamento e de risco baixo não entram na fila; aparecem em Relatórios."));
}
