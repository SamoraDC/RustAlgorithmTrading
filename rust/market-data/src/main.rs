use market_data::MarketDataService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;
use common::health::HealthCheck;
use common::metrics::{MetricsConfig, start_metrics_server};
use std::sync::Arc;
use tokio::sync::RwLock;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Market Data Service starting...");

    // Load configuration with validation
    let config = match SystemConfig::from_file("config/system.json") {
        Ok(cfg) => {
            tracing::info!(
                "Configuration loaded successfully - Environment: {}, Paper Trading: {}",
                cfg.environment(),
                cfg.is_paper_trading()
            );
            cfg
        }
        Err(e) => {
            tracing::error!("Failed to load configuration: {}", e);
            return Err(anyhow::anyhow!("Configuration error: {}", e));
        }
    };

    // Validate we're in the correct environment
    if config.is_production() && config.is_paper_trading() {
        tracing::warn!("⚠️  Production environment with paper trading enabled - this may be unintended!");
    }

    // Create health status tracker
    let health = Arc::new(RwLock::new(HealthCheck::healthy("market-data")));

    // Start metrics server
    let metrics_config = MetricsConfig::market_data();
    let metrics_handle = match start_metrics_server(metrics_config) {
        Ok(handle) => {
            tracing::info!("✓ Metrics server started on port 9091");
            Some(handle)
        }
        Err(e) => {
            tracing::warn!("Failed to start metrics server: {}. Continuing without metrics.", e);
            None
        }
    };

    // Store values before move
    let symbols_count = config.market_data.symbols.len();

    // Initialize service
    let mut service = match MarketDataService::new(config.market_data).await {
        Ok(svc) => {
            tracing::info!("✓ Market Data Service initialized successfully");
            svc
        }
        Err(e) => {
            tracing::error!("Failed to initialize service: {}", e);
            let mut h = health.write().await;
            *h = HealthCheck::unhealthy("market-data", format!("Initialization failed: {}", e));
            return Err(anyhow::anyhow!("Service initialization error: {}", e));
        }
    };

    // Update health status
    {
        let mut h = health.write().await;
        *h = HealthCheck::healthy("market-data")
            .with_metric("status", "running")
            .with_metric("symbols", symbols_count.to_string());
    }

    tracing::info!("🚀 Market Data Service is running");

    // Run service with error handling
    let result = match service.run().await {
        Ok(_) => {
            tracing::info!("Market Data Service stopped gracefully");
            Ok(())
        }
        Err(e) => {
            tracing::error!("Service error: {}", e);
            let mut h = health.write().await;
            *h = HealthCheck::unhealthy("market-data", format!("Service error: {}", e));
            Err(anyhow::anyhow!("Service error: {}", e))
        }
    };

    // Stop metrics server
    if let Some(handle) = metrics_handle {
        handle.abort();
        tracing::info!("Metrics server stopped");
    }

    result
}
