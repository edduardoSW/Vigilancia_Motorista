"""Envio da fila local para o servidor central, com reenvio automático quando a conexão volta."""
from __future__ import annotations

import json
import logging
import platform
import socket
import threading
import time
import urllib.error
import urllib.request
from typing import Callable

from vision import __version__
from vision.event_queue import EventStore

logger = logging.getLogger("drivesafe.sync")


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class ServerClient:
    def __init__(self, base_url: str, token: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": f"drivesafe-device/{__version__}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code, exc.read().decode("utf-8", "replace")[:300]) from exc
        return json.loads(body) if body else {}


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
