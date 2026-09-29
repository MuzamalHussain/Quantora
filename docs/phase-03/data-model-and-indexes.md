# Data model and indexes

Canonical executable definitions: quantora_api/data.py SCHEMAS/INDEXES, migration v1 with a checksum. All application documents have a string ID, schema_version=1 and UTC BSON datetime created_at. Mongo validators reject missing required fields, incorrect types and unknown fields. Do not store historical ticks in these documents; future bulk data remains immutable Parquet/object storage with references/provenance governed in Mongo.

| Collection | Ownership/content | Important index / expiry |
|---|---|---|
| users, tenants | Email/hash/role/auth epoch and unique owner | Unique email, tenant_id and owner_id; no TTL |
| sessions | User, token/CSRF hashes, absolute expiry, auth epoch | Unique token hash; user lookup; expires_at TTL=0 |
| tokens | User, purpose, token hash, expiry and auth epoch | Unique token hash; user/purpose; expiry TTL=0 |
| settings | Private tenant theme/timeframe preference | Unique tenant; no TTL |
| credentials | Tenant/owner/provider/environment/scope, masked status, revision, encrypted envelope | Unique tenant/provider/environment and key-ID/nonce; no TTL |
| audit | Event ID, actor/tenant/action/target/correlation/outcome/time | Tenant/time; no TTL or public mutation interface |
| idempotency | Tenant/operation/key, request fingerprint and sanitized consistent result | Unique tenant/operation/key; no TTL |
| migrations, rotations | Applied version/checksum and resumable per-key progress | Unique IDs; no TTL |
| bot_sessions, predictions, outcomes, order_intents, fill_events, ledger_events, model_versions, training_runs | Tenant/environment/record/version references; optional exact amount | Unique tenant/environment/record_ref; no public CRUD or TTL |

Future collections are data envelopes only, not fabricated orders, fills, forecasts, balances, ledger calculations or training runs. Monetary conversion accepts canonical non-exponent decimal strings (18 integer/18 fraction maxima) only when their significant digits fit Decimal128's 34-digit precision; overprecision is rejected rather than rounded. NaN/Infinity/exponents and oversized ranges are rejected. Real DB decimal round trips are tested. Contracts remain structural; later business logic must validate quantity signs, exchange filters and accounting semantics.

The existing server is local single-node quantora-rs, supporting transactions but not HA. infra/phase03-application-role.json specifies separate runtime audit insert/find privileges, mutable account collections and no financial/migration administration. Current loopback Compose has authentication disabled, so role-based database enforcement is not claimed. Enabling authenticated database principals, TLS and separate operator credentials is required before any nonlocal deployment; HTTP tenant enforcement is active and tested now.
