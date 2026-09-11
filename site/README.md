# RotaGuard · site de produto

Next.js 16 + Tailwind 4 + next-intl. Cinco idiomas: português, inglês, espanhol, francês e chinês simplificado.

## Rodar

```powershell
npm install
npm run dev
```

Abra http://localhost:3000/pt-BR.

## Verificar

```powershell
npm run build
npm run lint
npm test
node scripts/testes/navegador.mjs
npm run prints -- http://localhost:3000/pt-BR ../docs/site/prints/reformulacao-2026-09-11
```

A verificação de navegador usa o Edge local em modo headless. O teste opcional do PIN real recebe `ROTAGUARD_TEST_PIN` somente no ambiente do processo. Nunca coloque o PIN em arquivo, documentação ou commit.

## Organização

- `src/components/product-home.tsx`: apresentação, detalhes da caixa, seleção de frotas, etapas da viagem, FAQ e contato.
- `src/app/globals.css`: direção visual, tokens e responsividade.
- `messages/`: todos os textos nos cinco idiomas.
- `src/lib/acesso-local.ts`: conferência SHA-256 com sal e sessão local de 12 horas.
- `public/midia/rotaguard/`: imagens WebP e vídeo local usados na página.
- `../docs/site/midia/README.md`: índice de imagens, fontes e prompts.
- `../docs/specs/008-site.md`: requisitos e aceite desta versão.

## Acesso

PIN conferido no navegador; somente hash e sal no código. `rotaguard.acesso` fica no localStorage com validade de 12 horas; cinco erros geram uma pausa local de 15 minutos. Acesso sem sessão redireciona para entrar, e sair remove a sessão.

Isso é uma barreira de demonstração, controlável pelo próprio navegador, não autenticação de produção. Não protege dados reais ou APIs. Para uso comercial com dados reais, implementar autenticação no servidor.

## Configuração comercial

Copie `.env.example` para `.env.local`. Informe WhatsApp/telefone, domínio, URLs reais dos instaladores e PWA quando disponíveis. O site não inventa contatos ou downloads.

O produto é um protótipo: coleta automática, registro completo, trechos por recorrência e relatórios estão apresentados como recursos em desenvolvimento. As imagens de pessoas e veículos são geradas por IA; as imagens da caixa representam conceitos de design.

## Direção visual

Fotografia de estrada, hardware em destaque, verde profundo, branco e lima. Space Grotesk para títulos e Manrope para leitura. Prioridade para ônibus rodoviários interestaduais, seguida de carga/logística. Sem mapa-múndi, régua lateral ou painel SaaS.

A alteração permanece na branch `app-instalavel-em-andamento`, sem publicação ou push automático.
