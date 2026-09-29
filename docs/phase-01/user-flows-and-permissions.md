# User flows and permission contract

QNT-FR-0006–0012 and QNT-FR-0021 govern these boundaries. Proposed role granularity is an architecture input, pending D-02/D-12; server enforcement and tenant separation are confirmed requirements.

| Action | Tenant owner | Tenant trader | Tenant viewer | Platform admin | Model reviewer | Operations responder |
|---|---|---|---|---|---|---|
| View own authorized workspace/history | Yes | Yes | Yes | No by default | Deidentified model evidence only | Incident-scoped metadata only |
| Configure tenant keys/membership | Yes | No | No | No | No | No |
| Create/reset paper, start/pause/resume/stop authorized sessions | Yes | Yes | No | No | No | Safety inhibit only |
| Activate LIVE | Yes, explicit gate-checked action | No by default | No | No | No | No |
| Export/delete tenant data | Owner, subject to holds | No | No | No implicit access | No | No |
| Manage platform provider keys/ceilings | No | No | No | Yes, audited | No | No |
| Propose/train candidate | No | No | No implicit promotion | No implicit promotion | Assigned research authority | No |
| Approve model promotion | No | No | No implicit approval | No implicit approval | Independent reviewer, all gates | No |
| Global entry inhibit | No | No | No | Yes | No | Yes, audited |

Safety inhibition is not discretionary trading authority. Responders cannot open positions or browse plaintext keys. Managed closure follows previously authorized session policy. Any exceptional access is time-limited, justified, audited and scoped; no default impersonation capability.

Flow: owner creates tenant -> invites role-limited users -> opens paper account without Binance credentials -> sets bounded session config -> runs simulated session -> reviews labelled outcomes. Live requires separately adding/testing a LIVE integration, verified account identity, gates, and an explicit owner activation. Switching a visible mode tab never changes execution authority.

Integrations: owner selects supported provider/environment -> submits credentials over protected channel -> server encrypts and stores versioned metadata -> safe connection test returns permissions/health only -> UI masks values. Replace follows exposure-aware handover; revoke/disconnect inhibits entries immediately and reports residual obligations. If requested removal cannot safely complete while credentials are usable, preserve the protected close workflow until flat; if access is already lost or owner insists on immediate disconnection, remove access but retain recovery records and an explicit owner manual-intervention obligation. Never secretly keep using revoked authorization or claim a remote position is closed. Removing a local key does not assert exchange-side revocation was performed.

Every endpoint, stream, job and object link checks resolved tenant, role, account and environment, not a caller-supplied tenant ID. Public market data is shared only when its license permits it; private fills/configuration are not shared forecasting evidence by default.
