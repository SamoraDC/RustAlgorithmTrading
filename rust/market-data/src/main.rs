use market_data::MarketDataService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Market Data Service starting...");

    // Load configuration
    let config = SystemConfig::from_file("config/system.json")?;

    // Initialize service
    let mut service = MarketDataService::new(config.market_data).await?;

    // Run service
    service.run().await?;

    Ok(())
}
