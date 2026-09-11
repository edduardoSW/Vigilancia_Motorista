/* Autorizações do motorista (LGPD): dar ou retirar, com histórico. Registrar de novo nunca apaga o anterior. */
import { api } from "../api.js";
import { button, chip, emptyState, h, pageHeader, toast } from "../dom.js";
import { CONSENTS, relative } from "../format.js";

export default async function consentsView(ctx) {
  ctx.title("Minhas autorizações");
  const driverId = ctx.me.driver_id;
  if (!driverId) return emptyState("Conta sem motorista vinculado", "Peça à equipe DriveSafe para ligar seu acesso ao cadastro de motorista.");
  const driver = await api(`/api/drivers/${driverId}`, { signal: ctx.signal });

  const cards = CONSENTS.map((item) => {
    const state = driver.consents[item.kind];
    const last = driver.consent_history.find((entry) => entry.kind === item.kind);
    return h("article", { class: "consent" },
      h("div", null,
        h("h2", { class: "consent-title" }, item.title),
        h("p", { class: "consent-text" }, item.text),
        h("p", { class: ["consent-state", state && "is-on"] },
          state ? "Autorizado" : state === false ? "Autorização retirada" : "Ainda sem registro",
          last ? h("span", { class: "faint" }, ` · ${relative(last.recorded_at)}`) : null)),
      h("div", { class: "consent-actions" },
        button(state ? "Retirar autorização" : "Autorizar", {
          kind: state ? "danger" : "primary",
          onClick: async () => {
            try {
              await api(`/api/drivers/${driverId}/consents`, { method: "POST", body: { kind: item.kind, granted: !state, channel: "app_motorista" } });
              toast(state ? "Autorização retirada." : "Autorização registrada.");
              ctx.rerender();
            } catch (error) {
              toast(error.message, "error");
            }
          },
        }),
        state === undefined ? chip("sem registro") : null));
  });

  return h("div", { class: "page" },
    pageHeader("Minhas autorizações", {
      lead: "Você decide. Cada mudança fica registrada com data, e a empresa vê o histórico. Retirar a autorização do perfil apaga o perfil guardado no equipamento na próxima conexão.",
    }),
    h("div", { class: "consent-list" }, cards));
}
