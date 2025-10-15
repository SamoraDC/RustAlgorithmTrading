use common::types::{Position, Price, Quantity, Side, Symbol, Trade};
use chrono::Utc;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct PositionState {
    pub quantity: Quantity,
    pub avg_entry_price: Price,
    pub side: Side,
    pub realized_pnl: f64,
    pub total_cost: f64,
}

pub struct PnLTracker {
    positions: HashMap<String, PositionState>,
    total_realized_pnl: f64,
    daily_pnl: f64,
    trade_count: u64,
}

impl PnLTracker {
    pub fn new() -> Self {
        Self {
            positions: HashMap::new(),
            total_realized_pnl: 0.0,
            daily_pnl: 0.0,
            trade_count: 0,
        }
    }

    /// Update position with a new trade
    pub fn update_with_trade(&mut self, symbol: &str, trade: &Trade) {
        let position = self.positions.entry(symbol.to_string()).or_insert_with(|| {
            PositionState {
                quantity: Quantity(0.0),
                avg_entry_price: Price(0.0),
                side: trade.side,
                realized_pnl: 0.0,
                total_cost: 0.0,
            }
        });

        let trade_value = trade.price.0 * trade.quantity.0;

        match trade.side {
            Side::Bid => {
                // Buy
                position.total_cost += trade_value;
                position.quantity = Quantity(position.quantity.0 + trade.quantity.0);

                if position.quantity.0 > 0.0 {
                    position.avg_entry_price = Price(position.total_cost / position.quantity.0);
                }
                position.side = Side::Bid;
            }
            Side::Ask => {
                // Sell
                if position.quantity.0 >= trade.quantity.0 {
                    // Full or partial close
                    let pnl = (trade.price.0 - position.avg_entry_price.0) * trade.quantity.0;
                    position.realized_pnl += pnl;
                    self.total_realized_pnl += pnl;
                    self.daily_pnl += pnl;

                    position.quantity = Quantity(position.quantity.0 - trade.quantity.0);
                    position.total_cost -= position.avg_entry_price.0 * trade.quantity.0;

                    if position.quantity.0 == 0.0 {
                        // Position fully closed
                        self.positions.remove(symbol);
                    }
                } else {
                    // Reversing position (short)
                    let close_qty = position.quantity.0;
                    let pnl = (trade.price.0 - position.avg_entry_price.0) * close_qty;
                    position.realized_pnl += pnl;
                    self.total_realized_pnl += pnl;
                    self.daily_pnl += pnl;

                    let remaining_qty = trade.quantity.0 - close_qty;
                    position.quantity = Quantity(remaining_qty);
                    position.avg_entry_price = trade.price;
                    position.total_cost = trade.price.0 * remaining_qty;
                    position.side = Side::Ask;
                }
            }
        }

        self.trade_count += 1;
    }

    /// Calculate unrealized P&L for a position
    pub fn calculate_unrealized_pnl(&self, symbol: &str, current_price: Price) -> f64 {
        if let Some(position) = self.positions.get(symbol) {
            let price_diff = current_price.0 - position.avg_entry_price.0;
            let multiplier = match position.side {
                Side::Bid => 1.0,   // Long position
                Side::Ask => -1.0,  // Short position
            };
            price_diff * position.quantity.0 * multiplier
        } else {
            0.0
        }
    }

    /// Get total unrealized P&L across all positions
    pub fn get_unrealized_pnl(&self, current_prices: &HashMap<String, Price>) -> f64 {
        self.positions
            .iter()
            .map(|(symbol, _)| {
                current_prices
                    .get(symbol)
                    .map(|&price| self.calculate_unrealized_pnl(symbol, price))
                    .unwrap_or(0.0)
            })
            .sum()
    }

    /// Get total P&L (realized + unrealized)
    pub fn get_total_pnl(&self, current_prices: &HashMap<String, Price>) -> f64 {
        self.total_realized_pnl + self.get_unrealized_pnl(current_prices)
    }

    /// Convert internal state to Position for compatibility
    pub fn to_position(&self, symbol: &str, current_price: Price) -> Option<Position> {
        self.positions.get(symbol).map(|state| Position {
            symbol: Symbol(symbol.to_string()),
            side: state.side,
            quantity: state.quantity,
            entry_price: state.avg_entry_price,
            current_price,
            unrealized_pnl: self.calculate_unrealized_pnl(symbol, current_price),
            realized_pnl: state.realized_pnl,
            opened_at: Utc::now(),
            updated_at: Utc::now(),
        })
    }

    /// Get daily P&L
    pub fn get_daily_pnl(&self) -> f64 {
        self.daily_pnl
    }

    /// Reset daily P&L
    pub fn reset_daily_pnl(&mut self) {
        self.daily_pnl = 0.0;
    }

    /// Get position state
    pub fn get_position(&self, symbol: &str) -> Option<&PositionState> {
        self.positions.get(symbol)
    }

    /// Get all positions
    pub fn get_all_positions(&self) -> &HashMap<String, PositionState> {
        &self.positions
    }

    /// Get total realized P&L
    pub fn get_realized_pnl(&self) -> f64 {
        self.total_realized_pnl
    }

    /// Get trade count
    pub fn get_trade_count(&self) -> u64 {
        self.trade_count
    }

    /// Update position directly (for compatibility)
    pub fn update(&mut self, position: &Position) {
        let state = PositionState {
            quantity: position.quantity,
            avg_entry_price: position.entry_price,
            side: position.side,
            realized_pnl: position.realized_pnl,
            total_cost: position.entry_price.0 * position.quantity.0,
        };

        if position.quantity.0 == 0.0 {
            self.positions.remove(&position.symbol.0);
        } else {
            self.positions.insert(position.symbol.0.clone(), state);
        }
    }
}

impl Default for PnLTracker {
    fn default() -> Self {
        Self::new()
    }
}
