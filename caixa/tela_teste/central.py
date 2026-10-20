"""Conectar o app de teste à empresa (spec 026): pareamento por código, opção "Enviar para a empresa" e envio.

- O código de 8 caracteres é gerado no painel da empresa; a central devolve o token do aparelho e o nome da empresa.
- O token fica só em <pasta de dados>/central.json; "Desconectar" apaga. Ele nunca vai para a página.
- O que vai: eventos, sessão com o resumo e trechos de vídeo dos alertas. Nada de cardio (vision/sync.py sem_cardio).
- Tudo passa pela FilaCentral em disco antes de sair: sem internet ou com a central fora, nada trava e nada se perde.
"""
from __future__ import annotations

import json
import logging
import os
import re
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from vision import __version__
from vision.sync import ApiError, EnvioCentral, FilaCentral, ServerClient, trocar_codigo

logger = logging.getLogger("drivesafe.tela.central")

ENDERECO_PADRAO = "https://rotaguard.acexpartners.com.br"
ARQUIVO = "central.json"
CODIGO = re.compile(r"^[A-Za-z0-9]{4}-?[A-Za-z0-9]{4}$")
LOCAIS = ("127.0.0.1", "localhost")
SITUACOES = {
    "aguardando": "Preparando o envio",
    "enviando": "Enviando",
    "em_dia": "Tudo enviado",
    "sem_conexao": "Na fila, sem conexão",
    "recusado": "A empresa recusou este computador: conecte de novo com outro código",
    "limite": "Na fila: a central pediu para esperar um pouco",
    "desligado": "Envio desligado",
}
AVISO_REVOGADO = ("A empresa desconectou este computador. Nada daqui foi apagado; para voltar a enviar, peça um "
                  "código novo no painel dela.")


def validar_endereco(endereco: str) -> str:
    """Só HTTPS; HTTP apenas no próprio computador (central local de teste)."""
    endereco = (endereco or ENDERECO_PADRAO).strip().rstrip("/")
    partes = urlsplit(endereco)
    if partes.scheme == "https" and partes.hostname:
        return endereco
    if partes.scheme == "http" and partes.hostname in LOCAIS:
        return endereco
    raise ValueError("Use o endereço da central com https://.")


class CentralDoTeste:
    """Conexão e envio enquanto o app está aberto."""

    def __init__(self, pasta: Path, status: Callable[[], dict] | None = None, intervalo: float = 5.0):
        self.pasta = Path(pasta)
        self.status = status or (lambda: {})
        self.intervalo = intervalo
        self._trava = threading.RLock()
        self.aviso: str | None = None
        self.config: dict | None = self._carregar()
        self.fila: FilaCentral | None = None
        self.envio: EnvioCentral | None = None
        if self.config is not None:
            self._comecar_envio()

    # ------------------------------------------------------------------ arquivo
    @property
    def _arquivo(self) -> Path:
        return self.pasta / ARQUIVO

    def _carregar(self) -> dict | None:
        try:
            dados = json.loads(self._arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if isinstance(dados, dict) and dados.get("desconectado_pela_empresa"):
            self.aviso = AVISO_REVOGADO
        return dados if isinstance(dados, dict) and dados.get("token") else None

    def _salvar(self) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        temporario = self._arquivo.with_suffix(".tmp")
        temporario.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporario, self._arquivo)

    # ------------------------------------------------------------------ estado
    @property
    def conectado(self) -> bool:
        return self.config is not None

    @property
    def enviando(self) -> bool:
        """Conectado e com "Enviar para a empresa" ligado: só então a sessão grava trechos e vai para a fila."""
        return self.config is not None and bool(self.config.get("enviar", True))

    def estado(self) -> dict:
        with self._trava:
            config = self.config
            envio = self.envio
        if config is None:
            return {"conectado": False, "endereco": ENDERECO_PADRAO, "enviar": False, "situacao": None,
                    "aviso": self.aviso}
        situacao = envio.estado() if envio is not None else {"situacao": "desligado", "pendentes": {}}
        return {
            "conectado": True,
            "endereco": config.get("endereco"),
            "empresa": (config.get("empresa") or {}).get("nome"),
            "conectado_em": config.get("conectado_em"),
            "enviar": bool(config.get("enviar", True)),
            "situacao": situacao["situacao"],
            "situacao_texto": SITUACOES.get(situacao["situacao"], ""),
            "pendentes": situacao.get("pendentes", {}),
            "ultimo_envio": situacao.get("ultimo_envio"),
            "erro": situacao.get("erro"),
        }

    # ------------------------------------------------------------------ ações
    def conectar(self, endereco: str, codigo: str) -> dict:
        endereco = validar_endereco(endereco)
        codigo = (codigo or "").strip()
        if not CODIGO.fullmatch(codigo):
            raise ValueError("O código tem 8 letras e números, como ABCD-2345.")
        try:
            troca = trocar_codigo(endereco, codigo, computador=socket.gethostname()[:100],
                                  programa=f"RotaGuard Script {__version__}")
        except ApiError as exc:
            if exc.status == 429:
                raise ValueError("Muitas tentativas. Espere um minuto e tente de novo.") from exc
            if exc.status in (400, 404, 410, 422):
                raise ValueError("Código inválido ou vencido. Gere outro no painel da empresa.") from exc
            raise ValueError(f"A central respondeu com erro ({exc.status}).") from exc
        except OSError as exc:
            raise ValueError("Sem conexão com a central. Confira a internet e o endereço.") from exc
        with self._trava:
            self._parar_envio()
            self.config = {
                "endereco": endereco,
                "token": troca["token"],
                "aparelho_uid": troca.get("aparelho_uid"),
                "empresa": troca.get("empresa") or {},
                "conectado_em": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "enviar": True,
            }
            self.aviso = None
            self._salvar()
            self._comecar_envio()
        logger.info("Conectado à empresa %s pela central.", (troca.get("empresa") or {}).get("nome", "?"))
        return self.estado()

    def definir_envio(self, ligado: bool) -> dict:
        with self._trava:
            if self.config is None:
                raise ValueError("Conecte à empresa primeiro.")
            self.config["enviar"] = bool(ligado)
            self._salvar()
            if self.envio is not None:
                (self.envio.ligar if ligado else self.envio.desligar)()
        logger.info("Envio para a empresa %s.", "ligado" if ligado else "desligado")
        return self.estado()

    def desconectar(self) -> dict:
        """Apaga o token deste computador. A fila e os arquivos locais ficam (só "Apagar dados" apaga)."""
        with self._trava:
            self._parar_envio()
            self.config = None
            self.aviso = None
            try:
                self._arquivo.unlink()
            except FileNotFoundError:
                pass
        logger.info("Desconectado da empresa: token apagado deste computador.")
        return self.estado()

    def _recusado(self) -> None:
        """A central recusou o token (401/403): a empresa desconectou este computador. Roda na thread do envio:
        para sem esperar a si mesma, apaga só o token e mantém fila, trechos e eventos locais."""
        with self._trava:
            envio, self.envio = self.envio, None
            if envio is not None:
                envio.parar()
            anterior = self.config or {}
            self.config = None
            self.aviso = AVISO_REVOGADO
            registro = {"desconectado_pela_empresa": True, "empresa": anterior.get("empresa") or {},
                        "endereco": anterior.get("endereco"),
                        "desconectado_em": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00",
                                                                                                         "Z")}
            try:
                self.pasta.mkdir(parents=True, exist_ok=True)
                self._arquivo.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                logger.exception("Não foi possível anotar a desconexão.")
        logger.warning("A empresa desconectou este computador: envio parado, token apagado, dados locais mantidos.")

    def avisar(self) -> None:
        """Algo novo na fila (sessão, trecho): tenta enviar já."""
        envio = self.envio
        if envio is not None:
            envio.agora()

    def encerrar(self) -> None:
        with self._trava:
            self._parar_envio()
            if self.fila is not None:
                self.fila.fechar()
                self.fila = None

    # ------------------------------------------------------------------ envio
    def abrir_fila(self) -> FilaCentral:
        with self._trava:
            if self.fila is None:
                self.fila = FilaCentral(self.pasta / "central" / "fila.db")
            return self.fila

    def _comecar_envio(self) -> None:
        cliente = ServerClient(self.config["endereco"], self.config["token"], timeout=20)
        self.envio = EnvioCentral(self.abrir_fila(), cliente, status=self.status, intervalo=self.intervalo,
                                  device_info=lambda: {"hostname": socket.gethostname()[:100],
                                                       "software_version": __version__,
                                                       "platform": "RotaGuard Script"},
                                  ao_recusar=self._recusado)
        self.envio.start()
        if self.config.get("enviar", True):
            self.envio.ligar()

    def _parar_envio(self) -> None:
        envio, self.envio = self.envio, None
        if envio is not None:
            envio.parar()
            envio.join(timeout=10)
