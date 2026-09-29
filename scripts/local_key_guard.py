"""Fail closed before creating a first local custody key; never replace lost material."""

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/control-api"))

from quantora_api.config import Settings
from quantora_api.data import client
from quantora_api.security import SaaSConfig


async def main() -> int:
    mailbox = ROOT / ".cache/local-mail"
    if mailbox.exists() and any(mailbox.iterdir()):
        return 1
    mongo = client(Settings.from_env().mongo_url)
    try:
        database = mongo[os.getenv("QUANTORA_DATABASE", SaaSConfig().database)]
        return 1 if await database.credentials.count_documents({}) else 0
    finally:
        await mongo.close()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception:  # noqa: BLE001 -- No connection strings or record details in output.
        raise SystemExit(1) from None
