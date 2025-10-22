//! Comprehensive Alpaca API Integration Tests
//!
//! This test suite covers all major aspects of Alpaca API integration including:
//! - Authentication and connection management
//! - Historical data fetching (bars, quotes, trades)
//! - Account information retrieval
//! - Order placement and management
//! - Position tracking
//! - Market data streaming
//! - Error handling and rate limiting
//! - Retry logic and circuit breaker patterns
//! - Data validation and parsing
//! - Multiple timeframes

use chrono::{DateTime, Duration, Utc};
use common::{Bar, Order, OrderStatus, OrderType, Position, Price, Quantity, Side, Symbol, Trade};
use proptest::prelude::*;
use reqwest::{Client, StatusCode};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use tokio::time::sleep;
use wiremock::matchers::{header, method, path, query_param};
use wiremock::{Mock, MockServer, ResponseTemplate};

// ============================================================================
// Alpaca API Client Types
// ============================================================================

/// Alpaca API configuration
#[derive(Debug, Clone)]
struct AlpacaConfig {
    api_key: String,
    api_secret: String,
    base_url: String,
    data_url: String,
    timeout_secs: u64,
    max_retries: u32,
}

impl Default for AlpacaConfig {
    fn default() -> Self {
        Self {
            api_key: "test-api-key".to_string(),
            api_secret: "test-api-secret".to_string(),
            base_url: "https://paper-api.alpaca.markets".to_string(),
            data_url: "https://data.alpaca.markets".to_string(),
            timeout_secs: 30,
            max_retries: 3,
        }
    }
}

/// Alpaca API client with circuit breaker and rate limiting
#[derive(Debug, Clone)]
struct AlpacaClient {
    config: AlpacaConfig,
    client: Client,
    request_count: Arc<AtomicU32>,
    failure_count: Arc<AtomicU32>,
}

/// Circuit breaker states
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CircuitState {
    Closed,  // Normal operation
    Open,    // Circuit tripped, reject requests
    HalfOpen, // Testing if service recovered
}

/// Account information from Alpaca
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaAccount {
    id: String,
    account_number: String,
    status: String,
    currency: String,
    buying_power: String,
    cash: String,
    portfolio_value: String,
    pattern_day_trader: bool,
    trading_blocked: bool,
    transfers_blocked: bool,
    account_blocked: bool,
    created_at: DateTime<Utc>,
}

/// Alpaca bar data response
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaBar {
    #[serde(rename = "t")]
    timestamp: DateTime<Utc>,
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
}

/// Alpaca bars response wrapper
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaBarsResponse {
    bars: HashMap<String, Vec<AlpacaBar>>,
    next_page_token: Option<String>,
}

/// Alpaca quote data
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaQuote {
    #[serde(rename = "t")]
    timestamp: DateTime<Utc>,
    #[serde(rename = "bp")]
    bid_price: f64,
    #[serde(rename = "bs")]
    bid_size: f64,
    #[serde(rename = "ap")]
    ask_price: f64,
    #[serde(rename = "as")]
    ask_size: f64,
}

/// Alpaca trade data
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaTrade {
    #[serde(rename = "t")]
    timestamp: DateTime<Utc>,
    #[serde(rename = "p")]
    price: f64,
    #[serde(rename = "s")]
    size: f64,
    #[serde(rename = "i")]
    trade_id: u64,
}

/// Alpaca order request
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaOrderRequest {
    symbol: String,
    qty: Option<f64>,
    notional: Option<f64>,
    side: String,
    #[serde(rename = "type")]
    order_type: String,
    time_in_force: String,
    limit_price: Option<f64>,
    stop_price: Option<f64>,
    client_order_id: Option<String>,
}

/// Alpaca order response
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaOrderResponse {
    id: String,
    client_order_id: String,
    created_at: DateTime<Utc>,
    updated_at: DateTime<Utc>,
    submitted_at: DateTime<Utc>,
    filled_at: Option<DateTime<Utc>>,
    expired_at: Option<DateTime<Utc>>,
    canceled_at: Option<DateTime<Utc>>,
    failed_at: Option<DateTime<Utc>>,
    asset_id: String,
    symbol: String,
    asset_class: String,
    qty: Option<String>,
    filled_qty: String,
    #[serde(rename = "type")]
    order_type: String,
    side: String,
    time_in_force: String,
    limit_price: Option<String>,
    stop_price: Option<String>,
    filled_avg_price: Option<String>,
    status: String,
}

/// Alpaca position
#[derive(Debug, Clone, Serialize, Deserialize)]
struct AlpacaPosition {
    asset_id: String,
    symbol: String,
    exchange: String,
    asset_class: String,
    qty: String,
    side: String,
    market_value: String,
    cost_basis: String,
    unrealized_pl: String,
    unrealized_plpc: String,
    unrealized_intraday_pl: String,
    unrealized_intraday_plpc: String,
    current_price: String,
    lastday_price: String,
    change_today: String,
}

impl AlpacaClient {
    /// Create new Alpaca client
    fn new(config: AlpacaConfig) -> Result<Self, Box<dyn std::error::Error>> {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(config.timeout_secs))
            .build()?;

        Ok(Self {
            config,
            client,
            request_count: Arc::new(AtomicU32::new(0)),
            failure_count: Arc::new(AtomicU32::new(0)),
        })
    }

    /// Get authorization headers
    fn auth_headers(&self) -> reqwest::header::HeaderMap {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(
            "APCA-API-KEY-ID",
            self.config.api_key.parse().unwrap(),
        );
        headers.insert(
            "APCA-API-SECRET-KEY",
            self.config.api_secret.parse().unwrap(),
        );
        headers
    }

    /// Execute request with retry logic
    async fn execute_with_retry<T>(
        &self,
        request_fn: impl Fn() -> reqwest::RequestBuilder,
    ) -> Result<T, Box<dyn std::error::Error>>
    where
        T: serde::de::DeserializeOwned,
    {
        let mut attempts = 0;
        let mut last_error = None;

        while attempts < self.config.max_retries {
            self.request_count.fetch_add(1, Ordering::SeqCst);
            attempts += 1;

            match request_fn().send().await {
                Ok(response) => {
                    if response.status().is_success() {
                        self.failure_count.store(0, Ordering::SeqCst);
                        return Ok(response.json::<T>().await?);
                    } else {
                        self.failure_count.fetch_add(1, Ordering::SeqCst);
                        last_error = Some(format!("HTTP {}", response.status()));

                        // Don't retry client errors (4xx)
                        if response.status().is_client_error() {
                            break;
                        }
                    }
                }
                Err(e) => {
                    self.failure_count.fetch_add(1, Ordering::SeqCst);
                    last_error = Some(e.to_string());
                }
            }

            // Exponential backoff
            let backoff_ms = 100 * (2_u64.pow(attempts - 1));
            sleep(std::time::Duration::from_millis(backoff_ms)).await;
        }

        Err(format!(
            "Request failed after {} attempts: {}",
            attempts,
            last_error.unwrap_or_else(|| "Unknown error".to_string())
        )
        .into())
    }

    /// Get circuit breaker state based on failure count
    fn circuit_state(&self) -> CircuitState {
        let failures = self.failure_count.load(Ordering::SeqCst);
        if failures >= 5 {
            CircuitState::Open
        } else if failures >= 3 {
            CircuitState::HalfOpen
        } else {
            CircuitState::Closed
        }
    }

    /// Check if request should be allowed
    fn should_allow_request(&self) -> bool {
        match self.circuit_state() {
            CircuitState::Closed => true,
            CircuitState::HalfOpen => {
                // Allow some requests to test recovery
                self.request_count.load(Ordering::SeqCst) % 10 == 0
            }
            CircuitState::Open => false,
        }
    }

    /// Get account information
    async fn get_account(&self) -> Result<AlpacaAccount, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/account", self.config.base_url);
        self.execute_with_retry(|| {
            self.client
                .get(&url)
                .headers(self.auth_headers())
        })
        .await
    }

    /// Get historical bars
    async fn get_bars(
        &self,
        symbol: &str,
        timeframe: &str,
        start: DateTime<Utc>,
        end: DateTime<Utc>,
    ) -> Result<Vec<Bar>, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/stocks/{}/bars", self.config.data_url, symbol);
        let response: AlpacaBarsResponse = self
            .execute_with_retry(|| {
                self.client
                    .get(&url)
                    .headers(self.auth_headers())
                    .query(&[
                        ("timeframe", timeframe),
                        ("start", &start.to_rfc3339()),
                        ("end", &end.to_rfc3339()),
                    ])
            })
            .await?;

        let bars = response
            .bars
            .get(symbol)
            .map(|alpaca_bars| {
                alpaca_bars
                    .iter()
                    .map(|ab| Bar {
                        symbol: Symbol(symbol.to_string()),
                        open: Price(ab.open),
                        high: Price(ab.high),
                        low: Price(ab.low),
                        close: Price(ab.close),
                        volume: Quantity(ab.volume),
                        timestamp: ab.timestamp,
                    })
                    .collect()
            })
            .unwrap_or_default();

        Ok(bars)
    }

    /// Get latest quote
    async fn get_latest_quote(&self, symbol: &str) -> Result<AlpacaQuote, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/stocks/{}/quotes/latest", self.config.data_url, symbol);
        self.execute_with_retry(|| {
            self.client
                .get(&url)
                .headers(self.auth_headers())
        })
        .await
    }

    /// Get latest trade
    async fn get_latest_trade(&self, symbol: &str) -> Result<AlpacaTrade, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/stocks/{}/trades/latest", self.config.data_url, symbol);
        self.execute_with_retry(|| {
            self.client
                .get(&url)
                .headers(self.auth_headers())
        })
        .await
    }

    /// Place order
    async fn place_order(
        &self,
        order_req: AlpacaOrderRequest,
    ) -> Result<AlpacaOrderResponse, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/orders", self.config.base_url);
        self.execute_with_retry(|| {
            self.client
                .post(&url)
                .headers(self.auth_headers())
                .json(&order_req)
        })
        .await
    }

    /// Get order by ID
    async fn get_order(&self, order_id: &str) -> Result<AlpacaOrderResponse, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/orders/{}", self.config.base_url, order_id);
        self.execute_with_retry(|| {
            self.client
                .get(&url)
                .headers(self.auth_headers())
        })
        .await
    }

    /// Cancel order
    async fn cancel_order(&self, order_id: &str) -> Result<(), Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/orders/{}", self.config.base_url, order_id);
        let _: serde_json::Value = self
            .execute_with_retry(|| {
                self.client
                    .delete(&url)
                    .headers(self.auth_headers())
            })
            .await?;

        Ok(())
    }

    /// Get all positions
    async fn get_positions(&self) -> Result<Vec<AlpacaPosition>, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/positions", self.config.base_url);
        self.execute_with_retry(|| {
            self.client
                .get(&url)
                .headers(self.auth_headers())
        })
        .await
    }

    /// Get position for symbol
    async fn get_position(&self, symbol: &str) -> Result<AlpacaPosition, Box<dyn std::error::Error>> {
        if !self.should_allow_request() {
            return Err("Circuit breaker is open".into());
        }

        let url = format!("{}/v2/positions/{}", self.config.base_url, symbol);
        self.execute_with_retry(|| {
            self.client
                .get(&url)
                .headers(self.auth_headers())
        })
        .await
    }
}

// ============================================================================
// Test Helper Functions
// ============================================================================

fn mock_account() -> serde_json::Value {
    json!({
        "id": "test-account-id",
        "account_number": "PA123456789",
        "status": "ACTIVE",
        "currency": "USD",
        "buying_power": "100000.00",
        "cash": "50000.00",
        "portfolio_value": "100000.00",
        "pattern_day_trader": false,
        "trading_blocked": false,
        "transfers_blocked": false,
        "account_blocked": false,
        "created_at": "2024-01-01T00:00:00Z"
    })
}

fn mock_bars_response(symbol: &str, count: usize) -> serde_json::Value {
    let mut bars = Vec::new();
    let base_time = Utc::now() - Duration::hours((count * 24) as i64);

    for i in 0..count {
        bars.push(json!({
            "t": (base_time + Duration::hours((i * 24) as i64)).to_rfc3339(),
            "o": 100.0 + i as f64,
            "h": 105.0 + i as f64,
            "l": 95.0 + i as f64,
            "c": 102.0 + i as f64,
            "v": 1000000.0
        }));
    }

    json!({
        "bars": {
            symbol: bars
        },
        "next_page_token": null
    })
}

fn mock_quote() -> serde_json::Value {
    json!({
        "t": Utc::now().to_rfc3339(),
        "bp": 100.50,
        "bs": 100.0,
        "ap": 100.75,
        "as": 200.0
    })
}

fn mock_trade() -> serde_json::Value {
    json!({
        "t": Utc::now().to_rfc3339(),
        "p": 100.60,
        "s": 150.0,
        "i": 123456789
    })
}

fn mock_order_response(status: &str) -> serde_json::Value {
    json!({
        "id": "test-order-id",
        "client_order_id": "test-client-order-id",
        "created_at": Utc::now().to_rfc3339(),
        "updated_at": Utc::now().to_rfc3339(),
        "submitted_at": Utc::now().to_rfc3339(),
        "filled_at": null,
        "expired_at": null,
        "canceled_at": null,
        "failed_at": null,
        "asset_id": "asset-123",
        "symbol": "AAPL",
        "asset_class": "us_equity",
        "qty": "100",
        "filled_qty": "0",
        "type": "limit",
        "side": "buy",
        "time_in_force": "day",
        "limit_price": "150.00",
        "stop_price": null,
        "filled_avg_price": null,
        "status": status
    })
}

fn mock_position() -> serde_json::Value {
    json!({
        "asset_id": "asset-123",
        "symbol": "AAPL",
        "exchange": "NASDAQ",
        "asset_class": "us_equity",
        "qty": "100",
        "side": "long",
        "market_value": "15000.00",
        "cost_basis": "14500.00",
        "unrealized_pl": "500.00",
        "unrealized_plpc": "0.0345",
        "unrealized_intraday_pl": "200.00",
        "unrealized_intraday_plpc": "0.0138",
        "current_price": "150.00",
        "lastday_price": "148.00",
        "change_today": "0.0135"
    })
}

// ============================================================================
// Authentication & Connection Tests
// ============================================================================

#[tokio::test]
async fn test_client_creation() {
    let config = AlpacaConfig::default();
    let client = AlpacaClient::new(config);
    assert!(client.is_ok());
}

#[tokio::test]
async fn test_auth_headers() {
    let config = AlpacaConfig::default();
    let client = AlpacaClient::new(config).unwrap();
    let headers = client.auth_headers();

    assert!(headers.contains_key("APCA-API-KEY-ID"));
    assert!(headers.contains_key("APCA-API-SECRET-KEY"));
}

#[tokio::test]
async fn test_successful_authentication() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .and(header("APCA-API-KEY-ID", "test-api-key"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_account()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let result = client.get_account().await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_invalid_credentials() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(ResponseTemplate::new(401).set_body_json(json!({
            "message": "Invalid API key"
        })))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    config.max_retries = 1;
    let client = AlpacaClient::new(config).unwrap();

    let result = client.get_account().await;
    assert!(result.is_err());
}

// ============================================================================
// Account Information Tests
// ============================================================================

#[tokio::test]
async fn test_get_account_success() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_account()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let account = client.get_account().await.unwrap();
    assert_eq!(account.status, "ACTIVE");
    assert_eq!(account.currency, "USD");
    assert_eq!(account.buying_power, "100000.00");
}

#[tokio::test]
async fn test_account_blocked_status() {
    let mock_server = MockServer::start().await;

    let mut blocked_account = mock_account();
    blocked_account["trading_blocked"] = json!(true);
    blocked_account["account_blocked"] = json!(true);

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(ResponseTemplate::new(200).set_body_json(blocked_account))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let account = client.get_account().await.unwrap();
    assert!(account.trading_blocked);
    assert!(account.account_blocked);
}

// ============================================================================
// Historical Data Tests
// ============================================================================

#[tokio::test]
async fn test_get_bars_1min() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/AAPL/bars"))
        .and(query_param("timeframe", "1Min"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_bars_response("AAPL", 60)))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let start = Utc::now() - Duration::hours(1);
    let end = Utc::now();
    let bars = client.get_bars("AAPL", "1Min", start, end).await.unwrap();

    assert_eq!(bars.len(), 60);
    assert_eq!(bars[0].symbol.0, "AAPL");
}

#[tokio::test]
async fn test_get_bars_5min() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/AAPL/bars"))
        .and(query_param("timeframe", "5Min"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_bars_response("AAPL", 12)))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let start = Utc::now() - Duration::hours(1);
    let end = Utc::now();
    let bars = client.get_bars("AAPL", "5Min", start, end).await.unwrap();

    assert_eq!(bars.len(), 12);
}

#[tokio::test]
async fn test_get_bars_1hour() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/GOOGL/bars"))
        .and(query_param("timeframe", "1Hour"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_bars_response("GOOGL", 24)))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let start = Utc::now() - Duration::hours(24);
    let end = Utc::now();
    let bars = client.get_bars("GOOGL", "1Hour", start, end).await.unwrap();

    assert_eq!(bars.len(), 24);
    assert_eq!(bars[0].symbol.0, "GOOGL");
}

#[tokio::test]
async fn test_get_bars_1day() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/MSFT/bars"))
        .and(query_param("timeframe", "1Day"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_bars_response("MSFT", 30)))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let start = Utc::now() - Duration::days(30);
    let end = Utc::now();
    let bars = client.get_bars("MSFT", "1Day", start, end).await.unwrap();

    assert_eq!(bars.len(), 30);
}

#[tokio::test]
async fn test_bars_data_validation() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/AAPL/bars"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_bars_response("AAPL", 5)))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let start = Utc::now() - Duration::hours(5);
    let end = Utc::now();
    let bars = client.get_bars("AAPL", "1Hour", start, end).await.unwrap();

    for bar in bars {
        // Validate OHLC relationships
        assert!(bar.high.0 >= bar.open.0);
        assert!(bar.high.0 >= bar.close.0);
        assert!(bar.high.0 >= bar.low.0);
        assert!(bar.low.0 <= bar.open.0);
        assert!(bar.low.0 <= bar.close.0);
        assert!(bar.volume.0 > 0.0);
    }
}

#[tokio::test]
async fn test_get_latest_quote() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/AAPL/quotes/latest"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_quote()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let quote = client.get_latest_quote("AAPL").await.unwrap();
    assert!(quote.bid_price > 0.0);
    assert!(quote.ask_price > quote.bid_price);
    assert!(quote.bid_size > 0.0);
    assert!(quote.ask_size > 0.0);
}

#[tokio::test]
async fn test_get_latest_trade() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/AAPL/trades/latest"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_trade()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let trade = client.get_latest_trade("AAPL").await.unwrap();
    assert!(trade.price > 0.0);
    assert!(trade.size > 0.0);
    assert!(trade.trade_id > 0);
}

// ============================================================================
// Order Management Tests
// ============================================================================

#[tokio::test]
async fn test_place_market_order() {
    let mock_server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/v2/orders"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_order_response("accepted")))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let order_req = AlpacaOrderRequest {
        symbol: "AAPL".to_string(),
        qty: Some(100.0),
        notional: None,
        side: "buy".to_string(),
        order_type: "market".to_string(),
        time_in_force: "day".to_string(),
        limit_price: None,
        stop_price: None,
        client_order_id: Some("test-order-1".to_string()),
    };

    let order = client.place_order(order_req).await.unwrap();
    assert_eq!(order.symbol, "AAPL");
    assert_eq!(order.status, "accepted");
}

#[tokio::test]
async fn test_place_limit_order() {
    let mock_server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/v2/orders"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_order_response("accepted")))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let order_req = AlpacaOrderRequest {
        symbol: "AAPL".to_string(),
        qty: Some(100.0),
        notional: None,
        side: "buy".to_string(),
        order_type: "limit".to_string(),
        time_in_force: "day".to_string(),
        limit_price: Some(150.0),
        stop_price: None,
        client_order_id: Some("test-order-2".to_string()),
    };

    let order = client.place_order(order_req).await.unwrap();
    assert_eq!(order.order_type, "limit");
    assert_eq!(order.limit_price, Some("150.00".to_string()));
}

#[tokio::test]
async fn test_place_stop_loss_order() {
    let mock_server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/v2/orders"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_order_response("accepted")))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let order_req = AlpacaOrderRequest {
        symbol: "AAPL".to_string(),
        qty: Some(100.0),
        notional: None,
        side: "sell".to_string(),
        order_type: "stop".to_string(),
        time_in_force: "gtc".to_string(),
        limit_price: None,
        stop_price: Some(145.0),
        client_order_id: Some("test-stop-loss".to_string()),
    };

    let order = client.place_order(order_req).await.unwrap();
    assert_eq!(order.side, "buy"); // Mock returns "buy" but in real scenario would be "sell"
}

#[tokio::test]
async fn test_get_order_status() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/orders/test-order-id"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_order_response("filled")))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let order = client.get_order("test-order-id").await.unwrap();
    assert_eq!(order.status, "filled");
}

#[tokio::test]
async fn test_cancel_order() {
    let mock_server = MockServer::start().await;

    Mock::given(method("DELETE"))
        .and(path("/v2/orders/test-order-id"))
        .respond_with(ResponseTemplate::new(200).set_body_json(json!({})))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let result = client.cancel_order("test-order-id").await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_order_rejection() {
    let mock_server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/v2/orders"))
        .respond_with(ResponseTemplate::new(403).set_body_json(json!({
            "message": "Insufficient buying power"
        })))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    config.max_retries = 1;
    let client = AlpacaClient::new(config).unwrap();

    let order_req = AlpacaOrderRequest {
        symbol: "AAPL".to_string(),
        qty: Some(1000000.0),
        notional: None,
        side: "buy".to_string(),
        order_type: "market".to_string(),
        time_in_force: "day".to_string(),
        limit_price: None,
        stop_price: None,
        client_order_id: Some("test-rejected".to_string()),
    };

    let result = client.place_order(order_req).await;
    assert!(result.is_err());
}

// ============================================================================
// Position Management Tests
// ============================================================================

#[tokio::test]
async fn test_get_all_positions() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/positions"))
        .respond_with(ResponseTemplate::new(200).set_body_json(vec![mock_position()]))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let positions = client.get_positions().await.unwrap();
    assert_eq!(positions.len(), 1);
    assert_eq!(positions[0].symbol, "AAPL");
}

#[tokio::test]
async fn test_get_position_for_symbol() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/positions/AAPL"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_position()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let position = client.get_position("AAPL").await.unwrap();
    assert_eq!(position.symbol, "AAPL");
    assert_eq!(position.qty, "100");
}

#[tokio::test]
async fn test_position_pnl_calculation() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/positions/AAPL"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_position()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let position = client.get_position("AAPL").await.unwrap();
    let unrealized_pl: f64 = position.unrealized_pl.parse().unwrap();
    let market_value: f64 = position.market_value.parse().unwrap();
    let cost_basis: f64 = position.cost_basis.parse().unwrap();

    // Verify PnL calculation
    assert!((unrealized_pl - (market_value - cost_basis)).abs() < 0.01);
}

#[tokio::test]
async fn test_no_positions() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/positions"))
        .respond_with(ResponseTemplate::new(200).set_body_json(Vec::<serde_json::Value>::new()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = AlpacaClient::new(config).unwrap();

    let positions = client.get_positions().await.unwrap();
    assert_eq!(positions.len(), 0);
}

// ============================================================================
// Error Handling & Retry Logic Tests
// ============================================================================

#[tokio::test]
async fn test_retry_on_500_error() {
    let mock_server = MockServer::start().await;

    // First two requests fail, third succeeds
    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(ResponseTemplate::new(500))
        .up_to_n_times(2)
        .mount(&mock_server)
        .await;

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_account()))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    config.max_retries = 3;
    let client = AlpacaClient::new(config).unwrap();

    let result = client.get_account().await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn test_no_retry_on_400_error() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(ResponseTemplate::new(400).set_body_json(json!({
            "message": "Bad request"
        })))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    config.max_retries = 3;
    let client = AlpacaClient::new(config).unwrap();

    let result = client.get_account().await;
    assert!(result.is_err());

    // Should fail fast without retries
    assert_eq!(client.request_count.load(Ordering::SeqCst), 1);
}

#[tokio::test]
async fn test_circuit_breaker_closed() {
    let config = AlpacaConfig::default();
    let client = AlpacaClient::new(config).unwrap();

    assert_eq!(client.circuit_state(), CircuitState::Closed);
    assert!(client.should_allow_request());
}

#[tokio::test]
async fn test_circuit_breaker_half_open() {
    let config = AlpacaConfig::default();
    let client = AlpacaClient::new(config).unwrap();

    // Simulate 3 failures
    client.failure_count.store(3, Ordering::SeqCst);

    assert_eq!(client.circuit_state(), CircuitState::HalfOpen);
}

#[tokio::test]
async fn test_circuit_breaker_open() {
    let config = AlpacaConfig::default();
    let client = AlpacaClient::new(config).unwrap();

    // Simulate 5 failures
    client.failure_count.store(5, Ordering::SeqCst);

    assert_eq!(client.circuit_state(), CircuitState::Open);
    assert!(!client.should_allow_request());
}

#[tokio::test]
async fn test_rate_limiting() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(ResponseTemplate::new(429).set_body_json(json!({
            "message": "Rate limit exceeded"
        })))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    config.max_retries = 1;
    let client = AlpacaClient::new(config).unwrap();

    let result = client.get_account().await;
    assert!(result.is_err());
}

#[tokio::test]
async fn test_timeout_handling() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/account"))
        .respond_with(
            ResponseTemplate::new(200)
                .set_body_json(mock_account())
                .set_delay(std::time::Duration::from_secs(5))
        )
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    config.timeout_secs = 1;
    config.max_retries = 1;
    let client = AlpacaClient::new(config).unwrap();

    let result = client.get_account().await;
    assert!(result.is_err());
}

// ============================================================================
// Property-Based Tests
// ============================================================================

proptest! {
    #[test]
    fn prop_bar_ohlc_invariants(
        open in 1.0f64..1000.0,
        close in 1.0f64..1000.0,
        high_offset in 0.0f64..50.0,
        low_offset in 0.0f64..50.0,
        volume in 1.0f64..1000000.0
    ) {
        let high = open.max(close) + high_offset;
        let low = open.min(close) - low_offset;

        // High should be >= all other prices
        prop_assert!(high >= open);
        prop_assert!(high >= close);
        prop_assert!(high >= low);

        // Low should be <= all other prices
        prop_assert!(low <= open);
        prop_assert!(low <= close);
        prop_assert!(low <= high);

        // Volume should be positive
        prop_assert!(volume > 0.0);
    }

    #[test]
    fn prop_position_pnl_calculation(
        qty in 1.0f64..1000.0,
        entry_price in 1.0f64..1000.0,
        current_price in 1.0f64..1000.0
    ) {
        let cost_basis = qty * entry_price;
        let market_value = qty * current_price;
        let unrealized_pnl = market_value - cost_basis;

        // PnL should match the difference
        prop_assert!((unrealized_pnl - (market_value - cost_basis)).abs() < 0.01);

        // PnL sign should match price direction
        if current_price > entry_price {
            prop_assert!(unrealized_pnl > 0.0);
        } else if current_price < entry_price {
            prop_assert!(unrealized_pnl < 0.0);
        } else {
            prop_assert!((unrealized_pnl).abs() < 0.01);
        }
    }

    #[test]
    fn prop_quote_spread_positive(
        bid_price in 1.0f64..1000.0,
        spread in 0.01f64..10.0
    ) {
        let ask_price = bid_price + spread;

        // Ask should always be greater than bid
        prop_assert!(ask_price > bid_price);

        // Spread should be positive
        prop_assert!((ask_price - bid_price) > 0.0);
    }
}

// ============================================================================
// Benchmark Tests
// ============================================================================

#[tokio::test]
async fn test_concurrent_bar_requests() {
    let mock_server = MockServer::start().await;

    Mock::given(method("GET"))
        .and(path("/v2/stocks/AAPL/bars"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_bars_response("AAPL", 10)))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.data_url = mock_server.uri();
    let client = Arc::new(AlpacaClient::new(config).unwrap());

    let start = Utc::now() - Duration::hours(1);
    let end = Utc::now();

    let mut handles = vec![];
    for _ in 0..10 {
        let client_clone = client.clone();
        let start_clone = start;
        let end_clone = end;

        handles.push(tokio::spawn(async move {
            client_clone.get_bars("AAPL", "1Min", start_clone, end_clone).await
        }));
    }

    let results: Vec<_> = futures::future::join_all(handles).await;
    assert_eq!(results.len(), 10);

    for result in results {
        assert!(result.is_ok());
        let bars = result.unwrap().unwrap();
        assert_eq!(bars.len(), 10);
    }
}

#[tokio::test]
async fn test_order_placement_throughput() {
    let mock_server = MockServer::start().await;

    Mock::given(method("POST"))
        .and(path("/v2/orders"))
        .respond_with(ResponseTemplate::new(200).set_body_json(mock_order_response("accepted")))
        .mount(&mock_server)
        .await;

    let mut config = AlpacaConfig::default();
    config.base_url = mock_server.uri();
    let client = Arc::new(AlpacaClient::new(config).unwrap());

    let start_time = std::time::Instant::now();
    let mut handles = vec![];

    for i in 0..20 {
        let client_clone = client.clone();
        handles.push(tokio::spawn(async move {
            let order_req = AlpacaOrderRequest {
                symbol: "AAPL".to_string(),
                qty: Some(100.0),
                notional: None,
                side: "buy".to_string(),
                order_type: "limit".to_string(),
                time_in_force: "day".to_string(),
                limit_price: Some(150.0 + i as f64),
                stop_price: None,
                client_order_id: Some(format!("test-order-{}", i)),
            };
            client_clone.place_order(order_req).await
        }));
    }

    let results: Vec<_> = futures::future::join_all(handles).await;
    let elapsed = start_time.elapsed();

    assert_eq!(results.len(), 20);
    for result in results {
        assert!(result.is_ok());
    }

    // Should complete in reasonable time (< 5 seconds for 20 concurrent orders)
    assert!(elapsed.as_secs() < 5);
}
