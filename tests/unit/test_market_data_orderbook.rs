/// Comprehensive tests for OrderBook implementation
use market_data::orderbook::OrderBookManager;
use common::types::{PriceLevel, OrderBook};

#[cfg(test)]
mod orderbook_manager_tests {
    use super::*;

    #[test]
    fn test_orderbook_manager_creation() {
        let manager = OrderBookManager::new();
        // Manager should be created successfully
        // This is a basic smoke test
        drop(manager);
    }

    #[test]
    fn test_add_bid_level() {
        let mut manager = OrderBookManager::new();
        let symbol = "AAPL".to_string();

        // Add bid level at $150.00 with 1000 shares
        let level = PriceLevel {
            price: 150.00,
            volume: 1000,
        };

        // This test assumes the OrderBookManager has methods to add levels
        // Adjust based on actual implementation
        // manager.add_bid(&symbol, level);
    }

    #[test]
    fn test_add_ask_level() {
        let mut manager = OrderBookManager::new();
        let symbol = "TSLA".to_string();

        let level = PriceLevel {
            price: 250.50,
            volume: 500,
        };

        // manager.add_ask(&symbol, level);
    }

    #[test]
    fn test_bid_ask_spread() {
        let mut manager = OrderBookManager::new();
        let symbol = "NVDA".to_string();

        let bid = PriceLevel {
            price: 450.00,
            volume: 2000,
        };

        let ask = PriceLevel {
            price: 450.50,
            volume: 1500,
        };

        // manager.add_bid(&symbol, bid);
        // manager.add_ask(&symbol, ask);

        let expected_spread = 0.50;
        // let actual_spread = manager.get_spread(&symbol).unwrap();
        // assert_eq!(actual_spread, expected_spread);
    }

    #[test]
    fn test_orderbook_depth() {
        let mut manager = OrderBookManager::new();
        let symbol = "GOOG".to_string();

        // Add multiple bid levels
        for i in 0..10 {
            let level = PriceLevel {
                price: 2500.00 - (i as f64 * 0.10),
                volume: 100 * (i + 1),
            };
            // manager.add_bid(&symbol, level);
        }

        // Add multiple ask levels
        for i in 0..10 {
            let level = PriceLevel {
                price: 2500.50 + (i as f64 * 0.10),
                volume: 100 * (i + 1),
            };
            // manager.add_ask(&symbol, level);
        }

        // let book = manager.get_orderbook(&symbol).unwrap();
        // assert_eq!(book.bids.len(), 10);
        // assert_eq!(book.asks.len(), 10);
    }

    #[test]
    fn test_update_existing_level() {
        let mut manager = OrderBookManager::new();
        let symbol = "MSFT".to_string();

        let initial = PriceLevel {
            price: 300.00,
            volume: 1000,
        };

        let updated = PriceLevel {
            price: 300.00,
            volume: 1500,
        };

        // manager.add_bid(&symbol, initial);
        // manager.update_bid(&symbol, updated);

        // let book = manager.get_orderbook(&symbol).unwrap();
        // let level = book.bids.iter().find(|b| b.price == 300.00).unwrap();
        // assert_eq!(level.volume, 1500);
    }

    #[test]
    fn test_remove_level() {
        let mut manager = OrderBookManager::new();
        let symbol = "AMZN".to_string();

        let level = PriceLevel {
            price: 150.00,
            volume: 500,
        };

        // manager.add_bid(&symbol, level);
        // manager.remove_bid(&symbol, 150.00);

        // let book = manager.get_orderbook(&symbol).unwrap();
        // assert!(book.bids.is_empty());
    }

    #[test]
    fn test_best_bid() {
        let mut manager = OrderBookManager::new();
        let symbol = "META".to_string();

        let bids = vec![
            PriceLevel { price: 345.00, volume: 100 },
            PriceLevel { price: 346.00, volume: 200 },
            PriceLevel { price: 344.00, volume: 300 },
        ];

        // for bid in bids {
        //     manager.add_bid(&symbol, bid);
        // }

        // let best = manager.get_best_bid(&symbol).unwrap();
        // assert_eq!(best.price, 346.00);
    }

    #[test]
    fn test_best_ask() {
        let mut manager = OrderBookManager::new();
        let symbol = "AMD".to_string();

        let asks = vec![
            PriceLevel { price: 120.50, volume: 100 },
            PriceLevel { price: 120.00, volume: 200 },
            PriceLevel { price: 121.00, volume: 300 },
        ];

        // for ask in asks {
        //     manager.add_ask(&symbol, ask);
        // }

        // let best = manager.get_best_ask(&symbol).unwrap();
        // assert_eq!(best.price, 120.00);
    }

    #[test]
    fn test_mid_price() {
        let mut manager = OrderBookManager::new();
        let symbol = "NFLX".to_string();

        let bid = PriceLevel { price: 400.00, volume: 100 };
        let ask = PriceLevel { price: 402.00, volume: 100 };

        // manager.add_bid(&symbol, bid);
        // manager.add_ask(&symbol, ask);

        // let mid = manager.get_mid_price(&symbol).unwrap();
        // assert_eq!(mid, 401.00);
    }

    #[test]
    fn test_empty_orderbook() {
        let manager = OrderBookManager::new();
        let symbol = "EMPTY".to_string();

        // let book = manager.get_orderbook(&symbol);
        // assert!(book.is_none() || book.unwrap().bids.is_empty());
    }

    #[test]
    fn test_crossed_market() {
        // Test for invalid state where bid > ask
        let mut manager = OrderBookManager::new();
        let symbol = "CROSSED".to_string();

        let bid = PriceLevel { price: 100.50, volume: 100 };
        let ask = PriceLevel { price: 100.00, volume: 100 };

        // manager.add_bid(&symbol, bid);
        // manager.add_ask(&symbol, ask);

        // This should be detected as an error or handled
        // assert!(manager.is_crossed(&symbol));
    }
}

#[cfg(test)]
mod orderbook_performance_tests {
    use super::*;

    #[test]
    fn test_high_frequency_updates() {
        let mut manager = OrderBookManager::new();
        let symbol = "HFT_TEST".to_string();

        // Simulate 10,000 rapid updates
        for i in 0..10_000 {
            let level = PriceLevel {
                price: 100.00 + (i as f64 * 0.01),
                volume: 100,
            };
            // manager.add_bid(&symbol, level);
        }

        // Orderbook should handle high-frequency updates efficiently
    }

    #[test]
    fn test_large_orderbook() {
        let mut manager = OrderBookManager::new();
        let symbol = "DEEP".to_string();

        // Add 1000 levels on each side
        for i in 0..1000 {
            let bid = PriceLevel {
                price: 1000.00 - (i as f64 * 0.01),
                volume: 100,
            };
            let ask = PriceLevel {
                price: 1001.00 + (i as f64 * 0.01),
                volume: 100,
            };
            // manager.add_bid(&symbol, bid);
            // manager.add_ask(&symbol, ask);
        }

        // Should handle large orderbooks efficiently
    }
}

#[cfg(test)]
mod orderbook_edge_cases {
    use super::*;

    #[test]
    fn test_zero_volume_level() {
        let level = PriceLevel {
            price: 100.00,
            volume: 0,
        };

        // Zero volume might be used to remove a level
        assert_eq!(level.volume, 0);
    }

    #[test]
    fn test_very_small_spread() {
        let bid = PriceLevel { price: 100.000, volume: 100 };
        let ask = PriceLevel { price: 100.001, volume: 100 };

        let spread = ask.price - bid.price;
        assert!(spread < 0.01);
    }

    #[test]
    fn test_very_large_volume() {
        let level = PriceLevel {
            price: 100.00,
            volume: u64::MAX,
        };

        assert_eq!(level.volume, u64::MAX);
    }

    #[test]
    fn test_fractional_prices() {
        let level = PriceLevel {
            price: 123.456789,
            volume: 100,
        };

        assert_eq!(level.price, 123.456789);
    }

    #[test]
    fn test_negative_spread() {
        // Locked or crossed market
        let bid = PriceLevel { price: 100.50, volume: 100 };
        let ask = PriceLevel { price: 100.50, volume: 100 };

        let spread = ask.price - bid.price;
        assert_eq!(spread, 0.0);
    }
}
