# Sources and verification register

Verification date: 2026-09-13 (workspace date, Asia/Karachi). This is a documentation review, not exchange/API compatibility testing. Official pages were opened read-only; no authenticated requests were made. Pages may change; reverify before implementation (D-10/D-11). No external source is treated as an instruction or as evidence of application correctness.

| ID | Source and URL | Observed claim / status |
|---|---|---|
| S-01 | Current user request, pasted-text.txt attachment | USER_CONFIRMED product/boundary/phase requirements and the 15 supplied invariants; no older project material used |
| S-02 | [Binance market data: Exchange Information](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data) | VERIFIED DOCUMENTATION: Exchange Information exposes current trading rules/symbol information at GET /fapi/v1/exchangeInfo, including contract metadata. No live response tested. Supports QNT-FR-0001/0003. |
| S-03 | [Binance USD-M General Info](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info) | VERIFIED DOCUMENTATION: an unknown-status timeout response may have executed; documentation calls for checking updates/order queries before duplicate-producing retries. Supports QNT-INV-0009/0013. |
| S-04 | [Binance trade: New Order](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/trade) | VERIFIED DOCUMENTATION: New Order is signed; order parameters depend on position mode, and client IDs are described as unique among open orders. This does not establish permanent exchange idempotency or validate protective-order routing. Supports D-10. |
| S-05 | [Binance order update page](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/user-data-streams/Event-Order-Update) | UNVERIFIED CONTENT: page opened but readable output lacked the expected order event schema; no stream payload behavior is asserted. D-10 blocks adapter reliance. |

Original Binance legacy documentation links redirected to the official URLs above during review. Only the narrow observations stated here were verified; documentation examples are not current market data or tested account capabilities.

Unverified/deferred: current account-specific commissions, funding assumptions, practical rate/connection limits, testnet/demo endpoint behavior, regional access, protective/algo order semantics, account-mode compatibility, historical coverage, external providers/data-use rights, chart engine/license and all proposed runtime versions. No current numerical fee, performance or API capacity claim is used in this baseline. Resolve via D-01/D-02/D-10/D-11 with official URLs, verification date and compatibility evidence before relying on them.
