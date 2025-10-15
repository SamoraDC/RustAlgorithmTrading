use signal_bridge::SignalBridgeService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Signal Bridge Service starting...");

    // Load configuration
    let config = SystemConfig::from_file("config/system.json")?;

    // Initialize service
    let _service = SignalBridgeService::new(config.signal)?;

    tracing::info!("Signal Bridge ready for Python integration");

    Ok(())
}
