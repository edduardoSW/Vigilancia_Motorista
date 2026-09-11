"""Avisos em tempo real para o app, filtrados por quem está conectado.

Admin recebe tudo. Gestor recebe só a própria empresa. Motorista recebe só o que é dele.
"""
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger("drivesafe.live")


@dataclass(eq=False)
class Subscriber:
    websocket: WebSocket
    role: str
    company_id: Optional[int]
    driver_id: Optional[int]

    def wants(self, company_id: Optional[int], driver_id: Optional[int], admin_only: bool) -> bool:
        if self.role == "admin":
            return True
        if admin_only or company_id is None or company_id != self.company_id:
            return False
        return self.role != "motorista" or (driver_id is not None and driver_id == self.driver_id)


class LiveHub:
    def __init__(self):
        self._subscribers: set = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def add(self, subscriber: Subscriber) -> None:
        self._subscribers.add(subscriber)

    def remove(self, subscriber: Subscriber) -> None:
        self._subscribers.discard(subscriber)

    async def publish(self, message: dict, company_id: Optional[int] = None, driver_id: Optional[int] = None,
                      admin_only: bool = False) -> None:
        payload = json.dumps(jsonable_encoder(message), ensure_ascii=False)
        for subscriber in list(self._subscribers):
            if not subscriber.wants(company_id, driver_id, admin_only):
                continue
            try:
                await subscriber.websocket.send_text(payload)
            except Exception as exc:
                logger.info("Conexão de tempo real removida após falha no envio: %s", exc)
                self._subscribers.discard(subscriber)

    def publish_threadsafe(self, message: dict, **scope) -> None:
        """Para threads fora do servidor (modo teste, análise de vídeo)."""
        if self.loop is None or self.loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self.publish(message, **scope), self.loop)


hub = LiveHub()
