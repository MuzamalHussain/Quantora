import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    mode: str = "PAPER"
    core_url: str = "http://127.0.0.1:8101"
    mongo_url: str = "mongodb://127.0.0.1:27117/?directConnection=true&replicaSet=quantora-rs"
    redis_url: str = "redis://127.0.0.1:6381/0"
    cors_origin: str = "http://127.0.0.1:5173"

    def __post_init__(self) -> None:
        if self.mode not in {"PAPER", "TESTNET", "SHADOW", "REPLAY"}:
            raise ValueError("Invalid or disabled foundation mode")
        for value, scheme in [
            (self.core_url, "http"),
            (self.mongo_url, "mongodb"),
            (self.redis_url, "redis"),
            (self.cors_origin, "http"),
        ]:
            parsed = urlparse(value)
            if parsed.scheme != scheme or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Foundation addresses must be local")
            if parsed.username or parsed.password or parsed.fragment:
                raise ValueError("Credentials/fragments are not accepted in local examples")
            if parsed.port is None or not 1 <= parsed.port <= 65535:
                raise ValueError("Explicit valid port required")
        for value in (self.core_url, self.cors_origin):
            parsed = urlparse(value)
            if parsed.path not in {"", "/"} or parsed.query:
                raise ValueError("Service/origin must be a base address")

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            mode=os.getenv("QUANTORA_MODE", defaults.mode),
            core_url=os.getenv("QUANTORA_CORE_URL", defaults.core_url),
            mongo_url=os.getenv("QUANTORA_MONGO_URL", defaults.mongo_url),
            redis_url=os.getenv("QUANTORA_REDIS_URL", defaults.redis_url),
            cors_origin=os.getenv("QUANTORA_CORS_ORIGIN", defaults.cors_origin),
        )
