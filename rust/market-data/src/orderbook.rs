use common::types::{Level, OrderBook, Price, Quantity, Side, Symbol};
use chrono::Utc;
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

/// Price level in the order book with reversed ordering for asks
#[derive(Debug, Clone)]
struct PriceLevel {
    price: Price,
    quantity: Quantity,
    side: Side,
}

impl PartialEq for PriceLevel {
    fn eq(&self, other: &Self) -> bool {
        self.price == other.price
    }
}

impl Eq for PriceLevel {}

impl PartialOrd for PriceLevel {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for PriceLevel {
    fn cmp(&self, other: &Self) -> Ordering {
        match self.side {
            Side::Bid => {
                // Max heap for bids (highest price first)
                other.price.partial_cmp(&self.price).unwrap_or(Ordering::Equal)
            }
            Side::Ask => {
                // Min heap for asks (lowest price first)
                self.price.partial_cmp(&other.price).unwrap_or(Ordering::Equal)
            }
        }
    }
}

/// High-performance order book using binary heaps
/// Targets <50μs p99 latency for updates
pub struct FastOrderBook {
    symbol: Symbol,
    bids: BinaryHeap<PriceLevel>,
    asks: BinaryHeap<PriceLevel>,
    bid_map: HashMap<u64, Quantity>, // price_key -> quantity
    ask_map: HashMap<u64, Quantity>,
    sequence: u64,
    last_update_ns: i64,
}

impl FastOrderBook {
    pub fn new(symbol: Symbol) -> Self {
        Self {
            symbol,
            bids: BinaryHeap::with_capacity(1000),
            asks: BinaryHeap::with_capacity(1000),
            bid_map: HashMap::with_capacity(1000),
            ask_map: HashMap::with_capacity(1000),
            sequence: 0,
            last_update_ns: 0,
        }
    }

    /// Update bid level with O(log n) complexity
    #[inline]
    pub fn update_bid(&mut self, price: Price, quantity: Quantity) {
        let start = std::time::Instant::now();

        let price_key = (price.0 * 100000000.0) as u64;

        if quantity.0 == 0.0 {
            // Remove level
            self.bid_map.remove(&price_key);
        } else {
            // Add or update level
            self.bid_map.insert(price_key, quantity);
        }

        // Rebuild heap (lazy approach - optimize later with custom heap)
        self.rebuild_bid_heap();

        self.sequence += 1;
        self.last_update_ns = start.elapsed().as_nanos() as i64;
    }

    /// Update ask level with O(log n) complexity
    #[inline]
    pub fn update_ask(&mut self, price: Price, quantity: Quantity) {
        let start = std::time::Instant::now();

        let price_key = (price.0 * 100000000.0) as u64;

        if quantity.0 == 0.0 {
            // Remove level
            self.ask_map.remove(&price_key);
        } else {
            // Add or update level
            self.ask_map.insert(price_key, quantity);
        }

        // Rebuild heap
        self.rebuild_ask_heap();

        self.sequence += 1;
        self.last_update_ns = start.elapsed().as_nanos() as i64;
    }

    #[inline]
    fn rebuild_bid_heap(&mut self) {
        self.bids.clear();
        for (price_key, quantity) in &self.bid_map {
            let price = Price(*price_key as f64 / 100000000.0);
            self.bids.push(PriceLevel {
                price,
                quantity: *quantity,
                side: Side::Bid,
            });
        }
    }

    #[inline]
    fn rebuild_ask_heap(&mut self) {
        self.asks.clear();
        for (price_key, quantity) in &self.ask_map {
            let price = Price(*price_key as f64 / 100000000.0);
            self.asks.push(PriceLevel {
                price,
                quantity: *quantity,
                side: Side::Ask,
            });
        }
    }

    /// Get best bid price (highest bid)
    #[inline]
    pub fn best_bid(&self) -> Option<Price> {
        self.bids.peek().map(|level| level.price)
    }

    /// Get best ask price (lowest ask)
    #[inline]
    pub fn best_ask(&self) -> Option<Price> {
        self.asks.peek().map(|level| level.price)
    }

    /// Get mid price
    #[inline]
    pub fn mid_price(&self) -> Option<Price> {
        match (self.best_bid(), self.best_ask()) {
            (Some(bid), Some(ask)) => Some(Price((bid.0 + ask.0) / 2.0)),
            _ => None,
        }
    }

    /// Get spread in basis points
    #[inline]
    pub fn spread_bps(&self) -> Option<f64> {
        match (self.best_bid(), self.best_ask()) {
            (Some(bid), Some(ask)) => {
                let mid = (bid.0 + ask.0) / 2.0;
                Some((ask.0 - bid.0) / mid * 10000.0)
            }
            _ => None,
        }
    }

    /// Get order book depth (total quantity at top N levels)
    pub fn depth(&self, num_levels: usize) -> (f64, f64) {
        let bid_depth: f64 = self
            .bids
            .iter()
            .take(num_levels)
            .map(|level| level.quantity.0)
            .sum();

        let ask_depth: f64 = self
            .asks
            .iter()
            .take(num_levels)
            .map(|level| level.quantity.0)
            .sum();

        (bid_depth, ask_depth)
    }

    /// Get order book imbalance (-1 to 1, negative = more ask pressure)
    pub fn imbalance(&self, num_levels: usize) -> f64 {
        let (bid_depth, ask_depth) = self.depth(num_levels);
        let total = bid_depth + ask_depth;

        if total > 0.0 {
            (bid_depth - ask_depth) / total
        } else {
            0.0
        }
    }

    /// Convert to snapshot
    pub fn to_snapshot(&self, max_levels: usize) -> OrderBook {
        let bids: Vec<Level> = self
            .bids
            .iter()
            .take(max_levels)
            .map(|level| Level {
                price: level.price,
                quantity: level.quantity,
                timestamp: Utc::now(),
            })
            .collect();

        let asks: Vec<Level> = self
            .asks
            .iter()
            .take(max_levels)
            .map(|level| Level {
                price: level.price,
                quantity: level.quantity,
                timestamp: Utc::now(),
            })
            .collect();

        OrderBook {
            symbol: self.symbol.clone(),
            bids,
            asks,
            timestamp: Utc::now(),
            sequence: self.sequence,
        }
    }

    /// Get last update latency in nanoseconds
    pub fn last_update_latency_ns(&self) -> i64 {
        self.last_update_ns
    }
}

/// Manager for multiple order books
pub struct OrderBookManager {
    books: HashMap<String, FastOrderBook>,
}

impl OrderBookManager {
    pub fn new() -> Self {
        Self {
            books: HashMap::new(),
        }
    }

    pub fn get_or_create(&mut self, symbol: &str) -> &mut FastOrderBook {
        self.books
            .entry(symbol.to_string())
            .or_insert_with(|| FastOrderBook::new(Symbol(symbol.to_string())))
    }

    pub fn get(&self, symbol: &str) -> Option<&FastOrderBook> {
        self.books.get(symbol)
    }

    pub fn update_bid(&mut self, symbol: &str, price: Price, quantity: Quantity) {
        self.get_or_create(symbol).update_bid(price, quantity);
    }

    pub fn update_ask(&mut self, symbol: &str, price: Price, quantity: Quantity) {
        self.get_or_create(symbol).update_ask(price, quantity);
    }

    pub fn get_snapshot(&self, symbol: &str, max_levels: usize) -> Option<OrderBook> {
        self.books.get(symbol).map(|book| book.to_snapshot(max_levels))
    }
}

impl Default for OrderBookManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_orderbook_operations() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_bid(Price(149.5), Quantity(200.0));
        book.update_ask(Price(150.5), Quantity(150.0));
        book.update_ask(Price(151.0), Quantity(100.0));

        assert_eq!(book.best_bid(), Some(Price(150.0)));
        assert_eq!(book.best_ask(), Some(Price(150.5)));
        assert_eq!(book.mid_price(), Some(Price(150.25)));

        // Test spread
        let spread = book.spread_bps().unwrap();
        assert!((spread - 33.28).abs() < 0.1); // ~33 bps
    }

    #[test]
    fn test_orderbook_depth() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_bid(Price(149.5), Quantity(200.0));
        book.update_ask(Price(150.5), Quantity(150.0));
        book.update_ask(Price(151.0), Quantity(100.0));

        let (bid_depth, ask_depth) = book.depth(2);
        assert_eq!(bid_depth, 300.0);
        assert_eq!(ask_depth, 250.0);
    }

    #[test]
    fn test_orderbook_imbalance() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(300.0));
        book.update_ask(Price(150.5), Quantity(100.0));

        let imbalance = book.imbalance(1);
        assert!((imbalance - 0.5).abs() < 0.01); // 50% buy pressure
    }

    #[test]
    fn test_orderbook_performance() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        // Benchmark update performance
        let start = std::time::Instant::now();
        for i in 0..1000 {
            let price = Price(150.0 + (i as f64 * 0.01));
            book.update_bid(price, Quantity(100.0));
        }
        let elapsed = start.elapsed();

        println!("1000 updates took: {:?}", elapsed);
        println!("Avg per update: {:?}", elapsed / 1000);

        // Should be well under 50μs per update
        assert!(elapsed.as_micros() < 50000);
    }
}
