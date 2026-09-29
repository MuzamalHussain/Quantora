"""Exact isolated Phase 4 evidence DB lifecycle; refuses non-test names."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/control-api"))
from quantora_api.config import Settings
from quantora_api.data import client, migrate


async def main() -> None:
    action, name = sys.argv[1:3]
    if not name.startswith("quantora_test_collector_"):
        raise ValueError("isolated collector database required")
    mongo = client(Settings().mongo_url)
    try:
        if action == "prepare":
            await mongo.drop_database(name)
            await migrate(mongo[name])
        elif action == "drop":
            await mongo.drop_database(name)
        else:
            raise ValueError("invalid action")
    finally:
        await mongo.close()


if __name__ == "__main__":
    asyncio.run(main())
