# Spec 008 · Site RotaGuard · reformulação 11/09/2026

Status: implementado para revisão visual. Substitui a direção Escalas rejeitada. Escopo desta entrega: site de apresentação, imagens, acesso local e documentação do site. As implementações da caixa/backend/app seguem specs próprias.

## Produto e público

Empresas de ônibus rodoviários interestaduais são o público principal; transportadoras e logística são o segundo segmento. A caixa e o ciclo na cabine → na estrada → na chegada conduzem a página. Nenhum ônibus urbano, mapa de localização, painel web como promessa ou afirmação de eficácia não medida.

## Direção

Verde profundo #103e31, branco #fafcf7 e lima #d5f669; títulos Space Grotesk e corpo Manrope. Hero fotográfico de ônibus com texto curto e caixa conceitual visível. Seção do dispositivo com pontos interativos, seleção de frotas, etapas com foto da coleta e exemplo de relatório, compromisso com motorista, FAQ e contato. Sem régua lateral, mapa-múndi, escalas e tipografia da versão rejeitada.

Referências consultadas: apresentação de hardware DJI Osmo Action e câmera de frota Samsara. A preferência de paleta foi perguntada enquanto a prévia era preparada; sem resposta, foi aplicada a proposta informada. A aprovação estética continua sendo do usuário.

## Comportamento

- Cinco rotas de idioma, dropdown com bandeira e país, textos efetivamente traduzidos, lang/hreflang e metadados.
- Abas de frota atualizam imagem e texto; teclado com setas, Home e End.
- Pontos do produto abrem descrições correspondentes.
- Etapas da viagem alternam cena e explicação; a chegada destaca o diferencial do produto.
- FAQ nativo abre sem JavaScript adicional.
- Navegação móvel com menu; links de seção fecham o menu.
- WhatsApp recebe mensagem correspondente ao segmento; na ausência de contato, aviso explícito em vez de link quebrado.
- PIN SHA-256 com sal no navegador. Somente hash/sal versionados. Sessão em localStorage `rotaguard.acesso`, validade de 12 horas; cinco erros pausam novas tentativas por 15 minutos neste navegador.
- Área de downloads verifica sessão, redireciona em ausência/expiração e encerra acesso ao sair.
- Instaladores inexistentes aparecem em preparação. Não há downloads falsos.
- Controle local é de demonstração, sem garantia de autenticação contra adulteração pelo próprio navegador.

## Veracidade

Detecção e alerta têm implementação no projeto. Registro completo, trechos por recorrência, coleta e relatório ainda dependem das specs respectivas; essa distinção aparece no conteúdo. Hardware final sujeito a validação. Imagens de IA identificadas nos créditos e alt. Relatório é exemplo com dados fictícios. Não registra localização nem faz diagnóstico médico.

## Aceite e evidência

- Build de produção e TypeScript; lint.
- Testes de cinco idiomas, placeholders, ausência de cópias, veracidade, metadados e peso do HTML.
- Testes de PIN correto/errado, bloqueio, expiração, logout, armazenamento indisponível e sessão malformada.
- Navegador: fluxo de login completo; abas, teclado, menu, FAQ e mudança de idioma.
- Responsividade nos cinco idiomas a 320, 390, 768 e 1440 px.
- Respeito a prefers-reduced-motion; nenhum vídeo inicia automaticamente.
- Capturas em `docs/site/prints/reformulacao-2026-09-11/`.

## Pendências externas

WhatsApp, telefone, domínio comercial, preço, condições de piloto, instaladores reais e validação do hardware. Não criar números, depoimentos, clientes, preços ou certificados fictícios.
