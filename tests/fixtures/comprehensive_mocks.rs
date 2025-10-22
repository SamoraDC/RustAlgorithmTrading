/// Comprehensive test fixtures and mock data generators
/// Provides reusable test data for all test suites

use common::types::*;
use chrono::{Utc, Duration};
use rand::Rng;

/// Mock data builder for orders
pub struct OrderBuilder {
    id: String,
    symbol: String,
    side: OrderSide,
    order_type: OrderType,
    quantity: i32,
    price: Option<f64>,
    status: OrderStatus,
}

impl OrderBuilder {
    pub fn new() -> Self {
        Self {
            id: "test-order".to_string(),
            symbol: "AAPL".to_string(),
            side: OrderSide::Buy,
            order_type: OrderType::Market,
            quantity: 100,
            price: None,
            status: OrderStatus::Pending,
        }
    }

    pub fn id(mut self, id: &str) -> Self {
        self.id = id.to_string();
        self
    }

    pub fn symbol(mut self, symbol: &str) -> Self {
        self.symbol = symbol.to_string();
        self
    }

    pub fn side(mut self, side: OrderSide) -> Self {
        self.side = side;
        self
    }

    pub fn limit_order(mut self, price: f64) -> Self {
        self.order_type = OrderType::Limit;
        self.price = Some(price);
        self
    }

    pub fn market_order(mut self) -> Self {
        self.order_type = OrderType::Market;
        self.price = None;
        self
    }

    pub fn quantity(mut self, qty: i32) -> Self {
        self.quantity = qty;
        self
    }

    pub fn status(mut self, status: OrderStatus) -> Self {
        self.status = status;
        self
    }

    pub fn build(self) -> Order {
        Order {
            id: self.id,
            symbol: self.symbol,
            side: self.side,
            order_type: self.order_type,
            quantity: self.quantity,
            price: self.price,
            status: self.status,
            timestamp: Utc::now(),
        }
    }
}

/// Mock data builder for positions
pub struct PositionBuilder {
    symbol: String,
    quantity: i32,
    average_price: f64,
    current_price: f64,
}

impl PositionBuilder {
    pub fn new() -> Self {
        Self {
            symbol: "AAPL".to_string(),
            quantity: 100,
            average_price: 150.00,
            current_price: 155.00,
        }
    }

    pub fn symbol(mut self, symbol: &str) -> Self {
        self.symbol = symbol.to_string();
        self
    }

    pub fn quantity(mut self, qty: i32) -> Self {
        self.quantity = qty;
        self
    }

    pub fn average_price(mut self, price: f64) -> Self {
        self.average_price = price;
        self
    }

    pub fn current_price(mut self, price: f64) -> Self {
        self.current_price = price;
        self
    }

    pub fn build(self) -> Position {
        let unrealized_pnl = (self.current_price - self.average_price) * self.quantity as f64;

        Position {
            symbol: self.symbol,
            quantity: self.quantity,
            average_price: self.average_price,
            current_price: self.current_price,
            unrealized_pnl,
            realized_pnl: 0.0,
            timestamp: Utc::now(),
        }
    }

    pub fn with_profit(self, profit_percent: f64) -> Self {
        let current_price = self.average_price * (1.0 + profit_percent / 100.0);
        self.current_price(current_price)
    }

    pub fn with_loss(self, loss_percent: f64) -> Self {
        let current_price = self.average_price * (1.0 - loss_percent / 100.0);
        self.current_price(current_price)
    }
}

/// Mock trade generator
pub struct TradeBuilder {
    id: String,
    order_id: String,
    symbol: String,
    side: OrderSide,
    quantity: i32,
    price: f64,
    commission: f64,
}

impl TradeBuilder {
    pub fn new() -> Self {
        Self {
            id: "trade-1".to_string(),
            order_id: "order-1".to_string(),
            symbol: "AAPL".to_string(),
            side: OrderSide::Buy,
            quantity: 100,
            price: 150.00,
            commission: 1.00,
        }
    }

    pub fn id(mut self, id: &str) -> Self {
        self.id = id.to_string();
        self
    }

    pub fn order_id(mut self, order_id: &str) -> Self {
        self.order_id = order_id.to_string();
        self
    }

    pub fn symbol(mut self, symbol: &str) -> Self {
        self.symbol = symbol.to_string();
        self
    }

    pub fn side(mut self, side: OrderSide) -> Self {
        self.side = side;
        self
    }

    pub fn quantity(mut self, qty: i32) -> Self {
        self.quantity = qty;
        self
    }

    pub fn price(mut self, price: f64) -> Self {
        self.price = price;
        self
    }

    pub fn commission(mut self, comm: f64) -> Self {
        self.commission = comm;
        self
    }

    pub fn build(self) -> Trade {
        Trade {
            id: self.id,
            order_id: self.order_id,
            symbol: self.symbol,
            side: self.side,
            quantity: self.quantity,
            price: self.price,
            commission: self.commission,
            timestamp: Utc::now(),
        }
    }
}

/// Random data generators
pub struct RandomGenerator;

impl RandomGenerator {
    pub fn random_order() -> Order {
        let mut rng = rand::thread_rng();

        let side = if rng.gen_bool(0.5) {
            OrderSide::Buy
        } else {
            OrderSide::Sell
        };

        let order_type = if rng.gen_bool(0.5) {
            OrderType::Market
        } else {
            OrderType::Limit
        };

        let price = if matches!(order_type, OrderType::Limit) {
            Some(rng.gen_range(50.0..500.0))
        } else {
            None
        };

        Order {
            id: format!("order-{}", rng.gen::<u64>()),
            symbol: Self::random_symbol(),
            side,
            order_type,
            quantity: rng.gen_range(1..1000),
            price,
            status: OrderStatus::Pending,
            timestamp: Utc::now(),
        }
    }

    pub fn random_symbol() -> String {
        let symbols = vec!["AAPL", "TSLA", "NVDA", "GOOG", "MSFT", "AMZN", "META"];
        let mut rng = rand::thread_rng();
        symbols[rng.gen_range(0..symbols.len())].to_string()
    }

    pub fn random_price(min: f64, max: f64) -> f64 {
        let mut rng = rand::thread_rng();
        rng.gen_range(min..max)
    }

    pub fn random_quantity(min: i32, max: i32) -> i32 {
        let mut rng = rand::thread_rng();
        rng.gen_range(min..max)
    }

    pub fn random_tick(symbol: &str) -> Tick {
        let mut rng = rand::thread_rng();

        Tick {
            symbol: symbol.to_string(),
            price: rng.gen_range(50.0..500.0),
            volume: rng.gen_range(100..10000),
            timestamp: Utc::now(),
        }
    }

    pub fn random_bar(symbol: &str) -> Bar {
        let mut rng = rand::thread_rng();

        let open = rng.gen_range(100.0..300.0);
        let close = rng.gen_range(100.0..300.0);
        let high = open.max(close) + rng.gen_range(0.0..10.0);
        let low = open.min(close) - rng.gen_range(0.0..10.0);

        Bar {
            symbol: symbol.to_string(),
            open,
            high,
            low,
            close,
            volume: rng.gen_range(10000..1000000),
            timestamp: Utc::now(),
            timeframe: "1m".to_string(),
        }
    }

    pub fn random_orderbook(symbol: &str, depth: usize) -> (Vec<PriceLevel>, Vec<PriceLevel>) {
        let mut rng = rand::thread_rng();
        let mid_price = rng.gen_range(100.0..500.0);

        let mut bids = Vec::new();
        let mut asks = Vec::new();

        for i in 0..depth {
            bids.push(PriceLevel {
                price: mid_price - (i as f64 * 0.01),
                volume: rng.gen_range(100..10000),
            });

            asks.push(PriceLevel {
                price: mid_price + (i as f64 * 0.01),
                volume: rng.gen_range(100..10000),
            });
        }

        (bids, asks)
    }
}

/// Historical data generator
pub struct HistoricalDataGenerator;

impl HistoricalDataGenerator {
    pub fn generate_ticks(symbol: &str, count: usize, start_price: f64) -> Vec<Tick> {
        let mut rng = rand::thread_rng();
        let mut price = start_price;
        let mut ticks = Vec::new();
        let mut timestamp = Utc::now() - Duration::hours(1);

        for _ in 0..count {
            // Random walk
            price += rng.gen_range(-0.50..0.50);
            price = price.max(1.0); // Keep positive

            ticks.push(Tick {
                symbol: symbol.to_string(),
                price,
                volume: rng.gen_range(100..1000),
                timestamp,
            });

            timestamp = timestamp + Duration::milliseconds(100);
        }

        ticks
    }

    pub fn generate_bars(symbol: &str, count: usize, timeframe: &str) -> Vec<Bar> {
        let mut rng = rand::thread_rng();
        let mut bars = Vec::new();
        let mut timestamp = Utc::now() - Duration::hours(24);
        let mut prev_close = 150.0;

        for _ in 0..count {
            let open = prev_close + rng.gen_range(-2.0..2.0);
            let close = open + rng.gen_range(-5.0..5.0);
            let high = open.max(close) + rng.gen_range(0.0..3.0);
            let low = open.min(close) - rng.gen_range(0.0..3.0);

            bars.push(Bar {
                symbol: symbol.to_string(),
                open,
                high,
                low,
                close,
                volume: rng.gen_range(10000..100000),
                timestamp,
                timeframe: timeframe.to_string(),
            });

            prev_close = close;
            timestamp = timestamp + Duration::minutes(1);
        }

        bars
    }

    pub fn generate_trend_bars(
        symbol: &str,
        count: usize,
        start_price: f64,
        trend: f64, // Positive = uptrend, negative = downtrend
    ) -> Vec<Bar> {
        let mut rng = rand::thread_rng();
        let mut bars = Vec::new();
        let mut timestamp = Utc::now() - Duration::hours(24);
        let mut current_price = start_price;

        for _ in 0..count {
            current_price += trend;

            let open = current_price + rng.gen_range(-1.0..1.0);
            let close = current_price + rng.gen_range(-1.0..1.0);
            let high = open.max(close) + rng.gen_range(0.0..2.0);
            let low = open.min(close) - rng.gen_range(0.0..2.0);

            bars.push(Bar {
                symbol: symbol.to_string(),
                open,
                high,
                low,
                close,
                volume: rng.gen_range(10000..100000),
                timestamp,
                timeframe: "1m".to_string(),
            });

            timestamp = timestamp + Duration::minutes(1);
        }

        bars
    }
}

/// Scenario generators
pub struct ScenarioGenerator;

impl ScenarioGenerator {
    /// Generate a profitable trading scenario
    pub fn profitable_trades(symbol: &str, count: usize) -> Vec<Trade> {
        let mut trades = Vec::new();

        for i in 0..count {
            let buy_price = 150.0 + (i as f64 * 0.1);
            let sell_price = buy_price + 5.0; // $5 profit per share

            trades.push(TradeBuilder::new()
                .id(&format!("buy-{}", i))
                .symbol(symbol)
                .side(OrderSide::Buy)
                .quantity(100)
                .price(buy_price)
                .build());

            trades.push(TradeBuilder::new()
                .id(&format!("sell-{}", i))
                .symbol(symbol)
                .side(OrderSide::Sell)
                .quantity(100)
                .price(sell_price)
                .build());
        }

        trades
    }

    /// Generate a losing trading scenario
    pub fn losing_trades(symbol: &str, count: usize) -> Vec<Trade> {
        let mut trades = Vec::new();

        for i in 0..count {
            let buy_price = 150.0 + (i as f64 * 0.1);
            let sell_price = buy_price - 3.0; // $3 loss per share

            trades.push(TradeBuilder::new()
                .id(&format!("buy-{}", i))
                .symbol(symbol)
                .side(OrderSide::Buy)
                .quantity(100)
                .price(buy_price)
                .build());

            trades.push(TradeBuilder::new()
                .id(&format!("sell-{}", i))
                .symbol(symbol)
                .side(OrderSide::Sell)
                .quantity(100)
                .price(sell_price)
                .build());
        }

        trades
    }

    /// Generate volatile market conditions
    pub fn volatile_market(symbol: &str, duration_minutes: usize) -> Vec<Bar> {
        let mut rng = rand::thread_rng();
        let mut bars = Vec::new();
        let mut timestamp = Utc::now() - Duration::minutes(duration_minutes as i64);
        let mut price = 150.0;

        for _ in 0..duration_minutes {
            // High volatility: large price swings
            let change_percent = rng.gen_range(-5.0..5.0);
            price *= 1.0 + (change_percent / 100.0);

            let open = price;
            let close = price * (1.0 + rng.gen_range(-3.0..3.0) / 100.0);
            let high = open.max(close) * (1.0 + rng.gen_range(0.0..2.0) / 100.0);
            let low = open.min(close) * (1.0 - rng.gen_range(0.0..2.0) / 100.0);

            bars.push(Bar {
                symbol: symbol.to_string(),
                open,
                high,
                low,
                close,
                volume: rng.gen_range(50000..500000), // High volume
                timestamp,
                timeframe: "1m".to_string(),
            });

            price = close;
            timestamp = timestamp + Duration::minutes(1);
        }

        bars
    }
}
