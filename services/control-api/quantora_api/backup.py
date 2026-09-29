"""Encrypted quiescent local backups and isolated restore; never drop working data."""

import json
import os
import re
import secrets
from pathlib import Path
from typing import Any
from uuid import uuid4

from bson import json_util
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .data import DB, SCHEMAS, audit
from .security import Custody, SaaSConfig


async def backup(db: DB, output: Path, config: SaaSConfig, *, quiescent: bool) -> None:
    if not quiescent or config.active_key not in config.keys:
        raise ValueError("Quiescent source and external backup key required")
    collections: dict[str, Any] = {}
    for name in SCHEMAS:
        collections[name] = {
            "options": await db[name].options(),
            "indexes": await db[name].index_information(),
            "documents": await db[name].find({}).to_list(None),
        }
    payload = json_util.dumps(
        {"schema_version": 1, "source": db.name, "collections": collections}
    ).encode()
    header = json.dumps({"version": 1, "key_id": config.active_key}, sort_keys=True).encode()
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(config.keys[config.active_key]).encrypt(
        nonce, payload, b"QUANTORA_BACKUP_V1" + header
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation, never overwrite a previous backup. Contents always encrypted.
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(len(header).to_bytes(4, "big") + header + nonce + encrypted)
    await audit(db, None, "backup.created", "ENCRYPTED_LOCAL_BACKUP", str(uuid4()))


async def restore(source: Path, target: DB, config: SaaSConfig) -> dict[str, Any]:
    if not re.fullmatch(r"quantora_restore_[a-f0-9]{32}", target.name):
        raise ValueError("Restore requires a separately named disposable database")
    if await target.list_collection_names():
        raise ValueError("Restore target already exists; no data overwritten")
    raw = source.read_bytes()
    size = int.from_bytes(raw[:4], "big")
    if size > 4096 or len(raw) < size + 32:
        raise ValueError("Invalid backup")
    header, offset = raw[4 : 4 + size], 4 + size
    meta = json.loads(header)
    if meta.get("version") != 1 or meta["key_id"] not in config.keys:
        raise ValueError("Backup key unavailable")
    payload = AESGCM(config.keys[meta["key_id"]]).decrypt(
        raw[offset : offset + 12], raw[offset + 12 :], b"QUANTORA_BACKUP_V1" + header
    )
    data = json_util.loads(payload)
    if data["schema_version"] != 1 or set(data["collections"]) != set(SCHEMAS):
        raise ValueError("Unsupported backup schema")
    counts: dict[str, int] = {}
    for name, stored in data["collections"].items():
        await target.create_collection(name, **stored["options"])
        for index_name, index in stored["indexes"].items():
            if index_name != "_id_":
                options = {k: v for k, v in index.items() if k not in ("v", "key", "ns")}
                await target[name].create_index(index["key"], name=index_name, **options)
        if stored["documents"]:
            await target[name].insert_many(stored["documents"])
        restored = await target[name].find({}).to_list(None)
        if sorted(json_util.dumps(r, sort_keys=True) for r in restored) != sorted(
            json_util.dumps(r, sort_keys=True) for r in stored["documents"]
        ):
            raise ValueError("Restored documents differ")
        if await target[name].options() != stored["options"]:
            raise ValueError("Restored schema differs")
        indexes = await target[name].index_information()
        if json_util.dumps(indexes, sort_keys=True) != json_util.dumps(
            stored["indexes"], sort_keys=True
        ):
            raise ValueError("Restored indexes differ")
        counts[name] = len(restored)
    custody = Custody(config)
    verified = 0
    async for record in target.credentials.find({}):
        custody.decrypt(record["encrypted"], record)
        verified += 1
    await audit(target, None, "restore.verified", "ISOLATED_DATABASE", str(uuid4()))
    return {
        "collections": counts,
        "decrypted_credentials": verified,
        "isolated_target": target.name,
    }
