# RotaGuard · estado atual do projeto (passagem entre computadores)

Atualizado em **20/10/2026, ~15:00**. Escrito para o Claude Code de outro computador entender, depois de um `git pull`,
o que existe, o que está pela metade e como continuar. Leia inteiro antes de mexer.

## 1. O que é

- Produto **RotaGuard** (nome antigo do repositório: DriveSafe AI / Vigilancia_Motorista): detecta sono, distração e
  celular em motoristas de frota pela câmera, toca alarme local, grava só trechos curtos quando algo se repete e gera o
  relatório da viagem. **Não diagnostica nada** e **não grava a viagem inteira**.
- Dono das decisões: **Matheus Cortes**. Responder em pt-BR. Copy sem travessão, com acento, sem jargão, sem "cara de IA".
- Branch de trabalho: **`app-instalavel-em-andamento`** (a `main` só quando o Matheus pedir).
- Documento grande para leigos: `C:\Users\Matheus Corte\Downloads\RotaGuard - como funciona.md/.pdf` (fora do repo).
- Fonte das decisões: `docs/produto/PRD.md` (seção 11, histórico com as palavras do Matheus) e `docs/specs/001` a `032`.

## 2. As peças

| Peça | Onde | O que é |
|---|---|---|
| **RotaGuard Script** (antes "RotaGuard Teste") | `caixa/app_teste.py`, `caixa/tela_teste/` (janela HTML via pywebview), `caixa/vision/` (detecção) | App de computador que roda a detecção da caixa com a webcam. Envia eventos, resumo e trechos para a central se estiver conectado à empresa |
| **RotaGuard Painel** | `painel/desktop/` (Python, ponte pywebview), `painel/app/` (Next.js 16 static export) | App de computador da empresa. Dados locais. Conecta à central para ver os testes de outros computadores |
| **Central** | `servidor/` (FastAPI) | Na VPS, em `https://rotaguard.acexpartners.com.br/api`. Recebe do script, entrega ao painel |
| **Site** | `site/` (Next.js 16 + next-intl, 5 idiomas) | `https://rotaguard.acexpartners.com.br`. Área do PIN com os downloads |
| **Caixa** (Raspberry Pi) | ainda **sem hardware** | Mesmo código de `caixa/vision/` |

Painel no navegador (`painel/web/`, spec 024): implementado e **não publicado** (o Matheus quer o painel executável).

## 3. Método obrigatório (regra global do Matheus)

- **SDD:** PRD → spec em `docs/specs/NNN-nome.md` → **TDD** (teste com o ID do critério falhando antes) → código.
- Prova antes de dizer "pronto": rodar testes/build e mostrar a saída. O que não foi verificado é dito com todas as letras.
- Testes Python são scripts: `.venv/Scripts/python.exe tests/test_x.py` (sem pytest). Painel: `cd painel/app && npm test`.
  Site: `cd site && npm test`.
- Versões: sempre a última **estável** conferida no registro na hora (`npm view`, `pip index versions`). TypeScript
  fica em 6.0.3 (o 7 quebra o `next build`).
- Ao terminar trabalho grande: atualizar a vault Obsidian (`C:\Users\Matheus Corte\Desktop\Obsidian`, pasta
  `DriveSafe AI - Monitoramento de Motoristas`, notas 12 e 13) e dar push nela.
- Nunca gravar senha, PIN, token ou chave em arquivo do repo ou da vault.

## 4. O que está pronto (testado)

| Spec | Assunto | Testes |
|---|---|---|
| 021 | VPS: site + central, containers `morro-alto-os-rotaguard-site` e `-central` (prefixo só no `.env` da VPS) | deploy conferido |
| 022 | Pulso pela face (rPPG POS/CHROM/GREEN), 478 pontos, motivo medido, mede a partir de 10 quadros/s, nunca para por sinal fraco | `test_cardio.py` |
| 023, 029 | Tela nova do Script: malha discreta (nada cobre rosto e olho), trechos sem malha, painel lateral por blocos, resumo como relatório | `test_tela_teste.py`, `test_trechos.py` |
| 025 | Câmera do aparelho dentro do painel (MediaPipe JS 1.1.1, malha discreta, pulso igual ao Python) | `painel/app` `npm test` |
| 026 | Central: pareamento por código, sessões, trechos (WebM VP8), painel recebe ("Testes à distância") | `test_central_api.py`, `test_painel_central.py` |
| 027 | Alarme com 4 sons por urgência, distração pelo olhar, microssono com rosto perdido, calibração robusta | `test_alarme_risco.py`, `test_distracao.py`, `test_rosto_perdido.py`, `test_calibracao_robusta.py` |
| 028 | Celular na orelha sem confundir a mão vazia | `test_celular.py` |
| 030 | Painel sem dados fictícios (migração automática do banco em demonstração, com cópia) | `test_painel_sem_demonstracao.py` |
| 031 | Nome RotaGuard Script em tudo; pasta de dados `%LOCALAPPDATA%\RotaGuard\Script` (migra a antiga `Teste`) | `test_app_teste.py`, `test_painel_script_local.py` |
| 032 | Olhos esfregados (qualquer parte da mão, olho tapado mexendo, mãos sem pular medida) | `test_face_touch.py`, `test_celular.py` |
| — | Painel em outro computador: contrato tela ↔ Python, erro com código e `registro-painel.log`, primeiro uso testado dentro do `.exe` | `test_painel_contrato.py` |

## 5. Em andamento neste momento (20/10, ~15:00)

Dois pedidos do Matheus estavam sendo feitos quando este arquivo foi escrito (confira `git log` e `git status`):

1. **"o batimento cardíaco pede para ficar parada se não não funciona... deve captar em qualquer movimento"** →
   `caixa/vision/cardio.py`: não pausar mais por movimento (campo novo `em_movimento: bool`; `motivo = "mexendo"` só
   sem número), tirar o movimento do sinal (regressão contra deslocamento/escala/pose do rosto), interpolar trancos,
   rastrear o bpm com continuidade, e **nunca** virar número com balanço periódico da cabeça sem pulso.
   Depois disso, **copiar a mesma regra** para `painel/app/src/components/live/camera-rppg.ts` (há teste de paridade
   com o Python).
2. **"os mais detalhes continuou tudo junto"** → `caixa/tela_teste/web/*`: "Ver mais detalhes" por assunto (Sono,
   Atenção, Cabeça e boca, Coração, Câmera e desempenho), um assunto por vez, cartões em grade com explicação curta;
   nenhum texto "fique parado"; com movimento, só "Em movimento: leitura menos precisa".

**Atualização 15:10:** os dois ficaram prontos no Script (`tests/test_cardio.py` 29, `tests/test_tela_teste.py` 54) e foram
publicados. **Falta só** copiar a regra do movimento do pulso para a câmera do painel (`camera-rppg.ts`): as 5 linhas do
algoritmo estão na revisão de 20/10 da `docs/specs/022-cardio-pela-face.md` e no código de `caixa/vision/cardio.py`.

## 6. Como publicar (o Matheus exige site e computador com a **mesma versão**)

1. Commit primeiro (o carimbo usa o commit; com mudança sem commit sai "+local").
2. Feche o Painel e o Script abertos (o Windows trava os arquivos e o PyInstaller falha).
3. `PYTHONUTF8=1 .venv/Scripts/python.exe implantacao/app-teste/build.py` (Script: fumaça com a DLL marcada como
   "baixada da internet", sem câmera, tela, instalador).
4. `PYTHONUTF8=1 .venv/Scripts/python.exe implantacao/painel/build.py` (Painel: fumaça + **primeiro uso dentro do
   `.exe`**, instalador). Inno Setup 6 instalado por usuário em `%LOCALAPPDATA%\Programs\Inno Setup 6` (o build acha).
5. `.venv/Scripts/python.exe implantacao/publicar_downloads.py` (copia instaladores e `.zip`, apaga os velhos, grava
   `site/public/downloads/versoes.json` com o carimbo de cada app).
6. `bash implantacao/vps/enviar.sh site` e depois na VPS `cd /root/rotaguard && ./atualizar.sh site <tag>` (a tag sai
   impressa; o script volta sozinho para a anterior se não ficar saudável).
7. Conferir: `curl https://rotaguard.acexpartners.com.br/downloads/versoes.json` e o SHA-256 de cada arquivo baixado
   contra `site/public/downloads/`.
8. Central: `bash implantacao/vps/enviar.sh central` e `./atualizar.sh central <tag>`.

Acesso à VPS por chave SSH (`ssh root@187.127.41.22`); a VPS é **compartilhada com outros sites** (Brasigran, Hana
Decor, links da Jania, site Morro Alto): nunca mexer nos containers deles nem limpar cache de build sem perguntar.
Caddy de borda em `/root/edge` (validar antes de recarregar). Logins da central (usuário `teste@gmail.com`, empresa
RotaGuard) e o PIN do site **não estão no repo**: pergunte ao Matheus.

## 7. Armadilhas já conhecidas (não repetir)

- `Path.write_text` no Windows grava CRLF: scripts `.sh` quebram na VPS. Use `newline="\n"`; o `.gitattributes`
  força LF em `*.sh`, `Dockerfile*` e `*.caddy`.
- Git Bash troca `/painel` por `C:/Program Files/Git/painel` em variável: use `MSYS_NO_PATHCONV=1` ou PowerShell.
- Heredoc no Bash desta máquina transforma `\\n` em quebra de linha dentro de strings Python: código com barra
  invertida vai pela ferramenta de edição, não por heredoc.
- O guardrail global G4 bloqueia comando que tenha `git` e `-n` juntos (lê como `--no-verify`), inclusive `bash -n`.
- PIN do site é conferido **no navegador** (hash no JS público): não protege nada. Pendente: conferir no servidor.
- `test_painel_script_local.py` lê `em_execucao.json` enquanto uma thread troca o arquivo: o teste já tolera
  `PermissionError`; o painel também.

## 8. Pendências e perguntas abertas

- Validar com webcam real: pulso (com oxímetro), olhos esfregados (`docs/specs/032`), celular
  (`docs/validacao/roteiro-cel03-celular.md`). Tudo até agora foi validado com vídeo/dados sintéticos.
- PRD Q7: quem pode ativar o painel (hoje qualquer um com o link). O Matheus disse "por enquanto mantenha assim".
- Limpeza automática dos prazos de guarda no painel não existe (o texto da tela já diz isso).
- Pacotes 3 e 4 da spec 027 (desempenho; KSS e roteiro Euro NCAP no app).
- Gravação própria com a equipe para medir de verdade (protocolo em `docs/pesquisa/2026-10-19-datasets-e-validacao.md`).
- Specs 004, 005 e 006 citadas no PRD não existem como arquivo.
