use quantora_core::{Config, app, log_event};

async fn shutdown_signal() {
    #[cfg(unix)]
    {
        let mut term = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("signal registration");
        tokio::select! { _=tokio::signal::ctrl_c()=>{}, _=term.recv()=>{} }
    }
    #[cfg(windows)]
    {
        let mut stop = tokio::signal::windows::ctrl_break().expect("signal registration");
        tokio::select! { _=tokio::signal::ctrl_c()=>{}, _=stop.recv()=>{} }
    }
    println!("{}", log_event("shutdown", "", 0));
}

#[tokio::main]
async fn main() {
    let config = Config::parse(
        &std::env::var("QUANTORA_CORE_BIND").unwrap_or("127.0.0.1:8101".into()),
        &std::env::var("QUANTORA_MODE").unwrap_or("PAPER".into()),
    );
    let config = match config {
        Ok(v) => v,
        Err(_) => {
            eprintln!("{{\"event\":\"invalid_configuration\"}}");
            std::process::exit(2)
        }
    };
    let listener = match tokio::net::TcpListener::bind(config.bind).await {
        Ok(v) => v,
        Err(_) => {
            eprintln!("{{\"event\":\"bind_failed\"}}");
            std::process::exit(2)
        }
    };
    let (router, worker) = app(config.mode);
    println!("{}", log_event("started", "", 0));
    if axum::serve(listener, router)
        .with_graceful_shutdown(shutdown_signal())
        .await
        .is_err()
    {
        eprintln!("{{\"event\":\"serve_failed\"}}");
        std::process::exit(1)
    }
    if tokio::time::timeout(std::time::Duration::from_secs(5), worker)
        .await
        .is_err()
    {
        std::process::exit(1)
    }
}
