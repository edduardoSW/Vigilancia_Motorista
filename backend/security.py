"""Segredos do servidor: tokens de dispositivo, senhas e sessões. O banco guarda só hashes, nunca o valor."""
import base64
import hashlib
import hmac
import secrets
import threading
import time
from collections import deque

TOKEN_PREFIX = "dsk_"

# scrypt com o mínimo recomendado pela OWASP (Password Storage Cheat Sheet): N=2^17, r=8, p=1 (~128 MiB por hash).
SCRYPT_N = 2 ** 17
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAXMEM = 256 * 1024 * 1024
MIN_PASSWORD_LENGTH = 10

# Tentativas de login erradas por IP + login (e-mail ou celular) antes de bloquear por um tempo.
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_S = 15 * 60


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_device_token():
    """Retorna (token, hash, prefixo visível). O token só deve ser mostrado uma vez."""
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return token, hash_token(token), token[: len(TOKEN_PREFIX) + 6]


def token_matches(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), expected_hash)


def generate_session_token():
    """Retorna (token para o cookie, hash para o banco)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P,
                             maxmem=SCRYPT_MAXMEM, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(salt)}${_b64(derived)}"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        scheme, n, r, p, salt, expected = (stored or "").split("$")
        if scheme != "scrypt":
            return False
        derived = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r),
                                 p=int(p), maxmem=SCRYPT_MAXMEM, dklen=len(base64.b64decode(expected)))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived, base64.b64decode(expected))


def password_problem(password: str) -> str | None:
    """Motivo para recusar a senha, ou None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"A senha precisa de pelo menos {MIN_PASSWORD_LENGTH} caracteres."
    if password.strip() != password:
        return "A senha não pode começar nem terminar com espaço."
    return None


class LoginThrottle:
    """Conta falhas de login por chave (IP + login) numa janela deslizante, em memória."""

    def __init__(self, max_failures: int = LOGIN_MAX_FAILURES, window_s: float = LOGIN_WINDOW_S, clock=time.monotonic):
        self.max_failures = max_failures
        self.window_s = window_s
        self._clock = clock
        self._failures: dict[str, deque] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str) -> deque:
        failures = self._failures.setdefault(key, deque())
        horizon = self._clock() - self.window_s
        while failures and failures[0] < horizon:
            failures.popleft()
        return failures

    def blocked_for(self, key: str) -> float:
        """Segundos até poder tentar de novo; 0 se liberado."""
        with self._lock:
            failures = self._recent(key)
            if len(failures) < self.max_failures:
                return 0.0
            return max(0.0, failures[0] + self.window_s - self._clock())

    def fail(self, key: str) -> None:
        with self._lock:
            self._recent(key).append(self._clock())

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
