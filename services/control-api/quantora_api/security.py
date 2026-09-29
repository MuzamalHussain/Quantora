"""Phase 3 local security primitives. Never log arguments or return custody plaintext."""

import base64
import hashlib
import json
import os
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from bson.decimal128 import Decimal128
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))


def now() -> datetime:
    return datetime.now(UTC)


def token() -> str:
    return secrets.token_urlsafe(32)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_email(value: str) -> str:
    # Intentionally ASCII and case-insensitive for this local account system.
    result = value.strip().lower()
    if len(result) > 254 or not re.fullmatch(
        r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", result
    ):
        raise ValueError("Invalid email")
    return result


def password_hash(password: str) -> str:
    if not 12 <= len(password) <= 128 or len(password.encode()) > 512:
        raise ValueError("Password must contain 12 to 128 characters")
    return HASHER.hash(password)


def password_matches(encoded: str, password: str) -> bool:
    if len(password) > 128:
        return False
    try:
        return HASHER.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def decimal128(value: str) -> Decimal128:
    if not re.fullmatch(r"-?(?:0|[1-9]\d{0,17})(?:\.\d{1,18})?", value):
        raise ValueError("Invalid decimal")
    number = Decimal(value)
    if len(number.as_tuple().digits) > 34:
        raise ValueError("Decimal exceeds Decimal128 precision")
    try:
        return Decimal128(number)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid decimal") from exc


@dataclass(frozen=True)
class SaaSConfig:
    database: str = "quantora_app"
    secure_cookie: bool = False  # Explicit localhost HTTP development exception.
    origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://127.0.0.1:4173")
    session_seconds: int = 28800
    token_seconds: int = 900
    keys: dict[str, bytes] = field(default_factory=dict, repr=False)
    active_key: str = ""
    profile: str = "LOCAL"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"quantora_[a-zA-Z0-9_]{1,60}", self.database):
            raise ValueError("Invalid database")
        if self.profile != "LOCAL":
            raise ValueError("Production delivery and deployment are not configured")
        if not 1 <= self.session_seconds <= 28800 or not 1 <= self.token_seconds <= 900:
            raise ValueError("Invalid expiry")
        if any(len(k) != 32 for k in self.keys.values()):
            raise ValueError("Invalid custody key")
        if self.active_key and self.active_key not in self.keys:
            raise ValueError("Active custody key unavailable")

    @classmethod
    def from_env(cls) -> "SaaSConfig":
        raw = json.loads(os.getenv("QUANTORA_CUSTODY_KEYS", "{}"))
        if not isinstance(raw, dict):
            raise ValueError("Invalid custody configuration")  # noqa: TRY004 -- Sanitized startup configuration failure.
        secure = os.getenv("QUANTORA_SECURE_COOKIE", "false")
        if secure not in ("true", "false"):
            raise ValueError("Invalid cookie configuration")
        return cls(
            database=os.getenv("QUANTORA_DATABASE", "quantora_app"),
            secure_cookie=secure == "true",
            keys={k: base64.b64decode(v, validate=True) for k, v in raw.items()},
            active_key=os.getenv("QUANTORA_ACTIVE_KEY", ""),
            profile=os.getenv("QUANTORA_PROFILE", "LOCAL"),
        )

    @property
    def cookie(self) -> str:
        return "__Host-quantora_session" if self.secure_cookie else "quantora_session"


class Custody:
    def __init__(self, config: SaaSConfig):
        self.config = config

    @staticmethod
    def aad(meta: dict[str, Any]) -> bytes:
        return json.dumps(
            {k: meta[k] for k in ("_id", "tenant_id", "provider", "environment", "scope")},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    def encrypt(self, secret: dict[str, str], meta: dict[str, Any]) -> dict[str, Any]:
        key_id = self.config.active_key
        if key_id not in self.config.keys:
            raise ValueError("Custody unavailable")
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(self.config.keys[key_id]).encrypt(
            nonce, json.dumps(secret, sort_keys=True).encode(), self.aad(meta)
        )
        return {"version": 1, "key_id": key_id, "nonce": nonce, "ciphertext": ciphertext}

    def decrypt(self, encrypted: dict[str, Any], meta: dict[str, Any]) -> dict[str, str]:
        if encrypted["version"] != 1:
            raise ValueError("Unsupported ciphertext")
        key = self.config.keys.get(encrypted["key_id"])
        if key is None:
            raise ValueError("Custody unavailable")
        data = AESGCM(key).decrypt(encrypted["nonce"], encrypted["ciphertext"], self.aad(meta))
        value: dict[str, str] = json.loads(data)
        return value


class MailDelivery(Protocol):
    async def send(self, email: str, purpose: str, raw_token: str, expires: datetime) -> None: ...


class UnconfiguredMail:
    async def send(self, email: str, purpose: str, raw_token: str, expires: datetime) -> None:
        raise ValueError("Local delivery is not configured")


class LocalMail:
    """Bounded in-memory DEVELOPMENT delivery. No HTTP read route; no disk/log secrets."""

    def __init__(self) -> None:
        self.messages: dict[tuple[str, str], tuple[str, datetime]] = {}

    async def send(self, email: str, purpose: str, raw_token: str, expires: datetime) -> None:
        self.messages = {k: v for k, v in self.messages.items() if v[1] > now()}
        if len(self.messages) >= 1000:
            self.messages.pop(next(iter(self.messages)))
        self.messages[(email, purpose)] = (raw_token, expires)


class EncryptedLocalMail:
    """Development-only local mailbox. Root key stays in externally supplied keyring."""

    def __init__(self, config: SaaSConfig, directory: Path):
        self.config, self.directory = config, directory

    @staticmethod
    def metadata(email: str, purpose: str) -> dict[str, Any]:
        return {
            "_id": digest(normalize_email(email) + ":" + purpose),
            "tenant_id": "LOCAL_MAIL",
            "provider": purpose,
            "environment": "LOCAL",
            "scope": "DEVELOPMENT",
        }

    async def send(self, email: str, purpose: str, raw_token: str, expires: datetime) -> None:
        meta = self.metadata(email, purpose)
        encrypted = Custody(self.config).encrypt(
            {"token": raw_token, "expires_at": expires.isoformat()}, meta
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / (meta["_id"] + ".json")
        temporary = target.with_suffix("." + secrets.token_hex(8) + ".tmp")
        fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(
                {
                    **encrypted,
                    "nonce": base64.b64encode(encrypted["nonce"]).decode(),
                    "ciphertext": base64.b64encode(encrypted["ciphertext"]).decode(),
                },
                stream,
            )
        os.replace(temporary, target)

    def read(self, email: str, purpose: str) -> str:
        meta = self.metadata(email, purpose)
        value = json.loads((self.directory / (meta["_id"] + ".json")).read_text())
        for key in ("nonce", "ciphertext"):
            value[key] = base64.b64decode(value[key], validate=True)
        decoded = Custody(self.config).decrypt(value, meta)
        if datetime.fromisoformat(decoded["expires_at"]) <= now():
            raise ValueError("Local delivery expired")
        return decoded["token"]


class FoundationObligations:
    """Capability-gated replacement policy; a future executor must provide another checker."""

    def __init__(self, execution_capability: bool | None = None):
        self.execution_capability = execution_capability

    async def safe_to_remove(self, tenant_id: str, credential_id: str) -> bool:
        # Unknown/introduced execution is never assumed flat.
        return self.execution_capability is False
