/* Minha empresa (gestor): dados cadastrais, política dos sinais de ativação e acessos da empresa. */
import { api, query } from "../api.js";
import { button, chip, confirmDialog, facts, h, pageHeader, panel, toast } from "../dom.js";
import { POLICIES, ROLE_LABELS, relative } from "../format.js";
import { session } from "../session.js";

export default async function companyView(ctx) {
  ctx.title("Minha empresa");
  const [companies, users] = await Promise.all([
    api("/api/companies", { signal: ctx.signal }),
    api(`/api/users${query({})}`, { signal: ctx.signal }),
  ]);
  const company = companies[0];

  const policyForm = h("form", { class: "stack" },
    h("div", { class: "choice-row" }, POLICIES.map((policy) => h("label", { class: "choice" },
      h("input", { type: "radio", name: "policy", value: policy.value, checked: company.activation_policy === policy.value }),
      h("span", { class: "choice-title" }, policy.title),
      h("span", { class: "choice-text" }, policy.text)))),
    h("div", { class: "form-actions" }, h("button", { type: "submit", class: "btn btn-primary" }, "Salvar política")));
  policyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(`/api/companies/${company.id}`, { method: "PATCH", body: { activation_policy: new FormData(policyForm).get("policy") } });
      toast("Política salva. Os equipamentos recebem no próximo sinal.");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  const userRows = users.map((user) => h("li", { class: "row row-person" },
    user.active ? chip("ativo", "amber") : chip("bloqueado", "red"),
    h("span", { class: "row-main-wrap" },
      h("span", { class: "row-main" }, user.name),
      h("span", { class: "row-sub" }, `${ROLE_LABELS[user.role]} · último acesso ${relative(user.last_login_at)}`)),
    user.active && user.id !== session.me.id
      ? button("Bloquear", {
        small: true, kind: "danger", iconName: "ban",
        onClick: async () => {
          const ok = await confirmDialog({ title: `Bloquear o acesso de ${user.name}?`, message: "A pessoa sai do app na hora. Para liberar de novo, fale com a equipe DriveSafe.", confirmLabel: "Bloquear", danger: true });
          if (!ok) return;
          try {
            await api(`/api/users/${user.id}`, { method: "PATCH", body: { active: false } });
            toast("Acesso bloqueado.");
            ctx.rerender();
          } catch (error) {
            toast(error.message, "error");
          }
        },
      })
      : h("span")));

  return h("div", { class: "page" },
    pageHeader(company.name, { lead: "Para mudar dados cadastrais ou pedir novos acessos, fale com a equipe DriveSafe pelo celular." }),
    h("div", { class: "layout-halves" },
      h("div", { class: "stack" },
        panel({ title: "Cadastro", km: "01" }, h("div", { class: "panel-body" },
          facts([["CNPJ", company.document], ["Responsável", company.contact_name], ["Celular", company.contact_phone], ["Motoristas", String(company.drivers)], ["Veículos", String(company.vehicles)], ["Dispositivos", String(company.devices)]]))),
        panel({ title: "Sinais de ativação atípica", km: "02", lead: "Não é diagnóstico nem exame toxicológico. “Enviar” só vale para quem autorizou." },
          h("div", { class: "panel-body" }, policyForm))),
      panel({ title: "Acessos da empresa", km: "03" }, h("ul", { class: "rows" }, userRows))));
}
