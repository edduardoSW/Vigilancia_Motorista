/* Página de lista simples (tabela). Usada pelas telas de cadastro enquanto os formulários não ficam prontos. */
import { api } from "../api.js";
import { emptyState, h, pageHeader, panel } from "../dom.js";

export async function listPage(ctx, { title, lead = null, endpoint, rows = null, columns, empty, actions = null, note = null }) {
  ctx.title(title);
  const data = rows || (await api(endpoint, { signal: ctx.signal }));
  const table = data.length
    ? h("div", { class: "table-wrap" },
      h("table", { class: "table" },
        h("thead", null, h("tr", null, columns.map(([header]) => h("th", { scope: "col" }, header)))),
        h("tbody", null, data.map((row) => h("tr", null, columns.map(([, cell]) => h("td", null, cell(row))))))))
    : emptyState(empty[0], empty[1]);
  return h("div", { class: "page" },
    pageHeader(title, { lead, actions }),
    panel({ title: `${data.length} ${data.length === 1 ? "registro" : "registros"}` }, table),
    note ? h("p", { class: "field-hint" }, note) : null);
}

export const PENDING_FORMS = "Cadastro e edição por esta tela: próxima etapa (ver PENDENCIAS.md). No modo servidor, use o manage.py.";
