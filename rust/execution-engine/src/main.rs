use execution_engine::ExecutionEngineService;
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

    tracing::info!("Execution Engine Service starting...");

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

    // Production safety check
    if config.is_production() && config.is_paper_trading() {
        tracing::warn!("⚠️  Production environment with paper trading enabled!");
    }

    if config.is_production() && !config.is_paper_trading() {
        tracing::warn!("🔴 LIVE TRADING MODE - Real money at risk!");
        tracing::warn!("API URL: {}", config.execution.exchange_api_url);
    }

    // Create health status tracker
    let health = Arc::new(RwLock::new(HealthCheck::healthy("execution-engine")));

    // Start metrics server
    let metrics_config = MetricsConfig::execution_engine();
    let metrics_handle = match start_metrics_server(metrics_config) {
        Ok(handle) => {
            tracing::info!("✓ Metrics server started on port 9092");
            Some(handle)
        }
        Err(e) => {
            tracing::warn!("Failed to start metrics server: {}. Continuing without metrics.", e);
            None
        }
    };

    // Store values before move
    let is_paper_trading = config.is_paper_trading();
    let environment = config.environment();

    // Initialize service
    let _service = match ExecutionEngineService::new(config.execution).await {
        Ok(svc) => {
            tracing::info!("✓ Execution Engine initialized successfully");
            svc
        }
        Err(e) => {
            tracing::error!("Failed to initialize service: {}", e);
            let mut h = health.write().await;
            *h = HealthCheck::unhealthy("execution-engine", format!("Initialization failed: {}", e));
            return Err(anyhow::anyhow!("Service initialization error: {}", e));
        }
    };

    // Update health status
    {
        let mut h = health.write().await;
        *h = HealthCheck::healthy("execution-engine")
            .with_metric("status", "ready")
            .with_metric("paper_trading", is_paper_trading.to_string())
            .with_metric("environment", &environment);
    }

    tracing::info!("🚀 Execution Engine is ready");

    // Keep service running
    tokio::signal::ctrl_c().await?;
    tracing::info!("Shutdown signal received, stopping Execution Engine...");

    // Stop metrics server
    if let Some(handle) = metrics_handle {
        handle.abort();
        tracing::info!("Metrics server stopped");
    }

    Ok(())
}
