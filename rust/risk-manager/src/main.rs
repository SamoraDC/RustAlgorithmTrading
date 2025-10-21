use risk_manager::RiskManagerService;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};
use common::config::SystemConfig;
use common::health::HealthCheck;
use std::sync::Arc;
use tokio::sync::RwLock;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(fmt::layer())
        .with(EnvFilter::from_default_env())
        .init();

    tracing::info!("Risk Manager Service starting...");

    // Load configuration with validation
    let config = match SystemConfig::from_file("config/system.json") {
        Ok(cfg) => {
            tracing::info!(
                "Configuration loaded successfully - Environment: {}",
                cfg.environment()
            );
            cfg
        }
        Err(e) => {
            tracing::error!("Failed to load configuration: {}", e);
            return Err(anyhow::anyhow!("Configuration error: {}", e));
        }
    };

    // Log risk limits
    tracing::info!("Risk Limits:");
    tracing::info!("  Max Position Size: {}", config.risk.max_position_size);
    tracing::info!("  Max Notional Exposure: ${}", config.risk.max_notional_exposure);
    tracing::info!("  Max Open Positions: {}", config.risk.max_open_positions);
    tracing::info!("  Stop Loss: {}%", config.risk.stop_loss_percent);
    tracing::info!("  Trailing Stop: {}%", config.risk.trailing_stop_percent);
    tracing::info!("  Circuit Breaker: {}", if config.risk.enable_circuit_breaker { "ENABLED" } else { "DISABLED" });
    tracing::info!("  Max Loss Threshold: ${}", config.risk.max_loss_threshold);

    // Create health status tracker
    let health = Arc::new(RwLock::new(HealthCheck::healthy("risk-manager")));

    // Store values needed after moving config.risk
    let circuit_breaker_enabled = config.risk.enable_circuit_breaker;
    let max_positions = config.risk.max_open_positions;

    // Initialize service
    let _service = match RiskManagerService::new(config.risk) {
        Ok(svc) => {
            tracing::info!("✓ Risk Manager initialized successfully");
            svc
        }
        Err(e) => {
            tracing::error!("Failed to initialize service: {}", e);
            let mut h = health.write().await;
            *h = HealthCheck::unhealthy("risk-manager", format!("Initialization failed: {}", e));
            return Err(anyhow::anyhow!("Service initialization error: {}", e));
        }
    };

    // Update health status
    {
        let mut h = health.write().await;
        *h = HealthCheck::healthy("risk-manager")
            .with_metric("status", "monitoring")
            .with_metric("circuit_breaker", circuit_breaker_enabled.to_string())
            .with_metric("max_positions", max_positions.to_string());
    }

    tracing::info!("🚀 Risk Manager is monitoring");

    // Keep service running
    tokio::signal::ctrl_c().await?;
    tracing::info!("Shutdown signal received, stopping Risk Manager...");

    Ok(())
}
