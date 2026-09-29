use axum::{
    Json, Router,
    body::{Body, to_bytes},
    extract::{Request, State},
    http::{HeaderValue, StatusCode},
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::{get, post},
};
use serde_json::{Value, json};
use std::{
    net::SocketAddr,
    sync::{Arc, OnceLock},
    time::{Duration, SystemTime, UNIX_EPOCH},
};
use tokio::sync::{Semaphore, mpsc, oneshot};
use uuid::Uuid;

pub mod market;

pub const SCHEMA: &str = include_str!("../../../contracts/foundation-v1.schema.json");
static VALIDATOR: OnceLock<jsonschema::Validator> = OnceLock::new();

pub fn valid_contract(value: &Value) -> bool {
    VALIDATOR
        .get_or_init(|| {
            jsonschema::validator_for(&serde_json::from_str(SCHEMA).expect("schema JSON"))
                .expect("schema compiles")
        })
        .is_valid(value)
}

#[derive(Clone)]
pub struct Config {
    pub bind: SocketAddr,
    pub mode: String,
}

impl Config {
    pub fn parse(bind: &str, mode: &str) -> Result<Self, &'static str> {
        let bind: SocketAddr = bind.parse().map_err(|_| "invalid core bind")?;
        if !bind.ip().is_loopback() || bind.port() == 0 {
            return Err("core must bind loopback on a nonzero port");
        }
        if !["PAPER", "SHADOW", "TESTNET", "REPLAY"].contains(&mode) {
            return Err("mode is invalid or not enabled in foundation");
        }
        Ok(Self {
            bind,
            mode: mode.to_owned(),
        })
    }
}

pub fn envelope(mode: &str, cid: &str, event_type: &str, payload: Value) -> Value {
    let value = json!({"schema_version":"1.0.0", "event_id":Uuid::new_v4().to_string(),
        "correlation_id":cid, "occurred_at_ms":SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() as u64,
        "mode":mode, "source":{"kind":"FOUNDATION","name":"trading-core"}, "event_type":event_type,"payload":payload});
    debug_assert!(valid_contract(&value));
    value
}

fn health(mode: &str, cid: &str, ready: bool) -> Value {
    envelope(
        mode,
        cid,
        "HEALTH",
        json!({"service":"trading-core", "status":if ready {"READY"} else {"UP"},
        "profile":"FOUNDATION", "trading_enabled":false,
        "dependencies":{"core":"NOT_REQUIRED","mongodb":"NOT_REQUIRED","redis":"NOT_REQUIRED"}}),
    )
}

fn error(mode: &str, cid: &str, status: StatusCode, code: &str, message: &str) -> Response {
    (
        status,
        Json(envelope(
            mode,
            cid,
            "ERROR",
            json!({"code":code,"message":message}),
        )),
    )
        .into_response()
}

/// Logs deliberately accept only an internal event name, validated UUID and numeric result.
/// No URL, query, body, header, configuration or exception is logged.
pub fn log_event(event: &str, cid: &str, status: u16) -> String {
    let safe_event = match event {
        "started" | "shutdown" | "request" | "worker_stopped" => event,
        _ => "internal",
    };
    let safe_id = Uuid::parse_str(cid).ok().map(|v| v.to_string());
    json!({"service":"trading-core","event":safe_event,"correlation_id":safe_id,"status":status,
        "occurred_at_ms":SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() as u64})
        .to_string()
}

#[derive(Clone)]
pub struct AppState {
    mode: String,
    queue: mpsc::Sender<oneshot::Sender<()>>,
    slots: Arc<Semaphore>,
}

pub fn app(mode: String) -> (Router, tokio::task::JoinHandle<()>) {
    let (tx, mut rx) = mpsc::channel::<oneshot::Sender<()>>(32);
    let worker = tokio::spawn(async move {
        while let Some(reply) = rx.recv().await {
            let _ = reply.send(());
        }
        println!("{}", log_event("worker_stopped", "", 0));
    });
    let state = AppState {
        mode,
        queue: tx,
        slots: Arc::new(Semaphore::new(32)),
    };
    let router = Router::new()
        .route("/health/live", get(live))
        .route("/health/ready", get(ready))
        .route("/api/v1/foundation/ping", post(ping))
        .fallback(not_found)
        .method_not_allowed_fallback(method_not_allowed)
        .layer(middleware::from_fn_with_state(state.clone(), boundary))
        .with_state(state);
    (router, worker)
}

async fn boundary(State(s): State<AppState>, mut req: Request, next: Next) -> Response {
    let cid = req
        .headers()
        .get("x-request-id")
        .and_then(|h| h.to_str().ok())
        .filter(|v| v.len() == 36)
        .and_then(|v| Uuid::parse_str(v).ok())
        .filter(|v| v.get_version_num() == 4)
        .unwrap_or_else(Uuid::new_v4)
        .to_string();
    req.extensions_mut().insert(cid.clone());
    let start = std::time::Instant::now();
    let mut response = if let Ok(_permit) = s.slots.clone().try_acquire_owned() {
        let (parts, body) = req.into_parts();
        match tokio::time::timeout(Duration::from_secs(2), to_bytes(body, 4096)).await {
            Ok(Ok(bytes)) => match tokio::time::timeout(
                Duration::from_secs(2),
                next.run(Request::from_parts(parts, Body::from(bytes))),
            )
            .await
            {
                Ok(response) => response,
                Err(_) => error(
                    &s.mode,
                    &cid,
                    StatusCode::GATEWAY_TIMEOUT,
                    "TIMEOUT",
                    "Request timed out",
                ),
            },
            Ok(Err(_)) => error(
                &s.mode,
                &cid,
                StatusCode::PAYLOAD_TOO_LARGE,
                "TOO_LARGE",
                "Request exceeds limit",
            ),
            Err(_) => error(
                &s.mode,
                &cid,
                StatusCode::GATEWAY_TIMEOUT,
                "TIMEOUT",
                "Request timed out",
            ),
        }
    } else {
        error(
            &s.mode,
            &cid,
            StatusCode::SERVICE_UNAVAILABLE,
            "OVERLOADED",
            "Service is busy",
        )
    };
    response.headers_mut().insert(
        "x-request-id",
        HeaderValue::from_str(&cid).expect("UUID header"),
    );
    response
        .headers_mut()
        .insert("cache-control", HeaderValue::from_static("no-store"));
    response.headers_mut().insert(
        "x-content-type-options",
        HeaderValue::from_static("nosniff"),
    );
    let mut record: Value =
        serde_json::from_str(&log_event("request", &cid, response.status().as_u16()))
            .expect("log JSON");
    record["duration_ms"] = json!(start.elapsed().as_secs_f64() * 1000.0);
    println!("{record}");
    response
}

async fn live(
    State(s): State<AppState>,
    axum::Extension(cid): axum::Extension<String>,
) -> Json<Value> {
    Json(health(&s.mode, &cid, false))
}
async fn ready(
    State(s): State<AppState>,
    axum::Extension(cid): axum::Extension<String>,
) -> Response {
    if s.queue.is_closed() {
        return error(
            &s.mode,
            &cid,
            StatusCode::SERVICE_UNAVAILABLE,
            "NOT_READY",
            "Dependencies unavailable",
        );
    }
    Json(health(&s.mode, &cid, true)).into_response()
}
async fn ping(
    State(s): State<AppState>,
    axum::Extension(cid): axum::Extension<String>,
    body: axum::body::Bytes,
) -> Response {
    let parsed = serde_json::from_slice::<Value>(&body);
    if !parsed
        .as_ref()
        .is_ok_and(|v| valid_contract(v) && v["event_type"] == "PING" && v["mode"] == s.mode)
    {
        return error(
            &s.mode,
            &cid,
            StatusCode::BAD_REQUEST,
            "INVALID_REQUEST",
            "Request rejected",
        );
    }
    let (tx, rx) = oneshot::channel();
    if s.queue.try_send(tx).is_err() {
        return error(
            &s.mode,
            &cid,
            StatusCode::SERVICE_UNAVAILABLE,
            "OVERLOADED",
            "Service is busy",
        );
    }
    match tokio::time::timeout(Duration::from_millis(500), rx).await {
        Ok(Ok(())) => Json(health(&s.mode, &cid, true)).into_response(),
        _ => error(
            &s.mode,
            &cid,
            StatusCode::SERVICE_UNAVAILABLE,
            "NOT_READY",
            "Dependencies unavailable",
        ),
    }
}
async fn not_found(
    State(s): State<AppState>,
    axum::Extension(cid): axum::Extension<String>,
) -> Response {
    error(
        &s.mode,
        &cid,
        StatusCode::NOT_FOUND,
        "NOT_FOUND",
        "Route is unavailable",
    )
}
async fn method_not_allowed(
    State(s): State<AppState>,
    axum::Extension(cid): axum::Extension<String>,
) -> Response {
    error(
        &s.mode,
        &cid,
        StatusCode::METHOD_NOT_ALLOWED,
        "METHOD_NOT_ALLOWED",
        "Method is unavailable",
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use tower::ServiceExt;
    #[test]
    fn contract_fixtures() {
        let cases: Vec<Value> =
            serde_json::from_str(include_str!("../../../contracts/fixtures.json")).unwrap();
        for case in cases {
            assert_eq!(
                valid_contract(&case["value"]),
                case["valid"].as_bool().unwrap(),
                "{}",
                case["name"]
            );
        }
    }
    #[test]
    fn config_and_logs() {
        for mode in ["LIVE", "AUTO", "paper", ""] {
            assert!(Config::parse("127.0.0.1:8101", mode).is_err());
        }
        assert!(Config::parse("0.0.0.0:8101", "PAPER").is_err());
        assert!(
            !log_event("secret=SYNTHETIC_SENTINEL", "SYNTHETIC_SENTINEL", 400)
                .contains("SYNTHETIC_SENTINEL")
        );
    }
    #[tokio::test]
    async fn route_boundaries() {
        let (router, worker) = app("PAPER".into());
        for (method, path, body, expected) in [
            ("GET", "/health/ready", String::new(), 200),
            ("POST", "/orders", "SYNTHETIC_SENTINEL".into(), 404),
            ("POST", "/health/live", String::new(), 405),
            ("POST", "/api/v1/foundation/ping", "x".repeat(4097), 413),
            (
                "POST",
                "/api/v1/foundation/ping",
                "{\"bad\":\"SYNTHETIC_SENTINEL\"}".into(),
                400,
            ),
        ] {
            let response = router
                .clone()
                .oneshot(
                    Request::builder()
                        .method(method)
                        .uri(path)
                        .body(Body::from(body))
                        .unwrap(),
                )
                .await
                .unwrap();
            assert_eq!(response.status().as_u16(), expected);
            let bytes = to_bytes(response.into_body(), 10000).await.unwrap();
            let text = String::from_utf8(bytes.to_vec()).unwrap();
            assert!(!text.contains("SYNTHETIC_SENTINEL"));
            assert!(valid_contract(&serde_json::from_str(&text).unwrap()));
        }
        drop(router);
        worker.await.unwrap();
    }
    #[tokio::test]
    async fn bounded_queue_rejects_full() {
        let (tx, _rx) = mpsc::channel::<oneshot::Sender<()>>(1);
        let (a, _) = oneshot::channel();
        let (b, _) = oneshot::channel();
        tx.try_send(a).unwrap();
        assert!(tx.try_send(b).is_err());
    }
}
