# Alpaca Markets API Integration

This document describes how the trading system integrates with the Alpaca Markets API for market data and order execution.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Market Data API](#market-data-api)
4. [Trading API](#trading-api)
5. [Error Handling](#error-handling)
6. [Rate Limits](#rate-limits)
7. [Best Practices](#best-practices)

## Overview

[Alpaca Markets](https://alpaca.markets) provides commission-free stock trading with a developer-friendly REST API and real-time WebSocket data feeds.

### API Versions

- **REST API**: v2 (https://paper-api.alpaca.markets)
- **Market Data**: v2 (wss://data.alpaca.markets/stream)
- **Documentation**: https://alpaca.markets/docs/api-documentation/

### Environments

1. **Paper Trading** (Development):
   - API: `https://paper-api.alpaca.markets`
   - WebSocket: `wss://data.alpaca.markets/stream`
   - Unlimited API calls
   - No real money

2. **Live Trading** (Production):
   - API: `https://api.alpaca.markets`
   - WebSocket: `wss://data.alpaca.markets/stream`
   - Real money trading
   - Rate limits apply

## Authentication

### API Keys

Alpaca uses API key authentication with two components:

1. **API Key ID**: Public identifier (like username)
2. **Secret Key**: Private credential (like password)

**IMPORTANT**: Never commit secret keys to version control!

### Obtaining API Keys

1. Sign up at https://alpaca.markets
2. Navigate to "API Keys" in dashboard
3. Click "Generate API Key"
4. Select environment (Paper or Live)
5. Copy both keys immediately (secret shown only once)

### Implementation

#### HTTP Headers

All REST API requests must include:

```http
APCA-API-KEY-ID: YOUR_API_KEY_ID
APCA-API-SECRET-KEY: YOUR_SECRET_KEY
Content-Type: application/json
```

#### Rust Implementation

```rust
use reqwest::Client;
use serde::{Deserialize, Serialize};

pub struct AlpacaClient {
    client: Client,
    api_key: String,
    secret_key: String,
    base_url: String,
}

impl AlpacaClient {
    pub fn new(api_key: String, secret_key: String, paper_trading: bool) -> Self {
        let base_url = if paper_trading {
            "https://paper-api.alpaca.markets".to_string()
        } else {
            "https://api.alpaca.markets".to_string()
        };

        Self {
            client: Client::new(),
            api_key,
            secret_key,
            base_url,
        }
    }

    async fn request<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        method: &str,
        endpoint: &str,
        body: Option<&T>,
    ) -> Result<R> {
        let url = format!("{}{}", self.base_url, endpoint);

        let mut req = self.client
            .request(method.parse()?, &url)
            .header("APCA-API-KEY-ID", &self.api_key)
            .header("APCA-API-SECRET-KEY", &self.secret_key);

        if let Some(body) = body {
            req = req.json(body);
        }

        let resp = req.send().await?;
        let data = resp.json().await?;
        Ok(data)
    }
}
```

#### WebSocket Authentication

WebSocket requires authentication after connection:

```json
{
  "action": "auth",
  "key": "YOUR_API_KEY_ID",
  "secret": "YOUR_SECRET_KEY"
}
```

Response:
```json
{
  "T": "success",
  "msg": "authenticated"
}
```

## Market Data API

### WebSocket Streaming

#### Connection

```rust
use tokio_tungstenite::{connect_async, tungstenite::Message};
use futures::{StreamExt, SinkExt};

pub struct AlpacaWebSocket {
    stream: WebSocketStream,
}

impl AlpacaWebSocket {
    pub async fn connect(api_key: String, secret_key: String) -> Result<Self> {
        let url = "wss://data.alpaca.markets/stream";
        let (ws_stream, _) = connect_async(url).await?;

        let (mut write, read) = ws_stream.split();

        // Authenticate
        let auth_msg = json!({
            "action": "auth",
            "key": api_key,
            "secret": secret_key
        });
        write.send(Message::Text(auth_msg.to_string())).await?;

        Ok(Self { stream: ws_stream })
    }

    pub async fn subscribe(&mut self, symbols: Vec<String>) -> Result<()> {
        let subscribe_msg = json!({
            "action": "subscribe",
            "trades": symbols,
            "quotes": symbols,
            "bars": symbols
        });
        self.stream.send(Message::Text(subscribe_msg.to_string())).await?;
        Ok(())
    }
}
```

#### Message Types

**Trade Update**:
```json
{
  "T": "t",
  "S": "AAPL",
  "i": 12345,
  "x": "V",
  "p": 150.25,
  "s": 100,
  "t": "2024-10-14T20:30:00.123456Z",
  "c": ["@", "I"],
  "z": "C"
}
```

Fields:
- `T`: Message type ("t" = trade)
- `S`: Symbol
- `i`: Trade ID
- `x`: Exchange
- `p`: Price
- `s`: Size (shares)
- `t`: Timestamp
- `c`: Conditions
- `z`: Tape

**Quote Update**:
```json
{
  "T": "q",
  "S": "AAPL",
  "bx": "V",
  "bp": 150.24,
  "bs": 100,
  "ax": "V",
  "ap": 150.26,
  "as": 200,
  "t": "2024-10-14T20:30:00.123456Z"
}
```

Fields:
- `bx`: Bid exchange
- `bp`: Bid price
- `bs`: Bid size
- `ax`: Ask exchange
- `ap`: Ask price
- `as`: Ask size

**Bar Update** (OHLCV):
```json
{
  "T": "b",
  "S": "AAPL",
  "o": 150.20,
  "h": 150.50,
  "l": 150.15,
  "c": 150.45,
  "v": 10000,
  "t": "2024-10-14T20:30:00Z",
  "n": 1234,
  "vw": 150.35
}
```

### REST API (Historical Data)

#### Get Historical Bars

```rust
#[derive(Deserialize)]
pub struct Bar {
    pub t: String,  // Timestamp
    pub o: f64,     // Open
    pub h: f64,     // High
    pub l: f64,     // Low
    pub c: f64,     // Close
    pub v: u64,     // Volume
    pub n: u64,     // Trade count
    pub vw: f64,    // VWAP
}

impl AlpacaClient {
    pub async fn get_bars(
        &self,
        symbol: &str,
        timeframe: &str,  // "1Min", "1Hour", "1Day"
        start: &str,
        end: &str,
    ) -> Result<Vec<Bar>> {
        let endpoint = format!(
            "/v2/stocks/{}/bars?timeframe={}&start={}&end={}",
            symbol, timeframe, start, end
        );
        self.request("GET", &endpoint, None::<&()>).await
    }
}
```

Example:
```rust
let bars = client.get_bars(
    "AAPL",
    "1Min",
    "2024-10-14T09:30:00Z",
    "2024-10-14T16:00:00Z"
).await?;
```

## Trading API

### Account Information

#### Get Account

```rust
#[derive(Deserialize)]
pub struct Account {
    pub id: String,
    pub status: String,
    pub currency: String,
    pub buying_power: String,
    pub cash: String,
    pub portfolio_value: String,
    pub pattern_day_trader: bool,
    pub trading_blocked: bool,
    pub transfers_blocked: bool,
    pub account_blocked: bool,
}

impl AlpacaClient {
    pub async fn get_account(&self) -> Result<Account> {
        self.request("GET", "/v2/account", None::<&()>).await
    }
}
```

### Order Management

#### Place Order

```rust
#[derive(Serialize)]
pub struct OrderRequest {
    pub symbol: String,
    pub qty: f64,
    pub side: String,          // "buy" or "sell"
    pub r#type: String,        // "market", "limit", "stop", "stop_limit"
    pub time_in_force: String, // "day", "gtc", "ioc", "fok"
    #[serde(skip_serializing_if = "Option::is_none")]
    pub limit_price: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stop_price: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub client_order_id: Option<String>,
}

#[derive(Deserialize)]
pub struct OrderResponse {
    pub id: String,
    pub client_order_id: String,
    pub status: String,
    pub symbol: String,
    pub qty: String,
    pub filled_qty: String,
    pub side: String,
    pub r#type: String,
    pub limit_price: Option<String>,
    pub stop_price: Option<String>,
    pub filled_avg_price: Option<String>,
    pub submitted_at: String,
    pub filled_at: Option<String>,
    pub canceled_at: Option<String>,
}

impl AlpacaClient {
    pub async fn place_order(&self, order: &OrderRequest) -> Result<OrderResponse> {
        self.request("POST", "/v2/orders", Some(order)).await
    }
}
```

Example - Market Order:
```rust
let order = OrderRequest {
    symbol: "AAPL".to_string(),
    qty: 10.0,
    side: "buy".to_string(),
    r#type: "market".to_string(),
    time_in_force: "day".to_string(),
    limit_price: None,
    stop_price: None,
    client_order_id: Some("my-order-123".to_string()),
};

let response = client.place_order(&order).await?;
```

Example - Limit Order:
```rust
let order = OrderRequest {
    symbol: "AAPL".to_string(),
    qty: 10.0,
    side: "buy".to_string(),
    r#type: "limit".to_string(),
    time_in_force: "gtc".to_string(),
    limit_price: Some(150.00),
    stop_price: None,
    client_order_id: Some("my-order-124".to_string()),
};
```

#### Get Order Status

```rust
impl AlpacaClient {
    pub async fn get_order(&self, order_id: &str) -> Result<OrderResponse> {
        let endpoint = format!("/v2/orders/{}", order_id);
        self.request("GET", &endpoint, None::<&()>).await
    }

    pub async fn cancel_order(&self, order_id: &str) -> Result<()> {
        let endpoint = format!("/v2/orders/{}", order_id);
        self.request("DELETE", &endpoint, None::<&()>).await
    }
}
```

### Position Management

#### Get Positions

```rust
#[derive(Deserialize)]
pub struct Position {
    pub asset_id: String,
    pub symbol: String,
    pub exchange: String,
    pub qty: String,
    pub avg_entry_price: String,
    pub side: String,
    pub market_value: String,
    pub cost_basis: String,
    pub unrealized_pl: String,
    pub unrealized_plpc: String,
    pub current_price: String,
}

impl AlpacaClient {
    pub async fn get_positions(&self) -> Result<Vec<Position>> {
        self.request("GET", "/v2/positions", None::<&()>).await
    }

    pub async fn get_position(&self, symbol: &str) -> Result<Position> {
        let endpoint = format!("/v2/positions/{}", symbol);
        self.request("GET", &endpoint, None::<&()>).await
    }

    pub async fn close_position(&self, symbol: &str) -> Result<OrderResponse> {
        let endpoint = format!("/v2/positions/{}", symbol);
        self.request("DELETE", &endpoint, None::<&()>).await
    }
}
```

## Error Handling

### HTTP Status Codes

- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Invalid API keys
- `403 Forbidden`: Trading disabled or insufficient buying power
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Alpaca server error

### Error Response Format

```json
{
  "code": 40010001,
  "message": "insufficient buying power"
}
```

### Implementation

```rust
#[derive(Debug, thiserror::Error)]
pub enum AlpacaError {
    #[error("Authentication failed: {0}")]
    AuthenticationFailed(String),

    #[error("Rate limit exceeded, retry after {0}s")]
    RateLimitExceeded(u64),

    #[error("Insufficient buying power")]
    InsufficientBuyingPower,

    #[error("Symbol not found: {0}")]
    SymbolNotFound(String),

    #[error("HTTP error: {0}")]
    HttpError(#[from] reqwest::Error),
}

impl AlpacaClient {
    async fn handle_response<T: for<'de> Deserialize<'de>>(
        &self,
        response: Response,
    ) -> Result<T, AlpacaError> {
        match response.status() {
            StatusCode::OK => Ok(response.json().await?),
            StatusCode::UNAUTHORIZED => {
                Err(AlpacaError::AuthenticationFailed("Invalid API keys".into()))
            }
            StatusCode::FORBIDDEN => {
                let body: ErrorResponse = response.json().await?;
                if body.message.contains("buying power") {
                    Err(AlpacaError::InsufficientBuyingPower)
                } else {
                    Err(AlpacaError::AuthenticationFailed(body.message))
                }
            }
            StatusCode::TOO_MANY_REQUESTS => {
                let retry_after = response
                    .headers()
                    .get("Retry-After")
                    .and_then(|h| h.to_str().ok())
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(60);
                Err(AlpacaError::RateLimitExceeded(retry_after))
            }
            _ => {
                let body: ErrorResponse = response.json().await?;
                Err(AlpacaError::HttpError(reqwest::Error::new(
                    reqwest::ErrorKind::Status(response.status()),
                    body.message,
                )))
            }
        }
    }
}
```

## Rate Limits

### REST API Limits

- **Paper Trading**: Unlimited requests
- **Live Trading**:
  - 200 requests per minute per API key
  - Counted per IP address

### Handling Rate Limits

#### Exponential Backoff

```rust
use tokio::time::{sleep, Duration};

pub async fn retry_with_backoff<F, T, E>(
    mut f: F,
    max_retries: u32,
) -> Result<T, E>
where
    F: FnMut() -> std::pin::Pin<Box<dyn Future<Output = Result<T, E>>>>,
    E: std::fmt::Debug,
{
    let mut delay = Duration::from_secs(1);

    for attempt in 0..max_retries {
        match f().await {
            Ok(result) => return Ok(result),
            Err(e) if attempt < max_retries - 1 => {
                tracing::warn!(?e, attempt, "Request failed, retrying");
                sleep(delay).await;
                delay *= 2;  // Exponential backoff
            }
            Err(e) => return Err(e),
        }
    }

    unreachable!()
}
```

#### Rate Limiter

```rust
use governor::{Quota, RateLimiter};
use std::num::NonZeroU32;

pub struct RateLimitedClient {
    client: AlpacaClient,
    limiter: RateLimiter<DirectRateLimiter>,
}

impl RateLimitedClient {
    pub fn new(client: AlpacaClient) -> Self {
        let quota = Quota::per_minute(NonZeroU32::new(200).unwrap());
        let limiter = RateLimiter::direct(quota);

        Self { client, limiter }
    }

    pub async fn place_order(&self, order: &OrderRequest) -> Result<OrderResponse> {
        self.limiter.until_ready().await;
        self.client.place_order(order).await
    }
}
```

## Best Practices

### 1. Use Paper Trading for Development

Always test with paper trading before deploying to production:

```rust
let client = AlpacaClient::new(api_key, secret_key, true);  // paper_trading = true
```

### 2. Handle WebSocket Reconnections

WebSocket connections can drop. Implement automatic reconnection:

```rust
pub async fn run_websocket_with_reconnect(
    api_key: String,
    secret_key: String,
) -> Result<()> {
    loop {
        match connect_and_stream(&api_key, &secret_key).await {
            Ok(_) => break,  // Normal shutdown
            Err(e) => {
                tracing::error!(?e, "WebSocket disconnected, reconnecting in 5s");
                tokio::time::sleep(Duration::from_secs(5)).await;
            }
        }
    }
    Ok(())
}
```

### 3. Use Client Order IDs

Always set `client_order_id` for order tracking:

```rust
let client_order_id = format!("order-{}-{}", symbol, Utc::now().timestamp_millis());
```

### 4. Validate Orders Before Submission

Check account balance and position limits before placing orders.

### 5. Monitor API Health

Alpaca provides a status page: https://status.alpaca.markets

### 6. Log All API Calls

Use structured logging for debugging:

```rust
#[tracing::instrument(skip(self))]
async fn place_order(&self, order: &OrderRequest) -> Result<OrderResponse> {
    tracing::info!(symbol = %order.symbol, qty = order.qty, "Placing order");
    let response = self.client.place_order(order).await?;
    tracing::info!(order_id = %response.id, "Order placed successfully");
    Ok(response)
}
```

## References

- [Alpaca API Documentation](https://alpaca.markets/docs/api-documentation/)
- [API Rate Limits](https://alpaca.markets/docs/api-documentation/how-to/rate-limit/)
- [Market Data Specification](https://alpaca.markets/docs/api-documentation/api-v2/market-data/)
- [Trading API Reference](https://alpaca.markets/docs/api-documentation/api-v2/orders/)

---

**Last Updated**: 2024-10-14 | **API Version**: v2
