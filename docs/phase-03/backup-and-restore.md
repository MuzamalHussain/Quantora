# Backup and isolated restore

Implementation: quantora_api/backup.py and management CLI. This is a quiescent local foundation drill, not production PITR/HA recovery. Stop mutations to the source before explicitly acknowledging `--quiescent`. The source database is never dropped. The backup captures each required collection's documents, validators and indexes, then encrypts the entire payload using AES-GCM under the external keyring. Files use exclusive creation, restrictive creation mode and are ignored by version control (*.qbackup). Windows inherited directory ACLs must also restrict the chosen directory; encryption protects content independently of filesystem permissions.

From services/control-api:

```powershell
python -m quantora_api.manage backup --path PATH_TO_PRIVATE_ARCHIVE.qbackup --quiescent
python -m quantora_api.manage restore --path PATH_TO_PRIVATE_ARCHIVE.qbackup --target quantora_restore_UUID32HEX
```

Choose a new UUID target. Restore refuses other names or any preexisting target collections; it does not drop/rewrite existing data. It recreates validators/indexes, restores documents, compares documents and schema/index metadata, and decrypts every restored credential with separately supplied external keys. Restore appends a sanitized verification audit after comparing the captured snapshot. A failed partial restore remains for inspection; choose another new disposable target when rerunning rather than silently clearing it.

The integration drill backs up quiescent synthetic account/audit/encrypted credential records and restores to its own unique database. Tests remove only the database they created. A database archive alone cannot recover root-key custody; retain needed old keys independently, including keys used to encrypt backup files. No working keys are generated, rotated or replaced by this drill. Large production backup streaming, write-consistent snapshots during concurrent mutation and disaster recovery objectives remain future operational work.
