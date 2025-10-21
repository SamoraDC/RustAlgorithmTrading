use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};
use std::collections::HashMap;

/// Health status of a service or component
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthStatus {
    /// Service is healthy and operating normally
    Healthy,
    /// Service is operational but degraded
    Degraded,
    /// Service is unhealthy or failing
    Unhealthy,
}

impl HealthStatus {
    pub fn is_healthy(&self) -> bool {
        matches!(self, HealthStatus::Healthy)
    }

    pub fn is_operational(&self) -> bool {
        !matches!(self, HealthStatus::Unhealthy)
    }
}

/// Health check result for a component
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthCheck {
    /// Component name
    pub component: String,
    /// Overall status
    pub status: HealthStatus,
    /// Timestamp of the check
    pub timestamp: DateTime<Utc>,
    /// Optional message or details
    pub message: Option<String>,
    /// Additional metrics
    pub metrics: HashMap<String, String>,
}

impl HealthCheck {
    pub fn new(component: impl Into<String>) -> Self {
        Self {
            component: component.into(),
            status: HealthStatus::Healthy,
            timestamp: Utc::now(),
            message: None,
            metrics: HashMap::new(),
        }
    }

    pub fn healthy(component: impl Into<String>) -> Self {
        Self::new(component)
    }

    pub fn degraded(component: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            component: component.into(),
            status: HealthStatus::Degraded,
            timestamp: Utc::now(),
            message: Some(message.into()),
            metrics: HashMap::new(),
        }
    }

    pub fn unhealthy(component: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            component: component.into(),
            status: HealthStatus::Unhealthy,
            timestamp: Utc::now(),
            message: Some(message.into()),
            metrics: HashMap::new(),
        }
    }

    pub fn with_metric(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.metrics.insert(key.into(), value.into());
        self
    }

    pub fn with_message(mut self, message: impl Into<String>) -> Self {
        self.message = Some(message.into());
        self
    }
}

/// Aggregated health status for the entire system
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemHealth {
    /// Overall system status
    pub status: HealthStatus,
    /// Timestamp of the check
    pub timestamp: DateTime<Utc>,
    /// Individual component health checks
    pub components: Vec<HealthCheck>,
    /// System-wide metrics
    pub system_metrics: HashMap<String, String>,
}

impl SystemHealth {
    pub fn new() -> Self {
        Self {
            status: HealthStatus::Healthy,
            timestamp: Utc::now(),
            components: Vec::new(),
            system_metrics: HashMap::new(),
        }
    }

    pub fn add_component(mut self, check: HealthCheck) -> Self {
        self.components.push(check);
        self.update_status();
        self
    }

    pub fn with_metric(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.system_metrics.insert(key.into(), value.into());
        self
    }

    fn update_status(&mut self) {
        if self.components.iter().any(|c| c.status == HealthStatus::Unhealthy) {
            self.status = HealthStatus::Unhealthy;
        } else if self.components.iter().any(|c| c.status == HealthStatus::Degraded) {
            self.status = HealthStatus::Degraded;
        } else {
            self.status = HealthStatus::Healthy;
        }
        self.timestamp = Utc::now();
    }

    pub fn is_healthy(&self) -> bool {
        self.status.is_healthy()
    }

    pub fn is_operational(&self) -> bool {
        self.status.is_operational()
    }
}

impl Default for SystemHealth {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_health_check_creation() {
        let check = HealthCheck::healthy("market-data");
        assert_eq!(check.component, "market-data");
        assert_eq!(check.status, HealthStatus::Healthy);
        assert!(check.message.is_none());
    }

    #[test]
    fn test_degraded_health() {
        let check = HealthCheck::degraded("execution", "high latency");
        assert_eq!(check.status, HealthStatus::Degraded);
        assert_eq!(check.message, Some("high latency".to_string()));
    }

    #[test]
    fn test_system_health_aggregation() {
        let system = SystemHealth::new()
            .add_component(HealthCheck::healthy("market-data"))
            .add_component(HealthCheck::healthy("execution"))
            .add_component(HealthCheck::degraded("risk-manager", "high load"));

        assert_eq!(system.status, HealthStatus::Degraded);
        assert!(system.is_operational());
    }

    #[test]
    fn test_unhealthy_system() {
        let system = SystemHealth::new()
            .add_component(HealthCheck::healthy("market-data"))
            .add_component(HealthCheck::unhealthy("execution", "connection failed"));

        assert_eq!(system.status, HealthStatus::Unhealthy);
        assert!(!system.is_healthy());
    }
}
