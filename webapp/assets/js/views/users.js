/* Acessos ao app (equipe DriveSafe). Não há cadastro aberto: só a equipe cria logins. */
import { query } from "../api.js";
import { chip, h } from "../dom.js";
import { ROLE_LABELS, relative } from "../format.js";
import { PENDING_FORMS, listPage } from "./list.js";

export default function usersView(ctx) {
  return listPage(ctx, {
    title: "Acessos",
    lead: "Quem entra no app. Os logins são criados pela equipe DriveSafe (e-mail ou celular); ninguém se cadastra sozinho.",
    endpoint: `/api/users${query({ company_id: ctx.scopeId })}`,
    columns: [
      ["Nome", (user) => user.name],
      ["Login", (user) => h("span", { class: "mono" }, [user.email, user.phone].filter(Boolean).join(" · ") || "—")],
      ["Perfil", (user) => ROLE_LABELS[user.role]],
      ["Empresa", (user) => user.company?.name || "—"],
      ["Motorista", (user) => user.driver?.name || "—"],
      ["Situação", (user) => (user.active ? chip("ativo", "amber") : chip("bloqueado", "red"))],
      ["Último acesso", (user) => relative(user.last_login_at)],
    ],
    empty: ["Nenhum acesso", "Os acessos criados pela equipe aparecem aqui."],
    note: PENDING_FORMS,
  });
}
