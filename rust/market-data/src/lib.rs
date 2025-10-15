/// Market Data Feed Component
///
/// Handles WebSocket connections to exchanges, order book reconstruction,
/// and tick-to-bar aggregation. Publishes market data via ZMQ.

pub mod websocket;
pub mod orderbook;
pub mod aggregation;
pub mod publisher;

pub use websocket::WebSocketClient;
pub use orderbook::OrderBookManager;
pub use aggregation::BarAggregator;
pub use publisher::MarketDataPublisher;

use common::{Result, TradingError};
use tracing::{info, error};

/// Main market data service
pub struct MarketDataService {
    ws_client: WebSocketClient,
    orderbook_manager: OrderBookManager,
    bar_aggregator: BarAggregator,
    publisher: MarketDataPublisher,
}

impl MarketDataService {
    pub async fn new(config: common::config::MarketDataConfig) -> Result<Self> {
        info!("Initializing Market Data Service for exchange: {}", config.exchange);

        let ws_client = WebSocketClient::new(&config.websocket_url)?;
        let orderbook_manager = OrderBookManager::new();
        let bar_aggregator = BarAggregator::new();
        let publisher = MarketDataPublisher::new(&config.zmq_publish_address)?;

        Ok(Self {
            ws_client,
            orderbook_manager,
            bar_aggregator,
            publisher,
        })
    }

    pub async fn run(&mut self) -> Result<()> {
        info!("Starting Market Data Service");

        // Main processing loop
        loop {
            // TODO: Implement event processing
            // - Receive WebSocket messages
            // - Update order book
            // - Aggregate bars
            // - Publish updates

            tokio::time::sleep(tokio::time::Duration::from_millis(1)).await;
        }
    }
}
