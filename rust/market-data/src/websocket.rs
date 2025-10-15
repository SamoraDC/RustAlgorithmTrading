use common::{Result, TradingError};
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::time::{Duration, sleep};
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tracing::{debug, error, info, warn};
use url::Url;

const ALPACA_WSS_URL: &str = "wss://stream.data.alpaca.markets/v2/iex";
const RECONNECT_DELAY_MS: u64 = 5000;
const HEARTBEAT_INTERVAL_MS: u64 = 30000;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "T")]
pub enum AlpacaMessage {
    #[serde(rename = "t")]
    Trade {
        #[serde(rename = "S")]
        symbol: String,
        #[serde(rename = "p")]
        price: f64,
        #[serde(rename = "s")]
        size: f64,
        #[serde(rename = "t")]
        timestamp: String,
        #[serde(rename = "i")]
        id: u64,
    },
    #[serde(rename = "q")]
    Quote {
        #[serde(rename = "S")]
        symbol: String,
        #[serde(rename = "bp")]
        bid_price: f64,
        #[serde(rename = "bs")]
        bid_size: f64,
        #[serde(rename = "ap")]
        ask_price: f64,
        #[serde(rename = "as")]
        ask_size: f64,
        #[serde(rename = "t")]
        timestamp: String,
    },
    #[serde(rename = "b")]
    Bar {
        #[serde(rename = "S")]
        symbol: String,
        #[serde(rename = "o")]
        open: f64,
        #[serde(rename = "h")]
        high: f64,
        #[serde(rename = "l")]
        low: f64,
        #[serde(rename = "c")]
        close: f64,
        #[serde(rename = "v")]
        volume: f64,
        #[serde(rename = "t")]
        timestamp: String,
    },
    #[serde(other)]
    Unknown,
}

pub struct WebSocketClient {
    url: Url,
    api_key: String,
    api_secret: String,
    symbols: Vec<String>,
    reconnect_delay: Duration,
}

impl WebSocketClient {
    pub fn new(
        api_key: String,
        api_secret: String,
        symbols: Vec<String>,
    ) -> Result<Self> {
        let url = Url::parse(ALPACA_WSS_URL)
            .map_err(|e| TradingError::Configuration(format!("Invalid WebSocket URL: {}", e)))?;

        Ok(Self {
            url,
            api_key,
            api_secret,
            symbols,
            reconnect_delay: Duration::from_millis(RECONNECT_DELAY_MS),
        })
    }

    pub async fn connect<F>(&self, mut on_message: F) -> Result<()>
    where
        F: FnMut(AlpacaMessage) -> Result<()> + Send + 'static,
    {
        loop {
            match self.connect_inner(&mut on_message).await {
                Ok(_) => {
                    info!("WebSocket connection closed gracefully");
                    break;
                }
                Err(e) => {
                    error!("WebSocket error: {:?}, reconnecting in {:?}...", e, self.reconnect_delay);
                    sleep(self.reconnect_delay).await;
                }
            }
        }
        Ok(())
    }

    async fn connect_inner<F>(&self, on_message: &mut F) -> Result<()>
    where
        F: FnMut(AlpacaMessage) -> Result<()>,
    {
        info!("Connecting to Alpaca WebSocket: {}", self.url);

        let (ws_stream, _) = connect_async(self.url.as_str())
            .await
            .map_err(|e| TradingError::Network(format!("Connection failed: {}", e)))?;

        info!("WebSocket connected successfully");

        let (mut write, mut read) = ws_stream.split();

        // Send authentication
        let auth_msg = json!({
            "action": "auth",
            "key": self.api_key,
            "secret": self.api_secret
        });

        write
            .send(Message::Text(auth_msg.to_string()))
            .await
            .map_err(|e| TradingError::Network(format!("Auth failed: {}", e)))?;

        info!("Authentication sent");

        // Wait for auth confirmation
        if let Some(msg) = read.next().await {
            let msg = msg.map_err(|e| TradingError::Network(format!("Auth response error: {}", e)))?;
            debug!("Auth response: {:?}", msg);
        }

        // Subscribe to symbols
        let subscribe_msg = json!({
            "action": "subscribe",
            "trades": self.symbols,
            "quotes": self.symbols,
            "bars": self.symbols
        });

        write
            .send(Message::Text(subscribe_msg.to_string()))
            .await
            .map_err(|e| TradingError::Network(format!("Subscribe failed: {}", e)))?;

        info!("Subscribed to symbols: {:?}", self.symbols);

        // Start heartbeat task
        let heartbeat_write = write;
        let mut heartbeat_interval = tokio::time::interval(Duration::from_millis(HEARTBEAT_INTERVAL_MS));

        // Process messages
        while let Some(msg) = read.next().await {
            let msg = msg.map_err(|e| TradingError::Network(format!("Receive error: {}", e)))?;

            match msg {
                Message::Text(text) => {
                    // Parse and handle message
                    if let Err(e) = self.handle_text_message(&text, on_message) {
                        warn!("Failed to handle message: {:?}", e);
                    }
                }
                Message::Binary(data) => {
                    debug!("Received binary message: {} bytes", data.len());
                }
                Message::Ping(data) => {
                    debug!("Received ping, sending pong");
                    // Pong is sent automatically by tokio-tungstenite
                }
                Message::Pong(_) => {
                    debug!("Received pong");
                }
                Message::Close(frame) => {
                    info!("Received close frame: {:?}", frame);
                    break;
                }
                Message::Frame(_) => {}
            }

            // Check if it's time to send heartbeat
            if heartbeat_interval.poll_tick(tokio::time::Instant::now().into()).is_ready() {
                // Heartbeat is handled by ping/pong
                debug!("Heartbeat check");
            }
        }

        Ok(())
    }

    fn handle_text_message<F>(&self, text: &str, on_message: &mut F) -> Result<()>
    where
        F: FnMut(AlpacaMessage) -> Result<()>,
    {
        // Try to parse as array of messages
        if let Ok(messages) = serde_json::from_str::<Vec<AlpacaMessage>>(text) {
            for msg in messages {
                match msg {
                    AlpacaMessage::Unknown => {
                        debug!("Unknown message type: {}", text);
                    }
                    _ => {
                        on_message(msg)?;
                    }
                }
            }
        } else if let Ok(value) = serde_json::from_str::<Value>(text) {
            // Handle control messages (auth confirmation, subscription confirmation, etc.)
            debug!("Control message: {:?}", value);
        } else {
            warn!("Failed to parse message: {}", text);
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_trade_message() {
        let json = r#"[{"T":"t","S":"AAPL","p":150.25,"s":100,"t":"2024-01-01T10:00:00Z","i":12345}]"#;
        let messages: Vec<AlpacaMessage> = serde_json::from_str(json).unwrap();
        assert_eq!(messages.len(), 1);
    }

    #[test]
    fn test_parse_quote_message() {
        let json = r#"[{"T":"q","S":"AAPL","bp":150.00,"bs":10,"ap":150.05,"as":5,"t":"2024-01-01T10:00:00Z"}]"#;
        let messages: Vec<AlpacaMessage> = serde_json::from_str(json).unwrap();
        assert_eq!(messages.len(), 1);
    }
}
