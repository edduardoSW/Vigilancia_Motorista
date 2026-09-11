/* Relatórios: alertas dos últimos 30 dias em tabela e exportação para Excel (CSV). */
import { api, download, query } from "../api.js";
import { alertKind, button, h, severityMark, toast } from "../dom.js";
import { REVIEW_LABELS, dateTime, duration, localDay } from "../format.js";
import { listPage } from "./list.js";

export default async function reportsView(ctx) {
  const params = { company_id: ctx.scopeId, start: localDay(new Date(Date.now() - 29 * 86400000)) };
  const page = await api(`/api/alerts${query({ ...params, limit: 500 })}`, { signal: ctx.signal });
  return listPage(ctx, {
    title: "Relatórios",
    lead: `Alertas dos últimos 30 dias (${page.total}). O CSV abre direto no Excel, com acentos e vírgula decimal.`,
    rows: page.items,
    actions: button("Baixar CSV", {
      kind: "primary", iconName: "download",
      onClick: async () => {
        try {
          await download(`/api/alerts/export.csv${query(params)}`, "drivesafe-alertas.csv");
        } catch (error) {
          toast(error.message, "error");
        }
      },
    }),
    columns: [
      ["Quando", (alert) => h("span", { class: "mono nowrap" }, dateTime(alert.timestamp))],
      ["Nível", (alert) => severityMark(alertKind(alert.risk_level))],
      ["Evento", (alert) => alert.label],
      ["Motorista", (alert) => alert.driver?.name || "—"],
      ["Veículo", (alert) => alert.vehicle?.name || "—"],
      ["Duração", (alert) => (alert.duration ? duration(alert.duration) : "—")],
      ["Revisão", (alert) => REVIEW_LABELS[alert.review_status] || alert.review_status],
    ],
    empty: ["Nenhum alerta nos últimos 30 dias", "Quando houver eventos, eles aparecem aqui."],
    note: page.total > page.items.length ? `Mostrando ${page.items.length} de ${page.total}. O CSV traz todos.` : null,
  });
}
