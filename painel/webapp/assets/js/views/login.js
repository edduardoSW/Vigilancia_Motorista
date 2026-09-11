/* Entrar. Não há cadastro: quem não tem acesso fala com a equipe pelo celular. */
import { api, localServer } from "../api.js";
import { IS_LOCAL } from "../config.js";
import { h, icon, s } from "../dom.js";
import { home, navigate, session, startSession } from "../session.js";

function sign() {
  return s("svg", { viewBox: "0 0 200 200", class: "login-sign", "aria-hidden": "true" },
    s("path", { d: "M100 6 194 100 100 194 6 100z", class: "login-sign-plate" }),
    s("path", { d: "M100 22 178 100 100 178 22 100z", class: "login-sign-border" }),
    s("path", { d: "M58 92q42 40 84 0", class: "login-sign-lid" }),
    s("path", { d: "M73 116l-9 17 M100 126v20 M127 116l9 17", class: "login-sign-lashes" }));
}

function brandMark() {
  return s("svg", { viewBox: "0 0 32 32", class: "brand-mark", "aria-hidden": "true" },
    s("path", { d: "M16 1.8 30.2 16 16 30.2 1.8 16z", class: "brand-sign" }),
    s("path", { d: "M9.6 15.2q6.4 5.8 12.8 0", class: "brand-lid" }));
}

export function accessBox(contact) {
  return h("aside", { class: "access-box", "aria-labelledby": "acesso-titulo" },
    h("h2", { class: "access-title", id: "acesso-titulo" }, "Ainda não tem acesso?"),
    h("p", null, "Não existe cadastro aberto. A equipe DriveSafe cria o login de cada empresa, gestor e motorista."),
    contact
      ? [
        h("p", { class: "access-phone" }, icon("phone", { size: 18 }), h("span", null, "Fale com a equipe pelo celular:"),
          h("strong", { class: "mono" }, contact.phone)),
        h("div", { class: "access-actions" },
          h("a", { class: "btn btn-small", href: contact.tel_url }, icon("call", { size: 16 }), h("span", null, "Ligar")),
          contact.whatsapp_url
            ? h("a", { class: "btn btn-small", href: contact.whatsapp_url, target: "_blank", rel: "noopener noreferrer" },
              icon("chat", { size: 16 }), h("span", null, "WhatsApp"))
            : null),
      ]
      : h("p", { class: "muted" }, "Peça o acesso ao responsável pela sua transportadora."),
    h("p", { class: "access-note" }, "Esqueceu a senha? A equipe gera uma senha temporária, e você cria a sua no primeiro acesso."));
}

function hero() {
  return h("section", { class: "login-hero", "aria-label": "DriveSafe AI" },
    h("div", { class: "login-brand" }, brandMark(), h("span", null, "DriveSafe AI")),
    h("div", { class: "login-hero-body" },
      sign(),
      h("h1", { class: "login-headline" }, "Olhos na estrada, aviso na hora."),
      h("p", { class: "login-lead" }, "Sonolência e uso de celular ao volante, medidos dentro do veículo. Nenhuma imagem é gravada: chegam só os eventos.")),
    h("div", { class: "login-road", "aria-hidden": "true" }));
}

const LOCAL_ROLE_TEXT = { admin: "Equipe DriveSafe · testes", gestor: "Gestor da empresa", motorista: "Motorista" };

/** Modo de teste local: escolhe a conta de exemplo e entra com o PIN de teste. */
async function localLoginView(ctx) {
  const { localAccounts } = await localServer();
  const accounts = localAccounts();
  const choices = h("div", { class: "choice-group", role: "radiogroup", "aria-label": "Conta de teste" },
    accounts.map((account, index) => h("label", { class: "choice" },
      h("input", { type: "radio", name: "conta", value: account.login, checked: index === 0 }),
      h("span", { class: "choice-title" }, account.name),
      h("span", { class: "choice-text" }, [LOCAL_ROLE_TEXT[account.role], account.company].filter(Boolean).join(" · ")))));
  const pin = h("input", {
    id: "login-pin", name: "pin", type: "password", class: "input input-mono", inputmode: "numeric",
    autocomplete: "off", maxLength: 8, required: true,
  });
  const error = h("p", { class: "form-error", role: "alert" });
  const submit = h("button", { type: "submit", class: "btn btn-primary btn-block" }, "Entrar");
  const form = h("form", { class: "login-form" },
    h("fieldset", { class: "choice-group" }, h("legend", { class: "field-label" }, "Entrar como"), choices),
    h("div", { class: "field" }, h("label", { class: "field-label", for: "login-pin" }, "PIN de teste"), pin),
    error, submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    submit.disabled = true;
    try {
      const login = new FormData(form).get("conta");
      const me = await api("/api/auth/login", { method: "POST", body: { login, password: pin.value.trim() } });
      await startSession(me);
      const target = session.redirectAfterLogin || home(me.role);
      session.redirectAfterLogin = null;
      navigate(target, { replace: true });
    } catch (problem) {
      error.textContent = problem.message;
      pin.select();
      submit.disabled = false;
    }
  });
  requestAnimationFrame(() => pin.focus());
  return h("div", { class: "login" }, hero(),
    h("main", { id: "main", class: "login-panel", tabIndex: -1 },
      h("div", { class: "login-card" },
        h("h2", { class: "login-title" }, "Entrar"),
        h("div", { class: "notice-box" },
          h("p", { class: "notice-title" }, "Modo de teste local"),
          h("p", null, "Sem servidor e sem banco: os dados são de exemplo e ficam só neste navegador.")),
        form)));
}

export default async function loginView(ctx) {
  ctx.title("Entrar");
  if (IS_LOCAL) return localLoginView(ctx);
  const info = session.info || {};

  const loginInput = h("input", {
    id: "login-id", name: "login", type: "text", class: "input", autocomplete: "username", required: true,
    autocapitalize: "none", spellcheck: false, placeholder: "voce@empresa.com ou (11) 98765-4321",
  });
  const passwordInput = h("input", { id: "login-senha", name: "password", type: "password", class: "input", autocomplete: "current-password", required: true });
  const toggle = h("button", { type: "button", class: "input-addon", "aria-label": "Mostrar a senha", "aria-pressed": "false" }, icon("eye"));
  toggle.addEventListener("click", () => {
    const show = passwordInput.type === "password";
    passwordInput.type = show ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(show));
    toggle.setAttribute("aria-label", show ? "Esconder a senha" : "Mostrar a senha");
  });

  const error = h("p", { class: "form-error", role: "alert" });
  const submit = h("button", { type: "submit", class: "btn btn-primary btn-block" }, "Entrar");
  const form = h("form", { class: "login-form" },
    h("div", { class: "field" }, h("label", { class: "field-label", for: "login-id" }, "E-mail ou celular"), loginInput),
    h("div", { class: "field" }, h("label", { class: "field-label", for: "login-senha" }, "Senha"),
      h("div", { class: "input-group" }, passwordInput, toggle)),
    error,
    submit);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    submit.disabled = true;
    submit.textContent = "Entrando…";
    try {
      const me = await api("/api/auth/login", {
        method: "POST", body: { login: loginInput.value.trim(), password: passwordInput.value },
      });
      await startSession(me);
      const target = me.must_change_password ? "/trocar-senha" : session.redirectAfterLogin || home(me.role);
      session.redirectAfterLogin = null;
      navigate(target, { replace: true });
    } catch (problem) {
      error.textContent = problem.message;
      passwordInput.select();
      submit.disabled = false;
      submit.textContent = "Entrar";
    }
  });

  requestAnimationFrame(() => loginInput.focus());

  return h("div", { class: "login" },
    hero(),
    h("main", { id: "main", class: "login-panel", tabIndex: -1 },
      h("div", { class: "login-card" },
        h("h2", { class: "login-title" }, "Entrar"),
        form,
        accessBox(info.contact))));
}
