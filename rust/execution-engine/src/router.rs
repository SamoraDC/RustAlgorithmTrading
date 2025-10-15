use common::{Result, TradingError, types::Order, config::ExecutionConfig};
use crate::retry::RetryPolicy;
use crate::slippage::SlippageChecker;
use governor::{Quota, RateLimiter, clock::DefaultClock, state::{InMemoryState, NotKeyed}};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::num::NonZeroU32;
use std::sync::Arc;

#[derive(Debug, Serialize, Deserialize)]
pub struct AlpacaOrderRequest {
    pub symbol: String,
    pub qty: f64,
    pub side: String,
    pub r#type: String,
    pub time_in_force: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub limit_price: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stop_price: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub struct AlpacaOrderResponse {
    pub id: String,
    pub status: String,
    pub symbol: String,
    pub qty: String,
    pub filled_qty: String,
    pub side: String,
}

pub struct OrderRouter {
    config: ExecutionConfig,
    retry_policy: RetryPolicy,
    slippage_checker: SlippageChecker,
    rate_limiter: Arc<RateLimiter<NotKeyed, InMemoryState, DefaultClock>>,
    http_client: Client,
}

impl OrderRouter {
    pub fn new(config: ExecutionConfig) -> Result<Self> {
        let retry_policy = RetryPolicy::new(
            config.retry_attempts,
            config.retry_delay_ms,
        );

        let slippage_checker = SlippageChecker::new(50.0); // 50 bps max slippage

        // Create rate limiter (200 requests per minute = ~3.33/sec)
        let quota = Quota::per_second(NonZeroU32::new(config.rate_limit_per_second).unwrap());
        let rate_limiter = Arc::new(RateLimiter::direct(quota));

        let http_client = Client::builder()
            .timeout(std::time::Duration::from_secs(10))
            .build()
            .map_err(|e| TradingError::Network(format!("HTTP client error: {}", e)))?;

        Ok(Self {
            config,
            retry_policy,
            slippage_checker,
            rate_limiter,
            http_client,
        })
    }

    /// Route and execute order with retry logic
    pub async fn route(&self, order: Order, current_market_price: Option<f64>) -> Result<AlpacaOrderResponse> {
        // Check slippage for limit orders
        if let Some(limit_price) = order.price {
            if let Some(market_price) = current_market_price {
                if !self.slippage_checker.check(limit_price.0, market_price) {
                    return Err(TradingError::Risk(format!(
                        "Slippage too high: limit={}, market={}",
                        limit_price.0, market_price
                    )));
                }
            }
        }

        // Execute with retry and rate limiting
        let retry_policy = self.retry_policy.clone();
        let rate_limiter = self.rate_limiter.clone();
        let http_client = self.http_client.clone();
        let config = self.config.clone();

        retry_policy
            .execute(|| async {
                // Wait for rate limiter
                rate_limiter.until_ready().await;

                // Build request
                let alpaca_order = self.build_alpaca_request(&order)?;

                // Send to exchange
                self.send_to_exchange(&http_client, &config, alpaca_order).await
            })
            .await
    }

    fn build_alpaca_request(&self, order: &Order) -> Result<AlpacaOrderRequest> {
        let side = match order.side {
            common::types::Side::Bid => "buy",
            common::types::Side::Ask => "sell",
        };

        let order_type = match order.order_type {
            common::types::OrderType::Market => "market",
            common::types::OrderType::Limit => "limit",
            common::types::OrderType::StopMarket => "stop",
            common::types::OrderType::StopLimit => "stop_limit",
        };

        Ok(AlpacaOrderRequest {
            symbol: order.symbol.0.clone(),
            qty: order.quantity.0,
            side: side.to_string(),
            r#type: order_type.to_string(),
            time_in_force: "gtc".to_string(),
            limit_price: order.price.map(|p| p.0),
            stop_price: order.stop_price.map(|p| p.0),
        })
    }

    async fn send_to_exchange(
        &self,
        client: &Client,
        config: &ExecutionConfig,
        order: AlpacaOrderRequest,
    ) -> Result<AlpacaOrderResponse> {
        if config.paper_trading {
            // Paper trading mode - simulate response
            return Ok(AlpacaOrderResponse {
                id: uuid::Uuid::new_v4().to_string(),
                status: "filled".to_string(),
                symbol: order.symbol.clone(),
                qty: order.qty.to_string(),
                filled_qty: order.qty.to_string(),
                side: order.side.clone(),
            });
        }

        let url = format!("{}/v2/orders", config.exchange_api_url);

        let response = client
            .post(&url)
            .header("APCA-API-KEY-ID", config.api_key.as_ref().unwrap())
            .header("APCA-API-SECRET-KEY", config.api_secret.as_ref().unwrap())
            .json(&order)
            .send()
            .await
            .map_err(|e| TradingError::Network(format!("Request failed: {}", e)))?;

        if !response.status().is_success() {
            let status = response.status();
            let text = response.text().await.unwrap_or_default();
            return Err(TradingError::Exchange(format!(
                "Order rejected: {} - {}",
                status, text
            )));
        }

        response
            .json::<AlpacaOrderResponse>()
            .await
            .map_err(|e| TradingError::Parse(format!("Response parse error: {}", e)))
    }

    /// Fragment large order into smaller pieces (TWAP-style)
    pub async fn execute_twap(
        &self,
        order: Order,
        num_slices: usize,
        interval_ms: u64,
    ) -> Result<Vec<AlpacaOrderResponse>> {
        let slice_qty = order.quantity.0 / num_slices as f64;
        let mut responses = Vec::new();

        for i in 0..num_slices {
            let mut slice_order = order.clone();
            slice_order.quantity = common::types::Quantity(slice_qty);
            slice_order.client_order_id = format!("{}_slice_{}", order.client_order_id, i);

            let response = self.route(slice_order, None).await?;
            responses.push(response);

            if i < num_slices - 1 {
                tokio::time::sleep(tokio::time::Duration::from_millis(interval_ms)).await;
            }
        }

        Ok(responses)
    }

    /// Get order status
    pub async fn get_order_status(&self, order_id: &str) -> Result<AlpacaOrderResponse> {
        self.rate_limiter.until_ready().await;

        let url = format!("{}/v2/orders/{}", self.config.exchange_api_url, order_id);

        let response = self
            .http_client
            .get(&url)
            .header("APCA-API-KEY-ID", self.config.api_key.as_ref().unwrap())
            .header("APCA-API-SECRET-KEY", self.config.api_secret.as_ref().unwrap())
            .send()
            .await
            .map_err(|e| TradingError::Network(format!("Request failed: {}", e)))?;

        response
            .json::<AlpacaOrderResponse>()
            .await
            .map_err(|e| TradingError::Parse(format!("Response parse error: {}", e)))
    }

    /// Cancel order
    pub async fn cancel_order(&self, order_id: &str) -> Result<()> {
        self.rate_limiter.until_ready().await;

        let url = format!("{}/v2/orders/{}", self.config.exchange_api_url, order_id);

        self.http_client
            .delete(&url)
            .header("APCA-API-KEY-ID", self.config.api_key.as_ref().unwrap())
            .header("APCA-API-SECRET-KEY", self.config.api_secret.as_ref().unwrap())
            .send()
            .await
            .map_err(|e| TradingError::Network(format!("Cancel failed: {}", e)))?;

        Ok(())
    }
}
