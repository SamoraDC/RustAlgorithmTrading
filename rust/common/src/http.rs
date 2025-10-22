/// HTTP health check and monitoring endpoints
use crate::health::HealthCheck;
use crate::Result;
use axum::{
    extract::State,
    http::StatusCode,
    routing::get,
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;

#[derive(Debug, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub component: String,
    pub message: Option<String>,
    pub metrics: std::collections::HashMap<String, String>,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

impl From<HealthCheck> for HealthResponse {
    fn from(health: HealthCheck) -> Self {
        Self {
            status: if health.status.is_healthy() {
                "healthy".to_string()
            } else {
                "unhealthy".to_string()
            },
            component: health.component,
            message: health.message,
            metrics: health.metrics,
            timestamp: health.timestamp,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct ReadyResponse {
    pub ready: bool,
    pub component: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Application state for health endpoints
pub struct HealthState {
    pub health: Arc<RwLock<HealthCheck>>,
}

/// Create health check router
pub fn create_health_router(health: Arc<RwLock<HealthCheck>>) -> Router {
    let state = Arc::new(HealthState { health });

    Router::new()
        .route("/health", get(health_handler))
        .route("/ready", get(ready_handler))
        .route("/live", get(liveness_handler))
        .with_state(state)
}

/// Health check endpoint (detailed status)
async fn health_handler(
    State(state): State<Arc<HealthState>>,
) -> (StatusCode, Json<HealthResponse>) {
    let health = state.health.read().await;
    let status = if health.status.is_healthy() {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (status, Json(health.clone().into()))
}

/// Readiness probe endpoint
async fn ready_handler(
    State(state): State<Arc<HealthState>>,
) -> (StatusCode, Json<ReadyResponse>) {
    let health = state.health.read().await;

    let response = ReadyResponse {
        ready: health.status.is_healthy(),
        component: health.component.clone(),
        timestamp: chrono::Utc::now(),
    };

    let status = if health.status.is_healthy() {
        StatusCode::OK
    } else {
        StatusCode::SERVICE_UNAVAILABLE
    };

    (status, Json(response))
}

/// Liveness probe endpoint (always returns OK if service is running)
async fn liveness_handler() -> (StatusCode, &'static str) {
    (StatusCode::OK, "alive")
}

/// Start health check HTTP server
pub async fn start_health_server(
    port: u16,
    health: Arc<RwLock<HealthCheck>>,
) -> Result<()> {
    let app = create_health_router(health);

    let addr = std::net::SocketAddr::from(([0, 0, 0, 0], port));
    info!("Starting health check server on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr)
        .await
        .map_err(|e| crate::TradingError::Network(format!("Failed to bind: {}", e)))?;

    axum::serve(listener, app)
        .await
        .map_err(|e| crate::TradingError::Network(format!("Server error: {}", e)))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tower::Service;

    #[tokio::test]
    async fn test_health_endpoint() {
        let health = Arc::new(RwLock::new(HealthCheck::healthy("test-service")));
        let router = create_health_router(health.clone());

        // Test health endpoint
        let request = axum::http::Request::builder()
            .uri("/health")
            .body(axum::body::Body::empty())
            .unwrap();

        let response = axum::Router::into_service(router)
            .call(request)
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_unhealthy_status() {
        let health = Arc::new(RwLock::new(
            HealthCheck::unhealthy("test-service", "Test failure".to_string())
        ));
        let router = create_health_router(health.clone());

        let request = axum::http::Request::builder()
            .uri("/health")
            .body(axum::body::Body::empty())
            .unwrap();

        let response = axum::Router::into_service(router)
            .call(request)
            .await
            .unwrap();

        assert_eq!(response.status(), StatusCode::SERVICE_UNAVAILABLE);
    }

    #[tokio::test]
    async fn test_liveness_always_ok() {
        let health = Arc::new(RwLock::new(
            HealthCheck::unhealthy("test-service", "Unhealthy".to_string())
        ));
        let router = create_health_router(health);

        let request = axum::http::Request::builder()
            .uri("/live")
            .body(axum::body::Body::empty())
            .unwrap();

        let response = axum::Router::into_service(router)
            .call(request)
            .await
            .unwrap();

        // Liveness should always return OK even if unhealthy
        assert_eq!(response.status(), StatusCode::OK);
    }
}
