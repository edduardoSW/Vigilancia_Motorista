/* Motoristas da empresa: alertas da semana, autorização de monitoramento e acesso ao app. */
import { query } from "../api.js";
import { alertKind, chip, h, severityMark } from "../dom.js";
import { relative } from "../format.js";
import { PENDING_FORMS, listPage } from "./list.js";

export default function driversView(ctx) {
  return listPage(ctx, {
    title: "Motoristas",
    lead: "Alertas dos últimos 7 dias e autorização de cada motorista. Clique no nome para ver o dia e os 30 dias.",
    endpoint: `/api/drivers${query({ company_id: ctx.scopeId })}`,
    columns: [
      ["Motorista", (driver) => h("a", { href: `#/motoristas/${driver.id}` }, driver.name)],
      ["CNH", (driver) => h("span", { class: "mono" }, driver.license_number || "—")],
      ["Veículo", (driver) => (driver.vehicle ? h("span", { class: "plate" }, driver.vehicle.name) : "—")],
      ["Alertas em 7 dias", (driver) => (driver.alerts_7d ? severityMark(alertKind(driver.worst_risk_7d), { text: String(driver.alerts_7d) }) : "0")],
      ["Monitoramento", (driver) => (driver.consents.monitoramento ? chip("autorizado", "amber") : chip(driver.consents.monitoramento === false ? "retirado" : "sem registro"))],
      ["Acesso ao app", (driver) => (driver.has_login ? "sim" : "não")],
      ["Último alerta", (driver) => relative(driver.last_alert_at)],
    ],
    empty: ["Nenhum motorista", "Os motoristas cadastrados aparecem aqui."],
    note: PENDING_FORMS,
  });
}
