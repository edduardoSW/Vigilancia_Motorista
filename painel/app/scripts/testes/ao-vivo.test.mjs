// Spec 018 · tela "Teste neste computador": frase-resumo por categoria, nomes dos tipos e regras visuais do contrato.
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import { categoriaDe, nomeDoTipo, resumoDosEventos } from "../../src/components/live/summary.ts";

const raiz = path.join(import.meta.dirname, "..", "..");
const tipos = JSON.parse(readFileSync(path.join(raiz, "src", "content", "tipos-de-evento.json"), "utf8"));
const eventos = (...lista) => lista.map((tipo) => ({ tipo }));

test("SCR-11 frase-resumo por categoria: '3 de sono e 1 de celular'", () => {
  assert.equal(resumoDosEventos(eventos("sono", "microssono", "atencao", "celular_no_ouvido"), tipos), "3 de sono e 1 de celular");
  assert.equal(resumoDosEventos(eventos("olhando_celular"), tipos), "1 de celular");
  assert.equal(
    resumoDosEventos(eventos("celular_na_mao", "sono", "rosto_nao_detectado", "calibracao_suspeita"), tipos),
    "1 de sono, 1 de celular, 1 da câmera ou calibração e 1 de outro tipo",
  );
  assert.equal(resumoDosEventos([], tipos), "Nenhum evento");
});

test("SCR-12 nomes dos tipos vêm de tipos-de-evento.json; tipo desconhecido não quebra", () => {
  assert.equal(nomeDoTipo("sono", tipos), "Sono (olhos fechados 3 s)");
  assert.equal(nomeDoTipo("calibracao_suspeita", tipos), "calibracao suspeita");
  assert.equal(categoriaDe("mao_no_rosto", tipos), "sonolencia");
  assert.equal(categoriaDe("xyz", tipos), "outro");
});

test("SCR-13 tela ao vivo: consulta a ponte (3 s e 2 s), para ao sair, ponto só aberto, sem pílula nem maiúsculas", () => {
  const pasta = path.join(raiz, "src", "components", "live");
  const fontes = [path.join(raiz, "src", "app", "ao-vivo", "page.tsx"), ...readdirSync(pasta).map((nome) => path.join(pasta, nome))]
    .map((caminho) => readFileSync(caminho, "utf8"))
    .join("\n");
  assert.match(fontes, /bridge\.script_estado\(\)/);
  assert.match(fontes, /bridge\.script_eventos\(/);
  assert.match(fontes, /3000/);
  assert.match(fontes, /2000/);
  assert.match(fontes, /clearInterval|clearTimeout/);
  assert.match(fontes, /export function LiveScriptCard\(\)/);
  assert.match(fontes, /O script não está aberto\. Abra o RotaGuard Teste neste computador e ele aparece aqui sozinho\./);
  assert.match(fontes, /aberto && <span[^>]*pulse-dot/);
  assert.match(fontes, /anim-row/);
  assert.doesNotMatch(fontes, /rounded-full[^"]*px-|uppercase|font-mono/);
});
