# Local order-book synchronization

Each reconnect creates a new epoch. Depth events are buffered with a fixed cap while `GET /fapi/v1/depth` is acquired. Events with `u < lastUpdateId` are discarded. The first applicable event must cover `U <= lastUpdateId <= u`; later events must satisfy `pu == previous u`. Quantities are absolute; zero removes a level. Duplicate/obsolete events are ignored.

Any gap, epoch mismatch, buffer overflow, malformed decimal, crossed book or invalid side immediately sets `INVALID`, suppresses publication, clears the epoch buffer and requires a new snapshot bridge. A valid bridged partial book is labelled with its snapshot depth and is not declared execution-ready.

