//! Test suite for Rust Algorithm Trading System
//!
//! This crate contains comprehensive tests for all components:
//! - Unit tests for individual modules
//! - Integration tests for complete workflows
//! - Performance benchmarks

// Unit test modules
#[cfg(test)]
mod unit {
    mod test_types;
    mod test_errors;
    mod test_orderbook;
    mod test_retry;
    mod test_risk_manager;
    mod test_slippage;
}

// Integration test modules are defined separately in integration/*.rs files

// Test fixtures and utilities
pub mod fixtures;
