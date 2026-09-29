//! Binance USDⓈ-M public-market normalization and deterministic recovery rules.
//! This module has no credential or order-routing capability.

use serde_json::Value;
use std::collections::BTreeMap;
use std::time::Duration;

pub const INTERVALS: &[&str] = &[
    "1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M",
];

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Instrument {
    pub symbol: String,
    pub status: String,
    pub eligible: bool,
    pub tick_size: String,
    pub step_size: String,
    pub onboard_time_ms: u64,
}

fn filter<'a>(filters: &'a [Value], kind: &str, field: &str) -> Option<&'a str> {
    filters
        .iter()
        .find(|f| f["filterType"] == kind)?
        .get(field)?
        .as_str()
}

pub fn normalize_instrument(v: &Value) -> Result<Instrument, &'static str> {
    let symbol = v["symbol"].as_str().ok_or("symbol")?;
    let status = v["status"].as_str().unwrap_or("UNKNOWN");
    let filters = v["filters"].as_array().ok_or("filters")?;
    Ok(Instrument {
        symbol: symbol.to_owned(),
        status: status.to_owned(),
        eligible: v["contractType"] == "PERPETUAL"
            && v["quoteAsset"] == "USDT"
            && v["marginAsset"] == "USDT"
            && status == "TRADING",
        tick_size: filter(filters, "PRICE_FILTER", "tickSize")
            .ok_or("tickSize")?
            .to_owned(),
        step_size: filter(filters, "LOT_SIZE", "stepSize")
            .ok_or("stepSize")?
            .to_owned(),
        onboard_time_ms: v["onboardDate"].as_u64().ok_or("onboardDate")?,
    })
}

pub fn validate_window(
    interval: &str,
    start_ms: u64,
    end_ms: u64,
    limit: usize,
) -> Result<(), &'static str> {
    if !INTERVALS.contains(&interval) || start_ms >= end_ms || limit == 0 || limit > 1500 {
        return Err("invalid candle window");
    }
    if end_ms - start_ms > 200 * 24 * 60 * 60 * 1000 {
        return Err("window exceeds Binance 200-day bound");
    }
    Ok(())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BookState {
    Syncing,
    Live,
    Invalid,
}

fn nonzero_quantity(raw: &str) -> bool {
    raw.bytes().any(|b| b.is_ascii_digit() && b != b'0')
}

fn positive_decimal_parts(raw: &str) -> Option<(String, String)> {
    if raw.is_empty()
        || !raw.bytes().all(|b| b.is_ascii_digit() || b == b'.')
        || raw.matches('.').count() > 1
    {
        return None;
    }
    let (whole, fraction) = raw.split_once('.').unwrap_or((raw, ""));
    let whole = whole.trim_start_matches('0');
    let whole = if whole.is_empty() { "0" } else { whole };
    Some((whole.to_owned(), fraction.trim_end_matches('0').to_owned()))
}

fn decimal_cmp(a: &str, b: &str) -> Option<std::cmp::Ordering> {
    let (aw, af) = positive_decimal_parts(a)?;
    let (bw, bf) = positive_decimal_parts(b)?;
    let whole = aw.len().cmp(&bw.len()).then_with(|| aw.cmp(&bw));
    let n = af.len().max(bf.len());
    Some(whole.then_with(|| {
        af.bytes()
            .chain(std::iter::repeat_n(b'0', n - af.len()))
            .cmp(bf.bytes().chain(std::iter::repeat_n(b'0', n - bf.len())))
    }))
}

#[derive(Debug, Clone)]
pub struct DepthDelta {
    pub first: u64,
    pub final_id: u64,
    pub previous: u64,
    pub bids: Vec<(String, String)>,
    pub asks: Vec<(String, String)>,
}

#[derive(Debug, Clone)]
pub struct LocalBook {
    pub state: BookState,
    pub last_update_id: u64,
    pub epoch: u64,
    pub bids: BTreeMap<String, String>,
    pub asks: BTreeMap<String, String>,
}

impl LocalBook {
    pub fn snapshot(
        last_update_id: u64,
        bids: Vec<(String, String)>,
        asks: Vec<(String, String)>,
        epoch: u64,
    ) -> Self {
        Self {
            state: BookState::Syncing,
            last_update_id,
            epoch,
            bids: bids.into_iter().collect(),
            asks: asks.into_iter().collect(),
        }
    }
    pub fn apply(&mut self, d: &DepthDelta, epoch: u64) -> Result<bool, &'static str> {
        if epoch != self.epoch {
            self.state = BookState::Invalid;
            return Err("stream epoch changed");
        }
        if d.final_id < self.last_update_id {
            return Ok(false);
        }
        if self.state == BookState::Syncing {
            if !(d.first <= self.last_update_id && d.final_id >= self.last_update_id) {
                return Ok(false);
            }
        } else if d.previous != self.last_update_id {
            self.state = BookState::Invalid;
            return Err("sequence gap");
        }
        for (p, q) in &d.bids {
            if !nonzero_quantity(q) {
                self.bids.remove(p);
            } else {
                self.bids.insert(p.clone(), q.clone());
            }
        }
        for (p, q) in &d.asks {
            if !nonzero_quantity(q) {
                self.asks.remove(p);
            } else {
                self.asks.insert(p.clone(), q.clone());
            }
        }
        self.last_update_id = d.final_id;
        self.state = BookState::Live;
        let best_bid = self
            .bids
            .keys()
            .max_by(|a, b| decimal_cmp(a, b).unwrap_or(std::cmp::Ordering::Equal));
        let best_ask = self
            .asks
            .keys()
            .min_by(|a, b| decimal_cmp(a, b).unwrap_or(std::cmp::Ordering::Equal));
        if matches!((best_bid,best_ask), (Some(b),Some(a)) if decimal_cmp(b,a).is_some_and(|v| v != std::cmp::Ordering::Less))
        {
            self.state = BookState::Invalid;
            return Err("crossed book");
        }
        Ok(true)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Retry {
    After(Duration),
    Ban(Duration),
    Permanent,
}
pub fn retry_policy(status: u16, retry_after_secs: Option<u64>, attempt: u32) -> Retry {
    match status {
        418 => Retry::Ban(Duration::from_secs(retry_after_secs.unwrap_or(120))),
        429 => Retry::After(Duration::from_secs(retry_after_secs.unwrap_or(1))),
        500..=599 => Retry::After(Duration::from_millis(
            (200u64.saturating_mul(1u64 << attempt.min(4))).min(3200),
        )),
        _ => Retry::Permanent,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    #[test]
    fn discovery_is_filter_driven_and_unknown_safe() {
        let v = json!({"symbol":"BTCUSDT","status":"TRADING","contractType":"PERPETUAL","quoteAsset":"USDT","marginAsset":"USDT","onboardDate":1,"pricePrecision":2,"filters":[{"filterType":"PRICE_FILTER","tickSize":"0.10"},{"filterType":"LOT_SIZE","stepSize":"0.001"},{"filterType":"NEW_FILTER","x":1}]});
        let i = normalize_instrument(&v).unwrap();
        assert!(i.eligible);
        assert_eq!(i.tick_size, "0.10");
        let mut suspended = v;
        suspended["status"] = json!("BREAK");
        assert!(!normalize_instrument(&suspended).unwrap().eligible);
    }
    #[test]
    fn bounded_candle_windows() {
        assert!(validate_window("1m", 1, 2, 1500).is_ok());
        assert!(validate_window("7m", 1, 2, 1).is_err());
        assert!(validate_window("1m", 0, 201 * 86_400_000, 1).is_err());
    }
    #[test]
    fn bridge_delete_duplicate_gap_epoch_and_cross() {
        let mut b = LocalBook::snapshot(
            100,
            vec![("99".into(), "2".into())],
            vec![("102".into(), "3".into())],
            7,
        );
        assert!(
            !b.apply(
                &DepthDelta {
                    first: 90,
                    final_id: 99,
                    previous: 0,
                    bids: vec![],
                    asks: vec![]
                },
                7
            )
            .unwrap()
        );
        assert!(
            b.apply(
                &DepthDelta {
                    first: 100,
                    final_id: 101,
                    previous: 0,
                    bids: vec![("99".into(), "0".into()), ("100".into(), "1".into())],
                    asks: vec![]
                },
                7
            )
            .unwrap()
        );
        assert!(!b.bids.contains_key("99"));
        assert!(
            !b.apply(
                &DepthDelta {
                    first: 100,
                    final_id: 100,
                    previous: 0,
                    bids: vec![],
                    asks: vec![]
                },
                7
            )
            .unwrap()
        );
        assert!(
            b.apply(
                &DepthDelta {
                    first: 103,
                    final_id: 103,
                    previous: 102,
                    bids: vec![],
                    asks: vec![]
                },
                7
            )
            .is_err()
        );
        assert_eq!(b.state, BookState::Invalid);
        let mut c = LocalBook::snapshot(1, vec![], vec![], 1);
        assert!(
            c.apply(
                &DepthDelta {
                    first: 2,
                    final_id: 2,
                    previous: 1,
                    bids: vec![],
                    asks: vec![]
                },
                2
            )
            .is_err()
        );
        let mut x = LocalBook::snapshot(
            1,
            vec![("101".into(), "1".into())],
            vec![("102".into(), "1".into())],
            1,
        );
        assert!(
            x.apply(
                &DepthDelta {
                    first: 1,
                    final_id: 2,
                    previous: 1,
                    bids: vec![],
                    asks: vec![("100".into(), "1".into())]
                },
                1
            )
            .is_err()
        );
    }
    #[test]
    fn rate_failures_back_off() {
        assert_eq!(
            retry_policy(429, Some(9), 0),
            Retry::After(Duration::from_secs(9))
        );
        assert_eq!(
            retry_policy(418, None, 0),
            Retry::Ban(Duration::from_secs(120))
        );
        assert_eq!(
            retry_policy(503, None, 3),
            Retry::After(Duration::from_millis(1600))
        );
    }
}
