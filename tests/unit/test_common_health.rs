/// Unit tests for health check system
use common::{HealthCheck, HealthStatus, SystemHealth};

#[cfg(test)]
mod health_status_tests {
    use super::*;

    #[test]
    fn test_health_status_healthy() {
        let status = HealthStatus::Healthy;
        assert!(matches!(status, HealthStatus::Healthy));
    }

    #[test]
    fn test_health_status_degraded() {
        let status = HealthStatus::Degraded;
        assert!(matches!(status, HealthStatus::Degraded));
    }

    #[test]
    fn test_health_status_unhealthy() {
        let status = HealthStatus::Unhealthy;
        assert!(matches!(status, HealthStatus::Unhealthy));
    }
}

#[cfg(test)]
mod health_check_tests {
    use super::*;

    #[test]
    fn test_health_check_creation() {
        let health = HealthCheck {
            status: HealthStatus::Healthy,
            message: "All systems operational".to_string(),
            component: "market-data".to_string(),
        };

        assert!(matches!(health.status, HealthStatus::Healthy));
        assert_eq!(health.component, "market-data");
    }

    #[test]
    fn test_degraded_health_with_message() {
        let health = HealthCheck {
            status: HealthStatus::Degraded,
            message: "High latency detected".to_string(),
            component: "execution-engine".to_string(),
        };

        assert!(matches!(health.status, HealthStatus::Degraded));
        assert!(health.message.contains("latency"));
    }

    #[test]
    fn test_unhealthy_component() {
        let health = HealthCheck {
            status: HealthStatus::Unhealthy,
            message: "Database connection failed".to_string(),
            component: "risk-manager".to_string(),
        };

        assert!(matches!(health.status, HealthStatus::Unhealthy));
        assert!(health.message.contains("failed"));
    }
}

#[cfg(test)]
mod system_health_tests {
    use super::*;

    #[test]
    fn test_system_health_all_healthy() {
        let market_data = HealthCheck {
            status: HealthStatus::Healthy,
            message: "WebSocket connected".to_string(),
            component: "market-data".to_string(),
        };

        let execution = HealthCheck {
            status: HealthStatus::Healthy,
            message: "Router operational".to_string(),
            component: "execution-engine".to_string(),
        };

        let system = SystemHealth {
            overall: HealthStatus::Healthy,
            components: vec![market_data, execution],
        };

        assert!(matches!(system.overall, HealthStatus::Healthy));
        assert_eq!(system.components.len(), 2);
    }

    #[test]
    fn test_system_health_partial_degradation() {
        let components = vec![
            HealthCheck {
                status: HealthStatus::Healthy,
                message: "OK".to_string(),
                component: "market-data".to_string(),
            },
            HealthCheck {
                status: HealthStatus::Degraded,
                message: "Slow response".to_string(),
                component: "risk-manager".to_string(),
            },
        ];

        let system = SystemHealth {
            overall: HealthStatus::Degraded,
            components,
        };

        assert!(matches!(system.overall, HealthStatus::Degraded));
    }

    #[test]
    fn test_system_health_critical_failure() {
        let components = vec![
            HealthCheck {
                status: HealthStatus::Healthy,
                message: "OK".to_string(),
                component: "market-data".to_string(),
            },
            HealthCheck {
                status: HealthStatus::Unhealthy,
                message: "Critical error".to_string(),
                component: "execution-engine".to_string(),
            },
        ];

        let system = SystemHealth {
            overall: HealthStatus::Unhealthy,
            components,
        };

        assert!(matches!(system.overall, HealthStatus::Unhealthy));
        assert!(system.components.iter().any(|c| matches!(c.status, HealthStatus::Unhealthy)));
    }

    #[test]
    fn test_empty_components() {
        let system = SystemHealth {
            overall: HealthStatus::Healthy,
            components: vec![],
        };

        assert_eq!(system.components.len(), 0);
    }

    #[test]
    fn test_multiple_degraded_components() {
        let components = vec![
            HealthCheck {
                status: HealthStatus::Degraded,
                message: "High CPU".to_string(),
                component: "market-data".to_string(),
            },
            HealthCheck {
                status: HealthStatus::Degraded,
                message: "High memory".to_string(),
                component: "risk-manager".to_string(),
            },
            HealthCheck {
                status: HealthStatus::Degraded,
                message: "Network latency".to_string(),
                component: "execution-engine".to_string(),
            },
        ];

        let system = SystemHealth {
            overall: HealthStatus::Degraded,
            components: components.clone(),
        };

        let degraded_count = system.components.iter()
            .filter(|c| matches!(c.status, HealthStatus::Degraded))
            .count();

        assert_eq!(degraded_count, 3);
    }
}
