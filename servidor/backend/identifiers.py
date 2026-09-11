"""Login e contato: e-mail em minúsculas e celular num formato único (só dígitos, com código do país)."""
import re
from typing import Optional

BRAZIL = "55"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(raw: Optional[str]) -> Optional[str]:
    value = (raw or "").strip().lower()
    return value or None


def email_problem(email: Optional[str]) -> Optional[str]:
    if email is None or (len(email) <= 254 and EMAIL_RE.match(email)):
        return None
    return "E-mail inválido."


def normalize_phone(raw: Optional[str]) -> Optional[str]:
    """'(11) 98765-4321' → '5511987654321'. None se não tiver cara de telefone."""
    if raw is None:
        return None
    text = str(raw).strip()
    digits = re.sub(r"\D", "", text)
    if not text.startswith("+"):
        digits = digits.lstrip("0")  # prefixo de longa distância (0xx)
        if len(digits) in (10, 11):  # DDD + número, sem o código do país
            digits = BRAZIL + digits
    return digits if 10 <= len(digits) <= 15 else None


def format_phone(digits: Optional[str]) -> Optional[str]:
    if not digits:
        return None
    if digits.startswith(BRAZIL) and len(digits) in (12, 13):
        area, number = digits[2:4], digits[4:]
        return f"+55 ({area}) {number[:-4]}-{number[-4:]}"
    return "+" + digits
