"""Fila local de eventos em SQLite. Guarda tudo no dispositivo até o servidor confirmar o recebimento."""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("drivesafe.queue")

# Identifica o processo quando o sistema não expõe um boot_id (Windows e macOS).
_PROCESS_BOOT_ID = uuid.uuid4().hex


def current_boot_id() -> str:
    """Enquanto o boot_id não muda, time.monotonic() é comparável entre eventos (Linux: desde o boot)."""
    try:
        with open("/proc/sys/kernel/random/boot_id", encoding="ascii") as handle:
            return handle.read().strip()
    except OSError:
        return _PROCESS_BOOT_ID


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(timezone.utc)).isoformat(timespec="milliseconds")


class EventStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), timeout=10, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")  # menos gravações no cartão SD, seguro com WAL
        strict = " STRICT" if sqlite3.sqlite_version_info >= (3, 37, 0) else ""
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS events (
                event_uid TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                risk_level INTEGER NOT NULL,
                duration REAL NOT NULL,
                details TEXT,
                occurred_at TEXT NOT NULL,
                boot_id TEXT NOT NULL,
                monotonic REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'rejected')),
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                sent_at TEXT
            ){strict}
            """
        )
        self._conn.execute("CREATE INDEX IF NOT EXISTS ix_events_status ON events (status, occurred_at)")

    def add(self, alert_type: str, risk_level: int, duration: float, details: dict | None = None) -> str:
        event_uid = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                "INSERT INTO events (event_uid, alert_type, risk_level, duration, details, occurred_at, boot_id, monotonic)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_uid, alert_type, int(risk_level), float(duration),
                    json.dumps(details, ensure_ascii=False) if details else None,
                    _utc_iso(), current_boot_id(), time.monotonic(),
                ),
            )
        logger.info("Evento %s salvo na fila local (%.2fs).", alert_type, duration)
        return event_uid

    def pending(self, limit: int = 100) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE status = 'pending' ORDER BY occurred_at LIMIT ?", (limit,)
            ).fetchall()
        boot_id = current_boot_id()
        now = time.monotonic()
        events = []
        for row in rows:
            event = {
                "event_uid": row["event_uid"],
                "alert_type": row["alert_type"],
                "risk_level": row["risk_level"],
                "duration": row["duration"],
                "occurred_at": row["occurred_at"],
            }
            if row["details"]:
                event["details"] = json.loads(row["details"])
            # Mesmo boot: a idade medida pelo relógio monotônico corrige relógio de parede errado.
            if row["boot_id"] == boot_id and now >= row["monotonic"]:
                event["age_seconds"] = round(now - row["monotonic"], 3)
            events.append(event)
        return events

    def mark_sent(self, event_uids: list[str]) -> None:
        self._update_many("UPDATE events SET status = 'sent', sent_at = ?, last_error = NULL WHERE event_uid = ?",
                          [(_utc_iso(), uid) for uid in event_uids])

    def mark_rejected(self, event_uid: str, error: str) -> None:
        logger.error("Servidor rejeitou o evento %s: %s", event_uid, error)
        self._update_many("UPDATE events SET status = 'rejected', last_error = ? WHERE event_uid = ?",
                          [(error[:500], event_uid)])

    def record_failure(self, event_uids: list[str], error: str) -> None:
        self._update_many("UPDATE events SET attempts = attempts + 1, last_error = ? WHERE event_uid = ?",
                          [(error[:500], uid) for uid in event_uids])

    def count_pending(self) -> int:
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM events WHERE status = 'pending'").fetchone()[0]

    def purge_sent(self, older_than_days: int = 30) -> int:
        cutoff = _utc_iso(datetime.now(timezone.utc) - timedelta(days=older_than_days))
        with self._lock:
            cursor = self._conn.execute("DELETE FROM events WHERE status = 'sent' AND sent_at < ?", (cutoff,))
        return cursor.rowcount

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _update_many(self, sql: str, params: list[tuple]) -> None:
        if not params:
            return
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                self._conn.executemany(sql, params)
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
