# Spec 008 · Site RotaGuard

| Campo | Valor |
|---|---|
| Status | implementada (parcial: tradução e fotos definitivas pendentes) |
| PRD | RF-30, RF-31, RF-32, RF-33, RF-34, RNF-09 |
| Código | `site/` |
| Testes | `site/scripts/testes/*.test.mjs` (`npm test`), mais `npm run build` e `npm run lint` |

> [!note] Escrita depois do código
> O Matheus pediu o site pronto para modificar antes de o método SDD virar regra global (11/09/2026). Esta spec
> documenta o comportamento e amarra cada critério a um teste automático. Mudança nova no site começa aqui.

## Contexto

Site de divulgação do RotaGuard para transportadoras, operadores logísticos, fretamento, ônibus rodoviário e ônibus urbano.

- **Direção visual:** "Escalas", a direção C da avaliação de 11/09/2026 (`docs/site/avaliacoes/2026-09-11-previa-v2/`).
- **Stack:** Next.js + Tailwind + next-intl, nunca HTML estático.
- **Idiomas:** pt-BR, en, es, fr e zh-CN, escolhidos num menu com bandeira e nome do país.

## Comportamento

- **Primeira tela**
  - Dado um visitante no computador (1440×900), quando a página abre, então ele vê o título, o texto curto, o botão
    de WhatsApp, o mapa-múndi com a noite daquele instante e as três portas fotográficas (carga, fretamento, urbano)
    sem rolar.
- **Menu de idioma**
  - Dado o menu de idioma aberto, quando a pessoa escolhe outro país, então a mesma rota abre no outro idioma
    (`/pt-BR` → `/en`), com `lang` e `hreflang` corretos.
- **Contato**
  - Dado o número de WhatsApp não configurado, quando a página renderiza, então os botões aparecem desativados com
    aviso. Nunca como link morto.
- **Área de download**
  - Dado um PIN errado 5 vezes em 15 min no mesmo IP, quando a pessoa tenta de novo, então recebe "muitas
    tentativas" e o PIN nem é conferido.
  - Dado o PIN certo, quando a pessoa entra, então recebe um cookie httpOnly assinado com validade de 12 h e vai
    para `/<idioma>/app`.
  - Dado alguém sem sessão válida, quando abre `/<idioma>/app`, então é mandado para `/<idioma>/entrar`.
- **Mapas e rota**
  - Dado o mapa da malha, quando é renderizado, então usa a geometria do SNV/DNIT e as divisas do IBGE, e a
    extensão citada é a do SNV (74.829 km), não a soma da geometria.
  - Dada a rota BR-116, quando aparece, então leva o aviso "Viagem de demonstração. O RotaGuard não registra
    localização", sem pino de evento no mapa.

## Critérios de aceite

| ID | Critério | Teste |
|---|---|---|
| SITE-01 | `npm run build` sem erro | build |
| SITE-02 | `npm run lint` sem erro | lint |
| SITE-03 | Os 5 idiomas têm as mesmas chaves, sem texto copiado do português e com os mesmos placeholders | `i18n.test.mjs` |
| SITE-04 | Nenhuma das afirmações falsas da prévia v2 volta; as ressalvas "não é diagnóstico", "viagem de demonstração" e "em validação" estão no texto | `veracidade.test.mjs` |
| SITE-05 | PIN por hash scrypt; sessão assinada com validade; bloqueio após 5 erros por 15 min | `sessao.test.mjs` |
| SITE-06 | A noite do mapa-múndi vem do ponto subsolar calculado (erro < 0,6° nas datas de referência) | `solar.test.mjs` |
| SITE-07 | HTML gerado sem `href="#"`, com `lang` e `hreflang` dos 5 idiomas e `x-default`, e `noindex` enquanto for prévia | `html.test.mjs` |
| SITE-08 | HTML inicial de cada idioma abaixo de 700 KB | `html.test.mjs` |
| SITE-09 | Contraste AA dos tokens de texto (valores calculados no topo de `globals.css`) | revisão (automatizar com a paleta final) |
| SITE-10 | Com `prefers-reduced-motion`, a rota já aparece desenhada e não há animação | revisão manual |

## Fora de escopo agora

- Páginas por segmento (`/carga-e-logistica` etc.): próxima versão, depois das respostas do Matheus (`00-consolidado.md`).
- Medição (Umami ou Vercel).
- Fotos definitivas: seguem `docs/site/midia/`; hoje o site usa fotos provisórias de licença livre.

## Riscos e pendências

- **Licença das bases:** o SNV (DNIT) e a malha do IBGE não trazem licença escrita; o rodapé do gov.br do DNIT fala em
  CC BY-ND, que proibiria a simplificação. Confirmar com os órgãos antes de publicar (`docs/site/dados-mapas.md`).
- **Contato e preço:** número de WhatsApp, oferta de piloto e preço dependem do Matheus.
- **Área de download:** o PIN libera só downloads; usa Server Action e cookie, então o site precisa de Node
  (`next start` ou Vercel).
