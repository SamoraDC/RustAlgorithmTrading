// Comprehensive tests for order book functionality
use market_data::orderbook::{FastOrderBook, OrderBookManager};
use common::types::{Price, Quantity, Symbol};

#[cfg(test)]
mod fast_orderbook_tests {
    use super::*;

    #[test]
    fn test_new_orderbook() {
        let book = FastOrderBook::new(Symbol("AAPL".to_string()));
        assert!(book.best_bid().is_none());
        assert!(book.best_ask().is_none());
        assert!(book.mid_price().is_none());
    }

    #[test]
    fn test_update_bid() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        book.update_bid(Price(150.0), Quantity(100.0));

        assert_eq!(book.best_bid(), Some(Price(150.0)));
    }

    #[test]
    fn test_update_ask() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        book.update_ask(Price(150.5), Quantity(50.0));

        assert_eq!(book.best_ask(), Some(Price(150.5)));
    }

    #[test]
    fn test_best_bid_is_highest() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_bid(Price(149.5), Quantity(200.0));
        book.update_bid(Price(150.5), Quantity(50.0)); // Highest

        assert_eq!(book.best_bid(), Some(Price(150.5)));
    }

    #[test]
    fn test_best_ask_is_lowest() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_ask(Price(151.0), Quantity(100.0));
        book.update_ask(Price(150.5), Quantity(50.0)); // Lowest
        book.update_ask(Price(151.5), Quantity(75.0));

        assert_eq!(book.best_ask(), Some(Price(150.5)));
    }

    #[test]
    fn test_mid_price_calculation() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_ask(Price(151.0), Quantity(100.0));

        let mid = book.mid_price().unwrap();
        assert_eq!(mid.0, 150.5);
    }

    #[test]
    fn test_spread_bps() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(100.0), Quantity(100.0));
        book.update_ask(Price(100.1), Quantity(100.0));

        let spread = book.spread_bps().unwrap();
        // Spread = (100.1 - 100.0) / 100.05 * 10000 ≈ 99.95 bps
        assert!((spread - 99.95).abs() < 1.0);
    }

    #[test]
    fn test_remove_level_with_zero_quantity() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        assert_eq!(book.best_bid(), Some(Price(150.0)));

        // Remove by setting quantity to 0
        book.update_bid(Price(150.0), Quantity(0.0));
        assert!(book.best_bid().is_none());
    }

    #[test]
    fn test_depth_calculation() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_bid(Price(149.5), Quantity(200.0));
        book.update_bid(Price(149.0), Quantity(300.0));

        book.update_ask(Price(150.5), Quantity(150.0));
        book.update_ask(Price(151.0), Quantity(100.0));

        let (bid_depth, ask_depth) = book.depth(2);
        assert_eq!(bid_depth, 300.0); // Top 2 levels: 100 + 200
        assert_eq!(ask_depth, 250.0); // Top 2 levels: 150 + 100
    }

    #[test]
    fn test_imbalance_more_bids() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(300.0));
        book.update_ask(Price(150.5), Quantity(100.0));

        let imbalance = book.imbalance(1);
        // (300 - 100) / (300 + 100) = 200 / 400 = 0.5
        assert!((imbalance - 0.5).abs() < 0.01);
    }

    #[test]
    fn test_imbalance_more_asks() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_ask(Price(150.5), Quantity(300.0));

        let imbalance = book.imbalance(1);
        // (100 - 300) / (100 + 300) = -200 / 400 = -0.5
        assert!((imbalance - (-0.5)).abs() < 0.01);
    }

    #[test]
    fn test_imbalance_balanced() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(200.0));
        book.update_ask(Price(150.5), Quantity(200.0));

        let imbalance = book.imbalance(1);
        assert!(imbalance.abs() < 0.01); // Should be close to 0
    }

    #[test]
    fn test_snapshot_conversion() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_bid(Price(149.5), Quantity(200.0));
        book.update_ask(Price(150.5), Quantity(150.0));
        book.update_ask(Price(151.0), Quantity(100.0));

        let snapshot = book.to_snapshot(10);

        assert_eq!(snapshot.symbol.0, "AAPL");
        assert_eq!(snapshot.bids.len(), 2);
        assert_eq!(snapshot.asks.len(), 2);
    }

    #[test]
    fn test_snapshot_max_levels() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        // Add 5 bid levels
        for i in 0..5 {
            book.update_bid(Price(150.0 - i as f64 * 0.5), Quantity(100.0));
        }

        // Request only top 3 levels
        let snapshot = book.to_snapshot(3);

        assert_eq!(snapshot.bids.len(), 3);
    }

    #[test]
    fn test_update_latency_tracking() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));

        let latency = book.last_update_latency_ns();
        assert!(latency > 0);
        assert!(latency < 1_000_000); // Should be less than 1ms
    }

    #[test]
    fn test_multiple_updates_same_price() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_bid(Price(150.0), Quantity(200.0)); // Update same price

        assert_eq!(book.best_bid(), Some(Price(150.0)));
    }

    #[test]
    fn test_alternating_updates() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        for i in 0..100 {
            if i % 2 == 0 {
                book.update_bid(Price(150.0 + i as f64 * 0.01), Quantity(100.0));
            } else {
                book.update_ask(Price(151.0 + i as f64 * 0.01), Quantity(100.0));
            }
        }

        assert!(book.best_bid().is_some());
        assert!(book.best_ask().is_some());
    }

    #[test]
    fn test_empty_orderbook_spread() {
        let book = FastOrderBook::new(Symbol("AAPL".to_string()));
        assert!(book.spread_bps().is_none());
    }

    #[test]
    fn test_only_bids_no_spread() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        book.update_bid(Price(150.0), Quantity(100.0));

        assert!(book.spread_bps().is_none());
    }

    #[test]
    fn test_only_asks_no_spread() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));
        book.update_ask(Price(150.5), Quantity(100.0));

        assert!(book.spread_bps().is_none());
    }
}

#[cfg(test)]
mod orderbook_manager_tests {
    use super::*;

    #[test]
    fn test_manager_creation() {
        let manager = OrderBookManager::new();
        assert!(manager.get("AAPL").is_none());
    }

    #[test]
    fn test_get_or_create() {
        let mut manager = OrderBookManager::new();

        let _book = manager.get_or_create("AAPL");
        assert!(manager.get("AAPL").is_some());
    }

    #[test]
    fn test_update_bid_via_manager() {
        let mut manager = OrderBookManager::new();

        manager.update_bid("AAPL", Price(150.0), Quantity(100.0));

        let book = manager.get("AAPL").unwrap();
        assert_eq!(book.best_bid(), Some(Price(150.0)));
    }

    #[test]
    fn test_update_ask_via_manager() {
        let mut manager = OrderBookManager::new();

        manager.update_ask("AAPL", Price(150.5), Quantity(50.0));

        let book = manager.get("AAPL").unwrap();
        assert_eq!(book.best_ask(), Some(Price(150.5)));
    }

    #[test]
    fn test_get_snapshot_via_manager() {
        let mut manager = OrderBookManager::new();

        manager.update_bid("AAPL", Price(150.0), Quantity(100.0));
        manager.update_ask("AAPL", Price(150.5), Quantity(50.0));

        let snapshot = manager.get_snapshot("AAPL", 10);
        assert!(snapshot.is_some());

        let snapshot = snapshot.unwrap();
        assert_eq!(snapshot.symbol.0, "AAPL");
    }

    #[test]
    fn test_multiple_symbols() {
        let mut manager = OrderBookManager::new();

        manager.update_bid("AAPL", Price(150.0), Quantity(100.0));
        manager.update_bid("GOOGL", Price(2800.0), Quantity(10.0));
        manager.update_bid("MSFT", Price(350.0), Quantity(50.0));

        assert!(manager.get("AAPL").is_some());
        assert!(manager.get("GOOGL").is_some());
        assert!(manager.get("MSFT").is_some());
        assert!(manager.get("TSLA").is_none());
    }

    #[test]
    fn test_get_snapshot_nonexistent() {
        let manager = OrderBookManager::new();
        let snapshot = manager.get_snapshot("NONEXISTENT", 10);

        assert!(snapshot.is_none());
    }
}

#[cfg(test)]
mod performance_tests {
    use super::*;
    use std::time::Instant;

    #[test]
    fn test_update_performance() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        let start = Instant::now();

        for i in 0..1000 {
            let price = Price(150.0 + (i as f64 * 0.01));
            book.update_bid(price, Quantity(100.0));
        }

        let elapsed = start.elapsed();

        println!("1000 updates took: {:?}", elapsed);
        println!("Avg per update: {:?}", elapsed / 1000);

        // Should complete well under 50ms total (50μs per update * 1000)
        assert!(elapsed.as_millis() < 50);
    }

    #[test]
    fn test_mixed_operation_performance() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        let start = Instant::now();

        for i in 0..500 {
            let price_bid = Price(150.0 - (i as f64 * 0.01));
            let price_ask = Price(150.5 + (i as f64 * 0.01));

            book.update_bid(price_bid, Quantity(100.0));
            book.update_ask(price_ask, Quantity(50.0));

            // Query operations
            let _ = book.best_bid();
            let _ = book.best_ask();
            let _ = book.mid_price();
            let _ = book.spread_bps();
        }

        let elapsed = start.elapsed();

        println!("500 mixed operations took: {:?}", elapsed);

        // Should complete in reasonable time
        assert!(elapsed.as_millis() < 100);
    }

    #[test]
    fn test_large_orderbook_performance() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        // Build large order book
        for i in 0..10000 {
            let bid_price = Price(150.0 - (i as f64 * 0.001));
            let ask_price = Price(150.5 + (i as f64 * 0.001));

            book.update_bid(bid_price, Quantity(100.0));
            book.update_ask(ask_price, Quantity(100.0));
        }

        // Test query performance on large book
        let start = Instant::now();

        for _ in 0..1000 {
            let _ = book.depth(100);
            let _ = book.imbalance(50);
        }

        let elapsed = start.elapsed();

        println!("1000 queries on large book took: {:?}", elapsed);
        assert!(elapsed.as_millis() < 100);
    }
}

#[cfg(test)]
mod edge_case_tests {
    use super::*;

    #[test]
    fn test_zero_quantity_updates() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        book.update_bid(Price(150.0), Quantity(100.0));
        book.update_bid(Price(150.0), Quantity(0.0)); // Remove

        assert!(book.best_bid().is_none());
    }

    #[test]
    fn test_very_small_prices() {
        let mut book = FastOrderBook::new(Symbol("CRYPTO".to_string()));

        book.update_bid(Price(0.00001), Quantity(1000000.0));
        book.update_ask(Price(0.00002), Quantity(500000.0));

        assert_eq!(book.best_bid(), Some(Price(0.00001)));
        assert_eq!(book.best_ask(), Some(Price(0.00002)));
    }

    #[test]
    fn test_very_large_prices() {
        let mut book = FastOrderBook::new(Symbol("BRK.A".to_string()));

        book.update_bid(Price(500000.0), Quantity(1.0));
        book.update_ask(Price(501000.0), Quantity(1.0));

        assert_eq!(book.best_bid(), Some(Price(500000.0)));
    }

    #[test]
    fn test_rapid_updates_same_level() {
        let mut book = FastOrderBook::new(Symbol("AAPL".to_string()));

        for i in 0..100 {
            book.update_bid(Price(150.0), Quantity((i * 10) as f64));
        }

        assert_eq!(book.best_bid(), Some(Price(150.0)));
    }
}
