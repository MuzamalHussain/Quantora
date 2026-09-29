# Sources

Official guidance reviewed on 2026-09-21. Version selection is recorded by `services/control-api/requirements.lock`; these sources explain behavior and constraints, not proof that QUANTORA passed its tests.

| Source | Use |
|---|---|
| https://argon2-cffi.readthedocs.io/en/25.1.0/api.html | PasswordHasher Argon2id parameters, verification and rehash guidance |
| https://cryptography.io/en/latest/hazmat/primitives/aead/ | AESGCM confidentiality/integrity, AAD, 96-bit nonce guidance and InvalidTag behavior |
| https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html | Opaque high-entropy sessions, cookie attributes, expiry/revocation and fixation controls |
| https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html | Generic recovery responses, random single-use expiring tokens and session invalidation choices |
| https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html | Same-origin checks and synchronizer/double-submit defenses |
| https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/ | PyMongo `with_transaction`, callback retry behavior and transaction options |
| https://www.mongodb.com/docs/manual/core/schema-validation/ | Collection JSON schema validation |
| https://www.mongodb.com/docs/manual/core/index-unique/ | Unique-index behavior and duplicate conflicts |
| https://www.mongodb.com/docs/manual/core/index-ttl/ | TTL cleanup semantics; application still checks expiry |
| https://www.mongodb.com/docs/manual/tutorial/backup-and-restore-tools/ | Backup/restore context; Phase 3 uses a purpose-built encrypted local snapshot drill |
| https://redis.io/docs/latest/develop/interact/programmability/eval-intro/ | Atomic Lua counter used for bounded abuse control |

Phase 1 and Phase 2 source records remain historical. No official exchange API was consulted to implement connectivity because exchange calls are excluded. No legal/jurisdictional source was used to invent D-12 retention policy.
