use signal_bridge::SignalBridgeService;
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

    tracing::info!("Signal Bridge Service starting...");

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

    // Log signal configuration
    tracing::info!("Signal Configuration:");
    tracing::info!("  Model Path: {}", config.signal.model_path);
    tracing::info!("  Features: {:?}", config.signal.features);
    tracing::info!("  Update Interval: {}ms", config.signal.update_interval_ms);
    tracing::info!("  ZMQ Subscribe: {}", config.signal.zmq_subscribe_address);
    tracing::info!("  ZMQ Publish: {}", config.signal.zmq_publish_address);

    // Create health status tracker
    let health = Arc::new(RwLock::new(HealthCheck::healthy("signal-bridge")));

    // Store values before move
    let features_count = config.signal.features.len();

    // Initialize service
    let _service = match SignalBridgeService::new(config.signal) {
        Ok(svc) => {
            tracing::info!("✓ Signal Bridge initialized successfully");
            svc
        }
        Err(e) => {
            tracing::error!("Failed to initialize service: {}", e);
            let mut h = health.write().await;
            *h = HealthCheck::unhealthy("signal-bridge", format!("Initialization failed: {}", e));
            return Err(anyhow::anyhow!("Service initialization error: {}", e));
        }
    };

    // Update health status
    {
        let mut h = health.write().await;
        *h = HealthCheck::healthy("signal-bridge")
            .with_metric("status", "ready")
            .with_metric("features_count", features_count.to_string())
            .with_message("Ready for Python ML integration");
    }

    tracing::info!("🚀 Signal Bridge ready for Python integration");

    // Keep service running
    tokio::signal::ctrl_c().await?;
    tracing::info!("Shutdown signal received, stopping Signal Bridge...");

    Ok(())
}
