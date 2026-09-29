import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "contracts/foundation-v1.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft7Validator(SCHEMA)


def reject_constant(value: str) -> None:
    raise ValueError("Nonfinite JSON")


def parse_contract(raw: bytes) -> dict[str, Any]:
    value: Any = json.loads(raw, parse_constant=reject_constant)
    VALIDATOR.validate(value)
    if not isinstance(value, dict):
        raise TypeError("Envelope required")
    return value


def envelope(mode: str, cid: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema_version": "1.0.0",
        "event_id": str(uuid4()),
        "correlation_id": cid,
        "occurred_at_ms": time.time_ns() // 1_000_000,
        "mode": mode,
        "source": {"kind": "FOUNDATION", "name": "control-api"},
        "event_type": event_type,
        "payload": payload,
    }
    VALIDATOR.validate(value)
    return value
