"""Painel da empresa no navegador (spec 024): servidor HTTP da mesma ponte do app instalado.

As telas do painel só falam com `bridge` (painel/app/src/lib/bridge.ts). No build web, `bridge` chama
`POST {base}/api/ponte/{metodo}` com `{"args": [...]}` e este servidor chama o método de mesmo nome da `Ponte`
(painel/desktop/ponte.py), que devolve o mesmo `{"ok": ...}` da janela do app. As regras continuam nos módulos puros.

- Uma `Ponte` por sessão do navegador, todas sobre a mesma pasta de dados (uma conexão SQLite por Ponte, em modo de
  diário padrão: o WAL deixaria a cópia de segurança ilegível pelo `deserialize`). Quem ainda não entrou usa uma Ponte
  comum só para `estado` e `recuperar_acesso`; `entrar` e a ativação abrem uma Ponte nova e só viram sessão se derem
  certo. A espera crescente das contas (5 erros) é a mesma para todas as Pontes.
- Cookie `rg_painel` aleatório, HttpOnly, Secure, SameSite=Strict, Path={base}. Sessão some depois do tempo de bloqueio
  das configurações sem uso e, em uso, depois de 12 h. No máximo 200 sessões (a de uso mais antigo sai).
- POST só com `X-RotaGuard: 1` e `Origin` igual a PAINEL_ORIGEM; corpo até 16 MB; 10 tentativas por minuto por IP em
  entrar, recuperar_acesso, desbloquear e ativação.
- Ativar pela web exige o código de PAINEL_CODIGO_ATIVACAO, no campo `ativacao` do corpo (não em cabeçalho: proxies
  costumam registrar cabeçalhos).
- Exportações, cópia de segurança e o PDF do termo voltam no JSON em `arquivo: {nome, tipo, base64}`; a pasta
  temporária de cada chamada é apagada antes da resposta.
- Nunca registra senha, código nem corpo da requisição.

Rodar (um processo só: sessões e limites ficam na memória):
    python -m uvicorn servidor_web:app --app-dir painel/web --host 0.0.0.0 --port 8000 --workers 1 \
        --no-proxy-headers --no-server-header
"""
from __future__ import annotations

import base64
import collections
import hmac
import ipaddress
import json
import logging
import os
import re
import secrets
import shutil
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

AQUI = Path(__file__).resolve().parent
NUCLEO = Path(os.environ.get("PAINEL_NUCLEO") or AQUI.parent / "desktop").resolve()
if str(NUCLEO) not in sys.path:
    sys.path.insert(0, str(NUCLEO))

from contas import CUSTO_PRODUCAO  # noqa: E402
from ponte import ESTADO_SCRIPT_FECHADO, Ponte  # noqa: E402

registro = logging.getLogger("rotaguard.painel.web")

# Mesma lista e mesma ordem de NOMES em painel/app/src/lib/bridge.ts (o teste confere).
NOMES = (
    "estado", "ativar_local", "ativar_com_arquivo", "entrar", "sair", "bloquear", "tocar", "desbloquear",
    "trocar_senha", "recuperar_acesso", "equipe_listar", "equipe_adicionar", "equipe_alterar", "equipe_nova_senha",
    "atividades_listar", "atividades_exportar", "motoristas_listar", "motorista_salvar", "motorista_exportar",
    "veiculos_listar", "caixas_listar", "veiculo_salvar", "caixa_vincular", "config_ler", "config_salvar",
    "decisoes_listar", "decisao_registrar", "decisao_desfazer", "decisao_orientado", "video_abrir", "copia_fazer",
    "inicio_resumo", "primeiros_passos_esconder", "preferencias_salvar", "termo_importar", "termo_ver",
    "motorista_termos", "script_estado", "script_eventos",
)
# Spec 026: central e testes à distância são só do app instalado (o painel web não foi publicado). Ficam fora daqui:
# na web, 404 como qualquer nome desconhecido.
NOMES_SO_NO_APP = ("central_estado", "central_conectar", "central_desconectar", "central_gerar_codigo", "remotos_listar",
                   "remotos_sessao", "remotos_trecho")
_PERMITIDOS = frozenset(NOMES)
ATIVACAO = frozenset({"ativar_local", "ativar_com_arquivo"})
LIMITADOS = frozenset({"entrar", "recuperar_acesso", "desbloquear"}) | ATIVACAO
# Calculam scrypt (128 MB de memória cada): no máximo PAINEL_SCRYPT_SIMULTANEOS ao mesmo tempo (padrão 1).
PESADOS = frozenset({"entrar", "desbloquear", "trocar_senha", "recuperar_acesso", "equipe_adicionar",
                     "equipe_nova_senha", "copia_fazer"}) | ATIVACAO
EXPORTAM = frozenset({"atividades_exportar", "motorista_exportar", "copia_fazer"})

COOKIE = "rg_painel"
LIMITE_CORPO = 16 * 1024 * 1024
LIMITE_ARQUIVO = 32 * 1024 * 1024
MAXIMO_ARGUMENTOS = 8
MAXIMO_SESSOES = 200
SESSAO_MAXIMA_S = 12 * 60 * 60
BLOQUEIO_PADRAO_MIN = 15
TENTATIVAS_POR_MINUTO = 10
JANELA_TENTATIVAS_S = 60
VARREDURA_S = 60
TAMANHO_MINIMO_CODIGO = 12
PASTA_SAIDAS = "rg-painel-web"  # nomes curtos: no Windows sem caminho longo, o limite é 260 caracteres

MENSAGEM_SEM_SESSAO = "Entre de novo para continuar."
MENSAGEM_FALHA = "Algo deu errado. Tente de novo; se continuar, fale com a RotaGuard."
MENSAGEM_JA_ATIVADO = "O painel já foi ativado."
MENSAGEM_SCRIPT_WEB = ("O teste com o script deste computador não existe no painel pela internet. "
                       "Use a câmera deste aparelho.")
TIPOS_ARQUIVO = {".json": "application/json", ".csv": "text/csv", ".pdf": "application/pdf",
                 ".rotaguard-copia": "application/octet-stream"}

# X-Forwarded-For só vale quando a conexão vem destas redes (o Caddy, na rede do Docker). PAINEL_PROXIES troca.
PROXIES_PADRAO = tuple(ipaddress.ip_network(rede) for rede in (
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "::1/128", "fc00::/7"))

# Igual à do app instalado (rotaguard_painel.py), mais o que a câmera do navegador (spec 025) precisa: WebAssembly,
# trabalhadores e vídeo em blob:. PAINEL_CSP troca (vazio: sem a política).
POLITICA_PADRAO = "; ".join((
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "media-src 'self' blob:",
    "font-src 'self' data:",
    "connect-src 'self'",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))
PERMISSOES_NAVEGADOR = "camera=(self), microphone=(), geolocation=(), payment=(), usb=()"


# ---------------------------------------------------------------------------------------------------------------------
# Ajudas puras
# ---------------------------------------------------------------------------------------------------------------------
def _erro(texto: str, codigo: str, campo: str | None = None, esperar_s: int | None = None) -> dict:
    resposta = {"ok": False, "erro": texto, "codigo": codigo}
    if campo:
        resposta["campo"] = campo
    if esperar_s is not None:
        resposta["esperar_s"] = esperar_s
    return resposta


def ip_do_cliente(host, encaminhado, proxies) -> str:
    """IP de quem pediu. O primeiro IP de X-Forwarded-For só vale se a conexão vier de um proxy confiável."""
    if not host:
        return "desconhecido"
    try:
        par = ipaddress.ip_address(host)
    except ValueError:
        return str(host)
    if encaminhado and any(par in rede for rede in proxies):
        primeiro = encaminhado.split(",", 1)[0].strip()
        try:
            return str(ipaddress.ip_address(primeiro))
        except ValueError:
            pass
    return str(par)


def _nome_seguro(nome) -> str:
    texto = Path(str(nome)).name if nome else ""
    texto = re.sub(r"[^\w.-]", "-", texto).strip(".-")[:120]
    return texto or "arquivo"


def _base(valor) -> str:
    texto = (valor or "").strip().rstrip("/")
    if texto and not re.fullmatch(r"(/[A-Za-z0-9._-]+)+", texto):
        raise ValueError("PAINEL_BASE precisa ser um caminho como /painel")
    return texto


def _origem(valor) -> str | None:
    texto = (valor or "").strip().rstrip("/").lower()
    return texto or None


def _proxies(valor) -> tuple:
    if valor is None:
        return PROXIES_PADRAO
    texto = valor.strip().lower()
    if texto in ("", "nenhum"):
        return ()
    return tuple(ipaddress.ip_network(parte.strip(), strict=False) for parte in texto.split(",") if parte.strip())


def config_do_ambiente(ambiente=None) -> dict:
    """Parâmetros de `criar_app` a partir das variáveis PAINEL_* (padrões de produção)."""
    ambiente = os.environ if ambiente is None else ambiente
    codigo = (ambiente.get("PAINEL_CODIGO_ATIVACAO") or "").strip()
    if codigo and len(codigo) < TAMANHO_MINIMO_CODIGO:
        registro.warning("PAINEL_CODIGO_ATIVACAO tem menos de %d caracteres: ativação pela web desligada",
                         TAMANHO_MINIMO_CODIGO)
        codigo = ""
    estatico = (ambiente.get("PAINEL_ESTATICO") or "").strip()
    temp = (ambiente.get("PAINEL_TEMP") or "").strip()
    return {
        "pasta": Path(ambiente.get("PAINEL_DADOS") or "/dados"),
        "estatico": Path(estatico) if estatico else None,
        "base": _base(ambiente.get("PAINEL_BASE", "/painel")),
        "codigo_ativacao": codigo or None,
        "origem": _origem(ambiente.get("PAINEL_ORIGEM")),
        "cookie_seguro": (ambiente.get("PAINEL_COOKIE_SEGURO") or "1").strip() != "0",
        "pasta_temp": Path(temp) if temp else None,
        "proxies": _proxies(ambiente.get("PAINEL_PROXIES")),
        "csp": ambiente.get("PAINEL_CSP", POLITICA_PADRAO),
        "scrypt_simultaneos": max(1, int(ambiente.get("PAINEL_SCRYPT_SIMULTANEOS") or 1)),
    }


class ScriptIndisponivel:
    """No servidor não existe o script do computador: a tela Ao vivo usa a câmera do navegador (spec 025)."""

    def estado(self) -> dict:
        return {**ESTADO_SCRIPT_FECHADO, "indisponivel": MENSAGEM_SCRIPT_WEB}

    def eventos(self, desde_id) -> list:
        return []

    def iniciar(self) -> None:
        pass

    def parar(self) -> None:
        pass


class LimiteDeTentativas:
    """Janela deslizante em memória: no máximo `maximo` tentativas por chave a cada `janela_s` segundos."""

    def __init__(self, maximo: int, janela_s: float, relogio):
        self.maximo, self.janela_s, self.relogio = maximo, janela_s, relogio
        self._marcas: dict[str, collections.deque] = {}
        self._trava = threading.Lock()

    def permitir(self, chave: str) -> int:
        """0 se pode; senão, quantos segundos esperar."""
        agora = self.relogio()
        with self._trava:
            marcas = self._marcas.setdefault(chave, collections.deque())
            while marcas and marcas[0] <= agora - self.janela_s:
                marcas.popleft()
            if len(marcas) >= self.maximo:
                return max(1, int(marcas[0] + self.janela_s - agora + 0.999))
            marcas.append(agora)
            return 0

    def limpar(self) -> None:
        limite = self.relogio() - self.janela_s
        with self._trava:
            for chave in [c for c, m in self._marcas.items() if not m or m[-1] <= limite]:
                del self._marcas[chave]


# ---------------------------------------------------------------------------------------------------------------------
# Sessões e chamadas
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class Sessao:
    ponte: Ponte
    criada: float
    ultimo_uso: float
    uso: int = 0
    encerrada: bool = False


@dataclass
class Saida:
    """Arquivos de uma chamada: o que a Ponte gravou (pasta temporária própria) e o que pediu para abrir."""
    raiz: Path
    pasta: Path | None = None
    abertos: list = field(default_factory=list)

    def destino(self, nome) -> Path:
        if self.pasta is None:
            self.pasta = Path(tempfile.mkdtemp(prefix="s-", dir=self.raiz)).resolve()
        return self.pasta / _nome_seguro(nome)

    def limpar(self) -> None:
        if self.pasta is not None:
            shutil.rmtree(self.pasta, ignore_errors=True)
            self.pasta = None


class Recusa(Exception):
    def __init__(self, status: int, resposta: dict, cabecalhos: dict | None = None):
        super().__init__(resposta["erro"])
        self.status, self.resposta, self.cabecalhos = status, resposta, cabecalhos or {}


class ServidorPainel:
    def __init__(self, pasta, codigo_ativacao=None, cookie_seguro=True, base="/painel", custo_scrypt=CUSTO_PRODUCAO,
                 relogio=time.time, pasta_temp=None, max_sessoes=MAXIMO_SESSOES, scrypt_simultaneos=1):
        self.pasta = Path(pasta).resolve()
        self.pasta.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            try:
                os.chmod(self.pasta, 0o700)
            except OSError:
                registro.warning("não deu para restringir a pasta de dados a este usuário")
        self.codigo = codigo_ativacao.encode("utf-8") if codigo_ativacao else None
        self.cookie_seguro, self.base, self.custo, self.relogio = cookie_seguro, base, custo_scrypt, relogio
        self.max_sessoes = max_sessoes
        # Subpasta só nossa dentro de PAINEL_TEMP (ou da temporária do sistema): só ela é limpa ao subir.
        self.temp = Path(pasta_temp or tempfile.gettempdir()) / PASTA_SAIDAS
        if self.temp.exists():
            shutil.rmtree(self.temp, ignore_errors=True)  # sobras de um processo anterior
        self.temp.mkdir(parents=True, exist_ok=True)
        self.temp = self.temp.resolve()
        self.limite = LimiteDeTentativas(TENTATIVAS_POR_MINUTO, JANELA_TENTATIVAS_S, relogio)
        self._sessoes: dict[str, Sessao] = {}
        self._trava = threading.Lock()
        self._trava_ativacao = threading.Lock()
        self._scrypt = threading.BoundedSemaphore(scrypt_simultaneos)
        self._local = threading.local()
        self._erros_compartilhados: dict = {}
        self._ultima_varredura = relogio()
        # Ponte de quem ainda não entrou (só `estado` e `recuperar_acesso`, que nunca abrem sessão). Criada já aqui:
        # abre o banco e aplica as migrações antes de qualquer outra conexão.
        self._anonima = self._nova_ponte()
        self._bloqueio_s = self._ler_bloqueio_s()

    # Pontes ----------------------------------------------------------------------------------------------------------
    def _nova_ponte(self) -> Ponte:
        ponte = Ponte(self.pasta, relogio=self.relogio, custo_scrypt=self.custo, escolher_destino=self._destino,
                      script_local=ScriptIndisponivel(), abrir_arquivo=self._abrir)
        nucleo = ponte._n()  # noqa: SLF001 - abre o banco agora (dentro do limite de scrypt de quem chamou)
        # A contagem de erros de senha fica na memória de cada Contas: na web, uma só para todas as Pontes, senão
        # bastaria abrir outra sessão para zerar a espera crescente.
        nucleo.contas._erros = self._erros_compartilhados  # noqa: SLF001
        return ponte

    def _destino(self, nome_sugerido) -> Path:
        saida = getattr(self._local, "saida", None)
        if saida is None:
            raise RuntimeError("chamada sem contexto de saída")
        return saida.destino(nome_sugerido)

    def _abrir(self, caminho) -> None:
        saida = getattr(self._local, "saida", None)
        if saida is None:
            raise RuntimeError("chamada sem contexto de saída")
        saida.abertos.append(Path(caminho))

    def _ler_bloqueio_s(self) -> float:
        try:
            return float(self._anonima._n().config.bloqueio_min()) * 60  # noqa: SLF001
        except Exception:
            return BLOQUEIO_PADRAO_MIN * 60.0

    # Sessões ---------------------------------------------------------------------------------------------------------
    def total_sessoes(self) -> int:
        with self._trava:
            return len(self._sessoes)

    def sessoes_ativas(self) -> list[Sessao]:
        with self._trava:
            return list(self._sessoes.values())

    def _expirada(self, sessao: Sessao, agora: float) -> bool:
        return agora - sessao.ultimo_uso >= self._bloqueio_s or agora - sessao.criada >= SESSAO_MAXIMA_S

    def _encerrar(self, sessao: Sessao) -> None:
        """Chamar com self._trava. Fecha o banco agora ou, se alguma chamada ainda usa a Ponte, quando ela terminar."""
        sessao.encerrada = True
        if sessao.uso == 0:
            self._fechar(sessao)

    @staticmethod
    def _fechar(sessao: Sessao) -> None:
        try:
            nucleo = sessao.ponte._nucleo  # noqa: SLF001
            if nucleo is not None:
                nucleo.banco.fechar()
        except Exception as falha:
            registro.warning("não fechou o banco de uma sessão: %s", type(falha).__name__)

    def _varrer(self, agora: float) -> None:
        if agora - self._ultima_varredura < VARREDURA_S:
            return
        self._ultima_varredura = agora
        self._bloqueio_s = self._ler_bloqueio_s()
        with self._trava:
            for chave in [c for c, s in self._sessoes.items() if self._expirada(s, agora)]:
                self._encerrar(self._sessoes.pop(chave))
        self.limite.limpar()

    def _pegar(self, cookie: str | None) -> tuple[Sessao | None, bool]:
        """(sessão em uso, cookie_invalido). Marca o uso; quem pega devolve com `_soltar`."""
        agora = self.relogio()
        self._varrer(agora)
        if not cookie:
            return None, False
        with self._trava:
            sessao = self._sessoes.get(cookie)
            if sessao is None:
                return None, True
            if self._expirada(sessao, agora):
                self._encerrar(self._sessoes.pop(cookie))
                return None, True
            sessao.uso += 1
            sessao.ultimo_uso = agora
            return sessao, False

    def _soltar(self, sessao: Sessao) -> None:
        with self._trava:
            sessao.uso -= 1
            if sessao.encerrada and sessao.uso == 0:
                self._fechar(sessao)

    def _guardar(self, ponte: Ponte, sessao: Sessao | None = None) -> str:
        """Nova id para a Ponte (sessão nova ou troca de id ao entrar). Com o máximo cheio, sai a de uso mais antigo."""
        agora = self.relogio()
        chave = secrets.token_urlsafe(32)
        with self._trava:
            if sessao is not None:
                for antiga in [c for c, s in self._sessoes.items() if s is sessao]:
                    del self._sessoes[antiga]
            else:
                sessao = Sessao(ponte=ponte, criada=agora, ultimo_uso=agora)
            while len(self._sessoes) >= self.max_sessoes:
                mais_velha = min(self._sessoes, key=lambda c: self._sessoes[c].ultimo_uso)
                self._encerrar(self._sessoes.pop(mais_velha))
            sessao.ultimo_uso = agora
            self._sessoes[chave] = sessao
        return chave

    def _remover(self, sessao: Sessao) -> None:
        with self._trava:
            for chave in [c for c, s in self._sessoes.items() if s is sessao]:
                del self._sessoes[chave]
            self._encerrar(sessao)

    # Chamadas --------------------------------------------------------------------------------------------------------
    def _codigo_confere(self, ativacao) -> dict | None:
        if self.codigo is None:
            return _erro("A ativação pela internet está desligada neste servidor.", "sem_permissao", "codigo_ativacao")
        if not isinstance(ativacao, str) or not ativacao.strip():
            return _erro("Informe o código de ativação.", "sem_permissao", "codigo_ativacao")
        if not hmac.compare_digest(ativacao.strip().encode("utf-8"), self.codigo):
            return _erro("Código de ativação incorreto.", "sem_permissao", "codigo_ativacao")
        return None

    def _executar(self, ponte: Ponte, metodo: str, args: list) -> dict:
        saida = Saida(self.temp)
        self._local.saida = saida
        falhas_antes = len(ponte._falhas)  # noqa: SLF001
        try:
            resposta = getattr(ponte, metodo)(*args)
            if not isinstance(resposta, dict) or "ok" not in resposta:
                raise TypeError("resposta fora do contrato")
            resposta = self._anexar_arquivo(metodo, resposta, saida)
        finally:
            self._local.saida = None
            saida.limpar()
        for falha in ponte._falhas[falhas_antes:]:  # noqa: SLF001 - só "método: TipoDoErro", nunca argumentos
            registro.error("falha interna na ponte: %s", falha)
        return resposta

    def _anexar_arquivo(self, metodo: str, resposta: dict, saida: Saida) -> dict:
        if not resposta.get("ok"):
            return resposta
        caminho = None
        if metodo in EXPORTAM and saida.pasta is not None:
            caminho = Path(resposta["dados"]["caminho"]).resolve()
            if not caminho.is_relative_to(saida.pasta):
                raise RuntimeError("arquivo fora da pasta temporária")
            nome = caminho.name
            resposta["dados"]["caminho"] = nome  # sem caminho do servidor na tela
        elif metodo == "termo_ver" and resposta["dados"].get("tipo") == "pdf" and saida.abertos:
            caminho = saida.abertos[-1].resolve()
            if not caminho.is_relative_to(self.pasta):
                raise RuntimeError("termo fora da pasta de dados")
            nome = resposta["dados"].get("nome") or caminho.name
        if caminho is None:
            return resposta
        if caminho.stat().st_size > LIMITE_ARQUIVO:
            return _erro("O arquivo ficou grande demais para baixar pelo navegador (mais de 32 MB).", "invalido")
        resposta["arquivo"] = {"nome": nome, "tipo": TIPOS_ARQUIVO.get("".join(caminho.suffixes[-1:]).lower(),
                                                                       "application/octet-stream"),
                               "base64": base64.b64encode(caminho.read_bytes()).decode("ascii")}
        return resposta

    def _pesado(self, metodo: str):
        return self._scrypt if metodo in PESADOS else _SemTrava()

    def processar(self, metodo: str, args: list, ativacao, cookie: str | None) -> tuple[dict, str | None]:
        """Resposta da ponte e o que fazer com o cookie: None (nada), "" (apagar) ou a id nova."""
        if metodo in ATIVACAO:
            recusa = self._codigo_confere(ativacao)
            if recusa is not None:
                return recusa, None
        sessao, invalido = self._pegar(cookie)
        apagar = "" if invalido else None
        if sessao is None:
            return self._sem_sessao(metodo, args, apagar)
        try:
            with self._pesado(metodo):
                resposta = self._executar(sessao.ponte, metodo, args)
            if metodo == "sair":
                self._remover(sessao)
                return resposta, ""
            if metodo == "entrar" and resposta.get("ok"):
                return resposta, self._guardar(sessao.ponte, sessao)  # id nova a cada entrada
            if metodo in ATIVACAO and resposta.get("codigo") == "conflito":
                resposta["erro"] = MENSAGEM_JA_ATIVADO
            return resposta, None
        finally:
            self._soltar(sessao)

    def _sem_sessao(self, metodo: str, args: list, apagar) -> tuple[dict, str | None]:
        if metodo in ("estado", "recuperar_acesso"):
            with self._pesado(metodo):
                return self._executar(self._anonima, metodo, args), apagar
        if metodo == "sair":
            return {"ok": True, "dados": {}}, ""
        if metodo != "entrar" and metodo not in ATIVACAO:
            return _erro(MENSAGEM_SEM_SESSAO, "sem_sessao"), apagar
        trava = self._trava_ativacao if metodo in ATIVACAO else _SemTrava()
        with trava, self._scrypt:
            ponte = self._nova_ponte()
            try:
                resposta = self._executar(ponte, metodo, args)
            except BaseException:
                ponte._n().banco.fechar()  # noqa: SLF001
                raise
        if not resposta.get("ok"):
            ponte._n().banco.fechar()  # noqa: SLF001 - não vira sessão
            if metodo in ATIVACAO and resposta.get("codigo") == "conflito":
                resposta["erro"] = MENSAGEM_JA_ATIVADO
            return resposta, apagar
        return resposta, self._guardar(ponte)


class _SemTrava:
    def __enter__(self):
        return self

    def __exit__(self, *erro):
        return False


# ---------------------------------------------------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------------------------------------------------
class CabecalhosDeSeguranca:
    """ASGI: corrige o esquema vindo do proxy e põe os cabeçalhos de segurança e de cache em toda resposta."""

    def __init__(self, app, base: str, csp: str | None, proxies):
        self.app, self.base, self.csp, self.proxies = app, base, csp, proxies

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        cliente = scope.get("client")
        if cliente:
            try:
                confiavel = any(ipaddress.ip_address(cliente[0]) in rede for rede in self.proxies)
            except ValueError:
                confiavel = False
            if confiavel:
                for chave, valor in scope.get("headers", []):
                    if chave == b"x-forwarded-proto" and valor in (b"https", b"http"):
                        scope = {**scope, "scheme": valor.decode("ascii")}
        caminho = scope.get("path", "")

        async def enviar(mensagem):
            if mensagem["type"] == "http.response.start":
                cabecalhos = MutableHeaders(scope=mensagem)
                cabecalhos["X-Content-Type-Options"] = "nosniff"
                cabecalhos["Referrer-Policy"] = "same-origin"
                cabecalhos["X-Frame-Options"] = "DENY"
                cabecalhos["Permissions-Policy"] = PERMISSOES_NAVEGADOR
                if self.csp:
                    cabecalhos["Content-Security-Policy"] = self.csp
                if "cache-control" not in cabecalhos:
                    imutavel = caminho.startswith(f"{self.base}/_next/static/")
                    cabecalhos["Cache-Control"] = "public, max-age=31536000, immutable" if imutavel else "no-cache"
            await send(mensagem)

        await self.app(scope, receive, enviar)


def _json(conteudo: dict, status: int = 200, cabecalhos: dict | None = None) -> JSONResponse:
    resposta = JSONResponse(conteudo, status_code=status)
    resposta.headers["Cache-Control"] = "no-store"
    for chave, valor in (cabecalhos or {}).items():
        resposta.headers[chave] = valor
    return resposta


def _cookie(nome: str, valor: str, base: str, seguro: bool, apagar: bool = False) -> str:
    partes = [f"{nome}={valor}", f"Path={base or '/'}", "HttpOnly"]
    if seguro:
        partes.append("Secure")
    partes.append("SameSite=Strict")
    if apagar:
        partes.insert(1, "Max-Age=0")
    return "; ".join(partes)


async def _ler_corpo(request: Request) -> bytes:
    declarado = request.headers.get("content-length")
    if declarado is not None:
        try:
            tamanho = int(declarado)
        except ValueError:
            raise Recusa(400, _erro("Pedido inválido.", "invalido")) from None
        if tamanho > LIMITE_CORPO:
            raise Recusa(413, _erro("O pedido passou de 16 MB.", "invalido"))
    partes, total = [], 0
    async for parte in request.stream():
        total += len(parte)
        if total > LIMITE_CORPO:
            raise Recusa(413, _erro("O pedido passou de 16 MB.", "invalido"))
        partes.append(parte)
    return b"".join(partes)


def _recusar_constante(_valor):
    raise ValueError("número fora do JSON")


def _ler_pedido(corpo: bytes) -> tuple[list, str | None]:
    try:
        pedido = json.loads(corpo.decode("utf-8"), parse_constant=_recusar_constante) if corpo.strip() else {}
    except (ValueError, UnicodeDecodeError):
        raise Recusa(400, _erro("Pedido inválido.", "invalido")) from None
    if not isinstance(pedido, dict):
        raise Recusa(400, _erro("Pedido inválido.", "invalido"))
    args, ativacao = pedido.get("args", []), pedido.get("ativacao")
    if not isinstance(args, list) or len(args) > MAXIMO_ARGUMENTOS:
        raise Recusa(400, _erro("Pedido inválido.", "invalido"))
    if ativacao is not None and (not isinstance(ativacao, str) or len(ativacao) > 200):
        raise Recusa(400, _erro("Pedido inválido.", "invalido"))
    return args, ativacao


def criar_app(pasta, estatico=None, base="/painel", codigo_ativacao=None, origem=None, cookie_seguro=True,
              custo_scrypt=CUSTO_PRODUCAO, relogio=time.time, pasta_temp=None, max_sessoes=MAXIMO_SESSOES,
              proxies=PROXIES_PADRAO, csp=POLITICA_PADRAO, scrypt_simultaneos=1) -> CabecalhosDeSeguranca:
    base = _base(base)
    origem = _origem(origem)
    painel = ServidorPainel(pasta, codigo_ativacao, cookie_seguro, base, custo_scrypt, relogio, pasta_temp,
                            max_sessoes, scrypt_simultaneos)

    def origem_confere(request: Request) -> bool:
        recebida = _origem(request.headers.get("origin"))
        if not recebida:
            return False
        if origem is not None:
            return recebida == origem  # não é segredo: comparação simples (aceita qualquer caractere)
        partes = urlsplit(recebida)  # sem PAINEL_ORIGEM: o mesmo host que o navegador usou
        return bool(partes.netloc) and partes.netloc == (request.headers.get("host") or "").lower()

    async def ponte(request: Request) -> Response:
        metodo = request.path_params["metodo"]
        try:
            if request.headers.get("x-rotaguard") != "1" or not origem_confere(request):
                raise Recusa(403, _erro("Pedido recusado.", "sem_permissao"))
            if metodo not in _PERMITIDOS:
                raise Recusa(404, _erro("Esta função não existe no painel.", "nao_encontrado"))
            if metodo in LIMITADOS:
                ip = ip_do_cliente(request.client.host if request.client else None,
                                   request.headers.get("x-forwarded-for"), proxies)
                esperar = painel.limite.permitir(ip)
                if esperar:
                    raise Recusa(429, _erro(f"Muitas tentativas. Espere {esperar} segundos e tente de novo.",
                                            "espera", esperar_s=esperar), {"Retry-After": str(esperar)})
            args, ativacao = _ler_pedido(await _ler_corpo(request))
        except Recusa as recusa:
            return _json(recusa.resposta, recusa.status, recusa.cabecalhos)
        try:
            resposta, cookie = await run_in_threadpool(painel.processar, metodo, args, ativacao,
                                                       request.cookies.get(COOKIE))
        except Exception as falha:
            registro.error("falha interna em %s: %s", metodo, type(falha).__name__)
            return _json(_erro(MENSAGEM_FALHA, "invalido"), 500)
        saida = _json(resposta)
        if cookie is not None:
            saida.headers.append("Set-Cookie", _cookie(COOKIE, cookie, base, cookie_seguro, apagar=cookie == ""))
        return saida

    async def saude(_request: Request) -> Response:
        return _json({"ok": True})

    async def api_inexistente(request: Request) -> Response:
        if request.url.path.startswith(f"{base}/api/ponte/"):
            return _json(_erro("Use POST.", "invalido"), 405, {"Allow": "POST"})
        return _json(_erro("Endereço desconhecido.", "nao_encontrado"), 404)

    async def com_barra(_request: Request) -> Response:
        return RedirectResponse(f"{base}/", status_code=308)

    rotas = [
        Route(f"{base}/api/saude", saude, methods=["GET", "HEAD"]),
        Route(f"{base}/api/ponte/{{metodo}}", ponte, methods=["POST"]),
        Route(f"{base}/api/{{resto:path}}", api_inexistente),
    ]
    if base:
        rotas.append(Route(base, com_barra))
    if estatico is not None:
        rotas.append(Mount(base or "/", app=StaticFiles(directory=Path(estatico), html=True)))
    else:
        registro.warning("PAINEL_ESTATICO não definido: só a API do painel responde")
    app = Starlette(routes=rotas)
    app.state.painel = painel
    if not origem:
        registro.warning("PAINEL_ORIGEM não definido: o POST só passa com Origin do mesmo host do pedido")
    registro.info("painel web pronto: base=%s dados=%s interface=%s cookie_seguro=%s ativacao=%s", base or "/",
                  painel.pasta, estatico or "-", cookie_seguro, "ligada" if codigo_ativacao else "desligada")
    seguro = CabecalhosDeSeguranca(app, base, csp or None, proxies)
    seguro.state = app.state  # o teste chega ao ServidorPainel por app.state
    return seguro


class _AppPreguicoso:
    """`app` para o uvicorn: lê as variáveis e abre o banco só quando o servidor sobe (importar não grava nada)."""

    def __init__(self):
        self._app = None
        self._trava = threading.Lock()

    async def __call__(self, scope, receive, send):
        if self._app is None:
            with self._trava:
                if self._app is None:
                    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
                    self._app = criar_app(**config_do_ambiente())
        await self._app(scope, receive, send)


app = _AppPreguicoso()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("servidor_web:app", host=os.environ.get("PAINEL_HOST", "127.0.0.1"),
                port=int(os.environ.get("PAINEL_PORTA", "8000")), workers=1, proxy_headers=False,
                server_header=False, app_dir=str(AQUI))
