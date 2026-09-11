/* Frota ao vivo: faixa "agora na estrada", cada veículo com a faixa de 24 h, eventos para revisar e motoristas. */
import { api, query } from "../api.js";
import { hourStrip, setNumber, stripLevel } from "../charts.js";
import {
  alertKind, chip, deviceKind, emptyState, h, icon, pageHeader, panel, severityMark,
} from "../dom.js";
import {
  CATEGORY_LABELS, PHONE_STATES, drivingHours, humanize, localHour, percent, plural, relative, time,
} from "../format.js";

const KINDS = ["critical", "high", "attention", "normal", "none"];

function statusChips(device) {
  const live = device.live || {};
  const chips = [];
  if (!device.online) {
    chips.push(chip(device.last_seen_at ? `offline desde ${relative(device.last_seen_at)}` : "nunca conectou"));
    return chips;
  }
  if (device.camera_ok === false) chips.push(chip("câmera com problema", "red"));
  if (live.calibrating) chips.push(chip(`calibrando ${percent(live.calibration_progress || 0)}`, "amber"));
  if (live.phone_state && live.phone_state !== "sem_celular") chips.push(chip(PHONE_STATES[live.phone_state] || humanize(live.phone_state), "amber"));
  if (live.face_found === false) chips.push(chip("rosto fora da câmera"));
  else if (live.eyes_visible === false) chips.push(chip("olhos não visíveis"));
  if (live.driving_hours !== null && live.driving_hours !== undefined) {
    chips.push(chip(`${drivingHours(live.driving_hours)} ao volante`, live.driving_hours >= 5.5 ? "red" : null));
  }
  for (const reason of (live.reasons || []).slice(0, 2)) chips.push(chip(humanize(reason)));
  return chips;
}

function fleetRow(item) {
  const device = item.device;
  const kind = deviceKind(device);
  const chips = statusChips(device);
  const href = device.driver ? `#/motoristas/${device.driver.id}` : "#/dispositivos";
  const label = device.vehicle?.name || device.name;
  return h("li", { dataset: { device: String(device.id) } },
    h("a", { class: ["row", "row-fleet", `row-${kind}`], href },
      h("span", { class: "row-sev" }, severityMark(kind)),
      h("span", { class: "row-vehicle" },
        device.vehicle ? h("span", { class: "plate" }, device.vehicle.name) : h("span", { class: "plate plate-empty" }, "sem veículo"),
        h("span", { class: "row-sub" }, device.name)),
      h("span", { class: "row-driver" },
        h("span", { class: "row-main" }, device.driver?.name || "Sem motorista vinculado"),
        h("span", { class: "row-sub" }, item.alerts_today ? plural(item.alerts_today, "alerta hoje", "alertas hoje") : "nenhum alerta hoje")),
      h("span", { class: "row-status chips" },
        chips.length ? chips : h("span", { class: "row-sub" }, device.live ? "sem avisos agora" : "aguardando o primeiro estado")),
      h("span", { class: "row-strip" },
        hourStrip(item.risk_hours_today, { now: localHour(new Date()), label: `${label}, pior evento por hora hoje` })),
      h("span", { class: "row-time" }, device.online ? relative(device.status_at || device.last_seen_at) : "")));
}

function alertRow(alert, fresh = false) {
  return h("li", { class: fresh ? "is-new" : null, dataset: { alert: String(alert.id) } },
    h("a", { class: "row row-alert", href: `#/revisar?alerta=${alert.id}` },
      severityMark(alertKind(alert.risk_level), { showText: false }),
      h("span", { class: "row-main-wrap" },
        h("span", { class: "row-main" }, alert.label),
        h("span", { class: "row-sub" }, [alert.driver?.name || "Sem motorista", alert.vehicle?.name].filter(Boolean).join(" · "))),
      h("span", { class: "row-time" }, relative(alert.timestamp))));
}

export default async function fleetView(ctx) {
  ctx.title("Frota ao vivo");
  const scopeQuery = { company_id: ctx.scopeId };
  const load = () => Promise.all([
    api(`/api/overview${query(scopeQuery)}`, { signal: ctx.signal }),
    api(`/api/fleet${query(scopeQuery)}`, { signal: ctx.signal }),
    api(`/api/alerts${query({ ...scopeQuery, review_status: "pendente", limit: 6 })}`, { signal: ctx.signal }),
  ]);
  let [overview, items, pending] = await load();

  const counters = {};
  const updatedAt = h("span", { class: "mono" }, time(new Date()));
  const online = h("strong", null, "0");
  const alertsToday = h("strong", null, "0");
  const strongToday = h("strong", null, "0");
  const toReview = h("strong", null, "0");

  const band = h("section", { class: "road-band", "aria-labelledby": "agora-titulo" },
    h("div", null,
      h("h2", { class: "band-title", id: "agora-titulo" }, "Agora na estrada"),
      h("p", { class: "band-time" }, "atualizado às ", updatedAt)),
    h("ul", { class: "band-counts", "aria-label": "Veículos por nível de risco agora" },
      KINDS.map((kind) => {
        const value = h("span", { class: "count-value" }, "0");
        counters[kind] = value;
        return h("li", { class: `count count-${kind}` }, value, severityMark(kind));
      })),
    h("p", { class: "band-meta" },
      h("span", null, "Online: ", online),
      h("span", null, "Alertas hoje: ", alertsToday),
      h("span", null, "Altos e críticos hoje: ", strongToday),
      h("a", { class: "band-link", href: "#/revisar" }, "Para revisar: ", toReview, icon("chevron", { size: 14 }))));

  const fleetList = h("ul", { class: "rows" });
  const pendingList = h("ul", { class: "rows" });
  const attentionList = h("ul", { class: "rows" });

  function paintBand() {
    const counts = Object.fromEntries(KINDS.map((kind) => [kind, 0]));
    for (const item of items) counts[deviceKind(item.device)] += 1;
    for (const kind of KINDS) setNumber(counters[kind], counts[kind]);
    online.textContent = `${items.filter((item) => item.device.online).length} de ${items.length}`;
    setNumber(alertsToday, overview.alerts_today);
    setNumber(strongToday, overview.critical_today);
    setNumber(toReview, overview.to_review);
    updatedAt.textContent = time(new Date());
  }

  function paintFleet() {
    fleetList.replaceChildren(...items.map(fleetRow));
    if (!items.length) {
      fleetList.replaceChildren(h("li", null, emptyState("Nenhum dispositivo nesta empresa",
        "Quando um equipamento for cadastrado e ligado no veículo, ele aparece aqui com o estado ao vivo.",
        h("a", { class: "btn btn-small", href: "#/dispositivos" }, "Ver dispositivos"))));
    }
  }

  function paintPending() {
    pendingList.replaceChildren(...pending.items.map((alert) => alertRow(alert)));
    if (!pending.items.length) pendingList.replaceChildren(h("li", null, emptyState("Nada para revisar", "Os eventos novos de risco alto aparecem aqui assim que chegam.")));
  }

  function paintAttention() {
    attentionList.replaceChildren(...overview.drivers_attention.map((entry) => h("li", null,
      h("a", { class: "row row-person", href: `#/motoristas/${entry.driver.id}` },
        severityMark(alertKind(entry.worst_risk), { showText: false }),
        h("span", { class: "row-main-wrap" },
          h("span", { class: "row-main" }, entry.driver.name),
          h("span", { class: "row-sub" }, `${plural(entry.alerts_7d, "alerta", "alertas")} em 7 dias${entry.top_category ? ` · mais ${CATEGORY_LABELS[entry.top_category].toLowerCase()}` : ""}`)),
        icon("chevron", { size: 16 })))));
    if (!overview.drivers_attention.length) attentionList.replaceChildren(h("li", null, emptyState("Semana tranquila", "Nenhum motorista com alertas nos últimos 7 dias.")));
  }

  paintBand();
  paintFleet();
  paintPending();
  paintAttention();

  const inScope = (companyId) => !ctx.scopeId || companyId === ctx.scopeId;

  ctx.onLive("device", (device) => {
    if (!inScope(device.company?.id)) return;
    const index = items.findIndex((item) => item.device.id === device.id);
    if (index === -1) {
      refresh();
      return;
    }
    items[index] = { ...items[index], device };
    const row = fleetList.querySelector(`[data-device="${device.id}"]`);
    if (row) row.replaceWith(fleetRow(items[index]));
    paintBand();
  });

  ctx.onLive("alert", (alert) => {
    if (!inScope(alert.company?.id)) return;
    if (alert.category !== "sistema") {
      overview.alerts_today += 1;
      if (alert.risk_level >= 3) overview.critical_today += 1;
      const item = items.find((entry) => entry.device.id === alert.device?.id);
      if (item) {
        item.alerts_today += 1;
        const hour = localHour(alert.timestamp);
        item.risk_hours_today[hour] = Math.max(item.risk_hours_today[hour] || 0, alert.risk_level);
        const row = fleetList.querySelector(`[data-device="${item.device.id}"]`);
        if (row) row.replaceWith(fleetRow(item));
      }
    }
    if (alert.review_status === "pendente") {
      overview.to_review += 1;
      if (!pending.items.length) pendingList.replaceChildren();
      pending.items.unshift(alert);
      pending.items = pending.items.slice(0, 6);
      pendingList.prepend(alertRow(alert, true));
      while (pendingList.children.length > 6) pendingList.lastElementChild.remove();
    }
    paintBand();
  });

  ctx.onLive("alert_review", (alert) => {
    if (!inScope(alert.company?.id)) return;
    const row = pendingList.querySelector(`[data-alert="${alert.id}"]`);
    if (alert.review_status !== "pendente" && row) {
      row.remove();
      pending.items = pending.items.filter((entry) => entry.id !== alert.id);
      overview.to_review = Math.max(0, overview.to_review - 1);
      if (!pending.items.length) paintPending();
      paintBand();
    }
  });

  let refreshing = false;
  async function refresh() {
    if (refreshing || !ctx.alive) return;
    refreshing = true;
    try {
      [overview, items, pending] = await load();
      paintBand();
      paintFleet();
      paintPending();
      paintAttention();
    } catch (error) {
      if (error.name !== "AbortError") console.warn("Frota não atualizou:", error.message);
    } finally {
      refreshing = false;
    }
  }
  // O estado "online" depende do tempo desde o último sinal: atualiza mesmo sem mensagem nova.
  ctx.every(30000, refresh);

  const peakHint = items.some((item) => item.risk_hours_today.some((risk) => stripLevel(risk) === 3));

  return h("div", { class: "page" },
    pageHeader("Frota ao vivo", {
      lead: "Estado de cada veículo agora e o pior evento de cada hora de hoje. Forma e texto dizem a gravidade; nenhuma imagem sai do veículo.",
    }),
    band,
    h("div", { class: "layout-split" },
      panel({ title: "Veículos", km: "01", lead: peakHint ? "Barra vermelha na faixa de 24 h = hora com evento crítico." : null }, fleetList),
      h("div", { class: "stack" },
        panel({ title: "Para revisar", km: "02", actions: h("a", { class: "btn btn-small", href: "#/revisar" }, "Abrir revisão") }, pendingList),
        panel({ title: "Pedem atenção", km: "03", lead: "Motoristas com mais alertas nos últimos 7 dias." }, attentionList))));
}
