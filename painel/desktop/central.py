"""Central na VPS, lado do painel executável (spec 026): conectar, buscar novidades, baixar trechos e tocar no painel.

- Cliente HTTP só com a biblioteca padrão (`urllib`), sem redirecionamento (o token nunca segue para outro endereço),
  HTTPS obrigatório (http só para 127.0.0.1/localhost, testes e central local).
- O painel guarda só o token de sessão da central, nunca a senha: no Windows protegido com DPAPI (CryptProtectData, do
  usuário do Windows); fora dele, ou com o DPAPI indisponível, a reserva grava o token só codificado (ver `proteger`).
  O token fica em `central.token`, fora do banco e da cópia de segurança.
- Tudo o que chega fica em `central.db` (mesma pasta de dados, tabelas com `uid`, sem duplicar) e os vídeos em
  `trechos/<uid>.<formato>`, só depois de conferir o SHA-256. Sem internet ou com a central fora, nada quebra: a tela
  mostra o que já foi baixado e "sem conexão".
- A vigia busca a cada 30 s enquanto houver token. Dado de saúde (cardio) que chegue por engano é descartado aqui.

Módulo puro (sem pywebview). A Ponte confere as permissões e registra as atividades.
"""
from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import json
import logging
import math
import os
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dados import Banco, ErroPainel

registro = logging.getLogger("rotaguard.painel.central")

ENDERECO_PADRAO = "https://rotaguard.acexpartners.com.br"
NOME_BANCO = "central.db"
ARQUIVO_TOKEN = "central.token"
PASTA_TRECHOS = "trechos"
INTERVALO_S = 30.0
TEMPO_LIMITE_S = 15.0
TEMPO_LIMITE_DOWNLOAD_S = 120.0
LIMITE_TRECHO = 25 * 1024 * 1024
LIMITE_JSON = 20 * 1024 * 1024
LIMITE_ERRO = 64 * 1024
LIMITE_PAGINAS = 50
LIMITE_POR_PAGINA = 500
TRECHOS_POR_BUSCA = 10
MAX_TENTATIVAS = 5
SINAL_VIVO_S = 90  # "testando agora" some se o último sinal tem mais que isso (folga para relógio fora de hora)
RISCO_DE_ALERTA = 2  # risco médio ou alto: o que a tela chama de alerta (remote-data.ts, textoRisco)
VALIDADE_CODIGO_MIN = 30
FUNCOES_CENTRAL = ("gestor", "admin")
NOME_FUNCAO_CENTRAL = {"gestor": "gestor", "admin": "administrador"}
FORMATOS = {"mp4": "video/mp4", "webm": "video/webm", "rgclip": "application/zip"}
VIDEOS = ("mp4", "webm")
CABECALHO_APP = "X-DriveSafe"  # a central (servidor/backend/auth.py) pede em toda escrita
CABECALHO_CLIENTE = "X-RotaGuard-Cliente"  # "painel": o login devolve o token no corpo, sem cookie
COOKIE_SESSAO = "drivesafe_sessao"
ENTROPIA = b"RotaGuard Painel / central / 1"
CRYPTPROTECT_UI_FORBIDDEN = 0x1
LOCAIS = ("127.0.0.1", "localhost", "::1")

MENSAGEM_SEM_CONEXAO = "Sem conexão com a central em {host}. Confira a internet e o endereço."
MENSAGEM_SESSAO_VENCEU = "A sessão com a central terminou. Conecte de novo em Configurações › Central."
MENSAGEM_NAO_CONECTADO = "O painel não está conectado à central. Conecte em Configurações › Central."

_ID = re.compile(r"^[0-9A-Za-z_-]{8,64}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_CODIGO = re.compile(r"^[A-Z0-9]{8}$")
_CARDIO = re.compile(r"cardio|bpm|frequencia_card|freq_card|heart|rppg|hrv|pulso|^hr$", re.IGNORECASE)
_COMUNS = "uid TEXT NOT NULL UNIQUE, criado_em TEXT NOT NULL, alterado_em TEXT NOT NULL"

MIGRACOES = (
    f"""
    CREATE TABLE meta (chave TEXT PRIMARY KEY, {_COMUNS}, valor TEXT);
    CREATE TABLE central_aparelhos (id INTEGER PRIMARY KEY, {_COMUNS}, empresa TEXT NOT NULL, nome TEXT,
        computador TEXT, programa TEXT, pareado_em TEXT, ultimo_sinal TEXT, testando_agora INTEGER NOT NULL DEFAULT 0,
        risco_atual INTEGER, sessao_atual_uid TEXT, revogado_em TEXT, central_alterado_em TEXT);
    CREATE TABLE central_sessoes (id INTEGER PRIMARY KEY, {_COMUNS}, empresa TEXT NOT NULL, aparelho_uid TEXT,
        iniciada_em TEXT, encerrada_em TEXT, programa TEXT, camera TEXT, resumo TEXT, central_alterado_em TEXT);
    CREATE INDEX central_sessoes_inicio ON central_sessoes (empresa, iniciada_em);
    CREATE TABLE central_eventos (id INTEGER PRIMARY KEY, {_COMUNS}, empresa TEXT NOT NULL, aparelho_uid TEXT,
        sessao_uid TEXT, tipo TEXT, nivel_risco INTEGER, duracao_s REAL, ocorrido_em TEXT, detalhes TEXT,
        trecho_uid TEXT, central_alterado_em TEXT);
    CREATE INDEX central_eventos_sessao ON central_eventos (sessao_uid, ocorrido_em);
    CREATE TABLE central_trechos (id INTEGER PRIMARY KEY, {_COMUNS}, empresa TEXT NOT NULL, aparelho_uid TEXT,
        sessao_uid TEXT, evento_uid TEXT, tipo TEXT, inicio TEXT, fim TEXT, duracao_s REAL, formato TEXT,
        tamanho INTEGER, sha256 TEXT, recebido_em TEXT, central_alterado_em TEXT, arquivo TEXT, sha_local TEXT,
        baixado_em TEXT, tentativas INTEGER NOT NULL DEFAULT 0, erro TEXT);
    CREATE INDEX central_trechos_sessao ON central_trechos (sessao_uid, inicio);
    """,
)


# ---------------------------------------------------------------------------------------------------------------------
# Token: DPAPI no Windows
# ---------------------------------------------------------------------------------------------------------------------
def _dpapi(dados: bytes, cifrar: bool) -> bytes | None:
    """CryptProtectData/CryptUnprotectData do usuário do Windows. None fora do Windows ou se falhar."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        class Blob(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

        crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        bruto = ctypes.create_string_buffer(dados, len(dados))
        sal = ctypes.create_string_buffer(ENTROPIA, len(ENTROPIA))
        entrada = Blob(len(dados), ctypes.cast(bruto, ctypes.POINTER(ctypes.c_char)))
        entropia = Blob(len(ENTROPIA), ctypes.cast(sal, ctypes.POINTER(ctypes.c_char)))
        saida = Blob()
        if cifrar:
            funcao = crypt32.CryptProtectData
            funcao.argtypes = [ctypes.POINTER(Blob), ctypes.c_wchar_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                               ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
            funcao.restype = wintypes.BOOL
            certo = funcao(ctypes.byref(entrada), "RotaGuard Painel", ctypes.byref(entropia), None, None,
                           CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(saida))
        else:
            funcao = crypt32.CryptUnprotectData
            funcao.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob), ctypes.c_void_p,
                               ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
            funcao.restype = wintypes.BOOL
            certo = funcao(ctypes.byref(entrada), None, ctypes.byref(entropia), None, None,
                           CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(saida))
        if not certo:
            return None
        try:
            return ctypes.string_at(saida.pbData, saida.cbData)
        finally:
            kernel32.LocalFree(ctypes.cast(saida.pbData, ctypes.c_void_p))
    except Exception:  # DPAPI indisponível (perfil temporário, serviço): cai na reserva
        return None


def proteger(token: bytes) -> tuple[str, bool]:
    """Texto para o arquivo do token e se ficou protegido.

    RESERVA SEM PROTEÇÃO: fora do Windows, ou se o DPAPI falhar, o token fica só em base64 ("aberto:"), legível por quem
    abrir a pasta de dados deste usuário (o mesmo nível de proteção da pasta). O token só lê a central da empresa e
    deixa de valer ao desconectar ou quando a sessão da central vence (12 h).
    """
    cifrado = _dpapi(token, cifrar=True)
    if cifrado is not None:
        return "dpapi:" + base64.b64encode(cifrado).decode("ascii"), True
    return "aberto:" + base64.b64encode(token).decode("ascii"), False


def desproteger(texto: str) -> bytes | None:
    try:
        tipo, valor = texto.strip().split(":", 1)
        bruto = base64.b64decode(valor, validate=True)
    except (ValueError, TypeError):
        return None
    if tipo == "dpapi":
        return _dpapi(bruto, cifrar=False)
    return bruto if tipo == "aberto" else None


# ---------------------------------------------------------------------------------------------------------------------
# Ajudas puras
# ---------------------------------------------------------------------------------------------------------------------
def normalizar_endereco(texto) -> str:
    """https://host[:porta][/caminho] sem barra no fim; http só para a central local (127.0.0.1/localhost)."""
    invalido = ErroPainel("Use o endereço completo da central, começando com https://.", "invalido", "endereco")
    if not isinstance(texto, str) or not texto.strip() or len(texto) > 300:
        raise invalido
    partes = urllib.parse.urlsplit(texto.strip())
    if partes.scheme not in ("https", "http") or not partes.hostname or partes.username or partes.password:
        raise invalido
    if partes.query or partes.fragment or (partes.scheme == "http" and partes.hostname not in LOCAIS):
        raise invalido
    try:
        partes.port  # noqa: B018 - porta fora do intervalo levanta ValueError
    except ValueError:
        raise invalido from None
    return f"{partes.scheme}://{partes.netloc.lower()}{partes.path.rstrip('/')}"


def host_de(endereco: str) -> str:
    return urllib.parse.urlsplit(endereco).netloc


def _agora_iso(relogio) -> str:
    return datetime.fromtimestamp(relogio(), timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _ler_data(valor) -> datetime | None:
    if not isinstance(valor, str) or not 10 <= len(valor) <= 40:
        return None
    try:
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return instante if instante.tzinfo else instante.replace(tzinfo=timezone.utc)


def _data(valor) -> str | None:
    instante = _ler_data(valor)
    if instante is None:
        return None
    return instante.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _texto(valor, limite: int = 200) -> str | None:
    if not isinstance(valor, str):
        return None
    texto = " ".join(valor.split())[:limite]
    return texto or None


def _inteiro(valor, minimo: int, maximo: int) -> int | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        return None
    numero = int(valor)
    return numero if minimo <= numero <= maximo else None


def _real(valor, minimo: float = 0.0, maximo: float = 7 * 86400.0) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor):
        return None
    return float(valor) if minimo <= valor <= maximo else None


def _sem_saude(valor, profundidade: int = 0):
    """Tira qualquer chave de cardio (dado de saúde fica no computador de quem testou, spec 026 / CEN-10)."""
    if profundidade > 6:
        return None
    if isinstance(valor, dict):
        return {str(chave)[:80]: _sem_saude(item, profundidade + 1) for chave, item in list(valor.items())[:200]
                if not _CARDIO.search(str(chave))}
    if isinstance(valor, list):
        return [_sem_saude(item, profundidade + 1) for item in valor[:200]]
    if isinstance(valor, str):
        return valor[:500]
    if isinstance(valor, (int, float)) and not isinstance(valor, bool) and not math.isfinite(valor):
        return None
    return valor if valor is None or isinstance(valor, (bool, int, float)) else None


def _json_limpo(valor, limite: int = 20_000) -> str | None:
    if not isinstance(valor, dict):
        return None
    texto = json.dumps(_sem_saude(valor), ensure_ascii=False)
    return texto if len(texto) <= limite else None


def _formatar_codigo(codigo) -> str:
    texto = re.sub(r"[^A-Za-z0-9]", "", str(codigo or "")).upper()
    if _CODIGO.match(texto):
        return f"{texto[:4]}-{texto[4:]}"
    raise ErroPainel("A central respondeu um código fora do formato. Tente de novo.", "invalido")


# ---------------------------------------------------------------------------------------------------------------------
# .rgclip: zip com indice.json e quadros JPEG (formato de reserva dos trechos, tocado num canvas)
# ---------------------------------------------------------------------------------------------------------------------
_NOME_QUADRO = re.compile(r"^[\w.-]{1,120}\.jpe?g$", re.IGNORECASE)
LIMITE_QUADRO = 5 * 1024 * 1024
LIMITE_QUADROS = 2400


def ler_rgclip(caminho) -> dict:
    """{"fps", "largura", "altura", "quadros": [{"t", "arquivo"}]} em ordem de tempo.

    Aceita no `indice.json`: `quadros` como lista de objetos (`arquivo`/`nome` e `t`/`t_s`/`t_ms`), como lista de
    nomes (tempo = posição / fps) ou nenhum índice (os JPEGs em ordem de nome). Nome com pasta ou fora do pacote é
    ignorado; nada é extraído para o disco.
    """
    caminho = Path(caminho)
    estado = caminho.stat()
    return _ler_rgclip(str(caminho), estado.st_mtime_ns, estado.st_size)


@functools.lru_cache(maxsize=16)
def _ler_rgclip(caminho: str, _mtime: int, _tamanho: int) -> dict:
    with zipfile.ZipFile(caminho) as pacote:
        tamanhos = {info.filename: info.file_size for info in pacote.infolist()}
        validos = {nome for nome, tamanho in tamanhos.items() if _NOME_QUADRO.match(nome) and tamanho <= LIMITE_QUADRO}
        indice = {}
        if tamanhos.get("indice.json", LIMITE_QUADRO + 1) <= 1024 * 1024:
            try:
                lido = json.loads(pacote.read("indice.json").decode("utf-8"))
                indice = lido if isinstance(lido, dict) else {}
            except (ValueError, UnicodeDecodeError):
                indice = {}
    fps = _real(indice.get("fps"), 1, 120) or 15.0
    fps = int(fps) if float(fps).is_integer() else fps
    quadros = []
    brutos = indice.get("quadros")
    if isinstance(brutos, list) and brutos:
        for posicao, item in enumerate(brutos[:LIMITE_QUADROS]):
            if isinstance(item, str):
                nome, tempo = item, posicao / fps
            elif isinstance(item, dict):
                nome = item.get("arquivo") or item.get("nome") or item.get("imagem")
                if "t_ms" in item and _real(item.get("t_ms"), 0, 86400e3) is not None:
                    tempo = item["t_ms"] / 1000
                else:
                    tempo = next((item[c] for c in ("t", "t_s", "tempo_s") if _real(item.get(c), 0, 86400) is not None),
                                 posicao / fps)
            else:
                continue
            if isinstance(nome, str) and nome in validos:
                quadros.append({"t": tempo, "arquivo": nome})
    else:
        quadros = [{"t": posicao / fps, "arquivo": nome} for posicao, nome in enumerate(sorted(validos)[:LIMITE_QUADROS])]
    quadros.sort(key=lambda quadro: quadro["t"])
    return {"fps": fps, "largura": _inteiro(indice.get("largura"), 1, 8192), "altura": _inteiro(indice.get("altura"), 1, 8192),
            "quadros": quadros}


# ---------------------------------------------------------------------------------------------------------------------
# Servir os trechos para a janela do painel (servidor local de rotaguard_painel.py)
# ---------------------------------------------------------------------------------------------------------------------
_ROTA_VIDEO = re.compile(r"^/__trechos/([A-Za-z0-9_-]{16,64})/([0-9A-Za-z_-]{8,64})\.(mp4|webm)$")
_ROTA_QUADRO = re.compile(r"^/__trechos/([A-Za-z0-9_-]{16,64})/([0-9A-Za-z_-]{8,64})/q/(\d{1,5})\.jpg$")
_FAIXA = re.compile(r"^bytes=(\d*)-(\d*)$")
_NAO_ENCONTRADO = (404, {"Content-Type": "text/plain; charset=utf-8"}, "Não encontrado".encode("utf-8"))


def servir_trecho(rota: dict | None, caminho: str, faixa: str | None = None) -> tuple[int, dict, bytes]:
    """(status, cabeçalhos, corpo) para `/__trechos/<segredo>/<uid>.<mp4|webm>` e `/<segredo>/<uid>/q/<n>.jpg`.

    O segredo é aleatório a cada abertura do painel e só sai pela Ponte para quem tem `ver_video`. Nada de escape
    (%2e...) é decodificado: caminho fora do formato dá 404.
    """
    caminho = caminho.split("?", 1)[0]
    video, quadro = _ROTA_VIDEO.match(caminho), _ROTA_QUADRO.match(caminho)
    achado = video or quadro
    if not rota or not achado or not hmac.compare_digest(achado.group(1).encode(), str(rota["segredo"]).encode()):
        return _NAO_ENCONTRADO
    pasta = Path(rota["pasta"])
    base = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if video:
        arquivo = pasta / f"{video.group(2)}.{video.group(3)}"
        if not arquivo.is_file():
            return _NAO_ENCONTRADO
        tamanho = arquivo.stat().st_size
        inicio, fim, status = 0, tamanho - 1, 200
        pedido = _FAIXA.match((faixa or "").strip())
        if faixa and pedido and (pedido.group(1) or pedido.group(2)):
            if pedido.group(1):
                inicio = int(pedido.group(1))
                fim = min(int(pedido.group(2)), tamanho - 1) if pedido.group(2) else tamanho - 1
            else:
                inicio = max(0, tamanho - int(pedido.group(2)))
            if inicio > fim or inicio >= tamanho:
                return 416, {**base, "Content-Range": f"bytes */{tamanho}"}, b""
            status = 206
        with arquivo.open("rb") as entrada:
            entrada.seek(inicio)
            corpo = entrada.read(fim - inicio + 1)
        cabecalhos = {**base, "Content-Type": FORMATOS[video.group(3)], "Accept-Ranges": "bytes"}
        if status == 206:
            cabecalhos["Content-Range"] = f"bytes {inicio}-{fim}/{tamanho}"
        return status, cabecalhos, corpo
    arquivo = pasta / f"{quadro.group(2)}.rgclip"
    if not arquivo.is_file():
        return _NAO_ENCONTRADO
    try:
        quadros = ler_rgclip(arquivo)["quadros"]
        posicao = int(quadro.group(3))
        if posicao >= len(quadros):
            return _NAO_ENCONTRADO
        with zipfile.ZipFile(arquivo) as pacote:
            corpo = pacote.read(quadros[posicao]["arquivo"])
    except (OSError, zipfile.BadZipFile, KeyError, ValueError):
        return _NAO_ENCONTRADO
    if not corpo.startswith(b"\xff\xd8"):
        return _NAO_ENCONTRADO
    return 200, {**base, "Content-Type": "image/jpeg"}, corpo


# ---------------------------------------------------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------------------------------------------------
class ErroConexao(Exception):
    """Rede fora, central fora do ar, tempo esgotado ou certificado que não confere."""


class _SemRedirecionar(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: ARG002 - 3xx vira erro: o token não segue para outro lugar
        return None


class Cliente:
    def __init__(self, endereco: str, token: str | None = None, tempo_limite: float = TEMPO_LIMITE_S):
        self.endereco, self.token, self.tempo_limite = endereco, token, tempo_limite
        local = urllib.parse.urlsplit(endereco).hostname in LOCAIS
        manipuladores = [_SemRedirecionar(), urllib.request.ProxyHandler({} if local else None)]
        if endereco.startswith("https://"):
            manipuladores.append(urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        self._abrir = urllib.request.build_opener(*manipuladores).open

    def _pedido(self, metodo: str, rota: str, corpo=None, escrita: bool = False,
                extras: dict | None = None) -> urllib.request.Request:
        cabecalhos = {"Accept": "application/json", "User-Agent": "RotaGuardPainel", **(extras or {})}
        if self.token:
            cabecalhos["Authorization"] = f"Bearer {self.token}"
        if escrita:
            cabecalhos[CABECALHO_APP] = "1"
        dados = None
        if corpo is not None:
            dados = json.dumps(corpo).encode("utf-8")
            cabecalhos["Content-Type"] = "application/json"
        return urllib.request.Request(self.endereco + rota, data=dados, headers=cabecalhos, method=metodo)

    def _enviar(self, pedido, tempo_limite=None):
        try:
            return self._abrir(pedido, timeout=tempo_limite or self.tempo_limite)
        except urllib.error.HTTPError as resposta:
            return resposta
        except ssl.SSLError as falha:
            raise ErroConexao("Não deu para confirmar a segurança da conexão com a central (certificado).") from falha
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as falha:
            raise ErroConexao(MENSAGEM_SEM_CONEXAO.format(host=host_de(self.endereco))) from falha

    def json(self, metodo: str, rota: str, corpo=None, escrita: bool = False,
             extras: dict | None = None) -> tuple[int, dict, object]:
        """(status, cabeçalhos, JSON ou None). Erro HTTP volta como status; só falha de rede levanta ErroConexao."""
        resposta = self._enviar(self._pedido(metodo, rota, corpo, escrita, extras))
        with resposta:
            status = resposta.status if hasattr(resposta, "status") else resposta.code
            limite = LIMITE_JSON if 200 <= status < 300 else LIMITE_ERRO
            try:
                bruto = resposta.read(limite + 1)
            except (OSError, socket.timeout) as falha:
                raise ErroConexao(MENSAGEM_SEM_CONEXAO.format(host=host_de(self.endereco))) from falha
            cabecalhos = resposta.headers
        if len(bruto) > limite:
            raise ErroConexao("A central mandou uma resposta grande demais.")
        try:
            dados = json.loads(bruto.decode("utf-8")) if bruto.strip() else None
        except (ValueError, UnicodeDecodeError):
            dados = None
        return status, cabecalhos, dados

    def baixar(self, rota: str, destino: Path, limite: int) -> tuple[int, str, str | None]:
        """Grava em `destino` (em pedaços) e devolve (status, sha256 calculado, sha256 do cabeçalho)."""
        resposta = self._enviar(self._pedido("GET", rota), TEMPO_LIMITE_DOWNLOAD_S)
        with resposta:
            status = resposta.status if hasattr(resposta, "status") else resposta.code
            if status != 200:
                return status, "", None
            resumo, total = hashlib.sha256(), 0
            try:
                with destino.open("wb") as saida:
                    while pedaco := resposta.read(256 * 1024):
                        total += len(pedaco)
                        if total > limite:
                            return 413, "", None
                        resumo.update(pedaco)
                        saida.write(pedaco)
            except (socket.timeout, TimeoutError, ConnectionError) as falha:
                raise ErroConexao(MENSAGEM_SEM_CONEXAO.format(host=host_de(self.endereco))) from falha
            return 200, resumo.hexdigest(), (resposta.headers.get("X-RotaGuard-Sha256") or "").strip().lower() or None


def _detalhe(dados, padrao: str) -> str:
    texto = dados.get("detail") if isinstance(dados, dict) else None
    return texto[:300] if isinstance(texto, str) and texto.strip() else padrao


def _token_do_login(cabecalhos, dados) -> str | None:
    if isinstance(dados, dict):
        for chave in ("token", "access_token"):
            if isinstance(dados.get(chave), str) and 16 <= len(dados[chave]) <= 512:
                return dados[chave]
    from http.cookies import CookieError, SimpleCookie

    for linha in cabecalhos.get_all("Set-Cookie") or []:
        try:
            biscoito = SimpleCookie()
            biscoito.load(linha)
        except CookieError:
            continue
        if COOKIE_SESSAO in biscoito and 16 <= len(biscoito[COOKIE_SESSAO].value) <= 512:
            return biscoito[COOKIE_SESSAO].value
    return None


# ---------------------------------------------------------------------------------------------------------------------
# Central
# ---------------------------------------------------------------------------------------------------------------------
class Central:
    def __init__(self, pasta, relogio=time.time, intervalo_s: float = INTERVALO_S):
        self.pasta = Path(pasta)
        self.pasta_trechos = self.pasta / PASTA_TRECHOS
        self.relogio = relogio
        self.intervalo_s = intervalo_s
        self._banco_obj: Banco | None = None
        self._trava = threading.RLock()
        self._trava_busca = threading.Lock()
        self._geracao = 0
        self._buscando = False
        self._parar = threading.Event()
        self._acordar = threading.Event()
        self._linha: threading.Thread | None = None

    # Banco e meta ----------------------------------------------------------------------------------------------------
    def _banco(self) -> Banco:
        with self._trava:
            if self._banco_obj is None:
                self._banco_obj = Banco(self.pasta, self.relogio, nome=NOME_BANCO, migracoes=MIGRACOES)
            return self._banco_obj

    def _banco_existe(self) -> bool:
        return self._banco_obj is not None or (self.pasta / NOME_BANCO).is_file()

    def _meta(self, chave: str):
        return self._banco().meta_ler(chave) if self._banco_existe() else None

    def _gravar_meta(self, valores: dict) -> None:
        banco = self._banco()
        with banco.transacao():
            for chave, valor in valores.items():
                banco.meta_gravar(chave, None if valor is None else str(valor))

    def _cursor_zerar(self) -> None:
        self._gravar_meta({"cursor": None})

    # Token -----------------------------------------------------------------------------------------------------------
    def _arquivo_token(self) -> Path:
        return self.pasta / ARQUIVO_TOKEN

    def _token(self) -> str | None:
        try:
            texto = self._arquivo_token().read_text(encoding="ascii")
        except (OSError, UnicodeDecodeError):
            return None
        bruto = desproteger(texto)
        return bruto.decode("utf-8", "replace") if bruto else None

    def _token_trocar(self, token: str | None) -> bool:
        """Grava (ou apaga, com None) o token. Devolve se ficou protegido pelo DPAPI."""
        arquivo = self._arquivo_token()
        if token is None:
            try:
                arquivo.unlink()
            except FileNotFoundError:
                pass
            return False
        self.pasta.mkdir(parents=True, exist_ok=True)
        texto, protegido = proteger(token.encode("utf-8"))
        temporario = arquivo.with_name(arquivo.name + ".tmp")
        temporario.write_text(texto, encoding="ascii")
        if os.name == "posix":
            os.chmod(temporario, 0o600)
        os.replace(temporario, arquivo)
        return protegido

    # Estado ----------------------------------------------------------------------------------------------------------
    def estado(self) -> dict:
        token = self._arquivo_token().is_file()
        meta = {chave: self._meta(chave) for chave in ("endereco", "usuario_nome", "usuario_funcao", "empresa_nome",
                                                        "ultima_busca", "ultima_tentativa", "situacao", "ultimo_erro",
                                                        "token_protegido")}
        endereco = meta["endereco"] or ENDERECO_PADRAO
        pendentes = 0
        if token and self._banco_existe():
            pendentes = self._banco().um(
                "SELECT COUNT(*) AS n FROM central_trechos WHERE empresa = ? AND arquivo IS NULL AND tentativas < ?",
                (self._meta("empresa") or "", MAX_TENTATIVAS))["n"]
        return {
            "conectado": token,
            "endereco": endereco,
            "endereco_padrao": ENDERECO_PADRAO,
            "host": host_de(endereco),
            "usuario": {"nome": meta["usuario_nome"], "funcao": meta["usuario_funcao"]} if token and meta["usuario_nome"] else None,
            "empresa": {"nome": meta["empresa_nome"]} if meta["empresa_nome"] else None,
            "ultima_busca": meta["ultima_busca"],
            "ultima_tentativa": meta["ultima_tentativa"],
            "sem_conexao": bool(token and meta["situacao"] == "sem_conexao"),
            "ultimo_erro": meta["ultimo_erro"],
            "buscando": self._buscando,
            "token_protegido": (meta["token_protegido"] == "1") if token else None,
            "intervalo_s": self.intervalo_s,
            "trechos_pendentes": pendentes,
        }

    # Conectar, desconectar, código -----------------------------------------------------------------------------------
    def conectar(self, endereco, usuario, senha) -> dict:
        endereco = normalizar_endereco(endereco)
        if not isinstance(usuario, str) or not 3 <= len(usuario.strip()) <= 254:
            raise ErroPainel("Informe o e-mail ou o telefone do usuário da central.", "invalido", "usuario")
        if not isinstance(senha, str) or not senha or len(senha) > 256:
            raise ErroPainel("Informe a senha do usuário da central.", "invalido", "senha")
        cliente = Cliente(endereco)
        try:
            status, cabecalhos, dados = cliente.json("POST", "/api/auth/login",
                                                      {"login": usuario.strip(), "password": senha, "token": True},
                                                      escrita=True, extras={CABECALHO_CLIENTE: "painel"})
        except ErroConexao as falha:
            raise ErroPainel(str(falha), "invalido", "endereco") from None
        # A senha só passou pela memória até aqui: não vai para o banco, para o arquivo do token nem para o registro.
        if status == 401:
            raise ErroPainel("E-mail, telefone ou senha incorretos na central.", "invalido", "senha")
        if status == 429:
            raise ErroPainel(_detalhe(dados, "Muitas tentativas. Espere alguns minutos."), "espera", "senha")
        if status != 200 or not isinstance(dados, dict):
            raise ErroPainel(_detalhe(dados, f"A central respondeu {status}. Confira o endereço."), "invalido", "endereco")
        token = _token_do_login(cabecalhos, dados)
        if not token:
            raise ErroPainel("A central não devolveu a sessão. Confira o endereço.", "invalido", "endereco")
        funcao = dados.get("role")
        if funcao not in FUNCOES_CENTRAL or dados.get("must_change_password"):
            self._sair_da_central(endereco, token)
            if dados.get("must_change_password"):
                raise ErroPainel("Este usuário ainda tem senha temporária na central. Troque a senha lá antes.",
                                 "sem_permissao", "usuario")
            raise ErroPainel("Use um usuário gestor ou administrador da central.", "sem_permissao", "usuario")
        empresa = dados.get("company") if isinstance(dados.get("company"), dict) else {}
        chave_empresa = f"{endereco}#{empresa.get('id') if empresa.get('id') is not None else 'todas'}"
        with self._trava:
            self._geracao += 1
            protegido = self._token_trocar(token)
            mudou = self._meta("empresa") != chave_empresa
            self._gravar_meta({
                "endereco": endereco, "usuario_nome": _texto(dados.get("name"), 120) or usuario.strip()[:120],
                "usuario_funcao": NOME_FUNCAO_CENTRAL[funcao],
                "empresa_nome": _texto(empresa.get("name"), 120) or "Todas as empresas", "empresa": chave_empresa,
                "token_protegido": "1" if protegido else "0", "situacao": "ok", "ultimo_erro": None,
                **({"cursor": None, "ultima_busca": None} if mudou else {}),
            })
        self._acordar.set()
        return self.estado()

    def _sair_da_central(self, endereco: str, token: str) -> None:
        try:
            Cliente(endereco, token, 5).json("POST", "/api/auth/logout", escrita=True)
        except ErroConexao:
            pass

    def desconectar(self) -> dict:
        with self._trava:
            token, endereco = self._token(), self._meta("endereco")
            self._geracao += 1
            self._token_trocar(None)
            if self._banco_existe():
                self._gravar_meta({"usuario_nome": None, "usuario_funcao": None, "situacao": None,
                                   "ultimo_erro": None, "token_protegido": None})
        if token and endereco:
            self._sair_da_central(endereco, token)
        return self.estado()

    def _cliente(self) -> Cliente:
        token, endereco = self._token(), self._meta("endereco")
        if not token or not endereco:
            raise ErroPainel(MENSAGEM_NAO_CONECTADO, "conflito")  # estado, não permissão
        return Cliente(endereco, token)

    def gerar_codigo(self, nome) -> dict:
        if nome is not None and (not isinstance(nome, str) or len(nome.strip()) > 80):
            raise ErroPainel("O nome do computador pode ter até 80 letras.", "invalido", "nome")
        nome = _texto(nome, 80)
        cliente = self._cliente()
        try:
            status, _, dados = cliente.json("POST", "/api/pareamento/codigos", {"nome": nome} if nome else {},
                                            escrita=True)
        except ErroConexao as falha:
            raise ErroPainel(str(falha), "invalido") from None
        if status == 401:
            self._sessao_venceu()
            raise ErroPainel(MENSAGEM_SESSAO_VENCEU, "sem_sessao")
        if status not in (200, 201) or not isinstance(dados, dict):
            raise ErroPainel(_detalhe(dados, f"A central não gerou o código ({status})."), "invalido")
        expira = _data(dados.get("expira_em"))
        if expira is None:
            raise ErroPainel("A central respondeu sem a validade do código. Tente de novo.", "invalido")
        return {"codigo": _formatar_codigo(dados.get("codigo")), "expira_em": expira,
                "validade_min": VALIDADE_CODIGO_MIN, "nome": nome,
                "aparelho_uid": dados.get("aparelho_uid") if _ID.match(str(dados.get("aparelho_uid") or "")) else None}

    def _sessao_venceu(self) -> None:
        with self._trava:
            self._geracao += 1
            self._token_trocar(None)
            self._gravar_meta({"situacao": "erro", "ultimo_erro": MENSAGEM_SESSAO_VENCEU, "usuario_nome": None,
                               "token_protegido": None})

    # Busca -----------------------------------------------------------------------------------------------------------
    def buscar(self) -> dict:
        """Uma volta: novidades (todas as páginas) e até 10 trechos pendentes. Nunca levanta exceção."""
        with self._trava_busca:
            self._buscando = True
            try:
                return self._buscar()
            except ErroPainel as falha:
                return {"ok": False, "erro": falha.erro}
            except Exception as falha:  # nunca derruba a vigia
                registro.error("busca na central falhou: %s", type(falha).__name__)
                self._gravar_meta({"situacao": "erro", "ultimo_erro": "A busca na central falhou. Tentando de novo.",
                                   "ultima_tentativa": _agora_iso(self.relogio)})
                return {"ok": False, "erro": type(falha).__name__}
            finally:
                self._buscando = False

    def _buscar(self) -> dict:
        with self._trava:
            geracao, cliente = self._geracao, self._cliente()
            empresa = self._meta("empresa") or ""
        vale = lambda: self._geracao == geracao  # noqa: E731
        novos = {"aparelhos": 0, "sessoes": 0, "eventos": 0, "trechos": 0}
        try:
            for _ in range(LIMITE_PAGINAS):
                cursor = self._meta("cursor") or ""
                rota = f"/api/sync/novidades?desde={urllib.parse.quote(cursor, safe='')}&limite={LIMITE_POR_PAGINA}"
                status, _, pagina = cliente.json("GET", rota)
                if status == 401:
                    if vale():
                        self._sessao_venceu()
                    return {"ok": False, "erro": MENSAGEM_SESSAO_VENCEU}
                if status != 200 or not isinstance(pagina, dict):
                    raise ErroPainel(_detalhe(pagina, f"A central respondeu {status} na busca."))
                if not vale():
                    return {"ok": False, "erro": "desconectado"}
                for tipo, total in self._gravar_pagina(empresa, pagina).items():
                    novos[tipo] += total
                if not pagina.get("mais"):
                    break
            baixados = self._baixar_pendentes(cliente, empresa, vale)
        except ErroConexao as falha:
            if vale():
                self._gravar_meta({"situacao": "sem_conexao", "ultimo_erro": str(falha),
                                   "ultima_tentativa": _agora_iso(self.relogio)})
            return {"ok": False, "erro": str(falha)}
        except ErroPainel as falha:
            if vale():
                self._gravar_meta({"situacao": "erro", "ultimo_erro": falha.erro,
                                   "ultima_tentativa": _agora_iso(self.relogio)})
            return {"ok": False, "erro": falha.erro}
        if vale():
            agora = _agora_iso(self.relogio)
            self._gravar_meta({"situacao": "ok", "ultimo_erro": None, "ultima_busca": agora, "ultima_tentativa": agora})
        return {"ok": True, "novos": novos, "baixados": baixados}

    def _gravar_pagina(self, empresa: str, pagina: dict) -> dict:
        banco = self._banco()
        contagem = {}
        with banco.transacao():
            for tipo, limpar in (("aparelhos", self._aparelho), ("sessoes", self._sessao_item),
                                 ("eventos", self._evento), ("trechos", self._trecho_item)):
                itens = pagina.get(tipo)
                contagem[tipo] = 0
                for item in itens[:LIMITE_POR_PAGINA * 4] if isinstance(itens, list) else []:
                    valores = limpar(item) if isinstance(item, dict) else None
                    if valores is not None and self._guardar(banco, f"central_{tipo}", empresa, valores):
                        contagem[tipo] += 1
            cursor = pagina.get("cursor")
            if isinstance(cursor, str) and len(cursor) <= 500:
                banco.meta_gravar("cursor", cursor)
        return contagem

    @staticmethod
    def _base(item: dict) -> dict | None:
        uid = item.get("uid")
        if not isinstance(uid, str) or not _ID.match(uid):
            return None
        return {"uid": uid, "central_alterado_em": _data(item.get("alterado_em"))}

    @staticmethod
    def _id_ou_none(valor) -> str | None:
        return valor if isinstance(valor, str) and _ID.match(valor) else None

    def _aparelho(self, item: dict) -> dict | None:
        base = self._base(item)
        return base and {**base, "nome": _texto(item.get("nome"), 120), "computador": _texto(item.get("computador"), 120),
                         "programa": _texto(item.get("programa"), 80), "pareado_em": _data(item.get("pareado_em")),
                         "ultimo_sinal": _data(item.get("ultimo_sinal")),
                         "testando_agora": 1 if item.get("testando_agora") is True else 0,
                         "risco_atual": _inteiro(item.get("risco_atual"), 0, 3),
                         "sessao_atual_uid": self._id_ou_none(item.get("sessao_atual_uid")),
                         "revogado_em": _data(item.get("revogado_em"))}

    def _sessao_item(self, item: dict) -> dict | None:
        base = self._base(item)
        return base and {**base, "aparelho_uid": self._id_ou_none(item.get("aparelho_uid")),
                         "iniciada_em": _data(item.get("iniciada_em")), "encerrada_em": _data(item.get("encerrada_em")),
                         "programa": _texto(item.get("programa"), 80), "camera": _texto(item.get("camera"), 120),
                         "resumo": _json_limpo(item.get("resumo"))}

    def _evento(self, item: dict) -> dict | None:
        base = self._base(item)
        return base and {**base, "aparelho_uid": self._id_ou_none(item.get("aparelho_uid")),
                         "sessao_uid": self._id_ou_none(item.get("sessao_uid")), "tipo": _texto(item.get("tipo"), 60),
                         "nivel_risco": _inteiro(item.get("nivel_risco"), 0, 5), "duracao_s": _real(item.get("duracao_s")),
                         "ocorrido_em": _data(item.get("ocorrido_em")), "detalhes": _json_limpo(item.get("detalhes"), 5000),
                         "trecho_uid": self._id_ou_none(item.get("trecho_uid"))}

    def _trecho_item(self, item: dict) -> dict | None:
        base = self._base(item)
        sha = item.get("sha256").lower() if isinstance(item.get("sha256"), str) else None
        return base and {**base, "aparelho_uid": self._id_ou_none(item.get("aparelho_uid")),
                         "sessao_uid": self._id_ou_none(item.get("sessao_uid")),
                         "evento_uid": self._id_ou_none(item.get("evento_uid")), "tipo": _texto(item.get("tipo"), 60),
                         "inicio": _data(item.get("inicio")), "fim": _data(item.get("fim")),
                         "duracao_s": _real(item.get("duracao_s")), "formato": _texto(item.get("formato"), 12),
                         "tamanho": _inteiro(item.get("tamanho"), 0, 2**40),
                         "sha256": sha if sha and _SHA.match(sha) else None,
                         "recebido_em": _data(item.get("recebido_em"))}

    def _guardar(self, banco: Banco, tabela: str, empresa: str, valores: dict) -> bool:
        """Insere pelo uid ou atualiza se a central mudou depois. Devolve se mudou algo."""
        atual = banco.um(f"SELECT * FROM {tabela} WHERE uid = ?", (valores["uid"],))
        if atual is None:
            banco.inserir(tabela, {**valores, "empresa": empresa})
            return True
        novo, velho = _ler_data(valores["central_alterado_em"]), _ler_data(atual["central_alterado_em"])
        if novo is not None and velho is not None and novo <= velho:
            return False
        mudancas = {chave: valor for chave, valor in valores.items() if chave != "uid" and atual[chave] != valor}
        if not mudancas:
            return False
        if tabela == "central_trechos" and "sha256" in mudancas:  # o vídeo mudou na central: baixa de novo
            self._apagar_arquivo(atual["arquivo"])
            mudancas.update(arquivo=None, sha_local=None, baixado_em=None, tentativas=0, erro=None)
        banco.atualizar(tabela, "uid", valores["uid"], {**mudancas, "empresa": empresa})
        return True

    def _apagar_arquivo(self, relativo) -> None:
        if isinstance(relativo, str) and relativo.startswith(f"{PASTA_TRECHOS}/"):
            try:
                (self.pasta / relativo).unlink()
            except FileNotFoundError:
                pass

    def _baixar_pendentes(self, cliente: Cliente, empresa: str, vale) -> int:
        banco = self._banco()
        pendentes = banco.todos(
            "SELECT * FROM central_trechos WHERE empresa = ? AND arquivo IS NULL AND tentativas < ? "
            "ORDER BY recebido_em DESC LIMIT ?", (empresa, MAX_TENTATIVAS, TRECHOS_POR_BUSCA))
        baixados = 0
        for linha in pendentes:
            if not vale():
                break
            if linha["formato"] not in FORMATOS or not linha["sha256"]:
                banco.atualizar("central_trechos", "uid", linha["uid"],
                                {"tentativas": MAX_TENTATIVAS, "erro": "Formato ou conferência do trecho desconhecidos."})
                continue
            if (linha["tamanho"] or 0) > LIMITE_TRECHO:
                banco.atualizar("central_trechos", "uid", linha["uid"],
                                {"tentativas": MAX_TENTATIVAS, "erro": "Trecho acima de 25 MB."})
                continue
            if self._baixar(cliente, banco, linha, vale):
                baixados += 1
        return baixados

    def _baixar(self, cliente: Cliente, banco: Banco, linha, vale) -> bool:
        self.pasta_trechos.mkdir(parents=True, exist_ok=True)
        final = self.pasta_trechos / f"{linha['uid']}.{linha['formato']}"
        parte = final.with_name(final.name + ".parte")
        try:
            status, calculado, informado = cliente.baixar(f"/api/trechos/{urllib.parse.quote(linha['uid'])}/arquivo",
                                                          parte, LIMITE_TRECHO)
            certo = (status == 200 and hmac.compare_digest(calculado, linha["sha256"])
                     and (informado is None or hmac.compare_digest(informado, linha["sha256"])))
            if certo and vale():
                os.replace(parte, final)
                banco.atualizar("central_trechos", "uid", linha["uid"], {
                    "arquivo": f"{PASTA_TRECHOS}/{final.name}", "sha_local": calculado,
                    "baixado_em": _agora_iso(self.relogio), "erro": None})
                return True
        finally:
            try:
                parte.unlink()
            except FileNotFoundError:
                pass
        if not vale():
            return False
        if status == 200:
            erro = "O vídeo chegou diferente do que a central registrou (SHA-256). Tentando de novo."
        elif status == 404:
            erro = "A central não tem mais este trecho."
        elif status == 413:
            erro = "Trecho acima de 25 MB."
        else:
            erro = f"A central respondeu {status} ao baixar o trecho."
        banco.atualizar("central_trechos", "uid", linha["uid"],
                        {"tentativas": (linha["tentativas"] or 0) + (MAX_TENTATIVAS if status == 413 else 1),
                         "erro": erro})
        return False

    # Vigia -----------------------------------------------------------------------------------------------------------
    def iniciar(self) -> None:
        with self._trava:
            if self._linha is not None and self._linha.is_alive():
                return
            self._parar.clear()
            self._linha = threading.Thread(target=self._vigiar, name="rotaguard-central", daemon=True)
            self._linha.start()

    def _vigiar(self) -> None:
        while not self._parar.is_set():
            if self._arquivo_token().is_file():
                self.buscar()
            self._acordar.wait(self.intervalo_s)
            self._acordar.clear()

    def parar(self) -> None:
        self._parar.set()
        self._acordar.set()
        linha = self._linha
        if linha is not None:
            linha.join(timeout=5)

    def _linha_viva(self) -> bool:
        return self._linha is not None and self._linha.is_alive()

    # Consultas para as telas -----------------------------------------------------------------------------------------
    def _testando(self, linha) -> bool:
        sinal = _ler_data(linha["ultimo_sinal"])
        return (bool(linha["testando_agora"]) and not linha["revogado_em"] and sinal is not None
                and self.relogio() - sinal.timestamp() < SINAL_VIVO_S)

    @staticmethod
    def _nome_aparelho(linha) -> str:
        return (linha["nome"] or linha["computador"] or "Computador sem nome") if linha is not None else "Computador"

    def _aparelho_publico(self, linha, sessoes: int = 0) -> dict:
        testando = self._testando(linha)
        return {"uid": linha["uid"], "nome": self._nome_aparelho(linha), "computador": linha["computador"],
                "programa": linha["programa"], "pareado_em": linha["pareado_em"], "ultimo_sinal": linha["ultimo_sinal"],
                "testando_agora": testando, "risco_atual": linha["risco_atual"] if testando else None,
                "sessao_atual_uid": linha["sessao_atual_uid"] if testando else None,
                "revogado_em": linha["revogado_em"], "sessoes": sessoes}

    def _sessao_publica(self, linha, aparelhos: dict) -> dict:
        aparelho = aparelhos.get(linha["aparelho_uid"])
        try:
            resumo = json.loads(linha["resumo"]) if linha["resumo"] else {}
        except ValueError:
            resumo = {}
        andamento = (linha["encerrada_em"] is None and aparelho is not None and self._testando(aparelho)
                     and aparelho["sessao_atual_uid"] == linha["uid"])
        resultado = {"uid": linha["uid"], "aparelho_uid": linha["aparelho_uid"],
                     "aparelho_nome": self._nome_aparelho(aparelho), "iniciada_em": linha["iniciada_em"],
                     "encerrada_em": linha["encerrada_em"], "em_andamento": andamento,
                     "sem_fim": linha["encerrada_em"] is None and not andamento, "programa": linha["programa"],
                     "camera": linha["camera"], "resumo": resumo}
        for chave in ("eventos", "trechos", "trechos_baixados"):
            if chave in linha.keys():
                resultado[chave] = linha[chave]
        return resultado

    def listar(self) -> dict:
        estado = self.estado()
        if not self._banco_existe():
            return {"central": estado, "aparelhos": [], "sessoes": []}
        banco, empresa = self._banco(), self._meta("empresa") or ""
        linhas = banco.todos("SELECT a.*, (SELECT COUNT(*) FROM central_sessoes s WHERE s.aparelho_uid = a.uid) AS n "
                             "FROM central_aparelhos a WHERE a.empresa = ?", (empresa,))
        aparelhos = {linha["uid"]: linha for linha in linhas}
        publicos = sorted((self._aparelho_publico(linha, linha["n"]) for linha in linhas),
                          key=lambda a: (not a["testando_agora"], -(_ler_data(a["ultimo_sinal"]) or datetime.min.replace(
                              tzinfo=timezone.utc)).timestamp(), a["nome"].casefold()))
        sessoes = banco.todos(
            "SELECT s.*, (SELECT COUNT(*) FROM central_eventos e WHERE e.sessao_uid = s.uid) AS eventos, "
            "(SELECT COUNT(*) FROM central_trechos t WHERE t.sessao_uid = s.uid) AS trechos, "
            "(SELECT COUNT(*) FROM central_trechos t WHERE t.sessao_uid = s.uid AND t.arquivo IS NOT NULL) "
            "AS trechos_baixados FROM central_sessoes s WHERE s.empresa = ? ORDER BY s.iniciada_em DESC LIMIT 500",
            (empresa,))
        return {"central": estado, "aparelhos": publicos,
                "sessoes": [self._sessao_publica(linha, aparelhos) for linha in sessoes]}

    def resumo_do_dia(self, inicio: datetime, fim: datetime) -> dict:
        """Números do Início (spec 030, SDF-05): sessões começadas e eventos ocorridos entre `inicio` e `fim` (o dia
        local), alertas (risco 2 ou mais) por tipo, computadores testando agora e conectados. Só lê; sem o banco da
        central, tudo zero e nada é criado."""
        resumo = {"sessoes": 0, "eventos": 0, "alertas": 0, "alertas_por_tipo": {}, "testando_agora": 0,
                  "computadores": 0}
        if not self._banco_existe():
            return resumo
        banco, empresa = self._banco(), self._meta("empresa") or ""
        # Filtro grosso pelo texto (todas as datas da central são ISO em UTC), conferido depois pela data de verdade.
        corte = (inicio.astimezone(timezone.utc) - timedelta(days=1)).date().isoformat()

        def dentro(texto) -> bool:
            quando = _ler_data(texto)
            return quando is not None and inicio <= quando < fim

        resumo["sessoes"] = sum(dentro(l["iniciada_em"]) for l in banco.todos(
            "SELECT iniciada_em FROM central_sessoes WHERE empresa = ? AND iniciada_em >= ?", (empresa, corte)))
        for linha in banco.todos("SELECT tipo, nivel_risco, ocorrido_em FROM central_eventos WHERE empresa = ? "
                                 "AND ocorrido_em >= ?", (empresa, corte)):
            if not dentro(linha["ocorrido_em"]):
                continue
            resumo["eventos"] += 1
            if isinstance(linha["nivel_risco"], int) and linha["nivel_risco"] >= RISCO_DE_ALERTA:
                resumo["alertas"] += 1
                tipo = linha["tipo"] or "desconhecido"
                resumo["alertas_por_tipo"][tipo] = resumo["alertas_por_tipo"].get(tipo, 0) + 1
        for linha in banco.todos("SELECT * FROM central_aparelhos WHERE empresa = ?", (empresa,)):
            if linha["revogado_em"]:
                continue
            resumo["computadores"] += 1
            resumo["testando_agora"] += int(self._testando(linha))
        return resumo

    def _linha_por_uid(self, tabela: str, uid) -> object:
        if not isinstance(uid, str) or not _ID.match(uid) or not self._banco_existe():
            raise ErroPainel("Não encontrado.", "nao_encontrado")
        linha = self._banco().um(f"SELECT * FROM {tabela} WHERE uid = ? AND empresa = ?", (uid, self._meta("empresa") or ""))
        if linha is None:
            raise ErroPainel("Não encontrado.", "nao_encontrado")
        return linha

    def sessao(self, uid, pode_ver_trechos: bool) -> dict:
        linha = self._linha_por_uid("central_sessoes", uid)
        banco = self._banco()
        aparelho = banco.um("SELECT * FROM central_aparelhos WHERE uid = ?", (linha["aparelho_uid"],)) \
            if linha["aparelho_uid"] else None
        eventos = []
        for evento in banco.todos("SELECT * FROM central_eventos WHERE sessao_uid = ? ORDER BY ocorrido_em, id",
                                  (linha["uid"],)):
            try:
                detalhes = json.loads(evento["detalhes"]) if evento["detalhes"] else {}
            except ValueError:
                detalhes = {}
            eventos.append({"uid": evento["uid"], "tipo": evento["tipo"], "nivel_risco": evento["nivel_risco"],
                            "duracao_s": evento["duracao_s"], "ocorrido_em": evento["ocorrido_em"], "detalhes": detalhes,
                            "trecho_uid": evento["trecho_uid"] if pode_ver_trechos else None})
        trechos = [self._trecho_publico(t) for t in banco.todos(
            "SELECT * FROM central_trechos WHERE sessao_uid = ? ORDER BY inicio, id", (linha["uid"],))] \
            if pode_ver_trechos else []
        return {"sessao": self._sessao_publica(linha, {aparelho["uid"]: aparelho} if aparelho is not None else {}),
                "aparelho": self._aparelho_publico(aparelho) if aparelho is not None else None,
                "eventos": eventos, "trechos": trechos, "pode_ver_trechos": pode_ver_trechos}

    @staticmethod
    def _trecho_publico(linha) -> dict:
        return {"uid": linha["uid"], "sessao_uid": linha["sessao_uid"], "evento_uid": linha["evento_uid"],
                "tipo": linha["tipo"], "inicio": linha["inicio"], "fim": linha["fim"], "duracao_s": linha["duracao_s"],
                "formato": linha["formato"], "tamanho": linha["tamanho"], "baixado": linha["arquivo"] is not None,
                "erro": linha["erro"]}

    def trecho(self, uid, segredo: str) -> dict:
        """Como tocar o trecho: endereço do vídeo, ou quadros do .rgclip, ou por que ainda não dá."""
        linha = self._linha_por_uid("central_trechos", uid)
        banco = self._banco()
        aparelho = banco.um("SELECT * FROM central_aparelhos WHERE uid = ?", (linha["aparelho_uid"],)) \
            if linha["aparelho_uid"] else None
        resultado = {**self._trecho_publico(linha), "aparelho_nome": self._nome_aparelho(aparelho), "disponivel": False}
        if linha["arquivo"] is None:
            resultado["motivo"] = linha["erro"] if (linha["tentativas"] or 0) >= MAX_TENTATIVAS and linha["erro"] else \
                "Ainda baixando da central." if not linha["erro"] else linha["erro"]
            return resultado
        arquivo = self.pasta / linha["arquivo"]
        try:
            conteudo = arquivo.read_bytes()
        except FileNotFoundError:
            conteudo = None
        if conteudo is None or not hmac.compare_digest(hashlib.sha256(conteudo).hexdigest(), linha["sha256"] or ""):
            self._apagar_arquivo(linha["arquivo"])
            banco.atualizar("central_trechos", "uid", linha["uid"],
                            {"arquivo": None, "sha_local": None, "tentativas": 0, "erro": None})
            resultado["motivo"] = "O arquivo do trecho mudou ou sumiu da pasta. Ele vai ser baixado de novo."
            return resultado
        base = f"/__trechos/{segredo}/{linha['uid']}"
        if linha["formato"] in VIDEOS:
            return {**resultado, "disponivel": True, "url": f"{base}.{linha['formato']}", "mime": FORMATOS[linha["formato"]]}
        try:
            clip = ler_rgclip(arquivo)
        except (OSError, zipfile.BadZipFile):
            clip = {"quadros": []}
        if not clip["quadros"]:
            resultado["motivo"] = "O trecho não tem quadros que dê para mostrar."
            return resultado
        return {**resultado, "disponivel": True, "fps": clip["fps"], "largura": clip["largura"], "altura": clip["altura"],
                "quadros": [{"t": quadro["t"], "url": f"{base}/q/{posicao}.jpg"}
                            for posicao, quadro in enumerate(clip["quadros"])]}
