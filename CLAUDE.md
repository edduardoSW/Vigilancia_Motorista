# RotaGuard · instruções para o Claude Code neste repositório

Antes de qualquer coisa, leia **`docs/ESTADO-ATUAL.md`**: o que existe, o que está pela metade, como publicar e as
armadilhas já conhecidas. Depois, `docs/produto/PRD.md` (decisões do Matheus, seção 11) e a spec da área em que for mexer
(`docs/specs/`).

Regras curtas:
- Responder em pt-BR. Dono das decisões: Matheus Cortes.
- Trabalhar no branch `app-instalavel-em-andamento`.
- Método: spec → teste com o ID falhando → código → rodar os testes e mostrar a saída.
- Site e computador com a **mesma versão**: publicar só pelo roteiro de `docs/ESTADO-ATUAL.md` § 6 e conferir o
  carimbo (`versoes.json`) e o SHA-256 depois do deploy.
- Nunca gravar senha, PIN, token ou chave no repositório.
- A VPS é compartilhada com outros sites: nunca mexer nos containers deles.
- `site/` e `painel/app/` têm `AGENTS.md`: o Next.js desta versão difere do que você conhece; consulte
  `node_modules/next/dist/docs/` antes de mudar código de Next.
