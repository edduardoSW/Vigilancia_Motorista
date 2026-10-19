"""Envio da fila local para o servidor central, com reenvio automático quando a conexão volta.

SyncWorker: a caixa (eventos e sinal de vida). Central da spec 026, usada pelo app de teste: trocar_codigo (pareamento
por código), FilaCentral (sessões, eventos e trechos guardados em disco antes de enviar; sobrevive a fechar o app) e
EnvioCentral (envia em segundo plano; sem internet nada trava e tudo fica na fila). Nenhum dado de cardio sai do
computador: sem_cardio() limpa eventos e resumos antes de qualquer envio (dado de saúde, LGPD art. 11).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import platform
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from vision import __version__
from vision.event_queue import EventStore

logger = logging.getLogger("drivesafe.sync")


# Chaves de cardio (spec 022): nunca saem do computador, nem dentro de detalhes aninhados.
CARDIO_PARTES = ("cardio", "bpm", "frequencia_cardiaca", "pulso", "respiracao", "rmssd", "snr_db", "historico_bpm")
CARDIO_EXATAS = frozenset({"onda", "rois"})


def _e_cardio(chave) -> bool:
    nome = str(chave).lower()
    return nome in CARDIO_EXATAS or any(parte in nome for parte in CARDIO_PARTES)


def sem_cardio(valor):
    """Cópia sem nenhuma chave de cardio, em qualquer nível de dicionários e listas."""
    if isinstance(valor, dict):
        return {chave: sem_cardio(item) for chave, item in valor.items() if not _e_cardio(chave)}
    if isinstance(valor, list):
        return [sem_cardio(item) for item in valor]
    return valor


def _detalhe(corpo: bytes) -> str:
    """Mensagem de erro da central ({"detail": "..."}) ou o começo do corpo."""
    texto = corpo.decode("utf-8", "replace")
    try:
        dados = json.loads(texto)
    except ValueError:
        return texto[:300]
    if isinstance(dados, dict) and isinstance(dados.get("detail"), str):
        return dados["detail"][:300]
    return texto[:300]


class ApiError(Exception):
    def __init__(self, status: int, message: str, retry_after: float | None = None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message
        # Segundos pedidos pela central no Retry-After (429: limite de envios); None se não veio.
        self.retry_after = retry_after


def _segundos(valor) -> float | None:
    try:
        return max(0.0, float(valor))
    except (TypeError, ValueError):
        return None


class ServerClient:
    def __init__(self, base_url: str, token: str | None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def _pedir(self, metodo: str, path: str, data: bytes | None, headers: dict) -> dict:
        cabecalhos = {"User-Agent": f"drivesafe-device/{__version__}", **headers}
        if self.token:
            cabecalhos["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(self.base_url + path, data=data, method=metodo, headers=cabecalhos)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, _detalhe(exc.read()), _segundos(exc.headers.get("Retry-After"))) from exc
        return json.loads(body) if body else {}

    def post(self, path: str, payload: dict) -> dict:
        return self._pedir("POST", path, json.dumps(payload).encode("utf-8"), {"Content-Type": "application/json"})

    def put_json(self, path: str, payload: dict) -> dict:
        return self._pedir("PUT", path, json.dumps(payload).encode("utf-8"), {"Content-Type": "application/json"})

    def put_bytes(self, path: str, data: bytes, headers: dict) -> dict:
        return self._pedir("PUT", path, data, {"Content-Type": "application/octet-stream", **headers})


class SyncWorker(threading.Thread):
    def __init__(
        self,
        store: EventStore,
        client: ServerClient,
        status_provider: Callable[[], dict] | None = None,
        interval: float = 5.0,
        heartbeat_interval: float = 15.0,
        batch_size: int = 100,
        policy_handler: Callable[[dict], None] | None = None,
    ):
        super().__init__(name="drivesafe-sync", daemon=True)
        self.store = store
        self.client = client
        self.status_provider = status_provider or (lambda: {})
        # Recebe a política do servidor (motorista vinculado, consentimento, modo dos sinais de ativação).
        self.policy_handler = policy_handler
        self.interval = interval
        self.heartbeat_interval = heartbeat_interval
        self.batch_size = batch_size
        self._stop_event = threading.Event()
        self._failures = 0
        self._next_heartbeat = 0.0

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        while not self._stop_event.is_set():
            ok = self.sync_once()
            delay = self.interval if ok else min(300.0, self.interval * 2 ** min(self._failures, 6))
            self._stop_event.wait(delay)
        # Última tentativa ao encerrar, para não deixar evento recente parado na fila.
        self.sync_once()

    def device_info(self) -> dict:
        return {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "software_version": __version__,
            "pending_events": self.store.count_pending(),
        }

    def sync_once(self) -> bool:
        try:
            if time.monotonic() >= self._next_heartbeat:
                self._send_heartbeat()
            self._flush_events()
        except ApiError as exc:
            self._register_failure()
            if exc.status in (401, 403):
                logger.error("O servidor recusou o token deste dispositivo (HTTP %s). Os eventos continuam na fila local.", exc.status)
            else:
                logger.warning("Servidor respondeu %s. Nova tentativa em breve.", exc)
            return False
        except OSError as exc:  # sem rede, servidor desligado, timeout, DNS
            self._register_failure()
            if self._failures == 1:
                logger.warning("Servidor inacessível (%s). Os eventos ficam na fila local até a conexão voltar.", exc)
            return False
        except Exception:
            self._register_failure()
            logger.exception("Erro inesperado ao sincronizar com o servidor.")
            return False

        if self._failures:
            logger.info("Conexão com o servidor restabelecida.")
        self._failures = 0
        return True

    def _register_failure(self) -> None:
        self._failures += 1

    def _send_heartbeat(self) -> None:
        payload = {"device": self.device_info()}
        payload.update(self.status_provider())
        response = self.client.post("/api/devices/heartbeat", payload)
        self._next_heartbeat = time.monotonic() + self.heartbeat_interval
        if self.policy_handler is not None and isinstance(response.get("policy"), dict):
            try:
                self.policy_handler(response["policy"])
            except Exception:
                logger.exception("Falha ao aplicar a política recebida do servidor.")
        removed = self.store.purge_sent()
        if removed:
            logger.info("%d evento(s) antigo(s) já enviados foram apagados da fila local.", removed)

    def _flush_events(self) -> None:
        while True:
            events = self.store.pending(self.batch_size)
            if not events:
                return
            uids = [event["event_uid"] for event in events]
            events = [sem_cardio(event) for event in events]
            try:
                info = self.device_info()
                # Informa a fila já sem este lote; se o envio falhar, o próximo contato corrige o número.
                info["pending_events"] = max(0, info["pending_events"] - len(events))
                result = self.client.post("/api/events", {"device": info, "events": events})
            except ApiError as exc:
                if exc.status == 422:
                    self._send_one_by_one(events)
                    continue
                self.store.record_failure(uids, str(exc))
                raise
            except OSError as exc:
                self.store.record_failure(uids, str(exc))
                raise
            self.store.mark_sent(uids)
            logger.info(
                "%d evento(s) enviados ao servidor (%s novos, %s já registrados).",
                len(events), result.get("accepted"), result.get("duplicates"),
            )
            if len(events) < self.batch_size:
                return

    def _send_one_by_one(self, events: list[dict]) -> None:
        """Isola o evento inválido para ele não travar a fila inteira."""
        for event in events:
            try:
                self.client.post("/api/events", {"device": self.device_info(), "events": [event]})
            except ApiError as exc:
                if exc.status == 422:
                    self.store.mark_rejected(event["event_uid"], exc.message)
                    continue
                raise
            self.store.mark_sent([event["event_uid"]])


# ---------------------------------------------------------------------------------------------- central (spec 026)
def trocar_codigo(endereco: str, codigo: str, computador: str | None = None, programa: str | None = None,
                  timeout: float = 15.0) -> dict:
    """Pareamento: o código de 8 caracteres gerado no painel vira o token do aparelho. Uso único, 30 min."""
    cliente = ServerClient(endereco, None, timeout=timeout)
    return cliente.post("/api/pareamento/trocar", {"codigo": codigo.strip(), "computador": computador,
                                                   "programa": programa})


def _agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class FilaCentral:
    """O que vai para a central, guardado em SQLite antes de enviar: sobrevive a fechar o app e a ficar sem internet.

    - sessões: reenvia quando o conteúdo muda (início, depois o fim com o resumo);
    - eventos: os do teste conectado, já com sessao_uid e trecho_uid nos detalhes;
    - trechos: o metadado e o caminho do arquivo; o vídeo fica na pasta de dados.
    O que foi enviado não é apagado daqui nem da pasta de dados ("Apagar dados" do app continua sendo o jeito)."""

    def __init__(self, caminho: Path):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._trava = threading.Lock()
        self._conn = sqlite3.connect(str(self.caminho), timeout=10, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(
            "CREATE TABLE IF NOT EXISTS sessoes (uid TEXT PRIMARY KEY, payload TEXT NOT NULL, sha TEXT NOT NULL, "
            "  sha_enviado TEXT, alterado_em TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS eventos (uid TEXT PRIMARY KEY, payload TEXT NOT NULL, "
            "  situacao TEXT NOT NULL DEFAULT 'pendente', criado_em TEXT NOT NULL, erro TEXT);"
            "CREATE TABLE IF NOT EXISTS trechos (uid TEXT PRIMARY KEY, meta TEXT NOT NULL, arquivo TEXT NOT NULL, "
            "  situacao TEXT NOT NULL DEFAULT 'pendente', criado_em TEXT NOT NULL, "
            "  tentativas INTEGER NOT NULL DEFAULT 0, erro TEXT);"
        )

    def fechar(self) -> None:
        with self._trava:
            self._conn.close()

    def salvar_sessao(self, uid: str, payload: dict) -> None:
        texto = json.dumps(sem_cardio(payload), ensure_ascii=False, sort_keys=True)
        sha = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        with self._trava:
            self._conn.execute(
                "INSERT INTO sessoes (uid, payload, sha, alterado_em) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(uid) DO UPDATE SET payload = excluded.payload, sha = excluded.sha, "
                "alterado_em = excluded.alterado_em", (uid, texto, sha, _agora_iso()))

    def adicionar_evento(self, evento: dict) -> None:
        texto = json.dumps(sem_cardio(evento), ensure_ascii=False)
        with self._trava:
            self._conn.execute("INSERT OR IGNORE INTO eventos (uid, payload, criado_em) VALUES (?, ?, ?)",
                               (str(evento["event_uid"]), texto, _agora_iso()))

    def adicionar_trecho(self, meta: dict, pasta_trechos: Path) -> None:
        arquivo = Path(pasta_trechos) / meta["sessao_uid"] / meta["arquivo"]
        with self._trava:
            self._conn.execute("INSERT OR IGNORE INTO trechos (uid, meta, arquivo, criado_em) VALUES (?, ?, ?, ?)",
                               (meta["uid"], json.dumps(sem_cardio(meta), ensure_ascii=False), str(arquivo),
                                _agora_iso()))

    def ligar_evento_ao_trecho(self, trecho_uid: str, evento_uid: str) -> None:
        with self._trava:
            linha = self._conn.execute("SELECT meta FROM trechos WHERE uid = ?", (trecho_uid,)).fetchone()
            if linha is None:
                return
            meta = json.loads(linha["meta"])
            if not meta.get("evento_uid"):
                meta["evento_uid"] = evento_uid
                self._conn.execute("UPDATE trechos SET meta = ? WHERE uid = ?", (json.dumps(meta), trecho_uid))

    def pendentes(self) -> dict:
        with self._trava:
            sessoes = self._conn.execute(
                "SELECT COUNT(*) FROM sessoes WHERE sha_enviado IS NULL OR sha_enviado != sha").fetchone()[0]
            eventos = self._conn.execute("SELECT COUNT(*) FROM eventos WHERE situacao = 'pendente'").fetchone()[0]
            trechos = self._conn.execute("SELECT COUNT(*) FROM trechos WHERE situacao = 'pendente'").fetchone()[0]
        return {"sessoes": sessoes, "eventos": eventos, "trechos": trechos}

    def enviar(self, cliente: ServerClient, device_info: dict) -> dict:
        """Envia o que está pendente: sessões, eventos e trechos, nessa ordem. Falta de rede (OSError) e recusa do
        token (ApiError 401/403) sobem para quem chamou; o que não foi enviado continua na fila."""
        enviados = {"sessoes": self._enviar_sessoes(cliente), "eventos": self._enviar_eventos(cliente, device_info)}
        enviados["trechos"] = self._enviar_trechos(cliente)
        return enviados

    def _enviar_sessoes(self, cliente: ServerClient) -> int:
        with self._trava:
            linhas = self._conn.execute("SELECT uid, payload, sha FROM sessoes WHERE sha_enviado IS NULL "
                                        "OR sha_enviado != sha ORDER BY alterado_em").fetchall()
        enviadas = 0
        for linha in linhas:
            try:
                cliente.put_json(f"/api/sessoes/{linha['uid']}", json.loads(linha["payload"]))
                enviadas += 1
            except ApiError as exc:
                # 409 (sessão de outro aparelho), 413 (resumo grande demais), 422 (datas): reenviar igual não resolve.
                if exc.status not in (409, 413, 422):
                    raise
                logger.warning("A central recusou a sessão %s (%s): %s", linha["uid"], exc.status, exc.message)
            with self._trava:
                self._conn.execute("UPDATE sessoes SET sha_enviado = ? WHERE uid = ?", (linha["sha"], linha["uid"]))
        return enviadas

    def _enviar_eventos(self, cliente: ServerClient, device_info: dict, lote: int = 100) -> int:
        total = 0
        while True:
            with self._trava:
                linhas = self._conn.execute("SELECT uid, payload FROM eventos WHERE situacao = 'pendente' "
                                            "ORDER BY criado_em LIMIT ?", (lote,)).fetchall()
            if not linhas:
                return total
            eventos = [json.loads(linha["payload"]) for linha in linhas]
            try:
                cliente.post("/api/events", {"device": device_info, "events": eventos})
                self._marcar_eventos([linha["uid"] for linha in linhas], "enviado")
            except ApiError as exc:
                if exc.status != 422:
                    raise
                for linha, evento in zip(linhas, eventos):  # isola o inválido para não travar a fila
                    try:
                        cliente.post("/api/events", {"device": device_info, "events": [evento]})
                        self._marcar_eventos([linha["uid"]], "enviado")
                    except ApiError as erro:
                        if erro.status != 422:
                            raise
                        self._marcar_eventos([linha["uid"]], "recusado", erro.message)
            total += len(linhas)
            if len(linhas) < lote:
                return total

    def _marcar_eventos(self, uids: list, situacao: str, erro: str | None = None) -> None:
        with self._trava:
            self._conn.executemany("UPDATE eventos SET situacao = ?, erro = ? WHERE uid = ?",
                                   [(situacao, erro, uid) for uid in uids])

    def _enviar_trechos(self, cliente: ServerClient) -> int:
        with self._trava:
            linhas = self._conn.execute("SELECT uid, meta, arquivo FROM trechos WHERE situacao = 'pendente' "
                                        "ORDER BY criado_em").fetchall()
        enviados = 0
        for linha in linhas:
            meta = json.loads(linha["meta"])
            arquivo = Path(linha["arquivo"])
            try:
                dados = arquivo.read_bytes()
            except OSError as exc:  # apagado pela pessoa ("Apagar dados"): não há o que enviar
                self._marcar_trecho(linha["uid"], "sem_arquivo", str(exc))
                continue
            cabecalhos = {"X-RotaGuard-Sessao": meta["sessao_uid"], "X-RotaGuard-Tipo": meta["tipo"],
                          "X-RotaGuard-Inicio": meta["inicio"], "X-RotaGuard-Fim": meta["fim"],
                          "X-RotaGuard-Formato": meta["formato"], "X-RotaGuard-Sha256": meta["sha256"]}
            if meta.get("evento_uid"):
                cabecalhos["X-RotaGuard-Evento"] = str(meta["evento_uid"])
            try:
                cliente.put_bytes(f"/api/trechos/{linha['uid']}", dados, cabecalhos)
            except ApiError as exc:
                # 401/403 (token revogado), 429 (limite por dia, com Retry-After) e 5xx: tentar de novo depois.
                if exc.status in (401, 403, 429) or exc.status >= 500:
                    raise
                # 409 (outro SHA, outro aparelho, apagado ou mais de 20 na sessão), 410, 413 e 422: repetir não resolve.
                logger.warning("A central recusou o trecho %s (%s): %s", linha["uid"], exc.status, exc.message)
                self._marcar_trecho(linha["uid"], "recusado", exc.message)
                continue
            self._marcar_trecho(linha["uid"], "enviado")
            self._anotar_enviado(arquivo)
            enviados += 1
        return enviados

    def _marcar_trecho(self, uid: str, situacao: str, erro: str | None = None) -> None:
        with self._trava:
            self._conn.execute("UPDATE trechos SET situacao = ?, erro = ?, tentativas = tentativas + 1 WHERE uid = ?",
                               (situacao, erro, uid))

    @staticmethod
    def _anotar_enviado(arquivo: Path) -> None:
        metadado = arquivo.with_suffix(".json")
        try:
            dados = json.loads(metadado.read_text(encoding="utf-8"))
            dados["enviado"] = True
            dados["enviado_em"] = _agora_iso()
            metadado.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        except (OSError, ValueError):
            pass


class EnvioCentral(threading.Thread):
    """Envia a FilaCentral em segundo plano enquanto o app está aberto. Começa desligado; ligar() e desligar() seguem
    a opção "Enviar para a empresa". Sem internet, espera mais a cada falha (até 60 s) e nunca trava a tela."""

    def __init__(self, fila: FilaCentral, cliente: ServerClient, status: Callable[[], dict] | None = None,
                 intervalo: float = 5.0, heartbeat_s: float = 15.0, device_info: Callable[[], dict] | None = None,
                 ao_recusar: Callable[[], None] | None = None):
        super().__init__(name="rotaguard-central", daemon=True)
        # Token revogado pela empresa (401/403): o envio para e quem criou é avisado (a tela mostra "desconectado").
        self.ao_recusar = ao_recusar
        self.fila = fila
        self.cliente = cliente
        self.status = status or (lambda: {})
        self.intervalo = intervalo
        self.heartbeat_s = heartbeat_s
        self.device_info = device_info or (lambda: {"hostname": socket.gethostname(), "software_version": __version__})
        self._ligado = threading.Event()
        self._parar = threading.Event()
        self._acordar = threading.Event()
        self._trava = threading.Lock()
        self._proximo_sinal = -math.inf
        self._falhas = 0
        self._situacao = "aguardando"
        self._erro: str | None = None
        self._ultimo_envio: str | None = None

    def ligar(self) -> None:
        self._ligado.set()
        self._acordar.set()

    def desligar(self) -> None:
        self._ligado.clear()
        self._acordar.set()

    def parar(self) -> None:
        self._parar.set()
        self._acordar.set()

    def agora(self) -> None:
        """Acorda o envio já (sessão nova, trecho gravado)."""
        self._acordar.set()

    @property
    def ligado(self) -> bool:
        return self._ligado.is_set()

    def estado(self) -> dict:
        with self._trava:
            situacao = self._situacao if self._ligado.is_set() else "desligado"
            return {"situacao": situacao, "erro": self._erro, "ultimo_envio": self._ultimo_envio,
                    "pendentes": self.fila.pendentes()}

    def run(self) -> None:
        while not self._parar.is_set():
            espera = self.uma_vez() if self._ligado.is_set() else self.intervalo
            self._acordar.wait(espera)
            self._acordar.clear()

    def uma_vez(self) -> float:
        """Uma volta de envio. Devolve quanto esperar até a próxima."""
        try:
            if time.monotonic() >= self._proximo_sinal:
                self.cliente.post("/api/devices/heartbeat", {"device": self.device_info(), "status": self.status()})
                self._proximo_sinal = time.monotonic() + self.heartbeat_s
            enviados = self.fila.enviar(self.cliente, self.device_info())
        except ApiError as exc:
            if exc.status in (401, 403):
                self._falhou("recusado", exc.message)
                self.desligar()
                logger.warning("A central recusou o token deste computador: envio parado. Nada local foi apagado.")
                if self.ao_recusar is not None:
                    try:
                        self.ao_recusar()
                    except Exception:  # noqa: BLE001
                        logger.exception("Falha ao avisar a recusa do token.")
                return self.intervalo
            if exc.status == 429:
                self._falhou("limite", exc.message)
                return exc.retry_after if exc.retry_after is not None else 60.0
            self._falhou("sem_conexao", exc.message)
            return min(60.0, self.intervalo * 2 ** min(self._falhas, 4))
        except OSError as exc:
            self._falhou("sem_conexao", str(exc))
            return min(60.0, self.intervalo * 2 ** min(self._falhas, 4))
        except Exception as exc:  # noqa: BLE001 - nada aqui pode derrubar o app
            logger.exception("Falha inesperada no envio para a central.")
            self._falhou("sem_conexao", str(exc))
            return 60.0
        with self._trava:
            if self._falhas:
                logger.info("Conexão com a central restabelecida.")
            self._falhas = 0
            self._erro = None
            if any(enviados.values()):
                self._ultimo_envio = _agora_iso()
                logger.info("Enviado para a central: %d sessão(ões), %d evento(s), %d trecho(s).",
                            enviados["sessoes"], enviados["eventos"], enviados["trechos"])
            self._situacao = "em_dia" if not any(self.fila.pendentes().values()) else "enviando"
        return self.intervalo

    def _falhou(self, situacao: str, erro: str) -> None:
        with self._trava:
            self._falhas += 1
            if self._falhas == 1:
                logger.warning("Central indisponível (%s). Tudo fica na fila deste computador.", erro)
            self._situacao = situacao
            self._erro = erro
