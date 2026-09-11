/* Empresas clientes (equipe DriveSafe). */
import { chip, h } from "../dom.js";
import { POLICIES } from "../format.js";
import { PENDING_FORMS, listPage } from "./list.js";

export default function companiesView(ctx) {
  return listPage(ctx, {
    title: "Empresas",
    lead: "Transportadoras na plataforma. Cada uma só enxerga os próprios motoristas, veículos e alertas.",
    endpoint: "/api/companies",
    columns: [
      ["Empresa", (company) => h("span", null, h("span", { class: "row-main" }, company.name), h("span", { class: "row-sub" }, company.document || "sem CNPJ"))],
      ["Responsável", (company) => [company.contact_name, company.contact_phone].filter(Boolean).join(" · ") || "—"],
      ["Motoristas", (company) => String(company.drivers)],
      ["Veículos", (company) => String(company.vehicles)],
      ["Dispositivos", (company) => String(company.devices)],
      ["Acessos", (company) => String(company.users)],
      ["Sinais de ativação", (company) => POLICIES.find((policy) => policy.value === company.activation_policy)?.title || company.activation_policy],
      ["Situação", (company) => (company.active ? chip("ativa", "amber") : chip("inativa", "red"))],
    ],
    empty: ["Nenhuma empresa", "As empresas cadastradas aparecem aqui."],
    note: PENDING_FORMS,
  });
}
