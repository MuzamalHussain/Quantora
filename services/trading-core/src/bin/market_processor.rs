//! Stateful public-market normalizer. The Python collector transports and persists its output.
use quantora_core::market::{BookState, DepthDelta, LocalBook, normalize_instrument};
use serde_json::{Value, json};
use std::io::{self, BufRead, Write};

fn text<'a>(v: &'a Value, key: &str) -> Result<&'a str, &'static str> {
    v.get(key)
        .and_then(Value::as_str)
        .ok_or("missing string field")
}
fn number(v: &Value, key: &str) -> Result<u64, &'static str> {
    v.get(key)
        .and_then(Value::as_u64)
        .ok_or("missing integer field")
}
fn levels(v: &Value) -> Result<Vec<(String, String)>, &'static str> {
    v.as_array()
        .ok_or("missing levels")?
        .iter()
        .map(|row| {
            let pair = row.as_array().ok_or("invalid level")?;
            let price = pair
                .first()
                .and_then(Value::as_str)
                .ok_or("invalid price")?;
            let quantity = pair
                .get(1)
                .and_then(Value::as_str)
                .ok_or("invalid quantity")?;
            if decimal_parts(price).is_none()
                || !price.bytes().any(|b| b.is_ascii_digit() && b != b'0')
                || decimal_parts(quantity).is_none()
            {
                return Err("invalid decimal level");
            }
            Ok((price.to_owned(), quantity.to_owned()))
        })
        .collect()
}
fn decimal_parts(raw: &str) -> Option<(&str, &str)> {
    if raw.is_empty()
        || !raw.bytes().all(|b| b.is_ascii_digit() || b == b'.')
        || raw.matches('.').count() > 1
        || !raw.bytes().any(|b| b.is_ascii_digit())
    {
        return None;
    }
    Some(raw.split_once('.').unwrap_or((raw, "")))
}
fn decimal_cmp(a: &str, b: &str) -> std::cmp::Ordering {
    let (ai, af) = decimal_parts(a).unwrap_or(("", ""));
    let (bi, bf) = decimal_parts(b).unwrap_or(("", ""));
    let ai = ai.trim_start_matches('0');
    let bi = bi.trim_start_matches('0');
    let ai = if ai.is_empty() { "0" } else { ai };
    let bi = if bi.is_empty() { "0" } else { bi };
    let whole = ai.len().cmp(&bi.len()).then_with(|| ai.cmp(bi));
    let n = af.len().max(bf.len());
    whole.then_with(|| {
        af.bytes()
            .chain(std::iter::repeat_n(b'0', n - af.len()))
            .cmp(bf.bytes().chain(std::iter::repeat_n(b'0', n - bf.len())))
    })
}
fn book_view(book: &LocalBook, applied: bool) -> Value {
    let bid = book.bids.keys().max_by(|a, b| decimal_cmp(a, b));
    let ask = book.asks.keys().min_by(|a, b| decimal_cmp(a, b));
    json!({"ok":true,"applied":applied,"valid":book.state==BookState::Live && bid.is_some() && ask.is_some(),"last_update_id":book.last_update_id,"bid_levels":book.bids.len(),"ask_levels":book.asks.len(),"best_bid":bid,"best_ask":ask})
}
fn process(req: &Value, book: &mut Option<LocalBook>) -> Result<Value, &'static str> {
    let value = &req["value"];
    match text(req, "op")? {
        "instrument" => {
            let normalized = normalize_instrument(value)?;
            Ok(
                json!({"ok":true,"symbol":normalized.symbol,"status":normalized.status,"eligible":normalized.eligible,"tick_size":normalized.tick_size,"step_size":normalized.step_size,"onboard_time_ms":normalized.onboard_time_ms}),
            )
        }
        "book_snapshot" => {
            let state = LocalBook::snapshot(
                number(value, "lastUpdateId")?,
                levels(&value["bids"])?,
                levels(&value["asks"])?,
                number(req, "epoch")?,
            );
            *book = Some(state);
            Ok(json!({"ok":true,"state":"SYNCING"}))
        }
        "book_delta" => {
            let current = book.as_mut().ok_or("snapshot required")?;
            let delta = DepthDelta {
                first: number(value, "U")?,
                final_id: number(value, "u")?,
                previous: number(value, "pu")?,
                bids: levels(&value["b"])?,
                asks: levels(&value["a"])?,
            };
            let applied = current.apply(&delta, number(req, "epoch")?)?;
            Ok(book_view(current, applied))
        }
        "kline" => {
            let k = &value["k"];
            Ok(
                json!({"ok":true,"symbol":text(value,"s")?,"interval":text(k,"i")?,"open_time_ms":number(k,"t")?,"close_time_ms":number(k,"T")?,"open":text(k,"o")?,"high":text(k,"h")?,"low":text(k,"l")?,"close":text(k,"c")?,"volume":text(k,"v")?,"closed":k["x"].as_bool().ok_or("missing candle closure")?}),
            )
        }
        "mark" => Ok(
            json!({"ok":true,"symbol":text(value,"s")?,"source_time_ms":number(value,"E")?,"mark_price":text(value,"p")?,"index_price":text(value,"i")?,"estimated_funding_rate":text(value,"r")?,"next_funding_time_ms":number(value,"T")?}),
        ),
        "agg_trade" => Ok(
            json!({"ok":true,"symbol":text(value,"s")?,"source_time_ms":number(value,"T")?,"aggregate_trade_id":number(value,"a")?,"price":text(value,"p")?,"quantity":text(value,"q")?,"semantics":"AGGREGATE_TRADE"}),
        ),
        _ => Err("unsupported operation"),
    }
}
fn main() {
    let stdin = io::stdin();
    let mut output = io::stdout().lock();
    let mut book = None;
    for line in stdin.lock().lines() {
        let Ok(line) = line else { break };
        let result = if line.len() > 1_000_000 {
            json!({"ok":false,"error":"input too large"})
        } else {
            match serde_json::from_str::<Value>(&line) {
                Ok(req) => process(&req, &mut book)
                    .unwrap_or_else(|error| json!({"ok":false,"error":error})),
                Err(_) => json!({"ok":false,"error":"invalid JSON"}),
            }
        };
        if writeln!(output, "{result}").is_err() || output.flush().is_err() {
            break;
        }
    }
}
