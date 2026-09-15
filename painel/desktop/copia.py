"""Cópia de segurança do painel (spec 016, decisão 5; spec 019, TER-06): um arquivo `.rotaguard-copia` cifrado.

Formato: `RGCOPIA\\x01` + 4 bytes (tamanho do cabeçalho) + cabeçalho JSON + AES-256-GCM(conteúdo). A chave vem de scrypt
sobre a senha escolhida na hora; o cabeçalho (formato, parâmetros, sal e nonce) entra como dado autenticado.
- `rotaguard-copia/2` (atual): o conteúdo é um zip com `painel.db` (banco serializado, com as configurações) e os
  arquivos dos termos importados (`termos/<uid>.<pdf|png|jpg>`).
- `rotaguard-copia/1` (até 15/09/2026): o conteúdo é só o banco serializado. Continua abrindo.
Vídeos ainda não ficam no painel.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import zipfile
from pathlib import Path

from contas import CUSTO_PRODUCAO, MEMORIA_MAXIMA, validar_senha
from dados import Banco, ErroPainel

FORMATO_1 = "rotaguard-copia/1"
FORMATO = "rotaguard-copia/2"
FORMATOS = (FORMATO_1, FORMATO)
MAGICO = b"RGCOPIA\x01"
EXTENSAO = ".rotaguard-copia"
TAMANHO_MAXIMO_CABECALHO = 4096
N_MAXIMO = 2**20
BANCO_NA_COPIA = "painel.db"
ARQUIVO_TERMO = re.compile(r"^termos/[0-9a-f]{32}\.(pdf|png|jpg)$")
MENSAGEM_NAO_E_COPIA = "Este arquivo não é uma cópia de segurança do RotaGuard."


def _aesgcm(chave: bytes):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ErroPainel("Falta o componente de criptografia para fazer a cópia. Reinstale o RotaGuard Painel.") from None
    return AESGCM(chave)


def _chave(senha: str, n: int, r: int, p: int, sal: bytes) -> bytes:
    return hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=n, r=r, p=p, maxmem=MEMORIA_MAXIMA, dklen=32)


def cifrar(dados: bytes, senha: str, custo=CUSTO_PRODUCAO, criado_em: str = "", formato: str = FORMATO) -> bytes:
    n, r, p = custo
    sal, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    cabecalho = json.dumps({"formato": formato, "criado_em": criado_em,
                            "kdf": {"nome": "scrypt", "n": n, "r": r, "p": p, "sal": sal.hex()},
                            "cifra": {"nome": "AES-256-GCM", "nonce": nonce.hex()}},
                           separators=(",", ":")).encode("utf-8")
    cifrado = _aesgcm(_chave(senha, n, r, p, sal)).encrypt(nonce, dados, cabecalho)
    return MAGICO + len(cabecalho).to_bytes(4, "big") + cabecalho + cifrado


def ler_cabecalho(conteudo: bytes) -> tuple[dict, bytes, bytes]:
    nao_e = ErroPainel(MENSAGEM_NAO_E_COPIA, "invalido", "arquivo")
    if not conteudo.startswith(MAGICO) or len(conteudo) < len(MAGICO) + 4:
        raise nao_e
    tamanho = int.from_bytes(conteudo[len(MAGICO):len(MAGICO) + 4], "big")
    if not 0 < tamanho <= TAMANHO_MAXIMO_CABECALHO:
        raise nao_e
    inicio = len(MAGICO) + 4
    bruto = conteudo[inicio:inicio + tamanho]
    try:
        cabecalho = json.loads(bruto)
        kdf, cifra = cabecalho["kdf"], cabecalho["cifra"]
        valido = (cabecalho["formato"] in FORMATOS and kdf["nome"] == "scrypt" and cifra["nome"] == "AES-256-GCM"
                  and 2 <= kdf["n"] <= N_MAXIMO and kdf["n"] & (kdf["n"] - 1) == 0 and 1 <= kdf["r"] <= 32
                  and 1 <= kdf["p"] <= 16 and len(bytes.fromhex(kdf["sal"])) == 16
                  and len(bytes.fromhex(cifra["nonce"])) == 12)
    except (ValueError, KeyError, TypeError):
        raise nao_e from None
    if not valido:
        raise nao_e
    return cabecalho, bruto, conteudo[inicio + tamanho:]


def decifrar(conteudo: bytes, senha: str) -> tuple[dict, bytes]:
    cabecalho, bruto, cifrado = ler_cabecalho(conteudo)
    kdf = cabecalho["kdf"]
    chave = _chave(senha if isinstance(senha, str) else "", kdf["n"], kdf["r"], kdf["p"], bytes.fromhex(kdf["sal"]))
    try:
        from cryptography.exceptions import InvalidTag
    except ImportError:
        raise ErroPainel("Falta o componente de criptografia para abrir a cópia.") from None
    try:
        dados = _aesgcm(chave).decrypt(bytes.fromhex(cabecalho["cifra"]["nonce"]), cifrado, bruto)
    except InvalidTag:
        raise ErroPainel("Senha da cópia errada.", "invalido", "senha") from None
    return cabecalho, dados


def empacotar(banco_serializado: bytes, arquivos: dict[str, bytes]) -> bytes:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr(BANCO_NA_COPIA, banco_serializado)
        for nome in sorted(arquivos):
            pacote.writestr(nome, arquivos[nome])
    return memoria.getvalue()


def conteudo_da_copia(cabecalho: dict, dados: bytes) -> dict:
    """{"banco": bytes, "arquivos": {"termos/<uid>.pdf": bytes}} para os dois formatos. Nome fora do padrão é recusado."""
    if cabecalho.get("formato") == FORMATO_1:
        return {"banco": dados, "arquivos": {}}
    nao_e = ErroPainel(MENSAGEM_NAO_E_COPIA, "invalido", "arquivo")
    try:
        with zipfile.ZipFile(io.BytesIO(dados)) as pacote:
            nomes = pacote.namelist()
            if BANCO_NA_COPIA not in nomes or len(set(nomes)) != len(nomes):
                raise nao_e
            if any(nome != BANCO_NA_COPIA and not ARQUIVO_TERMO.match(nome) for nome in nomes):
                raise nao_e
            return {"banco": pacote.read(BANCO_NA_COPIA),
                    "arquivos": {nome: pacote.read(nome) for nome in nomes if nome != BANCO_NA_COPIA}}
    except (zipfile.BadZipFile, OSError, ValueError, KeyError, EOFError):
        raise nao_e from None


def arquivos_dos_termos(banco: Banco) -> dict[str, bytes]:
    """Arquivos de termo citados no banco, como estão no disco (o SHA-256 do banco confere depois de restaurar)."""
    arquivos = {}
    for linha in banco.todos("SELECT DISTINCT arquivo_caminho FROM termos WHERE arquivo_caminho IS NOT NULL"):
        caminho = linha["arquivo_caminho"]
        if not ARQUIVO_TERMO.match(caminho):
            continue
        try:
            arquivos[caminho] = (banco.pasta / Path(*caminho.split("/"))).read_bytes()
        except FileNotFoundError:
            continue  # sumiu fora do painel: a cópia segue; "Ver termo" avisa
    return arquivos


def nome_sugerido(agora_iso: str) -> str:
    return f"rotaguard-copia-{agora_iso[:10]}{EXTENSAO}"


def fazer_copia(banco: Banco, senha, destino, custo=CUSTO_PRODUCAO) -> dict:
    validar_senha(senha, "senha")
    destino = Path(destino)
    if destino.suffix != EXTENSAO:
        destino = destino.with_name(destino.name + EXTENSAO)
    with banco.trava:  # banco e arquivos do mesmo instante
        pacote = empacotar(banco.serializar(), arquivos_dos_termos(banco))
    conteudo = cifrar(pacote, senha, custo, banco.agora())
    temporario = destino.with_name(destino.name + ".tmp")
    temporario.write_bytes(conteudo)
    os.replace(temporario, destino)
    banco.meta_gravar("ultima_copia_em", banco.agora())
    return {"caminho": str(destino), "bytes": len(conteudo)}


def abrir_copia(caminho, senha) -> tuple[dict, bytes]:
    return decifrar(Path(caminho).read_bytes(), senha)
