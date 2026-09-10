/* Página do motorista: o dia hora a hora, os últimos 30 dias, autorizações e exportação dos dados (LGPD). */
import { api, download } from "../api.js";
import { hourStrip, trendChart } from "../charts.js";
import { alertKind, button, chip, emptyState, facts, h, pageHeader, panel, severityMark, toast } from "../dom.js";
import { CHANNEL_LABELS, CONSENTS, dayLabel, duration, localDay, localHour, relative, time } from "../format.js";

export async function driverPage(ctx, driverId, { own = false } = {}) {
  if (!driverId) return emptyState("Conta sem motorista vinculado", "Peça à equipe DriveSafe para ligar seu acesso ao cadastro de motorista.");
  const [driver, day] = await Promise.all([
    api(`/api/drivers/${driverId}`, { signal: ctx.signal }),
    api(`/api/drivers/${driverId}/day`, { signal: ctx.signal }),
  ]);
  ctx.title(own ? "Meu painel" : driver.name);
  const isToday = day.day === localDay();

  const dayAlerts = h("ul", { class: "rows" }, day.alerts.length
    ? day.alerts.map((alert) => h("li", null, h(own ? "div" : "a", { class: "row row-alert", href: own ? null : `#/revisar?alerta=${alert.id}&situacao=todos` },
      severityMark(alertKind(alert.risk_level), { showText: false }),
      h("span", { class: "row-main-wrap" }, h("span", { class: "row-main" }, alert.label),
        h("span", { class: "row-sub" }, [alert.vehicle?.name, alert.duration ? duration(alert.duration) : null].filter(Boolean).join(" · "))),
      h("span", { class: "row-time" }, time(alert.timestamp)))))
    : h("li", null, emptyState(isToday ? "Nenhum alerta hoje" : "Nenhum alerta neste dia")));

  const consentRows = CONSENTS.map((item) => {
    const state = driver.consents[item.kind];
    return h("li", { class: "row row-person" },
      state ? chip("autorizado", "amber") : chip(state === false ? "retirado" : "sem registro"),
      h("span", { class: "row-main-wrap" }, h("span", { class: "row-main" }, item.title)),
      h("span", null));
  });
  const history = driver.consent_history.slice(0, 6).map((entry) => h("li", { class: "row row-person" },
    chip(entry.granted ? "autorizou" : "retirou", entry.granted ? "amber" : null),
    h("span", { class: "row-main-wrap" },
      h("span", { class: "row-main" }, CONSENTS.find((item) => item.kind === entry.kind)?.title || entry.kind),
      h("span", { class: "row-sub" }, `${CHANNEL_LABELS[entry.channel] || entry.channel}${entry.recorded_by ? ` · ${entry.recorded_by}` : ""}`)),
    h("span", { class: "row-time" }, relative(entry.recorded_at))));

  return h("div", { class: "page" },
    pageHeader(own ? `Olá, ${driver.name.split(" ")[0]}` : driver.name, {
      back: own ? null : { href: "#/motoristas", label: "Motoristas" },
      lead: own
        ? "O que o sistema registrou sobre você. Nenhuma imagem é gravada: só os eventos abaixo."
        : [driver.company?.name, driver.vehicle ? `veículo ${driver.vehicle.name}` : null].filter(Boolean).join(" · "),
      actions: button("Exportar dados (LGPD)", {
        iconName: "download",
        onClick: async () => {
          try {
            await download(`/api/drivers/${driver.id}/export`, `drivesafe-dados-motorista-${driver.id}.json`);
          } catch (error) {
            toast(error.message, "error");
          }
        },
      }),
    }),
    facts([
      ["Alertas em 7 dias", String(driver.alerts_7d)],
      ["Alertas em 30 dias", String(driver.alerts_30d)],
      ["Último alerta", relative(driver.last_alert_at)],
      own ? null : ["CNH", driver.license_number],
      own ? null : ["Acesso ao app", driver.has_login ? "sim" : "não"],
    ], { className: "panel panel-body" }),
    h("div", { class: "layout-split" },
      h("div", { class: "stack" },
        panel({ title: isToday ? "Hoje, hora a hora" : `Dia ${dayLabel(day.day)}`, km: "01" },
          h("div", { class: "panel-body" }, hourStrip(day.hours, { now: isToday ? localHour(new Date()) : null, size: "large", label: "Pior evento em cada hora" })),
          dayAlerts),
        panel({ title: "Últimos 30 dias", km: "02" }, h("div", { class: "panel-body" }, trendChart(driver.trend, dayLabel)))),
      h("div", { class: "stack" },
        panel({ title: "Autorizações", km: "03", actions: own ? h("a", { class: "btn btn-small", href: "#/consentimentos" }, "Alterar") : null },
          h("ul", { class: "rows" }, consentRows)),
        history.length ? panel({ title: "Histórico das autorizações", km: "04" }, h("ul", { class: "rows" }, history)) : null)));
}

export default function driverView(ctx) {
  return driverPage(ctx, Number(ctx.params.id));
}
