# Security and tenant isolation

QNT-FR-0006–0012, 0045–0046, QNT-INV-0012/0015 and QNT-NFR-0005 define obligations. Every resource is owned by authenticated tenant plus environment and, where applicable, account/session/epoch. Scope includes indexes/queries, cache keys, object paths/signed links, websockets, jobs, logs and exports. Tests probe forged identifiers and stale memberships across each boundary. Public market data may be shared subject to rights; private events require explicit purpose controls.

Credential secrets are encrypted server-side. Root keys live in server secret management outside MongoDB; decryption authority is limited to the integration boundary. Browser reads return metadata/masked identifiers only. Synthetic sentinel checks cover success/error responses, analytics, tracing, logs, builds and exports. Revocation denies further authorization and preserves exposure recovery metadata. Provider IDs select server-owned destinations; arbitrary URLs/private-host redirects cannot reach a generic server fetcher.

Audit events record actor, tenant/environment, authorization outcome, timestamp, correlation, changed record/version and reason without secret values. Append-only/tamper-evident storage design, backup and privileged access controls are Phase 2 decisions, with tamper and restore evidence in Phase 16. Global operational inhibition cannot grant discretionary tenant trading access.

| Data class | Proposed boundary | Deferred policy |
|---|---|---|
| Credentials | Revoke/delete encrypted secret when disconnected; preserve nonsecret lifecycle events | Key rotation schedule and custody in D-02 |
| Profile/preferences | Tenant export and erasable fields after authorization | Duration/identity verification in D-12 |
| Orders/fills/ledger/audit | Restricted access; retain required evidence and active holds; export own records | Required duration/jurisdiction and hold authority in D-12 |
| Raw market/features | Source license/provenance; separate from private data | Coverage/retention/training and redistribution rights in D-11 |
| Research datasets/models | Immutable provenance, consent/purpose and access records | Tenant deletion effects on datasets/trained artifacts in D-12 |

No numeric legal retention period or jurisdictional compliance is invented. D-12 must resolve before production tenant collection and retention promises. Active financial obligations do not disappear on profile deletion. Deletion results report retained categories/reasons and remove eligible personal fields without exposing other tenants. Shared model artifacts must not be represented as automatically erasable or legally exempt without the reviewed policy.
