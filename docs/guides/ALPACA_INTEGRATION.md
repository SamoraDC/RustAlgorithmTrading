# Alpaca API Integration Guide
## Trading System Integration with Alpaca Markets

**Version**: 1.0.0
**Last Updated**: October 21, 2025
**Alpaca API Version**: v2
**Documentation**: https://alpaca.markets/docs/

---

## Table of Contents

1. [Overview](#overview)
2. [Account Setup](#account-setup)
3. [API Authentication](#api-authentication)
4. [Paper Trading Setup](#paper-trading-setup)
5. [WebSocket Integration](#websocket-integration)
6. [REST API Integration](#rest-api-integration)
7. [Rate Limiting](#rate-limiting)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## 1. Overview

### Alpaca Markets Platform

**Alpaca** is a commission-free API-first stock brokerage platform designed for algorithmic trading.

**Key Features**:
- Commission-free stock trading
- Real-time market data via WebSocket
- Paper trading environment for testing
- Fractional shares support
- Instant execution
- No minimum balance requirement

**Supported Markets**:
- US Equities (NYSE, NASDAQ, AMEX)
- ETFs
- Cryptocurrencies (limited support)

**Trading Hours**:
- Regular: 9:30 AM - 4:00 PM ET
- Pre-market: 4:00 AM - 9:30 AM ET (limited)
- After-hours: 4:00 PM - 8:00 PM ET (limited)

---

## 2. Account Setup

### 2.1 Create Alpaca Account

1. **Sign Up**:
   - Navigate to: https://alpaca.markets/
   - Click "Get Started" or "Sign Up"
   - Choose account type: Individual or Entity

2. **Complete Application**:
   - Personal information
   - Employment information
   - Financial information
   - Trading experience
   - Identity verification (SSN, driver's license)

3. **Account Approval**:
   - Wait for approval (typically 1-2 business days)
   - Check email for approval notification

4. **Funding** (for live trading):
   - Link bank account via Plaid
   - Initiate ACH transfer
   - Wait for funds to settle (1-3 business days)

### 2.2 Generate API Keys

1. **Access API Keys**:
   - Log in to Alpaca dashboard
   - Navigate to "API Keys" section
   - Click "Generate New Key"

2. **Paper Trading Keys**:
   - Endpoint: `https://paper-api.alpaca.markets`
   - Use for testing and development
   - Free unlimited paper trading

3. **Live Trading Keys**:
   - Endpoint: `https://api.alpaca.markets`
   - Use for real money trading
   - **CRITICAL**: Keep keys secure!

4. **Key Security**:
   ```bash
   # Store keys securely (NEVER commit to git)
   echo "ALPACA_API_KEY=your_key_here" >> .env.production
   echo "ALPACA_API_SECRET=your_secret_here" >> .env.production
   chmod 600 .env.production
   ```

### 2.3 Configure Trading Permissions

**Dashboard Settings**:
- Enable/disable options trading
- Enable/disable margin trading
- Set day trade protection
- Configure pattern day trader (PDT) protection

**API Restrictions**:
- IP whitelisting (recommended for production)
- Enable/disable specific API endpoints
- Set rate limits

---

## 3. API Authentication

### 3.1 Authentication Methods

**HTTP Header Authentication** (recommended):
```bash
curl -X GET "https://api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: YOUR_API_KEY" \
  -H "APCA-API-SECRET-KEY: YOUR_SECRET_KEY"
```

**Our Implementation** (`rust/execution-engine/src/router.rs`):
```rust
pub async fn route(&self, order: Order, current_market_price: Option<f64>) -> Result<AlpacaOrderResponse> {
    let http_client = self.http_client.clone();
    let config = self.config.clone();

    // Build authenticated request
    let response = http_client
        .post(&format!("{}/orders", config.exchange_api_url))
        .header("APCA-API-KEY-ID", config.api_key.as_ref()
            .ok_or_else(|| TradingError::Configuration("API key not configured".into()))?)
        .header("APCA-API-SECRET-KEY", config.api_secret.as_ref()
            .ok_or_else(|| TradingError::Configuration("API secret not configured".into()))?)
        .json(&alpaca_order)
        .send()
        .await?;

    // Handle response...
}
```

### 3.2 Security Best Practices

**DO**:
- ✅ Use HTTPS exclusively
- ✅ Store credentials in environment variables
- ✅ Rotate API keys every 90 days
- ✅ Use different keys for paper/live trading
- ✅ Monitor API key usage
- ✅ Revoke compromised keys immediately

**DON'T**:
- ❌ Hard-code API keys in source code
- ❌ Commit `.env` files to version control
- ❌ Share API keys via email/chat
- ❌ Use same keys across environments
- ❌ Log API keys or secrets

### 3.3 Credential Validation

```bash
# Test API connectivity
curl -X GET "https://api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}"

# Expected response (HTTP 200):
{
  "id": "904837e3-3b76-47ec-b432-046db621571b",
  "account_number": "010203ABCD",
  "status": "ACTIVE",
  "currency": "USD",
  "buying_power": "262113.632",
  "cash": "23781.82",
  "portfolio_value": "103820.56",
  "pattern_day_trader": false,
  "trading_blocked": false,
  "transfers_blocked": false,
  "account_blocked": false
}
```

---

## 4. Paper Trading Setup

### 4.1 Enable Paper Trading Mode

**Configuration** (`config/system.json`):
```json
{
  "execution": {
    "exchange_api_url": "https://paper-api.alpaca.markets/v2",
    "api_key": null,  // Load from .env
    "api_secret": null,  // Load from .env
    "paper_trading": true  // CRITICAL: Set to true for paper trading
  }
}
```

**Environment Variables**:
```bash
# .env (for paper trading)
ALPACA_API_KEY=PK1234567890ABCDEF  # Paper trading key
ALPACA_API_SECRET=abcdef1234567890
ALPACA_API_URL=https://paper-api.alpaca.markets
PAPER_TRADING=true
```

### 4.2 Paper Trading Features

**Virtual Funds**:
- Default: $100,000 starting balance
- Can be reset via dashboard
- Unlimited resets

**Market Data**:
- Real-time market data from IEX
- Same data as live trading
- Free tier: 200 symbols, 15-minute delay
- Unlimited tier: Real-time data ($9/month)

**Order Execution**:
- Simulated fills based on NBBO
- Realistic slippage simulation
- Same order types as live trading
- Instant execution (no queue)

**Limitations**:
- No extended hours trading simulation
- Simplified fill simulation
- May not reflect extreme market conditions

### 4.3 Switching to Live Trading

**CRITICAL SAFETY CHECKLIST**:
- [ ] Paper trading successful for minimum 1 week
- [ ] All tests passing
- [ ] Circuit breaker tested and working
- [ ] Risk limits configured appropriately
- [ ] Monitoring and alerts configured
- [ ] Team trained on emergency procedures
- [ ] Funding confirmed in Alpaca account

**Configuration Changes**:
```bash
# Update .env.production
ALPACA_API_KEY=AK1234567890ABCDEF  # LIVE trading key (different from paper)
ALPACA_API_SECRET=abcdef1234567890  # LIVE secret
ALPACA_API_URL=https://api.alpaca.markets
PAPER_TRADING=false  # CRITICAL: Set to false

# Update config/system.production.json
{
  "execution": {
    "exchange_api_url": "https://api.alpaca.markets/v2",
    "paper_trading": false
  }
}
```

**Gradual Rollout**:
1. Start with 10% of target position sizes
2. Monitor for 3-5 trading days
3. Increase to 50% if successful
4. Full size after 2 weeks of stable operation

---

## 5. WebSocket Integration

### 5.1 WebSocket Overview

**Endpoints**:
- **IEX Data** (free): `wss://stream.data.alpaca.markets/v2/iex`
- **SIP Data** (paid): `wss://stream.data.alpaca.markets/v2/sip`

**Data Streams**:
- Trades: Real-time trade executions
- Quotes: Best bid/ask updates
- Bars: Aggregated OHLCV data (1min, 5min, etc.)

### 5.2 Our WebSocket Implementation

**Connection** (`rust/market-data/src/websocket.rs`):
```rust
pub async fn connect<F>(&self, mut on_message: F) -> Result<()>
where
    F: FnMut(AlpacaMessage) -> Result<()>,
{
    let url = &self.config.websocket_url;  // wss://stream.data.alpaca.markets/v2/iex

    loop {
        match self.connect_websocket(url, &mut on_message).await {
            Ok(_) => info!("WebSocket connection closed normally"),
            Err(e) => {
                error!("WebSocket error: {}. Reconnecting in {} ms", e, self.config.reconnect_delay_ms);
                sleep(Duration::from_millis(self.config.reconnect_delay_ms)).await;
            }
        }
    }
}

async fn connect_websocket<F>(&self, url: &str, on_message: &mut F) -> Result<()>
where
    F: FnMut(AlpacaMessage) -> Result<()>,
{
    let (ws_stream, _) = connect_async(url).await
        .map_err(|e| TradingError::Network(format!("WebSocket connection failed: {}", e)))?;

    let (mut write, mut read) = ws_stream.split();

    // Authenticate
    let auth_msg = json!({
        "action": "auth",
        "key": self.api_key,
        "secret": self.api_secret
    });
    write.send(Message::Text(auth_msg.to_string())).await?;

    // Subscribe to symbols
    let subscribe_msg = json!({
        "action": "subscribe",
        "trades": self.symbols,
        "quotes": self.symbols,
        "bars": self.symbols
    });
    write.send(Message::Text(subscribe_msg.to_string())).await?;

    // Process messages
    while let Some(message) = read.next().await {
        match message? {
            Message::Text(text) => self.handle_text_message(&text, on_message)?,
            Message::Close(_) => break,
            _ => {}
        }
    }

    Ok(())
}
```

### 5.3 Message Types

**Trade Message**:
```json
{
  "T": "t",  // Message type: trade
  "S": "AAPL",  // Symbol
  "i": 52983525029461,  // Trade ID
  "x": "V",  // Exchange
  "p": 175.25,  // Price
  "s": 100,  // Size
  "t": "2021-02-22T15:51:44.208Z",  // Timestamp
  "c": ["@"],  // Conditions
  "z": "C"  // Tape
}
```

**Quote Message**:
```json
{
  "T": "q",  // Message type: quote
  "S": "AAPL",  // Symbol
  "bx": "V",  // Bid exchange
  "bp": 175.24,  // Bid price
  "bs": 200,  // Bid size
  "ax": "P",  // Ask exchange
  "ap": 175.26,  // Ask price
  "as": 100,  // Ask size
  "t": "2021-02-22T15:51:44.208Z",  // Timestamp
  "c": ["R"]  // Conditions
}
```

**Bar Message** (1-minute OHLCV):
```json
{
  "T": "b",  // Message type: bar
  "S": "AAPL",  // Symbol
  "o": 175.20,  // Open
  "h": 175.30,  // High
  "l": 175.15,  // Low
  "c": 175.25,  // Close
  "v": 15000,  // Volume
  "t": "2021-02-22T15:51:00Z",  // Timestamp
  "n": 150,  // Number of trades
  "vw": 175.22  // Volume-weighted average price
}
```

### 5.4 Reconnection Strategy

**Automatic Reconnection** (already implemented):
```rust
// Reconnect on failure
Err(e) => {
    error!("WebSocket error: {}. Reconnecting in {} ms", e, self.config.reconnect_delay_ms);
    sleep(Duration::from_millis(self.config.reconnect_delay_ms)).await;
}
```

**Best Practices**:
- ✅ Exponential backoff (5s, 10s, 20s, 40s, max 60s)
- ✅ Heartbeat/ping-pong to detect stale connections
- ✅ Automatic resubscription after reconnect
- ✅ Buffer messages during reconnection
- ✅ Alert on prolonged disconnection (>1 minute)

---

## 6. REST API Integration

### 6.1 Account Information

**Get Account Details**:
```bash
GET /v2/account

# Response:
{
  "account_number": "010203ABCD",
  "status": "ACTIVE",
  "currency": "USD",
  "buying_power": "262113.632",
  "cash": "23781.82",
  "portfolio_value": "103820.56",
  "pattern_day_trader": false,
  "trading_blocked": false,
  "daytrade_count": 0,
  "last_equity": "103820.56"
}
```

### 6.2 Order Management

**Submit Market Order**:
```rust
POST /v2/orders
{
  "symbol": "AAPL",
  "qty": 100,
  "side": "buy",
  "type": "market",
  "time_in_force": "day"
}
```

**Submit Limit Order**:
```rust
POST /v2/orders
{
  "symbol": "AAPL",
  "qty": 100,
  "side": "buy",
  "type": "limit",
  "limit_price": 175.00,
  "time_in_force": "gtc"  // Good 'til canceled
}
```

**Submit Stop-Loss Order**:
```rust
POST /v2/orders
{
  "symbol": "AAPL",
  "qty": 100,
  "side": "sell",
  "type": "stop",
  "stop_price": 170.00,
  "time_in_force": "gtc"
}
```

**Cancel Order**:
```bash
DELETE /v2/orders/{order_id}
```

**Get Order Status**:
```bash
GET /v2/orders/{order_id}

# Response:
{
  "id": "61e69015-8549-4bfd-b9c3-01e75843f47d",
  "client_order_id": "eb9e2aaa-f71a-4f51-b5b4-52a6c565dad4",
  "created_at": "2021-03-16T18:38:01.942282Z",
  "updated_at": "2021-03-16T18:38:01.942282Z",
  "submitted_at": "2021-03-16T18:38:01.937734Z",
  "filled_at": "2021-03-16T18:38:01.942282Z",
  "expired_at": null,
  "canceled_at": null,
  "failed_at": null,
  "replaced_at": null,
  "replaced_by": null,
  "replaces": null,
  "asset_id": "b0b6dd9d-8b9b-48a9-ba46-b9d54906e415",
  "symbol": "AAPL",
  "asset_class": "us_equity",
  "notional": null,
  "qty": "100",
  "filled_qty": "100",
  "filled_avg_price": "125.74",
  "order_class": "",
  "order_type": "market",
  "type": "market",
  "side": "buy",
  "time_in_force": "day",
  "limit_price": null,
  "stop_price": null,
  "status": "filled",
  "extended_hours": false,
  "legs": null,
  "trail_percent": null,
  "trail_price": null,
  "hwm": null
}
```

### 6.3 Position Management

**Get All Positions**:
```bash
GET /v2/positions

# Response:
[
  {
    "asset_id": "b0b6dd9d-8b9b-48a9-ba46-b9d54906e415",
    "symbol": "AAPL",
    "exchange": "NASDAQ",
    "asset_class": "us_equity",
    "qty": "100",
    "avg_entry_price": "175.25",
    "side": "long",
    "market_value": "17600.00",
    "cost_basis": "17525.00",
    "unrealized_pl": "75.00",
    "unrealized_plpc": "0.0043",
    "current_price": "176.00",
    "lastday_price": "175.50",
    "change_today": "0.0028"
  }
]
```

**Close Position**:
```bash
DELETE /v2/positions/{symbol}
```

### 6.4 Market Data

**Get Latest Trade**:
```bash
GET /v2/stocks/{symbol}/trades/latest

# Response:
{
  "symbol": "AAPL",
  "trade": {
    "t": "2021-02-22T15:51:44.208Z",
    "x": "V",
    "p": 175.25,
    "s": 100,
    "c": ["@"],
    "i": 52983525029461,
    "z": "C"
  }
}
```

**Get Latest Quote**:
```bash
GET /v2/stocks/{symbol}/quotes/latest

# Response:
{
  "symbol": "AAPL",
  "quote": {
    "t": "2021-02-22T15:51:44.208Z",
    "ax": "P",
    "ap": 175.26,
    "as": 100,
    "bx": "V",
    "bp": 175.24,
    "bs": 200,
    "c": ["R"]
  }
}
```

---

## 7. Rate Limiting

### 7.1 Alpaca Rate Limits

**REST API Limits**:
- **Default**: 200 requests per minute
- **Burst**: Up to 300 requests in short bursts
- **Penalty**: HTTP 429 (Too Many Requests) + cooldown period

**WebSocket Limits**:
- No explicit rate limit
- Fair usage policy applies
- Excessive usage may result in throttling

### 7.2 Our Rate Limiting Implementation

**Governor-based Rate Limiter** (`rust/execution-engine/src/router.rs`):
```rust
use governor::{Quota, RateLimiter, state::InMemoryState};
use nonzero_ext::nonzero;

pub struct OrderRouter {
    rate_limiter: Arc<RateLimiter<NotKeyed, InMemoryState, DefaultClock>>,
    // ...
}

impl OrderRouter {
    pub fn new(config: ExecutionConfig) -> Result<Self> {
        // Configure rate limiter (200 requests/second with config)
        let quota = Quota::per_second(nonzero!(config.rate_limit_per_second));
        let rate_limiter = Arc::new(RateLimiter::direct(quota));

        Ok(Self {
            rate_limiter,
            // ...
        })
    }

    pub async fn route(&self, order: Order) -> Result<AlpacaOrderResponse> {
        // Wait for rate limit token
        self.rate_limiter.until_ready().await;

        // Proceed with order submission
        // ...
    }
}
```

**Configuration** (`config/system.production.json`):
```json
{
  "execution": {
    "rate_limit_per_second": 200,  // Stay below Alpaca's 200/min limit
    "rate_limit_burst": 10  // Allow small bursts
  }
}
```

### 7.3 Handling Rate Limit Errors

**HTTP 429 Response**:
```json
{
  "code": 42910000,
  "message": "rate limit exceeded"
}
```

**Retry Strategy**:
```rust
// Exponential backoff with jitter
let retry_policy = ExponentialBackoff::builder()
    .retry_bounds(Duration::from_secs(1), Duration::from_secs(60))
    .jitter(Jitter::Full)
    .build_with_max_retries(3);

retry_policy.execute(|| async {
    match self.submit_order(&order).await {
        Ok(response) => Ok(response),
        Err(TradingError::RateLimit) => {
            warn!("Rate limit hit, retrying...");
            Err(backoff::Error::Transient(TradingError::RateLimit))
        }
        Err(e) => Err(backoff::Error::Permanent(e)),
    }
}).await
```

---

## 8. Error Handling

### 8.1 Common API Errors

| HTTP Code | Error | Cause | Solution |
|-----------|-------|-------|----------|
| 401 | Unauthorized | Invalid API key | Verify credentials |
| 403 | Forbidden | Account blocked | Contact support |
| 404 | Not Found | Invalid symbol/order ID | Verify input |
| 422 | Unprocessable Entity | Invalid order parameters | Check order details |
| 429 | Too Many Requests | Rate limit exceeded | Implement backoff |
| 500 | Internal Server Error | Alpaca issue | Retry with backoff |
| 503 | Service Unavailable | Maintenance | Wait and retry |

### 8.2 Order Rejection Reasons

**Insufficient Funds**:
```json
{
  "code": 40310000,
  "message": "insufficient buying power"
}
```
**Solution**: Check account buying power before submitting orders

**Market Closed**:
```json
{
  "code": 40310000,
  "message": "market is closed"
}
```
**Solution**: Verify market hours, use GTD (Good 'Til Date) orders

**Invalid Symbol**:
```json
{
  "code": 40410000,
  "message": "symbol not found"
}
```
**Solution**: Validate symbols before submission

**Position Limit**:
```json
{
  "code": 40310000,
  "message": "pattern day trader protection"
}
```
**Solution**: Check PDT status, reduce order frequency

### 8.3 Error Logging

```rust
match self.submit_order(&order).await {
    Ok(response) => {
        info!("Order submitted: {} {} {} @ ${}",
            response.id, order.symbol, order.side, response.filled_avg_price);
        Ok(response)
    }
    Err(TradingError::RateLimit) => {
        warn!("Rate limit exceeded for order: {:?}", order);
        Err(TradingError::RateLimit)
    }
    Err(TradingError::InsufficientFunds) => {
        error!("Insufficient funds for order: {:?}. Buying power: ${}",
            order, account.buying_power);
        Err(TradingError::InsufficientFunds)
    }
    Err(e) => {
        error!("Order submission failed: {:?}. Error: {}", order, e);
        Err(e)
    }
}
```

---

## 9. Best Practices

### 9.1 Order Submission

**Pre-Submission Validation**:
```rust
// Validate order before submission
fn validate_order(order: &Order, account: &Account) -> Result<()> {
    // Check buying power
    let order_value = order.quantity as f64 * order.price.unwrap_or(0.0);
    if order_value > account.buying_power {
        return Err(TradingError::InsufficientFunds);
    }

    // Check market hours
    if !is_market_open() && !order.extended_hours {
        return Err(TradingError::MarketClosed);
    }

    // Check symbol validity
    if !is_valid_symbol(&order.symbol) {
        return Err(TradingError::InvalidSymbol);
    }

    // Check position limits
    if account.positions.len() >= 10 {
        return Err(TradingError::PositionLimitExceeded);
    }

    Ok(())
}
```

### 9.2 Position Reconciliation

**Daily Reconciliation**:
```rust
// Compare local positions with Alpaca positions
async fn reconcile_positions() -> Result<()> {
    let local_positions = get_local_positions().await?;
    let alpaca_positions = get_alpaca_positions().await?;

    for (symbol, local_pos) in local_positions {
        match alpaca_positions.get(&symbol) {
            Some(alpaca_pos) => {
                if local_pos.quantity != alpaca_pos.quantity {
                    error!("Position mismatch for {}: local={}, alpaca={}",
                        symbol, local_pos.quantity, alpaca_pos.quantity);
                    // Reconcile: trust Alpaca positions
                    update_local_position(symbol, alpaca_pos).await?;
                }
            }
            None => {
                warn!("Local position {} not found in Alpaca", symbol);
                // Remove stale local position
                delete_local_position(symbol).await?;
            }
        }
    }

    Ok(())
}
```

**Run reconciliation**:
- Before market open (9:00 AM ET)
- After market close (4:15 PM ET)
- After any system restart

### 9.3 Monitoring

**Key Metrics**:
```promql
# Order submission success rate
sum(rate(orders_submitted_total{status="filled"}[5m]))
/
sum(rate(orders_submitted_total[5m]))

# API latency
histogram_quantile(0.95, rate(alpaca_api_request_duration_seconds_bucket[5m]))

# WebSocket message lag
alpaca_websocket_message_lag_seconds

# Rate limit usage
rate(alpaca_rate_limit_hits_total[5m])
```

---

## 10. Troubleshooting

### Issue: WebSocket Disconnects Frequently

**Symptoms**: Frequent reconnections, data gaps

**Diagnosis**:
```bash
journalctl -u trading-market-data | grep "WebSocket"
```

**Common Causes**:
- Network instability
- Firewall blocking WebSocket
- Invalid authentication
- Alpaca service issue

**Solutions**:
```bash
# Test WebSocket manually
wscat -c "wss://stream.data.alpaca.markets/v2/iex"

# Check firewall
sudo ufw status
sudo ufw allow out 443/tcp

# Verify credentials
curl -X GET "https://api.alpaca.markets/v2/account" \
  -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}"

# Check Alpaca status
curl https://status.alpaca.markets/api/v2/status.json
```

---

### Issue: Orders Not Executing

**Symptoms**: Orders stuck in "new" or "pending" status

**Diagnosis**:
```bash
# Check order status
curl -X GET "https://api.alpaca.markets/v2/orders" \
  -H "APCA-API-KEY-ID: ${ALPACA_API_KEY}" \
  -H "APCA-API-SECRET-KEY: ${ALPACA_API_SECRET}"
```

**Common Causes**:
- Market closed
- Limit price not reached
- Insufficient liquidity
- Account restrictions

**Solutions**:
- Verify market hours
- Check limit price vs current price
- Use market orders for guaranteed execution
- Review account status

---

### Issue: Rate Limit Errors

**Symptoms**: HTTP 429 errors

**Diagnosis**:
```bash
grep "429" /opt/trading-system/logs/execution-engine.log
```

**Solutions**:
```rust
// Reduce rate limit in config
{
  "execution": {
    "rate_limit_per_second": 150  // Reduced from 200
  }
}

// Add request throttling
use tokio::time::{sleep, Duration};
sleep(Duration::from_millis(100)).await;  // Add delay between requests
```

---

## Additional Resources

**Official Documentation**:
- API Docs: https://alpaca.markets/docs/api-references/trading-api/
- WebSocket Docs: https://alpaca.markets/docs/api-references/market-data-api/stock-pricing-data/realtime/
- Forum: https://forum.alpaca.markets/

**Status Page**:
- https://status.alpaca.markets/

**Support**:
- Email: support@alpaca.markets
- Response time: 24-48 hours

---

**Document Version**: 1.0.0
**Last Updated**: October 21, 2025
**Maintained By**: Documentation Specialist Agent
