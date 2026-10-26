from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import re
import secrets

ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

class Role(StrEnum):
    OWNER = "OWNER"
    PARTICIPANT = "PARTICIPANT"

class CheckpointKind(StrEnum):
    CHECK_IN = "CHECK_IN"
    PRESENCE_CHECK = "PRESENCE_CHECK"
    CHECK_OUT = "CHECK_OUT"

class Lifecycle(StrEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class FactKind(StrEnum):
    CHECKED_IN = "CHECKED_IN"
    PRESENCE_CONFIRMED = "PRESENCE_CONFIRMED"
    CHECKED_OUT = "CHECKED_OUT"

class DomainError(ValueError):
    def __init__(self, code, message, status=400):
        super().__init__(message); self.code=code; self.status=status

def now_iso(): return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
def opaque(prefix, size=18): return prefix + secrets.token_urlsafe(size)
def stable_user_id(subject): return "usr_" + hashlib.sha256(subject.encode()).hexdigest()[:32]
def require_text(value, name, maximum=120):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise DomainError("INVALID_INPUT", f"{name} is required and must be at most {maximum} characters")
    return value.strip()
def require_id(value, prefix):
    if not isinstance(value, str) or not value.startswith(prefix) or not ID_PATTERN.fullmatch(value):
        raise DomainError("INVALID_IDENTIFIER", f"Expected an opaque {prefix} identifier")
    return value

def display_state(checkpoint, fact=None, now=None):
    lifecycle=checkpoint["lifecycle"]
    if lifecycle == Lifecycle.CANCELLED: return "CANCELLED"
    if fact: return "COMPLETED"
    now = now or now_iso()
    if lifecycle == Lifecycle.OPEN: return "AVAILABLE"
    if lifecycle in (Lifecycle.DRAFT, Lifecycle.SCHEDULED): return "UPCOMING"
    return "MISSED"
