# Scope and traceability

Phase 3 implements the Phase 1 requirements whose primary phase is 3: QNT-FR-0006, 0007, 0009, 0010 and 0011. It also supplies foundations supporting QNT-FR-0012, 0029, 0038–0039, 0045–0049; QNT-INV-0009, 0012–0015; and QNT-NFR-0003, 0005–0007. This does not change the original count of 73 requirements, their phases, or their 73 acceptance scenarios. Those future scenarios remain NOT_RUN unless their full original scope is implemented in their owning phase.

| Phase 3 deliverable | Existing requirements | Implemented evidence | Later boundary |
|---|---|---|---|
| Registration, sessions, recovery | QNT-FR-0010/0011; QNT-NFR-0005 | saas.py/routes, Argon2/token/CSRF/rate-limit tests | Invitations and expanded canonical roles |
| Tenant/role isolation | QNT-FR-0010/0011; QNT-INV-0012 | Server session context, scoped repositories, two-tenant/admin tests | Every later job/stream/trading resource needs equivalent checks |
| Credential custody | QNT-FR-0006/0007/0009; QNT-NFR-0005 | AES-GCM AAD, lifecycle, rotation and leak checks | QNT-FR-0008 exposure-aware remote handover belongs Phase 12; no connection test |
| Mongo data foundations | QNT-FR-0038/0039/0049; QNT-NFR-0006 | Strict schemas/indexes/Decimal128 and real transaction tests | No trading entities or historical bulk datasets populated |
| Audit/idempotency | QNT-FR-0048; QNT-NFR-0005/0007 | Transaction-coupled audit, retry-safe settings primitive | Production database identities/tamper evidence and wider operations |
| Backup/restore | QNT-NFR-0003/0005/0006 | Encrypted quiescent synthetic backup and isolated restore | No PITR, HA, approved RTO/RPO or production key backup claim |
| Account/settings UI | QNT-FR-0006/0010/0011/0013/0016; QNT-NFR-0008 | Responsive forms and planned real browser flow | Full accessibility certification and final workspace remain Phase 11/16 |

Supporting requirements absent as standalone Phase 1 entries are recorded as Phase 3 extensions, not inserted into the Phase 1 registry: P3-EXT-AUTH (registration/session/recovery lifecycle), P3-EXT-MIGRATION (versioned schema runner), P3-EXT-IDEMPOTENCY (tenant-scoped durable retry), P3-EXT-BACKUP (encrypted isolated restore drill), and P3-EXT-LOCAL-MAIL (development-only delivery). They exist solely to make assigned security/data requirements implementable and verifiable.

Implemented behavior is distinguished from foundations: authentication, settings and credential storage APIs are working Phase 3 behavior. Future bot/prediction/order/fill/ledger/model/training collections are validated reference envelopes only. No public CRUD, fabricated record, business calculation, exchange request, learning process or trading authority exists. D-12 remains NOT_APPROVED and blocks production retention/deletion promises.
