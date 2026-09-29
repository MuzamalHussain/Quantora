"""Explicit local administration. Passwords are read with getpass, never CLI arguments."""

import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path
from uuid import uuid4

from redis.asyncio import Redis

from .backup import backup, restore
from .config import Settings
from .data import client, migrate
from .saas import SaaS
from .security import EncryptedLocalMail, SaaSConfig


async def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "operation",
        choices=[
            "migrate",
            "bootstrap-admin",
            "rotate",
            "backup",
            "restore",
            "unlock-migration",
            "read-local-mail",
        ],
    )
    parser.add_argument("--path", type=Path)
    parser.add_argument("--target")
    parser.add_argument("--quiescent", action="store_true")
    parser.add_argument("--lock-owner")
    args = parser.parse_args()
    settings, config = Settings.from_env(), SaaSConfig.from_env()
    if args.operation == "read-local-mail":
        directory = os.getenv("QUANTORA_LOCAL_MAIL_DIR")
        if not directory:
            raise ValueError("Local mailbox not configured")
        email = input("Local delivery email: ")
        purpose = input("Purpose (verify/reset): ")
        if purpose not in ("verify", "reset"):
            raise ValueError("Invalid purpose")
        # Explicit interactive local delivery, not an HTTP API/log. Never capture this output.
        print(EncryptedLocalMail(config, Path(directory)).read(email, purpose))
        return
    mongo = client(settings.mongo_url)
    redis = Redis.from_url(settings.redis_url)
    db = mongo[config.database]
    try:
        if args.operation == "migrate":
            await migrate(db)
        elif args.operation == "bootstrap-admin":
            email = input("Admin email: ")
            password = getpass.getpass("New admin password (12–128 characters): ")
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match")
            await SaaS(db, redis, config).register(email, password, str(uuid4()), admin=True)
        elif args.operation == "rotate":
            await SaaS(db, redis, config).rotate(str(uuid4()))
        elif args.operation == "backup" and args.path:
            await backup(db, args.path, config, quiescent=args.quiescent)
        elif args.operation == "restore" and args.path and args.target:
            print(json.dumps(await restore(args.path, mongo[args.target], config)))
        elif args.operation == "unlock-migration" and args.lock_owner:
            # Operator must first establish the recorded process is no longer running.
            result = await db.migration_lock.delete_one(
                {"_id": "exclusive", "owner": args.lock_owner}
            )
            if result.deleted_count != 1:
                raise ValueError("Lock owner did not match")
        else:
            raise ValueError("Required operation arguments missing")
        print("Operation completed")
    finally:
        await redis.aclose()
        await mongo.close()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception:  # noqa: BLE001 -- Do not expose secrets/connection details in admin errors.
        print(
            "Operation failed; check configuration, migration status and documented recovery steps"
        )
        raise SystemExit(1) from None
