/// Common types and utilities shared across all trading system components
///
/// This crate provides core domain types, messaging protocols, and utility functions
/// used throughout the algorithmic trading system.

pub mod types;
pub mod messaging;
pub mod errors;
pub mod config;
pub mod health;
pub mod http;

pub use types::*;
pub use errors::{TradingError, Result};
pub use health::{HealthCheck, HealthStatus, SystemHealth};
pub use http::{create_health_router, start_health_server, HealthResponse};
