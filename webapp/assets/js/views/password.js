/* Primeiro acesso: troca da senha temporária criada pela equipe. */
import { api } from "../api.js";
import { button, field, h, toast } from "../dom.js";
import { endSession, home, navigate, session, startSession } from "../session.js";

export function passwordForm({ temporary = false, onDone }) {
  const current = h("input", { type: "password", name: "current", class: "input", autocomplete: "current-password", required: true });
  const next = h("input", { type: "password", name: "next", class: "input", autocomplete: "new-password", required: true, minLength: 10 });
  const repeat = h("input", { type: "password", name: "repeat", class: "input", autocomplete: "new-password", required: true, minLength: 10 });
  const error = h("p", { class: "form-error", role: "alert" });
  const submit = h("button", { type: "submit", class: "btn btn-primary" }, temporary ? "Criar minha senha" : "Trocar a senha");
  const form = h("form", { class: "dialog-form" },
    field(temporary ? "Senha temporária" : "Senha atual", current),
    field("Nova senha", next, { hint: "Pelo menos 10 caracteres. Uma frase curta é mais fácil de lembrar e difícil de adivinhar." }),
    field("Repita a nova senha", repeat),
    error,
    h("div", { class: "form-actions" }, submit));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    if (next.value !== repeat.value) {
      error.textContent = "As duas senhas novas não são iguais.";
      repeat.focus();
      return;
    }
    submit.disabled = true;
    try {
      await api("/api/auth/password", { method: "POST", body: { current_password: current.value, new_password: next.value } });
      form.reset();
      await onDone();
    } catch (problem) {
      error.textContent = problem.message;
    } finally {
      submit.disabled = false;
    }
  });
  return form;
}

export default async function passwordView(ctx) {
  ctx.title("Criar sua senha");
  const me = session.me;
  if (!me.must_change_password) {
    navigate(home(), { replace: true });
    return h("div");
  }
  const form = passwordForm({
    temporary: true,
    onDone: async () => {
      me.must_change_password = false;
      await startSession(me);
      toast("Senha criada. Bem-vindo ao DriveSafe.");
      navigate(home(), { replace: true });
    },
  });
  requestAnimationFrame(() => form.querySelector("input")?.focus());
  return h("main", { id: "main", class: "password-page", tabIndex: -1 },
    h("div", { class: "password-card" },
      h("h1", { class: "page-title" }, "Crie a sua senha"),
      h("p", { class: "muted" }, `Olá, ${me.name.split(" ")[0]}. Você entrou com a senha temporária enviada pela equipe DriveSafe. Escolha agora uma senha só sua.`),
      form,
      button("Sair", { kind: "ghost", iconName: "logout", onClick: () => endSession() })));
}
