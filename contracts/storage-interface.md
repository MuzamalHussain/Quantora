# Future dataset storage interface (design, not implementation)

An immutable DatasetRef identifies dataset_id, data_version, schema_version, source/provenance, UTC event-time coverage, row count, content SHA-256, partition manifest and an object-store key. Parquet is the proposed columnar representation. Keys are server-owned storage identifiers, never arbitrary fetch URLs supplied by users. Tenant-private datasets carry tenant scope and permitted purpose; shared market datasets carry licensing/provenance.

Required future operations: put an immutable content-addressed object conditionally; resolve a manifest by ID/version; read a permitted partition; verify hash/coverage; tombstone an object subject to retention/holds. MongoDB stores application references and governance, while bulk bytes live in object storage. Model/artifact references pin data versions. No put/read endpoint or storage credentials are implemented in Phase 2, and no unavailable provider is claimed configured.
