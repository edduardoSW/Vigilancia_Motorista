# Contrato comum — RotaGuard Painel, parte 2 (leia inteiro antes de começar)

Repositório: `C:\Users\Matheus Corte\Downloads\Vigilancia_Motorista-main\Vigilancia_Motorista-main` (pt-BR em tudo que o usuário vê).
Specs aprovadas pelo Matheus em 14/09/2026 ("gostei, pode fazer"): `docs/specs/014-entrar-equipe-e-permissoes.md`,
`015-cadastro-de-motoristas-veiculos-e-caixas.md`, `016-configuracoes-do-painel.md`, `017-guia-de-uso-do-painel.md`.
Prévia aprovada (imagens, leia com Read): `docs/painel/previa-2026-09-14-parte-2/3-entrar.png` a `9-guia-de-uso.png`.
Telas já construídas e aprovadas: `painel/app` (Next 16.3.5 export estático, React 19.3.0, Tailwind 4.3.3, TS 6.0.3, ESLint 9.39.5)
e a janela Python `painel/desktop/rotaguard_painel.py` (pywebview 6.2.1 + WebView2).

## Decisões novas do Matheus (valem acima das specs)
- "gostei pode fazer, mas deixe um pouco menos com cara de IA e quero algo mais dinâmico".
- "lembre-se: por enquanto local, e caso eu inicie o script no computador, deve reconhecer que ele está aberto e capturar as logs".
- Perguntas das specs sem resposta usam o padrão proposto: contas só neste computador; Consulta não vê vídeo; CPF opcional;
  vídeos 30 dias, registros 5 anos; sem revezamento de motorista.
- "futuramente tudo isso vai estar conectado a uma VPS e depois vamos ter o Raspberry Pi etc.": hoje é tudo local, mas
  cada registro do banco nasce com `uid` (uuid4 em hex), `criado_em` e `alterado_em` (ISO em UTC), e as regras ficam em
  módulos Python puros, sem depender do pywebview, para poderem ir para o servidor depois. A tela só conversa com `bridge`,
  então trocar o transporte (ponte local → API na VPS) não muda as telas.
- Prazo: começou às 14:16. **Pare às 15:05**, num ponto que compila, e relate o que ficou pronto e o que falta. Melhor
  pouco funcionando do que muito quebrado.

## Regras de trabalho (obrigatórias)
- SDD/TDD: cada critério com ID da spec vira teste com o ID no nome/mensagem. Rodar os testes e mostrar o resultado real.
- Nunca abrir navegador nem janela visível; nunca rodar `npm run dev`; nunca rodar `next build`/`npm run build` (só o
  integrador roda o build, porque 3 agentes mexem no mesmo `painel/app`). Para conferir TS: `npx tsc --noEmit` dentro de
  `painel/app` e olhe só os erros dos SEUS arquivos. Lint: `npx eslint <seus arquivos>`.
- Nunca matar processos (o Matheus pode estar com o app aberto). Nunca `git commit`/`push`.
- Não instalar dependência nova sem necessidade real; nada de shadcn, Radix, lucide, clsx, framer-motion, react-hook-form, zod.
- Python: `.venv\Scripts\python.exe` na raiz do repo (Python 3.14.5). Testes no estilo de `tests/test_painel_desktop.py`
  (leia antes). Rodar com `.venv\Scripts\python.exe tests\<arquivo>.py`.
- Casa (vault): arquivos kebab-case em inglês em `src/components`, conteúdo em pt-BR, `cn()` de `src/lib/utils.ts`,
  sem utilitário repetido da mesma propriedade, sem rótulo em maiúsculas, sem fonte mono.
- Nunca gravar segredo real em arquivo. Senhas de teste são descartáveis e ficam só nos testes.
- Só edite os arquivos que são SEUS (tabela abaixo). Precisa de algo em arquivo de outro? Escreva no relatório final.

## Divisão de arquivos
| Agente | Arquivos |
|---|---|
| 1 Python núcleo | `painel/desktop/dados.py`, `contas.py`, `cadastros.py`, `configuracoes.py`, `atividades.py`, `copia.py`, `ponte.py`; ligação do `js_api` em `rotaguard_painel.py`; `implantacao/painel/rotaguard-painel.spec` (só se precisar de import oculto); `tests/test_painel_contas.py`, `tests/test_painel_cadastros.py`, `tests/test_painel_configuracoes.py` |
| 2 Script local | `docs/specs/018-script-local-no-painel.md`, `painel/desktop/script_local.py`, `tests/test_painel_script_local.py`, mudança mínima no lado da caixa/app de teste para anunciar que está aberto (+ teste), `painel/app/src/app/ao-vivo/page.tsx`, `painel/app/src/components/live/*` |
| 3 Casca da interface | `painel/app/src/lib/bridge.ts`, `src/lib/demo-backend.ts`, `src/components/ui/*`, `src/components/session-provider.tsx`, `src/components/auth-gate.tsx`, `src/components/sidebar.tsx`, `src/components/command-palette.tsx`, `src/components/decisions-provider.tsx`, `src/components/moment-list.tsx`, `src/app/layout.tsx`, `src/app/globals.css`, `src/app/page.tsx` (Início), `src/app/viagens/page.tsx`, `src/app/viagens/[id]/page.tsx`, `scripts/testes/previa.test.mjs`, `scripts/testes/shell.test.mjs` |
| 4 Cadastros | `src/app/motoristas/page.tsx`, `src/components/drivers/*`, `src/app/veiculos/page.tsx`, `src/components/vehicles/*`, `src/lib/validators.ts`, `scripts/testes/cadastros.test.mjs` |
| 5 Equipe, configurações e guia | `src/app/equipe/page.tsx`, `src/components/team/*`, `src/app/configuracoes/page.tsx`, `src/components/settings/*`, `src/app/guia/page.tsx`, `src/components/guide/*`, `src/content/guide.ts`, `scripts/testes/guia.test.mjs` |

## Ponte tela ↔ Python (pywebview `js_api`)
- Python: classe `Ponte` em `painel/desktop/ponte.py`, passada em `webview.create_window(..., js_api=Ponte(...))`.
  **Todo atributo interno da Ponte começa com `_`** (o pywebview expõe atributos públicos ao JavaScript). Os métodos são
  chamados em threads diferentes: SQLite com trava.
- JS: `window.pywebview.api.<metodo>(...args)` devolve Promise. Em `src/lib/bridge.ts` o objeto `bridge` tem exatamente os
  mesmos nomes. Sem pywebview (build, testes, captura de tela), `bridge` usa `src/lib/demo-backend.ts`, que imita o contrato
  em memória com os mesmos dados de demonstração.
- Toda resposta: `{ ok: true, dados }` ou `{ ok: false, erro: "frase simples em pt-BR", codigo?, campo?, esperar_s? }`.
  `codigo`: `invalido` | `sem_permissao` | `sem_sessao` | `bloqueado` | `espera` | `nao_encontrado` | `conflito`.
  `campo` = nome da propriedade com erro (para o formulário marcar o campo).
- Pasta de dados: `%LOCALAPPDATA%\RotaGuard\Painel\` (Linux `~/.local/share/rotaguard-painel/`); variável
  `ROTAGUARD_PAINEL_DADOS` troca a pasta (testes). Banco `painel.db`.

### Tipos (TS; o Python devolve dicts iguais)
```ts
type Funcao = "administrador" | "supervisor" | "consulta";
type Acao = "ver_viagens" | "ver_video" | "importar" | "decidir" | "cadastrar" | "equipe" | "configuracoes" | "atividades";
interface Usuario { id: number; nome: string; usuario: string; funcao: Funcao; ativo: boolean; ultimo_acesso: string | null; trocar_senha: boolean }
interface Estado { ativado: boolean; modo: "demonstracao" | "empresa" | null; empresa: { nome: string } | null; sessao: Usuario | null; bloqueado: boolean; versao: string; bloqueio_min: number;
  texto_maior: boolean /* 15/09: aparência de Configurações, vale inclusive na tela de entrar */;
  tema: Tema /* spec 019: o da pessoa que entrou; sem sessão, o último usado neste computador */; preferencias: Preferencias | null; videos_dias: number }
// Spec 019 (15/09): tema e lista ou cards por pessoa; termo importado como comprovante.
type Tema = "claro" | "escuro" | "sistema";
type Visao = "lista" | "cards";
type TelaComVisao = "viagens" | "momentos" | "motoristas" | "veiculos" | "caixas" | "equipe";
interface Preferencias { tema: Tema; visao: Record<TelaComVisao, Visao> } // padrão: tema "claro", todas "cards"
interface ArquivoTermo { nome: string; tipo: "pdf" | "imagem"; bytes: number; importado_em: string; importado_por: string }
interface TermoRegistro { id: number; assinado: boolean; data: string | null; versao: string | null; registrado_por: string | null; registrado_em: string; arquivo: ArquivoTermo | null }
interface InicioResumo { ultima_copia_em: string | null; dias_desde_copia: number | null; primeiros_passos_escondidos: boolean } // 15/09
interface Motorista { id: number; ref: string | null; nome: string; nome_curto: string; matricula: string; cpf: string | null; telefone: string | null;
  cnh_numero: string; cnh_categoria: "C" | "D" | "E"; cnh_validade: string /* AAAA-MM-DD */; situacao: "ativo" | "afastado" | "desligado";
  termo: { assinado: boolean; data: string | null; versao: string | null; arquivo: ArquivoTermo | null }; observacoes: string | null; viagens_30d: number; confirmados_30d: number }
interface Veiculo { id: number; numero: string; placa: string; tipo: "onibus" | "micro_onibus" | "caminhao" | "van"; transporta: "passageiros" | "carga";
  modelo: string | null; ano: number | null; situacao: "em_uso" | "oficina" | "fora_de_uso"; caixa_id: number | null }
interface Caixa { id: number; codigo: string; veiculo_id: number | null; situacao: "ok" | "atencao" | "bloqueada"; detalhe: string | null; ultima_coleta: string | null; versao: string | null }
interface Atividade { id: number; em: string; usuario: string | null; acao: string; alvo: string | null; detalhe: string | null }
interface Configuracoes { empresa: { nome: string; razao_social: string; cnpj: string; telefone: string; endereco: string };
  regras: { direcao_continua_min: number /* 60..330 */ }; guarda: { videos_dias: 7 | 15 | 30 | 60 | 90; registros_anos: 1 | 2 | 5; desligados_anos: 1 | 2 | 5 };
  acesso: { bloqueio_min: number /* 5..60 */ }; aparencia: { texto_maior: boolean } }
interface Decisao { momento_id: string; resultado: ResultadoMomento /* valores de src/content/moments.ts */; orientado: boolean; por: string; funcao: Funcao; em: string }
interface ScriptEstado { aberto: boolean; programa: string | null; desde: string | null; pid: number | null; camera: string | null; ultimo_sinal: string | null; eventos: number; pasta: string | null }
interface EventoScript { id: number; em: string; tipo: string; risco: number; duracao_s: number | null; sessao: string | null }
```

### Métodos (mesmos nomes nos dois lados; argumentos posicionais)
| Método | Quem pode | Devolve |
|---|---|---|
| `estado()` | qualquer um | `Estado` |
| `ativar_demonstracao(admin: {nome, usuario, senha})` | só sem ativação | `{ codigo_recuperacao }` (cria "Viação Demonstração" com os motoristas, veículos e caixas de demonstração e já entra) |
| `ativar_com_arquivo(conteudo: string, admin)` | só sem ativação | `{ codigo_recuperacao }` (arquivo `rotaguard-chaveiro-coleta/1` da spec 003) |
| `entrar(usuario, senha)` | qualquer um | `Usuario` ou `codigo: "espera"` com `esperar_s` |
| `sair()`, `bloquear()` | sessão | `{}` |
| `tocar()` | sessão | `{ bloqueado }` (a tela chama no máximo a cada 30 s quando há uso; o Python bloqueia sozinho depois de `bloqueio_min`) |
| `desbloquear(senha)` | sessão bloqueada | `Usuario` |
| `trocar_senha(atual, nova)` | sessão | `{}` |
| `recuperar_acesso(usuario, codigo, nova_senha)` | qualquer um | `{}` |
| `equipe_listar()` | administrador | `Usuario[]` |
| `equipe_adicionar({nome, usuario, funcao})` | administrador | `{ usuario: Usuario, senha_temporaria }` |
| `equipe_alterar(id, {funcao?, ativo?})` | administrador | `Usuario` |
| `equipe_nova_senha(id)` | administrador | `{ senha_temporaria }` |
| `atividades_listar({usuario_id?, de?, ate?, limite?})` | administrador | `{ itens: Atividade[], integro: boolean }` |
| `atividades_exportar()` | administrador | `{ caminho }` (diálogo de salvar do sistema) |
| `motoristas_listar()` | sessão | `Motorista[]` |
| `motorista_salvar(dados)` | adm/supervisor | `Motorista` (sem `id` cria; com `id` altera) |
| `motorista_exportar(id)` | adm/supervisor | `{ caminho }` |
| `veiculos_listar()`, `caixas_listar()` | sessão | `Veiculo[]`, `Caixa[]` |
| `veiculo_salvar(dados)` | adm/supervisor | `Veiculo` |
| `caixa_vincular(caixa_id, veiculo_id \| null)` | adm/supervisor | `Caixa` |
| `config_ler()` | administrador (15/09, CFG-01: só o administrador lê e muda) | `Configuracoes` |
| `config_salvar(secao, valores)` | administrador | `Configuracoes` |
| `decisoes_listar()` | sessão | `Decisao[]` |
| `decisao_registrar(momento_id, resultado)` | adm/supervisor | `Decisao` |
| `decisao_desfazer(momento_id)` | adm/supervisor | `{}` |
| `decisao_orientado(momento_id, orientado)` | adm/supervisor | `Decisao` |
| `video_abrir(momento_id, motorista_ref)` | adm/supervisor | `{ liberado, motivo? }` (sem termo: `liberado: false`) |
| `copia_fazer(senha)` | administrador | `{ caminho, bytes }` (senha escolhida na hora, com a regra das contas; não é a senha de quem entrou). Spec 019: formato `rotaguard-copia/2`, com o mesmo envelope cifrado do formato 1 e, dentro, um zip com `painel.db` e os arquivos dos termos; `copia.conteudo_da_copia()` lê os dois formatos |
| `inicio_resumo()` | sessão (15/09) | `InicioResumo` (aviso da cópia com mais de 7 dias, BKP-03; Primeiros passos escondidos) |
| `primeiros_passos_esconder(esconder: boolean)` | administrador (15/09) | `{ primeiros_passos_escondidos }` (registra "escondeu/mostrou primeiros passos") |
| `preferencias_salvar(valores: { tema?, visao?: Partial<Record<TelaComVisao, Visao>> })` | qualquer sessão (spec 019) | `Preferencias` (por pessoa; o `tema` também vira o último usado neste computador) |
| `termo_importar(motorista_id, arquivo: { nome, conteudo_base64 }, dados: { data, versao? })` | adm/supervisor (spec 019) | `Motorista` (registro novo de termo assinado, com o arquivo; PDF, PNG ou JPEG até 10 MB; registra "importou termo assinado") |
| `termo_ver(motorista_id)` | adm/supervisor (spec 019) | imagem: `{ tipo: "imagem", nome, conteudo: "data:image/...;base64,..." }`; PDF: abre no leitor do computador e devolve `{ tipo: "pdf", nome, aberto: true }` (registra "abriu termo") |
| `motorista_termos(motorista_id)` | adm/supervisor (spec 019) | `TermoRegistro[]`, mais novo primeiro |
| `script_estado()` | sessão | `ScriptEstado` (delegado a `ScriptLocal` do agente 2) |
| `script_eventos(desde_id)` | sessão | `EventoScript[]` (idem) |

Permissões (spec 014, decisão 3): todos veem viagens; adm e supervisor veem vídeo, importam, decidem e cadastram; só adm
mexe em equipe, configurações, atividades e cópia. Com a tela bloqueada, tudo menos `estado`, `desbloquear`, `sair` e
`tocar` devolve `codigo: "bloqueado"`.

Ligação do script local: `painel/desktop/script_local.py` (agente 2) tem `class ScriptLocal(pasta_dados_painel: Path)`
com `estado() -> dict`, `eventos(desde_id: int) -> list[dict]`, `iniciar()` e `parar()` (vigia em thread que captura os
eventos para `capturas.db` na pasta de dados do painel). A Ponte (agente 1) importa com `try/except ImportError` e, sem o
módulo, devolve `aberto: false`.

### Dados de demonstração (os dois lados iguais)
- Empresa "Viação Demonstração".
- Motoristas: m-01 Carlos Menezes (Carlos M., matr. 0412, D, válida até 2028-03-31, termo 2026-09-02), m-02 Juliana Prado
  (Juliana P., 0388, D, 2027-11-30, termo 2026-09-02), m-03 Rogério Lima (Rogério L., 0291, E, 2026-09-26, termo 2026-09-03),
  m-04 Aline Costa (Aline C., 0455, D, 2029-06-30, termo 2026-09-02), m-05 Marcos Teixeira (Marcos T., 0467, D, 2030-01-15, sem termo).
  CNH de demonstração: gerar números de 11 dígitos válidos pelo dígito verificador.
- Veículos (de `painel/app/src/content/demo.json`): 3302 caminhão carga BRA2E19 RG-0129; 2258 ônibus passageiros BRA3F27 RG-0139;
  2240 ônibus BRA1C84 RG-0142; 3310 caminhão BRA5H02 RG-0133; 2251 ônibus BRA4D66 RG-0150; 2263 ônibus BRA7B31 RG-0147;
  1187 ônibus BRA8A12 RG-0118. Caixa livre: RG-0155. RG-0129 com situação "atencao" e o detalhe do demo.json.

## Direção visual: "menos cara de IA e mais dinâmico"
Mantém: cores e fontes de `globals.css` (verde, tinta, papel, lateral, grafite, fio, lima, alarme; Space Grotesk nos
títulos, Manrope no texto), `.btn`, `.btn-primary`, a coluna de menu da prévia aprovada.

Tira (é o que deixa com cara de template de IA):
- filtros em pílula ("Ativos · 5") → abas de texto com contagem e sublinhado de 2 px que desliza até a aba escolhida;
- caixas de aviso com ícone (i), cartão lateral "Por que pedimos isso?", ícone em toda linha, avatar redondo em tabela;
- selo colorido para estado normal (cor só quando pede ação: texto em `alarme`);
- link "Como funciona?" sublinhado ao lado do título → link discreto "Guia" com ícone de livro no canto do cabeçalho;
- frases de marketing, "Bem-vindo", subtítulo genérico. O subtítulo traz número real: "5 ativos · 1 CNH vence em 12 dias".

Põe (jeito de programa de computador e movimento com intenção):
- tabela densa com cabeçalho grudado no topo, linha de 48 px, hover e linha selecionada; ↑/↓ muda a seleção, Enter
  abre, Esc fecha; clicar na linha abre um **painel lateral** que desliza da direita (ver e editar sem trocar de tela);
- `Ctrl+K` abre a busca rápida (ir para telas, achar motorista, veículo ou capítulo do guia); `Ctrl+N` cadastra na tela
  de lista; atalhos mostrados discretos no botão (componente `Kbd`);
- movimento de 160 a 220 ms com `cubic-bezier(.2,.8,.2,1)`: conteúdo entra com opacidade e 6 px de subida ao trocar de
  tela; a barrinha do menu desliza até o item ativo; painel lateral desliza; diálogo cresce de 0,98 para 1; aviso curto
  sobe no canto de baixo à direita com "Desfazer" quando fizer sentido; contagens mudam com transição; linha nova entra
  suave; botão de salvar mostra "Salvando…" e depois "Salvo";
- ponto de situação pulsando só enquanto algo acontece de verdade (script aberto, caixa lendo);
- tudo isso some com `prefers-reduced-motion`.

### Peças compartilhadas (o agente 3 cria primeiro, em até 10 min; os outros programam contra esta API)
- `@/lib/bridge`: `export const bridge` (métodos da tabela, cada um devolve `Promise<Resposta<T>>`), `export type` de todos os tipos acima, `export type Resposta<T>`.
- `@/components/session-provider`: `useSession()` → `{ estado: Estado | null, usuario: Usuario | null, pode(acao: Acao): boolean, atualizar(): Promise<void>, sair(): Promise<void> }`.
- `@/components/ui/page-header`: `<PageHeader title summary actions guide={{ capitulo: string }} />`.
- `@/components/ui/tabs`: `<Tabs items={[{ id, label, count? }]} value onChange />`.
- `@/components/ui/data-table`: `<DataTable columns={[{ id, header, cell: (row) => ReactNode, width? }]} rows getRowId selectedId onSelect onOpen empty />` (cabeçalho grudado, teclado ↑/↓/Enter).
- `@/components/ui/drawer`: `<Drawer open onClose title summary footer>{children}</Drawer>`.
- `@/components/ui/dialog`: `<Dialog open onClose title summary footer>{children}</Dialog>`.
- `@/components/ui/field`: `<Field label optional hint error htmlFor>{children}</Field>`; classes `.input` e `.select` no `globals.css`.
- `@/components/ui/choice`: `<Choice name value checked onChange title description />`.
- `@/components/ui/toast`: `useToast()` → `toast({ text, action?: { label, onClick } })`.
- `@/components/ui/kbd`: `<Kbd>Ctrl N</Kbd>`.
- `@/components/ui/save-button`: `<SaveButton state="idle" | "saving" | "saved">Salvar</SaveButton>`.
- Classes de animação no `globals.css`: `.anim-enter`, `.anim-drawer`, `.anim-dialog`, `.anim-toast`, `.anim-row`, `.pulse-dot`.

Rotas (export estático, sem rota dinâmica para registro do banco): `/` Início, `/viagens/`, `/viagens/[id]/` (já existe),
`/motoristas/`, `/veiculos/`, `/equipe/`, `/configuracoes/`, `/guia/` (capítulo por `?capitulo=`), `/ao-vivo/`.
Capítulos do guia (ids): `primeiros-passos`, `veiculo-chega`, `verificar-momentos`, `alertas`, `motoristas`, `veiculos`,
`equipe`, `copia`, `problemas`, `privacidade`.

## Relatório final (curto)
Arquivos criados/alterados, testes rodados com a saída resumida (quantos passaram, IDs), o que ficou faltando e qualquer
coisa que precise em arquivo de outro agente.
