/* Conta: dados de acesso, senha, tema, instalar o app e contato com a equipe. */
import { button, facts, h, icon, pageHeader, panel, toast } from "../dom.js";
import { ROLE_LABELS } from "../format.js";
import { currentTheme, endSession, session, setTheme } from "../session.js";
import { accessBox } from "./login.js";
import { passwordForm } from "./password.js";

function themeChooser() {
  const options = [["noite", "Noite", "Carvão quente, para cabine e sala escura."], ["dia", "Dia", "Papel claro, para ambiente iluminado."]];
  const group = h("div", { class: "choice-row", role: "radiogroup", "aria-label": "Tema" });
  for (const [value, title, text] of options) {
    const input = h("input", { type: "radio", name: "tema", value, checked: currentTheme() === value });
    input.addEventListener("change", () => setTheme(value));
    group.append(h("label", { class: "choice" }, input, h("span", { class: "choice-title" }, title), h("span", { class: "choice-text" }, text)));
  }
  return group;
}

function installPanel() {
  const body = h("div", { class: "panel-body stack" });
  const paint = () => {
    const prompt = session.installPrompt;
    const standalone = window.matchMedia("(display-mode: standalone)").matches;
    body.replaceChildren(
      standalone
        ? h("p", null, "Você já está usando o app instalado.")
        : prompt
          ? button("Instalar o DriveSafe neste aparelho", {
            kind: "primary", iconName: "install",
            onClick: async () => {
              prompt.prompt();
              await prompt.userChoice.catch(() => null);
              session.installPrompt = null;
              paint();
            },
          })
          : h("ul", { class: "muted" },
            h("li", null, "Computador (Chrome ou Edge): ícone de instalar na barra de endereço, ou menu ⋮ → Instalar DriveSafe."),
            h("li", null, "Android (Chrome): menu ⋮ → Instalar app."),
            h("li", null, "iPhone (Safari): Compartilhar → Adicionar à Tela de Início.")),
      h("p", { class: "field-hint" }, "Fora deste computador, o navegador só oferece a instalação quando o servidor usa HTTPS."),
    );
  };
  paint();
  return { body, paint };
}

export default async function accountView(ctx) {
  ctx.title("Sua conta");
  const me = session.me;
  const install = installPanel();
  ctx.listen(document, "drivesafe:instalar", install.paint);

  return h("div", { class: "page" },
    pageHeader("Sua conta", {
      lead: `${ROLE_LABELS[me.role]}${me.company ? ` · ${me.company.name}` : ""}`,
      actions: button("Sair", { iconName: "logout", onClick: () => endSession() }),
    }),
    h("div", { class: "layout-halves" },
      h("div", { class: "stack" },
        panel({ title: "Dados de acesso", km: "01" },
          h("div", { class: "panel-body stack" },
            facts([["Nome", me.name], ["E-mail", me.email], ["Celular", me.phone], ["Perfil", ROLE_LABELS[me.role]], ["Empresa", me.company?.name]]),
            h("p", { class: "field-hint" }, "Para mudar nome, e-mail ou celular de acesso, fale com a equipe DriveSafe."))),
        panel({ title: "Trocar a senha", km: "02" },
          h("div", { class: "panel-body" },
            passwordForm({ onDone: async () => toast("Senha trocada. As outras sessões abertas foram encerradas.") })))),
      h("div", { class: "stack" },
        panel({ title: "Aparência", km: "03" }, h("div", { class: "panel-body" }, themeChooser())),
        panel({ title: "Instalar o app", km: "04" }, install.body),
        panel({ title: "Ajuda", km: "05" },
          h("div", { class: "panel-body" }, accessBox(session.info?.contact)),
          h("p", { class: "panel-foot field-hint" }, icon("info", { size: 14 }), ` DriveSafe AI ${session.info?.version || ""}`)))));
}
