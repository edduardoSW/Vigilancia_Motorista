/* Veículos da empresa. */
import { query } from "../api.js";
import { h } from "../dom.js";
import { date } from "../format.js";
import { PENDING_FORMS, listPage } from "./list.js";

export default function vehiclesView(ctx) {
  return listPage(ctx, {
    title: "Veículos",
    endpoint: `/api/vehicles${query({ company_id: ctx.scopeId })}`,
    columns: [
      ["Placa", (vehicle) => h("span", { class: "plate" }, vehicle.plate)],
      ["Modelo", (vehicle) => vehicle.model || "—"],
      ["Tipo", (vehicle) => vehicle.type || "—"],
      ctx.role === "admin" ? ["Empresa", (vehicle) => vehicle.company?.name || "—"] : null,
      ["Cadastrado em", (vehicle) => date(vehicle.created_at)],
    ].filter(Boolean),
    empty: ["Nenhum veículo", "Os veículos cadastrados aparecem aqui."],
    note: PENDING_FORMS,
  });
}
