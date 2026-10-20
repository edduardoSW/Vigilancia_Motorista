"""Ponte entre a tela e o Python (pywebview `js_api`), specs 014, 015 e 016.

Todo atributo interno começa com "_": o pywebview expõe ao JavaScript os atributos públicos. Cada método público
devolve {"ok": True, "dados": ...} ou {"ok": False, "erro": ..., "codigo": ..., "campo"?, "esperar_s"?}; exceção nunca
chega crua ao JavaScript. As regras ficam nos módulos puros (contas, cadastros, configuracoes, atividades, copia).
"""
from __future__ import annotations

import functools
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import copia
import demonstracao
from atividades import Atividades
from cadastros import Cadastros, Decisoes, carregar_caixas_do_arquivo
from central import Central
from configuracoes import Configuracoes, validar_nome_empresa
from contas import CUSTO_PRODUCAO, Contas, ler_chaveiro, pode, validar_senha
from dados import Banco, ErroPainel, pasta_dados
from preferencias import Preferencias

AQUI = Path(__file__).resolve().parent
MENSAGEM_FALHA = "Algo deu errado. Tente de novo; se continuar, fale com a RotaGuard."
ARQUIVO_REGISTRO = "registro-painel.log"
ARQUIVO_COMPILACAO = "versao.txt"
TAMANHO_MAXIMO_COMPILACAO = 200
TAMANHO_MAXIMO_REGISTRO = 1_000_000
MENSAGEM_JA_ATIVADO = "O painel já foi ativado neste computador."
MENSAGEM_NAO_ATIVADO = "O painel ainda não foi ativado."
CHAVE_PASSOS_ESCONDIDOS = "primeiros_passos_escondidos"
ESTADO_SCRIPT_FECHADO = {"aberto": False, "programa": None, "desde": None, "pid": None, "camera": None,
                         "ultimo_sinal": None, "eventos": 0, "pasta": None}


def versao_app() -> str:
    bruta = os.environ.get("ROTAGUARD_VERSAO", "").strip()
    if bruta:
        return bruta.rsplit("-v", 1)[-1].lstrip("v")
    try:
        return json.loads((AQUI.parent / "app" / "package.json").read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return "0.0.0"


def compilacao_do_pacote(congelado: bool | None = None, executavel: str | None = None) -> str | None:
    """Linha que o build grava em versao.txt ao lado do RotaGuardPainel.exe ("RotaGuard Painel 0.1.0 · compilação
    e94ca11 · 20/10/2026 13:10"), para conferir se o programa deste computador é o mesmo do site (pedido de 20/10/2026).
    Fora do pacote congelado, ou sem o arquivo, None. Só para mostrar: qualquer falha de leitura vira None."""
    congelado = bool(getattr(sys, "frozen", False)) if congelado is None else congelado
    if not congelado:
        return None
    try:
        caminho = Path(executavel or sys.executable).resolve().parent / ARQUIVO_COMPILACAO
        with open(caminho, "rb") as arquivo:
            bruto = arquivo.read(4096)
        texto = bruto.decode("utf-8-sig", errors="replace")
        linha = next((linha.strip() for linha in texto.splitlines() if linha.strip()), "")
        linha = "".join(letra for letra in linha if letra.isprintable() and letra != "�").strip()
        return linha[:TAMANHO_MAXIMO_COMPILACAO] or None
    except Exception:  # noqa: BLE001 - o arquivo é só informativo: nunca derruba o estado()
        return None


def _resposta(travar: bool = True):
    def decorador(metodo):
        @functools.wraps(metodo)
        def envolvido(self, *args):
            try:
                if travar:
                    with self._trava:
                        return {"ok": True, "dados": metodo(self, *args)}
                return {"ok": True, "dados": metodo(self, *args)}
            except ErroPainel as erro:
                return erro.resposta()
            except Exception as erro:  # nunca exceção crua para o JavaScript (argumento errado, disco cheio...)
                self._falhas.append(f"{metodo.__name__}: {type(erro).__name__}")
                codigo = self._registrar_falha(metodo.__name__, erro)
                return {"ok": False, "erro": f"{MENSAGEM_FALHA} (código {codigo})" if codigo else MENSAGEM_FALHA}
        return envolvido
    return decorador


class Ponte:
    def __init__(self, pasta=None, relogio=time.time, custo_scrypt=CUSTO_PRODUCAO, escolher_destino=None,
                 script_local=None, abrir_arquivo=None, central=None):
        self._pasta = Path(pasta) if pasta is not None else None
        self._relogio = relogio
        self._custo = custo_scrypt
        self._escolher_destino_injetado = escolher_destino
        self._abrir_arquivo_injetado = abrir_arquivo  # testes passam um falso: nenhum leitor de PDF abre
        self._janela = None
        self._trava = threading.RLock()
        self._nucleo = None
        self._script = script_local
        self._central_obj = central  # spec 026; criada na primeira chamada (não abre rede nem banco ao nascer)
        self._segredo_trechos = secrets.token_urlsafe(24)  # endereço dos trechos no servidor da janela, por abertura
        self._falhas: list[str] = []

    # Interno ---------------------------------------------------------------------------------------------------------
    def _n(self) -> SimpleNamespace:
        """Banco aberto na primeira chamada: criar a ponte não grava nada."""
        if self._nucleo is None:
            banco = Banco(self._pasta if self._pasta is not None else pasta_dados(), self._relogio)
            atividades = Atividades(banco)
            config = Configuracoes(banco, atividades)
            contas = Contas(banco, atividades, self._relogio, self._custo, config.bloqueio_min)
            cadastros = Cadastros(banco, atividades, lambda: datetime.fromtimestamp(self._relogio()).date())
            self._nucleo = SimpleNamespace(banco=banco, atividades=atividades, config=config, contas=contas,
                                           cadastros=cadastros, decisoes=Decisoes(banco, atividades),
                                           preferencias=Preferencias(banco))
            self._remover_demonstracao()
        return self._nucleo

    def _remover_demonstracao(self) -> None:
        """Spec 030, decisão 5: painel ativado na demonstração antiga perde os registros fictícios ao abrir (uma vez).
        Falha aqui não impede o painel de abrir: nada foi apagado (transação) e a próxima abertura tenta de novo."""
        n = self._nucleo
        try:
            if not demonstracao.precisa_remover(n.banco):
                return
            demonstracao.remover(n.banco, n.atividades, self._empresa_da_central())
        except Exception as erro:
            self._falhas.append(f"remover_demonstracao: {type(erro).__name__}")

    def _empresa_da_central(self) -> str | None:
        """Nome da empresa na central (spec 026), quando o painel já se ligou a ela; só lê o que está guardado."""
        try:
            empresa = self._central().estado().get("empresa") or {}
        except Exception:
            return None
        nome = empresa.get("nome")
        return nome.strip() if isinstance(nome, str) and nome.strip() else None

    def _registrar_falha(self, metodo: str, erro: BaseException) -> str | None:
        """ATV-03 (20/10/2026): falha inesperada vai para registro-painel.log na pasta de dados, com um código curto que
        a tela mostra. Só o nome do método e o erro com o rastro: nunca os argumentos (senha, nomes, arquivos).
        O arquivo passa de 1 MB → recomeça. Falha ao gravar o registro nunca vira outra falha."""
        codigo = "E-" + secrets.token_hex(3).upper()
        try:
            pasta = self._pasta if self._pasta is not None else pasta_dados()
            pasta.mkdir(parents=True, exist_ok=True)
            arquivo = pasta / ARQUIVO_REGISTRO
            if arquivo.exists() and arquivo.stat().st_size > TAMANHO_MAXIMO_REGISTRO:
                arquivo.unlink()
            rastro = "".join(traceback.format_exception(type(erro), erro, erro.__traceback__))
            with open(arquivo, "a", encoding="utf-8") as saida:
                cabecalho = f"{datetime.now().isoformat(timespec='seconds')} {codigo} {metodo} versão {versao_app()}"
                saida.write(cabecalho + "\n" + rastro + "\n")
        except Exception:  # noqa: BLE001 - registro é ajuda, não pode derrubar a resposta
            return None
        return codigo

    def _ligar_janela(self, janela) -> None:
        self._janela = janela

    def _exigir(self, acao: str | None = None) -> dict:
        return self._n().contas.exigir(acao)

    def _escolher_destino(self, nome_sugerido: str) -> Path:
        if self._escolher_destino_injetado is not None:
            escolhido = self._escolher_destino_injetado(nome_sugerido)
        elif self._janela is not None:
            import webview

            tipo = getattr(getattr(webview, "FileDialog", None), "SAVE", None) or getattr(webview, "SAVE_DIALOG")
            escolhido = self._janela.create_file_dialog(tipo, save_filename=nome_sugerido)
        else:
            raise ErroPainel("Não foi possível abrir a janela para escolher onde salvar.")
        if isinstance(escolhido, (list, tuple)):
            escolhido = escolhido[0] if escolhido else None
        if not escolhido:
            raise ErroPainel("Nada foi salvo.", "invalido")
        return Path(escolhido)

    def _abrir_arquivo(self, caminho: Path) -> None:
        """Abre o arquivo no programa padrão do computador (PDF do termo, spec 019)."""
        if self._abrir_arquivo_injetado is not None:
            self._abrir_arquivo_injetado(caminho)
        elif sys.platform == "win32":
            os.startfile(str(caminho))  # noqa: S606 - arquivo do próprio painel, caminho conferido
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(caminho)])  # noqa: S603, S607
        else:
            subprocess.Popen(["xdg-open", str(caminho)])  # noqa: S603, S607

    def _carregar_script(self):
        if self._script is None:
            try:
                from script_local import ScriptLocal
            except Exception:  # módulo do script local ausente ou com erro: painel segue, script aparece fechado
                return None
            try:
                self._script = ScriptLocal(self._pasta if self._pasta is not None else pasta_dados())
            except Exception:
                return None
        return self._script

    def _iniciar_script(self) -> None:
        try:
            script = self._carregar_script()
            if script is not None:
                script.iniciar()
        except Exception as erro:
            self._falhas.append(f"script_local.iniciar: {type(erro).__name__}")

    def _parar_script(self) -> None:
        try:
            if self._script is not None:
                self._script.parar()
        except Exception as erro:
            self._falhas.append(f"script_local.parar: {type(erro).__name__}")

    # Central (spec 026) ------------------------------------------------------------------------------------------------
    def _central(self) -> Central:
        if self._central_obj is None:
            self._central_obj = Central(self._pasta if self._pasta is not None else pasta_dados(), relogio=self._relogio)
        return self._central_obj

    def _rota_trechos(self) -> dict:
        """Para o servidor da janela (rotaguard_painel.py) servir os trechos baixados só com o segredo desta abertura."""
        return {"pasta": self._central().pasta_trechos, "segredo": self._segredo_trechos}

    def _iniciar_central(self) -> None:
        try:
            self._central().iniciar()
        except Exception as erro:
            self._falhas.append(f"central.iniciar: {type(erro).__name__}")

    def _parar_central(self) -> None:
        try:
            if self._central_obj is not None:
                self._central_obj.parar()
        except Exception as erro:
            self._falhas.append(f"central.parar: {type(erro).__name__}")

    def _ativar(self, admin, modo: str, empresa_nome: str, carregar, empresa_id=None) -> dict:
        n = self._n()
        if n.contas.ativado():
            raise ErroPainel(MENSAGEM_JA_ATIVADO, "conflito")
        n.contas.validar_admin(admin)  # antes de gravar qualquer coisa
        with n.banco.transacao():
            n.config.iniciar(empresa_nome)
            carregar(n.banco)
            linha, codigo = n.contas.criar_admin_inicial(admin)
            n.banco.meta_gravar("modo", modo)
            if empresa_id is not None:
                n.banco.meta_gravar("empresa_id", str(empresa_id))
            n.banco.meta_gravar("ativado", "1")
            n.atividades.registrar("ativou o painel", dict(linha),
                                   detalhe="sem o arquivo da empresa" if empresa_id is None else f"empresa {empresa_id}")
        usuario = n.contas.abrir_sessao(linha["id"])
        n.atividades.registrar("entrou", usuario)
        return {"codigo_recuperacao": codigo}

    # Entrar e sessão ---------------------------------------------------------------------------------------------------
    @_resposta()
    def estado(self):
        n = self._n()
        ativado = n.contas.ativado()
        sessao, bloqueado = n.contas.estado_sessao() if ativado else (None, False)
        config = n.config.ler()
        # Spec 019: tema e preferências da pessoa na sessão; sem sessão, o último tema salvo neste computador.
        preferencias = n.preferencias.ler(sessao["id"]) if sessao else None
        return {"ativado": ativado, "modo": n.banco.meta_ler("modo") if ativado else None,
                "empresa": {"nome": config["empresa"]["nome"]} if ativado else None, "sessao": sessao,
                "bloqueado": bloqueado, "versao": versao_app(), "compilacao": compilacao_do_pacote(),
                "bloqueio_min": config["acesso"]["bloqueio_min"],
                "texto_maior": bool(config["aparencia"]["texto_maior"]) if ativado else False,
                "tema": preferencias["tema"] if preferencias else n.preferencias.tema_ultimo(),
                "preferencias": preferencias, "videos_dias": config["guarda"]["videos_dias"]}

    @_resposta()
    def preferencias_salvar(self, valores):
        """Spec 019 (PRF-01): qualquer função, por pessoa; não vai para o registro de atividades."""
        quem = self._exigir()
        return self._n().preferencias.salvar(quem["id"], valores)

    @_resposta()
    def ativar_local(self, empresa, admin, opcoes=None):  # noqa: ARG002 - opcoes: só na web (código de ativação)
        """Spec 030 (SDF-06): sem o arquivo da empresa, cria a empresa com o nome digitado e o administrador, sem
        carregar nenhum registro. As caixas só chegam com o arquivo da empresa (CXA-01)."""
        if self._n().contas.ativado():
            raise ErroPainel(MENSAGEM_JA_ATIVADO, "conflito")
        return self._ativar(admin, "local", validar_nome_empresa(empresa), lambda banco: None)

    @_resposta()
    def ativar_com_arquivo(self, conteudo, admin, opcoes=None):  # noqa: ARG002 - opcoes: só na web
        if self._n().contas.ativado():
            raise ErroPainel(MENSAGEM_JA_ATIVADO, "conflito")
        chaveiro = ler_chaveiro(conteudo)
        return self._ativar(admin, "empresa", chaveiro["empresa_nome"],
                            lambda banco: carregar_caixas_do_arquivo(banco, chaveiro["caixas"]), chaveiro["empresa_id"])

    @_resposta()
    def entrar(self, usuario, senha):
        n = self._n()
        if not n.contas.ativado():
            raise ErroPainel(MENSAGEM_NAO_ATIVADO, "sem_sessao")
        return n.contas.entrar(usuario, senha)

    @_resposta()
    def sair(self):
        return self._n().contas.sair()

    @_resposta()
    def bloquear(self):
        return self._n().contas.bloquear()

    @_resposta()
    def tocar(self):
        return self._n().contas.tocar()

    @_resposta()
    def desbloquear(self, senha):
        return self._n().contas.desbloquear(senha)

    @_resposta()
    def trocar_senha(self, atual, nova):
        return self._n().contas.trocar_senha(atual, nova)

    @_resposta()
    def recuperar_acesso(self, usuario, codigo, nova_senha):
        n = self._n()
        if not n.contas.ativado():
            raise ErroPainel(MENSAGEM_NAO_ATIVADO, "sem_sessao")
        return n.contas.recuperar_acesso(usuario, codigo, nova_senha)

    # Equipe e atividades ----------------------------------------------------------------------------------------------
    @_resposta()
    def equipe_listar(self):
        self._exigir("equipe")
        return self._n().contas.equipe_listar()

    @_resposta()
    def equipe_adicionar(self, dados):
        return self._n().contas.equipe_adicionar(dados, self._exigir("equipe"))

    @_resposta()
    def equipe_alterar(self, usuario_id, mudancas):
        return self._n().contas.equipe_alterar(usuario_id, mudancas, self._exigir("equipe"))

    @_resposta()
    def equipe_nova_senha(self, usuario_id):
        return self._n().contas.equipe_nova_senha(usuario_id, self._exigir("equipe"))

    @_resposta()
    def atividades_listar(self, filtros=None):
        self._exigir("atividades")
        filtros = filtros if isinstance(filtros, dict) else {}
        n = self._n()
        try:
            itens = n.atividades.listar(filtros.get("usuario_id"), filtros.get("de"), filtros.get("ate"),
                                        filtros.get("limite"))
        except (TypeError, ValueError):
            raise ErroPainel("Filtro inválido.", "invalido") from None
        return {"itens": itens, "integro": n.atividades.verificar()}

    @_resposta(travar=False)
    def atividades_exportar(self):
        with self._trava:
            self._exigir("atividades")
            agora = self._n().banco.agora()
        destino = self._escolher_destino(f"rotaguard-atividades-{agora[:10]}.csv")  # sem trava: diálogo aberto
        with self._trava:
            n, quem = self._n(), self._exigir("atividades")
            n.atividades.registrar("exportou registro de atividades", quem, alvo=destino.name)
            n.atividades.exportar_csv(destino)
        return {"caminho": str(destino)}

    # Cadastros --------------------------------------------------------------------------------------------------------
    @_resposta()
    def motoristas_listar(self):
        self._exigir("ver_viagens")
        return self._n().cadastros.motoristas_listar()

    @_resposta()
    def motorista_salvar(self, dados):
        return self._n().cadastros.motorista_salvar(dados, self._exigir("cadastrar"))

    @_resposta(travar=False)
    def motorista_exportar(self, motorista_id):
        with self._trava:
            self._exigir("cadastrar")
            n = self._n()
            linha = n.banco.um("SELECT nome_curto FROM motoristas WHERE id = ?", (motorista_id,)) \
                if isinstance(motorista_id, int) and not isinstance(motorista_id, bool) else None
            if linha is None:
                raise ErroPainel("Motorista não encontrado.", "nao_encontrado")
            nome = "".join(c if c.isalnum() else "-" for c in linha["nome_curto"]).strip("-").lower()
        destino = self._escolher_destino(f"rotaguard-motorista-{nome}.json")
        with self._trava:
            return self._n().cadastros.motorista_exportar(motorista_id, destino, self._exigir("cadastrar"))

    # Termo importado (spec 019): só administrador e supervisor, pela ação "cadastrar" ---------------------------------
    @_resposta()
    def motorista_termos(self, motorista_id):
        self._exigir("cadastrar")
        return self._n().cadastros.motorista_termos(motorista_id)

    @_resposta()
    def termo_importar(self, motorista_id, arquivo, dados_termo):
        return self._n().cadastros.termo_importar(motorista_id, arquivo, dados_termo, self._exigir("cadastrar"))

    @_resposta()
    def termo_ver(self, motorista_id):
        return self._n().cadastros.termo_ver(motorista_id, self._exigir("cadastrar"), self._abrir_arquivo)

    @_resposta()
    def veiculos_listar(self):
        self._exigir("ver_viagens")
        return self._n().cadastros.veiculos_listar()

    @_resposta()
    def caixas_listar(self):
        self._exigir("ver_viagens")
        return self._n().cadastros.caixas_listar()

    @_resposta()
    def veiculo_salvar(self, dados):
        return self._n().cadastros.veiculo_salvar(dados, self._exigir("cadastrar"))

    @_resposta()
    def caixa_vincular(self, caixa_id, veiculo_id):
        return self._n().cadastros.caixa_vincular(caixa_id, veiculo_id, self._exigir("cadastrar"))

    # Configurações e cópia --------------------------------------------------------------------------------------------
    @_resposta()
    def config_ler(self):
        self._exigir("configuracoes")  # CFG-01: só o administrador lê; os outros recebem o que precisam em estado()
        return self._n().config.ler()

    @_resposta()
    def config_salvar(self, secao, valores):
        return self._n().config.salvar(secao, valores, self._exigir("configuracoes"))

    @_resposta(travar=False)
    def copia_fazer(self, senha):
        with self._trava:
            self._exigir("configuracoes")
            validar_senha(senha, "senha")
            agora = self._n().banco.agora()
        destino = self._escolher_destino(copia.nome_sugerido(agora))
        with self._trava:
            n, quem = self._n(), self._exigir("configuracoes")
            resultado = copia.fazer_copia(n.banco, senha, destino, self._custo)
            n.atividades.registrar("fez cópia de segurança", quem, alvo=Path(resultado["caminho"]).name,
                                   detalhe=f"{resultado['bytes']} bytes")
        return resultado

    # Início ------------------------------------------------------------------------------------------------------------
    @_resposta(travar=False)
    def inicio_resumo(self):
        """BKP-03 (aviso de cópia com mais de 7 dias), Primeiros passos (spec 017, decisão 6) e os números de hoje
        (spec 030, SDF-05). A central e o script local são lidos fora da trava: a tela não espera por eles."""
        with self._trava:
            self._exigir("ver_viagens")
            banco = self._n().banco
            ultima = banco.meta_ler("ultima_copia_em")
            escondidos = banco.meta_ler(CHAVE_PASSOS_ESCONDIDOS) == "1"
        dias = None
        if ultima:
            instante = datetime.fromisoformat(ultima.replace("Z", "+00:00")).timestamp()
            dias = max(0, int((self._relogio() - instante) // 86400))
        return {"ultima_copia_em": ultima, "dias_desde_copia": dias, "primeiros_passos_escondidos": escondidos,
                "hoje": self._resumo_de_hoje()}

    def _resumo_de_hoje(self) -> dict:
        """Testes, eventos e alertas do dia local (central + este computador) e quem está testando agora. Sem número
        inventado: o que não dá para ler conta zero."""
        inicio = datetime.fromtimestamp(self._relogio()).astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(days=1)
        vazio = {"sessoes": 0, "eventos": 0, "alertas": 0, "alertas_por_tipo": {}}
        script, aberto, local = self._carregar_script(), False, dict(vazio)
        if script is not None:
            try:
                aberto = bool(script.estado().get("aberto"))  # antes de contar: abre a sessão de quem acabou de abrir
                contar = getattr(script, "resumo_do_dia", None)
                if callable(contar):
                    local = contar(inicio, fim)
            except Exception as erro:
                self._falhas.append(f"script_local.resumo_do_dia: {type(erro).__name__}")
        central, conectada = {**vazio, "testando_agora": 0, "computadores": 0}, False
        try:
            conectada = bool(self._central().estado().get("conectado"))
            central = self._central().resumo_do_dia(inicio, fim)
        except Exception as erro:
            self._falhas.append(f"central.resumo_do_dia: {type(erro).__name__}")
        por_tipo = dict(central["alertas_por_tipo"])
        for tipo, quantidade in local["alertas_por_tipo"].items():
            por_tipo[tipo] = por_tipo.get(tipo, 0) + quantidade
        return {"testes": central["sessoes"] + local["sessoes"], "testes_central": central["sessoes"],
                "testes_locais": local["sessoes"], "eventos": central["eventos"] + local["eventos"],
                "alertas": central["alertas"] + local["alertas"], "alertas_por_tipo": dict(sorted(por_tipo.items())),
                "testando_agora": central["testando_agora"] + int(aberto), "computadores": central["computadores"],
                "script_aberto": aberto, "central_conectada": conectada}

    @_resposta()
    def primeiros_passos_esconder(self, esconder):
        quem = self._exigir("configuracoes")
        if not isinstance(esconder, bool):
            raise ErroPainel("Valor inválido.", "invalido", "esconder")
        n = self._n()
        with n.banco.transacao():
            n.banco.meta_gravar(CHAVE_PASSOS_ESCONDIDOS, "1" if esconder else "0")
            n.atividades.registrar("escondeu primeiros passos" if esconder else "mostrou primeiros passos", quem)
        return {"primeiros_passos_escondidos": esconder}

    # Decisões e vídeo -------------------------------------------------------------------------------------------------
    @_resposta()
    def decisoes_listar(self):
        self._exigir("ver_viagens")
        return self._n().decisoes.listar()

    @_resposta()
    def decisao_registrar(self, momento_id, resultado):
        return self._n().decisoes.registrar(momento_id, resultado, self._exigir("decidir"))

    @_resposta()
    def decisao_desfazer(self, momento_id):
        return self._n().decisoes.desfazer(momento_id, self._exigir("decidir"))

    @_resposta()
    def decisao_orientado(self, momento_id, orientado):
        return self._n().decisoes.orientado(momento_id, orientado, self._exigir("decidir"))

    @_resposta()
    def video_abrir(self, momento_id, motorista_ref):
        quem = self._exigir("ver_video")
        n = self._n()
        Decisoes._validar_momento(momento_id)  # noqa: SLF001 - mesma regra de identificador do momento
        resultado = n.cadastros.video_liberado(motorista_ref)
        n.atividades.registrar("abriu vídeo" if resultado["liberado"] else "vídeo trancado", quem, alvo=momento_id,
                               detalhe=None if resultado["liberado"] else resultado["motivo"])
        return resultado

    # Central e testes à distância (spec 026) --------------------------------------------------------------------------
    # A rede roda fora da trava da Ponte: a tela não congela esperando a central.
    @_resposta(travar=False)
    def central_estado(self):
        with self._trava:
            self._exigir("ver_viagens")
        return self._central().estado()

    @_resposta(travar=False)
    def central_conectar(self, endereco, usuario, senha):
        with self._trava:
            quem = self._exigir("configuracoes")
        estado = self._central().conectar(endereco, usuario, senha)
        with self._trava:
            nome = (estado.get("usuario") or {}).get("nome")
            empresa = (estado.get("empresa") or {}).get("nome")
            self._n().atividades.registrar("conectou à central", quem, alvo=estado["host"],
                                           detalhe=f"como {nome} · {empresa}")
        return estado

    @_resposta(travar=False)
    def central_desconectar(self):
        with self._trava:
            quem = self._exigir("configuracoes")
        estado = self._central().desconectar()
        with self._trava:
            self._n().atividades.registrar("desconectou da central", quem, alvo=estado["host"],
                                           detalhe="o que já foi baixado continua no painel")
        return estado

    @_resposta(travar=False)
    def central_gerar_codigo(self, nome=None):
        with self._trava:
            quem = self._exigir("configuracoes")
        codigo = self._central().gerar_codigo(nome)
        with self._trava:  # o código em si não vai para o registro: vale 30 min e serve uma vez
            self._n().atividades.registrar("gerou código para outro computador", quem, alvo=codigo["nome"] or "sem nome",
                                           detalhe=f"vale {codigo['validade_min']} min")
        return codigo

    @_resposta(travar=False)
    def remotos_listar(self):
        with self._trava:
            self._exigir("ver_viagens")
        return self._central().listar()

    @_resposta(travar=False)
    def remotos_sessao(self, sessao_uid):
        with self._trava:
            quem = self._exigir("ver_viagens")
        return self._central().sessao(sessao_uid, pode(quem["funcao"], "ver_video"))

    @_resposta(travar=False)
    def remotos_trecho(self, trecho_uid):
        with self._trava:
            quem = self._exigir("ver_video")
        trecho = self._central().trecho(trecho_uid, self._segredo_trechos)
        if trecho["disponivel"]:
            with self._trava:
                self._n().atividades.registrar("abriu trecho", quem, alvo=f"{trecho['tipo']} · {trecho['aparelho_nome']}",
                                               detalhe=trecho["uid"])
        return trecho

    # Script local (agente 2) ------------------------------------------------------------------------------------------
    @_resposta(travar=False)
    def script_estado(self):
        with self._trava:
            self._exigir("ver_viagens")
        script = self._carregar_script()
        return dict(ESTADO_SCRIPT_FECHADO) if script is None else script.estado()

    @_resposta(travar=False)
    def script_eventos(self, desde_id=0):
        with self._trava:
            self._exigir("ver_viagens")
        if not isinstance(desde_id, int) or isinstance(desde_id, bool) or desde_id < 0:
            raise ErroPainel("Número de evento inválido.", "invalido", "desde_id")
        script = self._carregar_script()
        return [] if script is None else script.eventos(desde_id)
