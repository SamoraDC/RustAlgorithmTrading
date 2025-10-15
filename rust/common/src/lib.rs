/// Common types and utilities shared across all trading system components
///
/// This crate provides core domain types, messaging protocols, and utility functions
/// used throughout the algorithmic trading system.

pub mod types;
pub mod messaging;
pub mod errors;
pub mod config;

pub use types::*;
pub use errors::{TradingError, Result};
