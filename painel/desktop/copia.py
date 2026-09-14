"""Cópia de segurança do painel (spec 016, decisão 5): um arquivo `.rotaguard-copia` cifrado.

Formato: `RGCOPIA\\x01` + 4 bytes (tamanho do cabeçalho) + cabeçalho JSON + AES-256-GCM(banco serializado). A chave
vem de scrypt sobre a senha escolhida na hora; o cabeçalho (parâmetros, sal e nonce) entra como dado autenticado.
Nesta versão a cópia leva o banco (que inclui as configurações); vídeos ainda não ficam no painel.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

from contas import CUSTO_PRODUCAO, MEMORIA_MAXIMA, validar_senha
from dados import Banco, ErroPainel

FORMATO = "rotaguard-copia/1"
MAGICO = b"RGCOPIA\x01"
EXTENSAO = ".rotaguard-copia"
TAMANHO_MAXIMO_CABECALHO = 4096
N_MAXIMO = 2**20


def _aesgcm(chave: bytes):
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise ErroPainel("Falta o componente de criptografia para fazer a cópia. Reinstale o RotaGuard Painel.") from None
    return AESGCM(chave)


def _chave(senha: str, n: int, r: int, p: int, sal: bytes) -> bytes:
    return hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=n, r=r, p=p, maxmem=MEMORIA_MAXIMA, dklen=32)


def cifrar(dados: bytes, senha: str, custo=CUSTO_PRODUCAO, criado_em: str = "") -> bytes:
    n, r, p = custo
    sal, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    cabecalho = json.dumps({"formato": FORMATO, "criado_em": criado_em,
                            "kdf": {"nome": "scrypt", "n": n, "r": r, "p": p, "sal": sal.hex()},
                            "cifra": {"nome": "AES-256-GCM", "nonce": nonce.hex()}},
                           separators=(",", ":")).encode("utf-8")
    cifrado = _aesgcm(_chave(senha, n, r, p, sal)).encrypt(nonce, dados, cabecalho)
    return MAGICO + len(cabecalho).to_bytes(4, "big") + cabecalho + cifrado


def ler_cabecalho(conteudo: bytes) -> tuple[dict, bytes, bytes]:
    nao_e = ErroPainel("Este arquivo não é uma cópia de segurança do RotaGuard.", "invalido", "arquivo")
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
        valido = (cabecalho["formato"] == FORMATO and kdf["nome"] == "scrypt" and cifra["nome"] == "AES-256-GCM"
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


def nome_sugerido(agora_iso: str) -> str:
    return f"rotaguard-copia-{agora_iso[:10]}{EXTENSAO}"


def fazer_copia(banco: Banco, senha, destino, custo=CUSTO_PRODUCAO) -> dict:
    validar_senha(senha, "senha")
    destino = Path(destino)
    if destino.suffix != EXTENSAO:
        destino = destino.with_name(destino.name + EXTENSAO)
    conteudo = cifrar(banco.serializar(), senha, custo, banco.agora())
    temporario = destino.with_name(destino.name + ".tmp")
    temporario.write_bytes(conteudo)
    os.replace(temporario, destino)
    banco.meta_gravar("ultima_copia_em", banco.agora())
    return {"caminho": str(destino), "bytes": len(conteudo)}


def abrir_copia(caminho, senha) -> tuple[dict, bytes]:
    return decifrar(Path(caminho).read_bytes(), senha)
