use serde::{Deserialize, Serialize};
use crate::types::{Order, OrderBook, Trade, Bar, Signal, Position};

/// Message types for inter-component communication via ZMQ
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum Message {
    /// Market data messages
    OrderBookUpdate(OrderBook),
    TradeUpdate(Trade),
    BarUpdate(Bar),

    /// Signal messages
    SignalGenerated(Signal),

    /// Execution messages
    OrderRequest(Order),
    OrderResponse(OrderResponse),

    /// Risk management messages
    PositionUpdate(Position),
    RiskCheck(RiskCheckRequest),
    RiskCheckResult(RiskCheckResult),

    /// System messages
    Heartbeat(Heartbeat),
    Shutdown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrderResponse {
    pub order_id: String,
    pub client_order_id: String,
    pub success: bool,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskCheckRequest {
    pub order: Order,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskCheckResult {
    pub approved: bool,
    pub reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Heartbeat {
    pub component: String,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// ZMQ topic prefixes for PUB/SUB pattern
pub mod topics {
    pub const MARKET_DATA: &str = "market";
    pub const SIGNALS: &str = "signal";
    pub const ORDERS: &str = "order";
    pub const POSITIONS: &str = "position";
    pub const RISK: &str = "risk";
    pub const SYSTEM: &str = "system";
}
