//! Unit tests for order book manager
//!
//! Tests cover:
//! - Order book creation and updates
//! - Order book retrieval
//! - Order book state management
//! - Edge cases (empty books, multiple symbols)

use chrono::Utc;
use common::types::{OrderBook, Level, Symbol, Price, Quantity};
use market_data::orderbook::OrderBookManager;

#[cfg(test)]
mod orderbook_manager_tests {
    use super::*;

    fn create_test_orderbook(symbol: &str, sequence: u64) -> OrderBook {
        OrderBook {
            symbol: Symbol(symbol.to_string()),
            bids: vec![
                Level {
                    price: Price(100.0),
                    quantity: Quantity(10.0),
                    timestamp: Utc::now(),
                },
                Level {
                    price: Price(99.5),
                    quantity: Quantity(20.0),
                    timestamp: Utc::now(),
                },
            ],
            asks: vec![
                Level {
                    price: Price(100.5),
                    quantity: Quantity(15.0),
                    timestamp: Utc::now(),
                },
                Level {
                    price: Price(101.0),
                    quantity: Quantity(25.0),
                    timestamp: Utc::now(),
                },
            ],
            timestamp: Utc::now(),
            sequence,
        }
    }

    #[test]
    fn test_new_orderbook_manager() {
        let manager = OrderBookManager::new();
        assert!(manager.get("AAPL").is_none());
    }

    #[test]
    fn test_default_orderbook_manager() {
        let manager = OrderBookManager::default();
        assert!(manager.get("AAPL").is_none());
    }

    #[test]
    fn test_update_orderbook() {
        let mut manager = OrderBookManager::new();
        let book = create_test_orderbook("AAPL", 1);

        manager.update(book);

        let retrieved = manager.get("AAPL");
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().symbol, Symbol("AAPL".to_string()));
        assert_eq!(retrieved.unwrap().sequence, 1);
    }

    #[test]
    fn test_update_multiple_symbols() {
        let mut manager = OrderBookManager::new();

        let book1 = create_test_orderbook("AAPL", 1);
        let book2 = create_test_orderbook("MSFT", 2);
        let book3 = create_test_orderbook("GOOGL", 3);

        manager.update(book1);
        manager.update(book2);
        manager.update(book3);

        assert!(manager.get("AAPL").is_some());
        assert!(manager.get("MSFT").is_some());
        assert!(manager.get("GOOGL").is_some());
        assert!(manager.get("TSLA").is_none());
    }

    #[test]
    fn test_update_same_symbol_twice() {
        let mut manager = OrderBookManager::new();

        let book1 = create_test_orderbook("AAPL", 1);
        let book2 = create_test_orderbook("AAPL", 2);

        manager.update(book1);
        manager.update(book2);

        let retrieved = manager.get("AAPL");
        assert!(retrieved.is_some());
        // Should have the latest update (sequence 2)
        assert_eq!(retrieved.unwrap().sequence, 2);
    }

    #[test]
    fn test_get_nonexistent_symbol() {
        let manager = OrderBookManager::new();
        assert!(manager.get("NONEXISTENT").is_none());
    }

    #[test]
    fn test_orderbook_bid_levels() {
        let mut manager = OrderBookManager::new();
        let book = create_test_orderbook("AAPL", 1);

        manager.update(book);

        let retrieved = manager.get("AAPL").unwrap();
        assert_eq!(retrieved.bids.len(), 2);
        assert_eq!(retrieved.bids[0].price, Price(100.0));
        assert_eq!(retrieved.bids[1].price, Price(99.5));
    }

    #[test]
    fn test_orderbook_ask_levels() {
        let mut manager = OrderBookManager::new();
        let book = create_test_orderbook("AAPL", 1);

        manager.update(book);

        let retrieved = manager.get("AAPL").unwrap();
        assert_eq!(retrieved.asks.len(), 2);
        assert_eq!(retrieved.asks[0].price, Price(100.5));
        assert_eq!(retrieved.asks[1].price, Price(101.0));
    }

    #[test]
    fn test_orderbook_spread() {
        let mut manager = OrderBookManager::new();
        let book = create_test_orderbook("AAPL", 1);

        manager.update(book);

        let retrieved = manager.get("AAPL").unwrap();
        let best_bid = retrieved.bids[0].price;
        let best_ask = retrieved.asks[0].price;
        let spread = best_ask.0 - best_bid.0;

        assert_eq!(spread, 0.5);
    }

    #[test]
    fn test_empty_orderbook() {
        let empty_book = OrderBook {
            symbol: Symbol("EMPTY".to_string()),
            bids: vec![],
            asks: vec![],
            timestamp: Utc::now(),
            sequence: 1,
        };

        let mut manager = OrderBookManager::new();
        manager.update(empty_book);

        let retrieved = manager.get("EMPTY").unwrap();
        assert_eq!(retrieved.bids.len(), 0);
        assert_eq!(retrieved.asks.len(), 0);
    }

    #[test]
    fn test_orderbook_sequence_ordering() {
        let mut manager = OrderBookManager::new();

        // Insert out of order
        let book3 = create_test_orderbook("AAPL", 3);
        let book1 = create_test_orderbook("AAPL", 1);
        let book2 = create_test_orderbook("AAPL", 2);

        manager.update(book1);
        manager.update(book3);
        manager.update(book2);

        let retrieved = manager.get("AAPL").unwrap();
        // Should have the last update (sequence 2)
        assert_eq!(retrieved.sequence, 2);
    }

    #[test]
    fn test_concurrent_updates() {
        let mut manager = OrderBookManager::new();

        // Simulate rapid updates
        for i in 0..100 {
            let book = create_test_orderbook("AAPL", i);
            manager.update(book);
        }

        let retrieved = manager.get("AAPL").unwrap();
        assert_eq!(retrieved.sequence, 99);
    }

    #[test]
    fn test_orderbook_levels_quantities() {
        let mut manager = OrderBookManager::new();
        let book = create_test_orderbook("AAPL", 1);

        manager.update(book);

        let retrieved = manager.get("AAPL").unwrap();

        // Check bid quantities
        assert_eq!(retrieved.bids[0].quantity, Quantity(10.0));
        assert_eq!(retrieved.bids[1].quantity, Quantity(20.0));

        // Check ask quantities
        assert_eq!(retrieved.asks[0].quantity, Quantity(15.0));
        assert_eq!(retrieved.asks[1].quantity, Quantity(25.0));
    }

    #[test]
    fn test_orderbook_timestamp() {
        let mut manager = OrderBookManager::new();
        let now = Utc::now();

        let book = OrderBook {
            symbol: Symbol("AAPL".to_string()),
            bids: vec![],
            asks: vec![],
            timestamp: now,
            sequence: 1,
        };

        manager.update(book);

        let retrieved = manager.get("AAPL").unwrap();
        assert_eq!(retrieved.timestamp, now);
    }
}

#[cfg(test)]
mod orderbook_performance_tests {
    use super::*;

    #[test]
    fn test_large_number_of_symbols() {
        let mut manager = OrderBookManager::new();

        // Add 1000 symbols
        for i in 0..1000 {
            let symbol = format!("SYM{}", i);
            let book = create_test_orderbook(&symbol, 1);
            manager.update(book);
        }

        // Verify all symbols are present
        for i in 0..1000 {
            let symbol = format!("SYM{}", i);
            assert!(manager.get(&symbol).is_some());
        }
    }

    #[test]
    fn test_deep_orderbook() {
        let mut manager = OrderBookManager::new();

        let mut bids = Vec::new();
        let mut asks = Vec::new();

        // Create 100 levels each side
        for i in 0..100 {
            bids.push(Level {
                price: Price(100.0 - i as f64 * 0.1),
                quantity: Quantity((i + 1) as f64),
                timestamp: Utc::now(),
            });
            asks.push(Level {
                price: Price(100.5 + i as f64 * 0.1),
                quantity: Quantity((i + 1) as f64),
                timestamp: Utc::now(),
            });
        }

        let deep_book = OrderBook {
            symbol: Symbol("AAPL".to_string()),
            bids,
            asks,
            timestamp: Utc::now(),
            sequence: 1,
        };

        manager.update(deep_book);

        let retrieved = manager.get("AAPL").unwrap();
        assert_eq!(retrieved.bids.len(), 100);
        assert_eq!(retrieved.asks.len(), 100);
    }
}
