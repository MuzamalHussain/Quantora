# State machines and accounting

These proposed detailed conventions implement QNT-FR-0025–0037 and QNT-INV-0001–0014; D-08/D-13 must approve production defaults before Phase 9 release. An event records before/after state, guard, actor, reason, time, environment, epoch and configuration version. Transition guards are checked again at dispatch. Unknown state never implies zero exposure.

## Session state

| Current/event | Guard and resulting state | Actions |
|---|---|---|
| DRAFT / start | Authorized, allocation/risk config valid -> PREFLIGHT | Validate mode, credentials when needed, model/input/risk budgets and account ownership |
| PREFLIGHT / checks pass | Reconciled account, no unknown intents -> RUNNING | Start admission; persist starting equity/config |
| PREFLIGHT / checks fail | -> BLOCKED | Show reasons; no dispatch |
| RUNNING / pause | -> PAUSED_PROTECTED | Cancel entries; keep risk monitoring, exits and protective orders |
| PAUSED_PROTECTED / resume | Deadline/target latch absent -> PREFLIGHT | Revalidate current state; original deadline is unchanged |
| RUNNING or PAUSED_PROTECTED / stop, target, deadline | -> STOPPING | Latch no-new-entry, cancel entries, close confirmed exposure and reconcile late fills |
| PREFLIGHT, BLOCKED or RECOVERING / stop or deadline; valid fresh target event where equity is attributable | Preserve RECOVERING if state is unresolved; otherwise -> STOPPING | Persist termination latch even during outage/restart; no later preflight may reopen admission; cancel/close only when safe authority and state permit |
| Any active state / emergency stop or hard breach | -> EMERGENCY_RECOVERY | Persist safety latch, cancel entries, prioritized safe reduction; alert on inability |
| Any active state / lost data, credentials, process or authority | -> RECOVERING | Inhibit entries, retain/check protection; reconcile and alert |
| RECOVERING / verified consistent | Emergency latch -> EMERGENCY_RECOVERY; otherwise termination latch -> STOPPING; otherwise -> PAUSED_PROTECTED | Never silently resume entry after incident |
| STOPPING or EMERGENCY_RECOVERY / reconciled flat and settled | -> COMPLETED | Confirm zero position, no executable entries/protection remnants/unknown intents; settle ledger |
| BLOCKED / corrected config | -> PREFLIGHT on authorized restart | No silent bypass |

Emergency latch needs authorized acknowledgement plus preflight before a new session. Terminal history never reopens: a restart after completion uses a new session ID/epoch. Recovery can continue indefinitely during an external outage; RTO measures restoration of our safe management capability, not guaranteed exchange closure. UI must expose residual/unknown exposure and the owner's next action.

The deadline uses the persisted absolute session time and continues during pause, preflight, blocked operation and recovery. Restart checks whether it has already elapsed before admission. A stale equity mark cannot newly trigger a profit target, but an already persisted target/stop/deadline latch survives restart. An emergency latch also survives ordinary RECOVERING transitions: verified recovery returns to EMERGENCY_RECOVERY until closure is reconciled, not to PAUSED_PROTECTED or RUNNING.

Priority: reconcile uncertain state sufficiently for safe action; then emergency/hard limits/invalid position exit; then target/deadline/stop termination; then protection, reduction and take-profit; then hold; finally new entry. Reconciliation is not a reason to disable known valid protective orders. Target/deadline termination cannot be undone by a later falling mark. A partial late entry fill after cancellation is exposure to protect/close, never a new session strategy opportunity.

## Position/action state

FLAT -> OPENING only after independent edge, risk reservation and durable intent. Fill quantity > 0 -> OPEN (possibly with entry remainder pending). HOLD keeps valid exposure and protection; REDUCE and TAKE_PROFIT enter REDUCING with residual protected. CLOSE enters CLOSING. Partial closing fills reduce known quantity; FLAT is recorded only after reconciliation confirms zero. Unknown quantity -> RECONCILING, never FLAT by assumption. Dust below normal filters invokes verified venue close semantics/manual recovery (D-10); never increase size solely to permit a close.

REVERSE is a two-stage workflow, not a single opposite oversized order: request CLOSE -> reconcile flat and no old executable entry -> compute fresh opposite opportunity/costs/risk -> OPENING if approved, otherwise FLAT. Failed/partial first leg keeps old residual protection; rejected second leg stays flat; partial second leg protects only newly confirmed quantity. An invalid SHORT with +1 unrealized P&L and 1.20 total estimated reversal cost still requires independent exit evaluation. Aggregate reversal cost cannot veto an invalid-position exit or substitute for a separate estimate of opposite entry edge.

## Order state and durable intent

PROPOSED -> RESERVED -> INTENT_DURABLE -> SUBMITTING -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED. Guards can reject before dispatch, releasing the reservation. A definitive venue rejection -> REJECTED. Cancellation request -> CANCEL_PENDING, not CANCELED until confirmed. Partial execution may precede CANCELED/EXPIRED; executed quantity remains real. A timeout at any remote boundary -> UNKNOWN -> RECONCILING -> observed state. A late fill after apparent terminal status corrects the ledger/exposure through a deduplicated reconciliation event; never discard it solely because local state was terminal.

Durably commit intent/client identity/reservation before dispatch. Recovery checks orders/trades/positions and request identity before retries. A local transaction cannot roll back remote execution. Client IDs remain locally unique across completed as well as open orders; exchange identifier retention/lookup guarantees require D-10 verification. If absence cannot be established conclusively, retain UNKNOWN, reservation and alert. Cancel/replace protection verifies new protection before removing old when venue semantics safely allow it; otherwise use a documented guarded reduction/recovery route. No unverified atomic stop replacement assumption.

One fenced coordinator per account/environment serializes risk reservations across sessions. Reserve against filled plus possible pending exposure; release only on conclusive failure/cancel/fill reconciliation. A stale lease holder cannot dispatch. Manual/unattributed positions are included conservatively in account risk but not silently adopted as session profit or discretionary closure authority. Entry freeze remains until ownership and settings are reconciled.

## Accounting definitions

All quantities/currency use declared fixed-decimal precision and versioned contract units (D-02); illustrative numbers below are fixtures, not market data. Let E0 be allocated opening equity, CF(t) signed net external contributions after start (deposits positive, withdrawals negative), R(t) fill-price realized P&L, U(t) marked unrealized P&L, F(t) explicit fees paid and G(t) signed funding receipts. Then E(t)=E0+CF(t)+R(t)+U(t)-F(t)+G(t), with separately attributed reconciliation adjustments when supported by evidence. A capital reallocation is an external flow, not profit.

TargetProgress(t)=E(t)-E0-CF(t)-Cclose(t), where Cclose is incremental expected closing fees and adverse price impact relative to the valuation mark, including expected funding until closure if material. Do not subtract historical entry costs again. If valuation already uses executable exit bid/ask, do not add that spread again. Mark source/time and valuation convention are part of every snapshot; stale/unattributable equity cannot newly trigger a performance target. Hard-risk/deadline exits still apply. Percentage target uses fixed E0 as denominator under the proposed convention; changing allocation requires recorded flow and reapproved config, never a reset of drawdown history.

Realized trade P&L uses actual entry/exit fills. Spread/slippage measured against a reference price are attribution metrics, not another debit. Gross fill P&L +1.00, fees 1.10 and funding paid 0.10 gives net -0.20. Direction can be correct while net performance is negative. Initial 1000 plus external deposit 100 with zero trading result gives zero target progress before incremental close costs, not +100 profit.

Closing target evaluation can differ from final realized result due to later fills/costs; final result equals reconciled realized P&L minus fees plus funding and evidenced adjustments after flat settlement. Account equity is not duplicated across sessions: allocation and every fill/flow have exclusive attribution keys, and shared account totals cap all sessions. Unknown account activity blocks definitive session-performance claims. Fill IDs are deduplicated by venue/account/environment/trade identity; funding/fees use their own transaction identity. Corrections append adjusting records rather than erasing history.
