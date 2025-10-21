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
pub use aggregation::{BarAggregator, TimeWindow};
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

        // Load API credentials from environment
        let api_key = std::env::var("ALPACA_API_KEY")
            .map_err(|_| TradingError::Configuration(
                "ALPACA_API_KEY environment variable not set".to_string()
            ))?;

        let api_secret = std::env::var("ALPACA_SECRET_KEY")
            .map_err(|_| TradingError::Configuration(
                "ALPACA_SECRET_KEY environment variable not set".to_string()
            ))?;

        // Create WebSocket client with proper parameters
        let ws_client = WebSocketClient::new(
            api_key,
            api_secret,
            config.symbols.clone(),
        )?;

        let orderbook_manager = OrderBookManager::new();

        // Create BarAggregator with default time windows
        let time_windows = vec![
            TimeWindow::Minutes1,
            TimeWindow::Minutes5,
            TimeWindow::Minutes15,
        ];
        let bar_aggregator = BarAggregator::new(time_windows);

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
