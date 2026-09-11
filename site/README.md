# Site RotaGuard

Next.js 16.3.4 · React 19.3.0 · Tailwind CSS 4.3.3 · next-intl 4.14.4 · TypeScript 6.0.3 · ESLint 9.39.5.
Idiomas: português (Brasil), inglês, espanhol, francês e chinês.

## Rodar

```bash
cd site
npm install
npm run dev          # http://localhost:3000/pt-BR
npm run build        # prova 1
npm run lint         # prova 2 (as duas precisam passar)
npm run start        # serve o build
```

Prints de página inteira (computador 1440×900 e celular 400×850), com o Edge ou o Chrome sem janela:

```bash
npm run build && npx next start -p 3100
node scripts/prints/tirar-prints.mjs http://localhost:3100/pt-BR ../docs/site/prints/AAAA-MM-DD
```

## Onde mexer

| Quero mudar | Arquivo |
|---|---|
| Qualquer texto do site | `messages/pt-BR.json` (e o mesmo caminho em `en.json`, `es.json`, `fr.json`, `zh-CN.json`) |
| Ordem das seções da página inicial | `src/app/[locale]/page.tsx` |
| Uma seção | `src/components/sections/<nome>.tsx` |
| Cores, fontes, botões | `src/app/globals.css` (tokens em `:root`; botões em `@layer components`) |
| Idiomas do seletor, bandeira e país | `src/content/idiomas.ts` (bandeiras em `src/components/flag.tsx`) |
| Escalas da régua lateral | `src/content/escalas.ts` |
| WhatsApp, telefone, domínio | variáveis de ambiente (ver `.env.example`) ou `src/content/site.ts` |
| Links de download do app | `src/content/downloads.ts` e `NEXT_PUBLIC_ROTAGUARD_DOWNLOADS_BASE` |
| Situação dos itens da ficha técnica | `src/components/sections/ficha-tecnica.tsx` |

## Direção visual: "Escalas"

O site muda de escala como um mapa: mundo (1:40 000 000) → Brasil → a rota → a rodovia → a cabine (1:20) → o olho (1:1)
→ a garagem → o relatório. A régua na borda esquerda (telas largas) ou a faixa sob o cabeçalho (celular) é a navegação.

- **Cores:** neutros de concreto e asfalto; o escuro só nas cenas fotográficas; a única cor saturada é a do alarme.
  Contrastes calculados pela WCAG (valores no topo do `globals.css`).
- **Fontes:** Sofia Sans Extra Condensed (títulos), Sofia Sans (texto), B612 (voz do instrumento: escalas, dados).
  Todas por `next/font/google`, servidas pelo próprio site.
- **Proibido voltar:** hero de SaaS com widget, mono como enfeite, fundo escuro de interface com âmbar, janela falsa,
  JSON, mira ou pontos sobre rosto, brilho, laço infinito, cartões iguais, selo "em piloto", tracejado de estrada.
- **Tailwind 4:** token e override fora de camada; regra de elemento em `@layer base`; primitivo em `@layer components`
  (regra sem camada vence utilitário). Não criar classe com nome de utilitário (`overline`, `col-7`, `table`).

## Mapas (dado real, nunca IA)

Arquivos em `src/data/mapas/`, gerados por `npm run mapas` (scripts em `scripts/mapas/`). Fontes, licenças e
atribuições em `../docs/site/dados-mapas.md`. O produto não registra localização: nada de pino de veículo ou evento;
a rota é sempre "viagem de demonstração".

- A noite no mapa-múndi é calculada no navegador pela posição do Sol (`src/lib/solar.ts`, fórmulas da NOAA).
- A malha federal e a rota são desenhadas no build com `d3-geo` (Albers com os parâmetros do IBGE).

## Fotos

- Hoje são **provisórias**, de bancos com licença livre: `public/fotos/provisorias/`, com o manifesto em
  `src/data/fotos-provisorias.json` e os créditos na página `/creditos`.
- A série definitiva sai do roteiro de mídia em `../docs/site/midia/`. Para trocar uma foto, substitua o arquivo e
  atualize o manifesto (código da cena, autor, licença e texto alternativo).
- Sem foto para um código, a cena aparece como um bloco com o nome dela, sem quebrar o layout.

## Área do cliente (PIN)

- `/<idioma>/entrar` confere o PIN no servidor; `/<idioma>/app` mostra os downloads do app.
- O PIN **nunca** fica no código. Gere o hash com `node scripts/gerar-hash-pin.mjs` e ponha as duas linhas em
  `site/.env.local` (fora do git) ou nas variáveis do servidor.
- O PIN libera só o download do app. Não protege dado de motorista.
- Por usar cookie e Server Action, o site precisa rodar com Node (`next start` ou Vercel), não como exportação estática.

## Travas de versão

- **TypeScript 6.0.3**, não a 7.0.2 (`latest`): o `typescript-eslint` 8.70.0 aceita só `<6.1.0`.
- **ESLint 9.39.5** (tag `maintenance`), não a 10: o `eslint-plugin-react` do `eslint-config-next` quebra no 10
  (erro 30 do vault).
